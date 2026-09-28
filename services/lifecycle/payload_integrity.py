# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exact packaged-file inventory for independent installation inspection.

The caller supplies release/inventory bytes from its verified artifact and holds
maintenance admission. Hashes bind bytes; they do not establish publisher trust.
Inspection never imports installed code, follows redirects, removes extra files
or repairs an installation. Windows adopts this shared format first.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

SCHEMA = 'augmentor-payload/1'
INVENTORY = 'payload-integrity.json'
METADATA = 'release.json'
MAX_ENTRIES = 250000
MAX_INVENTORY = 64*1024**2
MAX_PAYLOAD = 32*1024**3


def _object(pairs):
    result = {}
    for key,value in pairs:
        if key in result: raise ValueError('Duplicate payload metadata field.')
        result[key] = value
    return result


def _json(raw,limit):
    if not isinstance(raw,bytes) or not 0 < len(raw) <= limit:
        raise ValueError('Payload metadata exceeds its supported size.')
    try: return json.loads(raw.decode('utf-8'),object_pairs_hook=_object)
    except (UnicodeError,ValueError,RecursionError):
        raise ValueError('Invalid payload metadata.') from None


def _name(value):
    if not isinstance(value,str) or not value or len(value)>32700:
        raise ValueError('Invalid payload path.')
    parts=value.split('/')
    if len(parts)>128 or any(not part or part in ('.','..') or part.endswith((' ','.')) or
            any(ord(c)<32 or c in '<>:"\\|?*' for c in part) or
            re.fullmatch(r'(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?',part,re.IGNORECASE)
            for part in parts):
        raise ValueError('Unsafe or nonportable payload path.')
    try:value.encode('utf-8')
    except UnicodeError:raise ValueError('Invalid payload path encoding.') from None
    return value


def _plain(info, *, directory=False):
    if (getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400) or
            not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)) or
            (not directory and info.st_nlink!=1)):
        raise ValueError('Payload contains a reparse/link or nonordinary entry.')


def _root(root):
    root=Path(root).absolute()
    for parent in (*reversed(root.parents),root): _plain(parent.lstat(),directory=True)
    return root


def _scan(root, *, allow_missing=False):
    """Bound traversal, including empty directories, before hashing any file."""
    root=Path(root).absolute()
    _root(root.parent)
    try:_plain(root.lstat(),directory=True)
    except FileNotFoundError:
        # Only a genuinely absent final directory can represent a lost payload.
        # A missing/redirected ancestor, denied access or non-directory refuses.
        if allow_missing:return root,{},[]
        raise
    files={};directories=[];names=set();total=0
    pending=[root]
    while pending:
        directory=pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                name=_name(Path(entry.path).relative_to(root).as_posix())
                if name.casefold() in names:raise ValueError('Payload paths collide on Windows.')
                names.add(name.casefold())
                if len(names)>MAX_ENTRIES:raise ValueError('Payload contains too many entries.')
                # Windows DirEntry.stat caches FindFirstFile fields and reports
                # st_ino/st_dev/st_nlink as zero. Use the full no-follow stat for
                # file identity and hard-link checks on every platform.
                info=os.stat(entry.path,follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    _plain(info,directory=True);directories.append(name);pending.append(Path(entry.path))
                else:
                    _plain(info)
                    total+=info.st_size
                    if total>MAX_PAYLOAD:raise ValueError('Payload exceeds its supported size.')
                    files[name]=info
    return root,files,sorted(directories)


def _identity(info):
    # CPython 3.13 Windows path stat preserves legacy ctime=birth time,
    # whereas fstat exposes the actual change time. Compare birth time across
    # those APIs; retain change-time checks between handle observations below.
    timestamp=info.st_birthtime_ns if os.name=='nt' else info.st_ctime_ns
    return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,timestamp)


def _digest(path,expected):
    # Admission excludes cooperating writers. Reject a changed scan/open/read
    # identity; this is not a sandbox against a hostile same-user administrator.
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0))
    with os.fdopen(fd,'rb') as source:
        before=os.fstat(source.fileno());_plain(before)
        if _identity(before)!=_identity(expected):raise ValueError('Payload changed during inspection.')
        digest=hashlib.file_digest(source,'sha256').hexdigest()
        after=os.fstat(source.fileno());_plain(after)
        if _identity(after)!=_identity(before) or after.st_ctime_ns!=before.st_ctime_ns:
            raise ValueError('Payload changed during inspection.')
        return digest


def _read(path,limit):
    info=path.lstat();_plain(info)
    if not 0 < info.st_size <= limit:raise ValueError('Payload metadata exceeds its supported size.')
    with path.open('rb') as stream:raw=stream.read(limit+1)
    if len(raw)!=info.st_size:raise ValueError('Payload metadata changed during inspection.')
    return raw


def seal_payload(root):
    """Build-only final step after launcher compilation; never reseal installed code."""
    root,files,directories=_scan(root)
    if INVENTORY in files or INVENTORY in directories:
        raise ValueError('Use an unsealed build tree, never reseal a selected installation.')
    release=_json(_read(root/METADATA,65536),65536)
    if not isinstance(release,dict) or 'payloadSHA256' in release:
        raise ValueError('Use fresh release metadata for payload sealing.')
    content={name:{'bytes':info.st_size,'sha256':_digest(root/name,info)}
        for name,info in sorted(files.items()) if name!=METADATA}
    inventory={'schema':SCHEMA,'files':content,'directories':directories,
        'totalBytes':sum(row['bytes'] for row in content.values())}
    raw=(json.dumps(inventory,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8')
    if len(raw)>MAX_INVENTORY:raise ValueError('Payload inventory exceeds its supported size.')
    release['payloadSHA256']=hashlib.sha256(raw).hexdigest()
    metadata=(json.dumps(release,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if len(metadata)>65536:raise ValueError('Release metadata exceeds its supported size.')
    validate_inventory(metadata,raw)
    with (root/INVENTORY).open('xb') as stream:stream.write(raw)
    (root/METADATA).write_bytes(metadata)
    return release


def validate_inventory(release_bytes,inventory_bytes):
    release=_json(release_bytes,65536)
    if (not isinstance(release,dict) or not isinstance(release.get('payloadSHA256'),str) or
            not re.fullmatch('[a-f0-9]{64}',release['payloadSHA256'])):
        raise ValueError('Verified release metadata must bind its payload inventory.')
    if not isinstance(inventory_bytes,bytes) or not 0<len(inventory_bytes)<=MAX_INVENTORY:
        raise ValueError('Payload inventory exceeds its supported size.')
    if hashlib.sha256(inventory_bytes).hexdigest()!=release['payloadSHA256']:
        raise ValueError('Payload inventory differs from the independently identified release.')
    inventory=_json(inventory_bytes,MAX_INVENTORY)
    if (not isinstance(inventory,dict) or set(inventory)!={'schema','files','directories','totalBytes'} or
            inventory['schema']!=SCHEMA or not isinstance(inventory['files'],dict) or
            not isinstance(inventory['directories'],list) or type(inventory['totalBytes']) is not int or
            not 0<=inventory['totalBytes']<=MAX_PAYLOAD or
            len(inventory['files'])+len(inventory['directories'])+2>MAX_ENTRIES):
        raise ValueError('Invalid payload inventory.')
    files=inventory['files'];directories=inventory['directories'];names={}
    for name in [*files,*directories,METADATA,INVENTORY]:
        normalized=_name(name).casefold()
        if normalized in names:raise ValueError('Duplicate or colliding payload path.')
        names[normalized]=name
    directory_names=set(directories)
    for name in [*files,*directories]:
        parts=name.split('/')
        if any('/'.join(parts[:i]) not in directory_names for i in range(1,len(parts))):
            raise ValueError('Payload inventory omits a parent directory.')
    total=0
    for row in files.values():
        if (not isinstance(row,dict) or set(row)!={'bytes','sha256'} or
                type(row['bytes']) is not int or not 0<=row['bytes']<=MAX_PAYLOAD or
                not isinstance(row['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',row['sha256'])):
            raise ValueError('Invalid payload file identity.')
        total+=row['bytes']
    if total!=inventory['totalBytes']:raise ValueError('Payload inventory size does not match its files.')
    return inventory


def inspect_payload(root,release_bytes,inventory_bytes):
    """Compare every installed entry to independently supplied artifact metadata.

    Supplying both metadata files permits inspection when either installed copy
    is missing/corrupt. Returned differences never authorize deletion or apply.
    Reparse paths, aliases, unreadable files and changed observations raise.
    """
    expected=validate_inventory(release_bytes,inventory_bytes)
    root,actual,directories=_scan(root,allow_missing=True)
    files=dict(expected['files'])
    for name,raw in ((METADATA,release_bytes),(INVENTORY,inventory_bytes)):
        files[name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    missing=sorted(files.keys()-actual.keys());unexpected=sorted(actual.keys()-files.keys())
    changed=[]
    for name in sorted(actual.keys()&files.keys()):
        if actual[name].st_size!=files[name]['bytes'] or _digest(root/name,actual[name])!=files[name]['sha256']:
            changed.append(name)
    absent_directories=sorted(set(expected['directories'])-set(directories))
    extra_directories=sorted(set(directories)-set(expected['directories']))
    return {'complete':not any((missing,unexpected,changed,absent_directories,extra_directories)),
        'files':len(files),'bytes':expected['totalBytes']+len(release_bytes)+len(inventory_bytes),
        'missing':missing,'changed':changed,'unexpected':unexpected,
        'missingDirectories':absent_directories,'unexpectedDirectories':extra_directories}


def verify_payload(root,release_bytes):
    """Require an intact sealed payload; no publisher or health claim."""
    root=_root(root)
    result=inspect_payload(root,release_bytes,_read(root/INVENTORY,MAX_INVENTORY))
    if not result['complete']:
        raise ValueError('The payload is incomplete, changed or contains unexpected files.')
    return result
