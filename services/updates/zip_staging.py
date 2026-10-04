# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bounded shared ZIP inspection before any platform extracts release content."""
import os
from pathlib import PurePosixPath
import stat
import struct
import unicodedata
import zipfile

from lifecycle.payload_integrity import MAX_ENTRIES,MAX_INVENTORY,MAX_PAYLOAD
from .policy import MAX_ARTIFACT


def bounded_zip(stream):
    """Bound central-directory allocation before the standard parser runs."""
    length=os.fstat(stream.fileno()).st_size
    if not 22<=length<=MAX_ARTIFACT:raise ValueError('Unsupported release ZIP length.')
    stream.seek(max(0,length-65557));tail=stream.read(65557)
    index=tail.rfind(b'PK\x05\x06')
    if index<0 or len(tail)-index<22:raise ValueError('The release ZIP has no bounded end record.')
    tag,disk,start_disk,on_disk,count,size,offset,comment=struct.unpack('<4s4H2IH',tail[index:index+22])
    end=length-len(tail)+index
    if disk or start_disk or comment or len(tail)-index!=22 or on_disk!=count:
        raise ValueError('Use a single-volume release ZIP without trailing data.')
    boundary=end;zip64=False
    locator=b''
    if end>=20:
        stream.seek(end-20);locator=stream.read(20)
    if locator.startswith(b'PK\x06\x07'):
        marker,number,position,disks=struct.unpack('<4sIQI',locator)
        if marker!=b'PK\x06\x07' or number or disks!=1 or not 0<=position<=end-76:
            raise ValueError('Unsupported ZIP64 volume locator.')
        stream.seek(position);raw=stream.read(56)
        marker,record_size,made,needed,disk,start_disk,on_disk,count,size,offset=struct.unpack('<4sQ2H2I4Q',raw)
        if (marker!=b'PK\x06\x06' or record_size!=44 or position+56!=end-20
                or disk or start_disk or on_disk!=count):raise ValueError('Unsupported ZIP64 end record.')
        boundary=position
        zip64=True
    elif size==0xffffffff or offset==0xffffffff:
        raise ValueError('A ZIP64 directory requires its complete locator.')
    if not 0<=count<=MAX_ENTRIES or not 0<size<=MAX_INVENTORY or offset+size!=boundary:
        raise ValueError('The release ZIP directory exceeds its supported boundary.')
    # Some native writers wrap the 16-bit entry counter instead of supplying
    # ZIP64 for a large number of small files. Count actual central records
    # before ZipFile allocates them; size alone is an insufficient entry bound.
    stream.seek(offset);actual=0
    while stream.tell()<boundary:
        raw=stream.read(46)
        if len(raw)!=46:raise ValueError('Truncated ZIP central header.')
        fields=struct.unpack('<4s6H3I5H2I',raw)
        if fields[0]!=b'PK\x01\x02' or fields[13] or not 0<fields[10]<=32768:
            raise ValueError('Unsupported ZIP central record.')
        following=stream.tell()+sum(fields[10:13])
        if following>boundary:raise ValueError('The ZIP central record exceeds its directory.')
        stream.seek(following);actual+=1
        if actual>MAX_ENTRIES:raise ValueError('The ZIP contains too many entries before parsing.')
    if (not actual or stream.tell()!=boundary or
            count!=actual and not (not zip64 and actual>65535 and count==(actual&65535))):
        raise ValueError('The actual ZIP record count differs from its bounded end record ('+str(actual)+' versus '+str(count)+').')
    stream.seek(0)
    bundle=zipfile.ZipFile(stream)
    if len(bundle.infolist())!=actual:bundle.close();raise ValueError('The release ZIP parser differs from its verified central records.')
    bundle.augmentor_directory={'entries':actual,'endCounter':count,'zip64':zip64,
        'wrapped16':not zip64 and count!=actual}
    return bundle


def validate_zip(stream,bundle_name):
    if bundle_name not in ('Augmentor Agent Desktop.app','Augmentor Agent Browser Companion.app','Augmentor Agent Desktop'):
        raise ValueError('Use a fixed product bundle name.')
    # Linux's pinned terminfo tree contains legitimate A/a directory names.
    # Keep Mac's case-insensitive collision policy; Linux extraction still
    # creates files exclusively and refuses aliases on the destination volume.
    def path_key(name):
        normalized=unicodedata.normalize('NFC',name)
        return normalized.casefold() if bundle_name.endswith('.app') else normalized
    seen=set();links=set();paths=[];total=0;payload=False
    with bounded_zip(stream) as bundle:
        directory=dict(bundle.augmentor_directory)
        for entry in bundle.infolist():
            if entry.orig_filename!=entry.filename:raise ValueError('The ZIP path contains a truncated character.')
            # ditto may use local names. Verify them against the bounded central
            # directory before extraction; a safe central name alone is weaker.
            with bundle.open(entry):pass
            name=entry.filename.rstrip('/');parts=name.split('/')
            if (not name or any(not part or part in ('.','..') or ':' in part or '\\' in part
                    or any(ord(c)<32 for c in part) for part in parts)):
                raise ValueError('The release ZIP contains an unsafe path.')
            folded=path_key(name)
            if folded in seen:raise ValueError('The release ZIP contains a duplicate or colliding path.')
            seen.add(folded)
            mode=entry.external_attr>>16;kind=stat.S_IFMT(mode)
            if entry.flag_bits&1 or entry.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED) or mode&0o6000:
                raise ValueError('Unsupported encrypted, privileged or compressed ZIP entry.')
            if kind not in (0,stat.S_IFREG,stat.S_IFDIR,stat.S_IFLNK):raise ValueError('The ZIP contains a nonordinary entry.')
            if parts[0]=='__MACOSX':
                if (not bundle_name.endswith('.app') or kind==stat.S_IFLNK or len(parts)>1 and parts[1] not in (bundle_name,'._'+bundle_name)):
                    raise ValueError('The resource sidecar belongs to another bundle.')
            elif parts[0]==bundle_name:
                payload=True;paths.append((folded,parts))
            else:raise ValueError('The ZIP contains data outside the expected bundle.')
            total+=entry.file_size
            if total>MAX_PAYLOAD:raise ValueError('The ZIP expands beyond its supported size.')
            if kind==stat.S_IFLNK:
                if not 0<entry.file_size<=4096:raise ValueError('Unsupported bundle link length.')
                target=bundle.read(entry).decode('utf-8')
                if not target or target.startswith('/') or '\\' in target or ':' in target or any(ord(c)<32 for c in target):
                    raise ValueError('The ZIP contains an external bundle link.')
                resolved=parts[1:-1].copy()
                for part in PurePosixPath(target).parts:
                    if part=='..':
                        if not resolved:raise ValueError('A bundle link escapes the bundle.')
                        resolved.pop()
                    elif part!='.':resolved.append(part)
                links.add(folded)
        if not payload:raise ValueError('The ZIP contains no product bundle.')
        for folded,parts in paths:
            if any(path_key('/'.join(parts[:index])) in links for index in range(1,len(parts))):
                raise ValueError('The ZIP writes through a symbolic link.')
    return {'entries':len(seen),'bytes':total,'bundle':bundle_name,'directory':directory}
