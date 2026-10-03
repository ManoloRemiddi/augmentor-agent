# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Stage exact retained Mac ZIP bytes without granting installation authority."""
import hashlib
import os
from pathlib import Path,PurePosixPath
import stat
import shutil
import struct
import subprocess
import sys
import unicodedata
import zipfile

from lifecycle.payload_integrity import MAX_ENTRIES,MAX_INVENTORY,MAX_PAYLOAD,_read,_json
from lifecycle.macos_payload import verify_bundle
from platform_adapters.private_files import descriptor,require_directory
from .policy import MAX_ARTIFACT,installed_identity


def bounded_zip(stream):
    """Bound central-directory allocation before the standard parser runs."""
    length=os.fstat(stream.fileno()).st_size
    if not 22<=length<=MAX_ARTIFACT:raise ValueError('Unsupported Mac release ZIP length.')
    stream.seek(max(0,length-65557));tail=stream.read(65557)
    index=tail.rfind(b'PK\x05\x06')
    if index<0 or len(tail)-index<22:raise ValueError('The release ZIP has no bounded end record.')
    tag,disk,start_disk,on_disk,count,size,offset,comment=struct.unpack('<4s4H2IH',tail[index:index+22])
    end=length-len(tail)+index
    if disk or start_disk or comment or len(tail)-index!=22 or on_disk!=count:
        raise ValueError('Use a single-volume release ZIP without trailing data.')
    boundary=end
    if count==65535 or size==0xffffffff or offset==0xffffffff:
        if end<20:raise ValueError('Invalid ZIP64 end locator.')
        stream.seek(end-20);locator=stream.read(20)
        marker,number,position,disks=struct.unpack('<4sIQI',locator)
        if marker!=b'PK\x06\x07' or number or disks!=1 or not 0<=position<=end-76:
            raise ValueError('Unsupported ZIP64 volume locator.')
        stream.seek(position);raw=stream.read(56)
        marker,record_size,made,needed,disk,start_disk,on_disk,count,size,offset=struct.unpack('<4sQ2H2I4Q',raw)
        if (marker!=b'PK\x06\x06' or record_size!=44 or position+56!=end-20
                or disk or start_disk or on_disk!=count):raise ValueError('Unsupported ZIP64 end record.')
        boundary=position
    if not 1<=count<=MAX_ENTRIES or not 0<size<=MAX_INVENTORY or offset+size!=boundary:
        raise ValueError('The Mac release ZIP directory exceeds its supported boundary.')
    stream.seek(0)
    bundle=zipfile.ZipFile(stream)
    if len(bundle.infolist())!=count:bundle.close();raise ValueError('The release ZIP entry count differs from its end record.')
    return bundle


def validate_zip(stream,bundle_name):
    if bundle_name not in ('Augmentor Agent Desktop.app','Augmentor Agent Browser Companion.app'):
        raise ValueError('Use a fixed product bundle name.')
    seen=set();links=set();paths=[];total=0;payload=False
    with bounded_zip(stream) as bundle:
        for entry in bundle.infolist():
            if entry.orig_filename!=entry.filename:raise ValueError('The ZIP path contains a truncated character.')
            # ditto may use local names. Verify them against the bounded central
            # directory before extraction; a safe central name alone is weaker.
            with bundle.open(entry):pass
            name=entry.filename.rstrip('/');parts=name.split('/')
            if (not name or any(not part or part in ('.','..') or ':' in part or '\\' in part
                    or any(ord(c)<32 for c in part) for part in parts)):
                raise ValueError('The release ZIP contains an unsafe path.')
            folded=unicodedata.normalize('NFC',name).casefold()
            if folded in seen:raise ValueError('The release ZIP contains a duplicate or colliding path.')
            seen.add(folded)
            mode=entry.external_attr>>16;kind=stat.S_IFMT(mode)
            if entry.flag_bits&1 or entry.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED) or mode&0o6000:
                raise ValueError('Unsupported encrypted, privileged or compressed ZIP entry.')
            if kind not in (0,stat.S_IFREG,stat.S_IFDIR,stat.S_IFLNK):raise ValueError('The ZIP contains a nonordinary entry.')
            if parts[0]=='__MACOSX':
                if (kind==stat.S_IFLNK or len(parts)>1 and parts[1] not in (bundle_name,'._'+bundle_name)):
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
            if any(unicodedata.normalize('NFC','/'.join(parts[:index])).casefold() in links for index in range(1,len(parts))):
                raise ValueError('The ZIP writes through a symbolic link.')
    return {'entries':len(seen),'bytes':total,'bundle':bundle_name}


def stage_download(held,directory,candidate,*,team,development=False):
    if sys.platform!='darwin':raise RuntimeError('Mac extraction requires native macOS.')
    directory=require_directory(Path(directory));item=held['artifact']
    if item['role']!='bundle' or item not in candidate['artifacts']:raise ValueError('Retain the exact publisher-verified bundle artifact.')
    archive=directory/'target.zip';fd=descriptor(archive,writable=True,exclusive=True)
    digest=hashlib.sha256();length=0
    os.lseek(held['fd'],0,os.SEEK_SET)
    with os.fdopen(fd,'wb') as target,os.fdopen(os.dup(held['fd']),'rb') as source:
        while chunk:=source.read(min(1024**2,item['bytes']-length+1)):
            length+=len(chunk)
            if length>item['bytes']:raise ValueError('The retained ZIP grew during staging.')
            digest.update(chunk);target.write(chunk)
        target.flush();os.fsync(target.fileno())
    os.lseek(held['fd'],0,os.SEEK_SET)
    if length!=item['bytes'] or digest.hexdigest()!=item['sha256']:
        raise ValueError('The staged ZIP differs from the original signed bytes.')
    name='Augmentor Agent Desktop.app' if candidate.get('component','desktop')=='desktop' else 'Augmentor Agent Browser Companion.app'
    with os.fdopen(descriptor(archive),'rb') as stream:report=validate_zip(stream,name)
    if shutil.disk_usage(directory).free<report['bytes']+64*1024**2:
        raise OSError('The destination volume has insufficient room for the verified expanded bundle.')
    subprocess.run(['/usr/bin/ditto','-x','-k',str(archive),str(directory)],check=True,
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=180)
    bundle=directory/name;project=bundle/'Contents/Resources/app'
    release=_read(project/'release.json',65536)
    if _json(release,65536).get('target')!=candidate['target']:
        raise ValueError('The actual packaged target differs from the publisher selection.')
    payload=verify_bundle(bundle,release,development=development,team=team)
    current=installed_identity(project,target=candidate['target'])
    keys=('version','build','sourceCommit','target','channel','component','protocols','dataSchema','readableDataSchemas','installType')
    if any(current[key]!=candidate.get(key,'desktop' if key=='component' else None) for key in keys):
        raise ValueError('The staged build differs from the original publisher-verified candidate.')
    if not development and (not current['automaticInstallQualified'] or not current['buildKnown']):
        raise ValueError('The staged build does not qualify automatic installation.')
    return bundle,release,payload
