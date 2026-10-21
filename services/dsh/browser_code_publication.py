# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Linux Browser code-slot exchange owned by a cold client publication.

Only an explicitly selected existing unpacked extension below deployment/browser
is eligible. Browser storage/profile data and immutable application roots are not
moved. The operator must first quiesce the real browser and every shared caller.
"""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from . import preservation_transaction as tx
from . import cold_backup as archives
from . import shared_data_adoption as data

SCHEMA='augmentor-browser-code-publication/1'
MAX_ENTRIES=2048
MAX_BYTES=32*1024**2
MAX_FILE=8*1024**2


def require(guard):
    data.require(guard)


def identity(path):
    info=Path(path).lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o7000:
        raise ValueError('Browser code must use owned ordinary directories, not links.')
    return [info.st_dev,info.st_ino]


def fingerprint(rows):
    return {'sha256':tx.preserve.sha(json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()),
            'entries':len(rows),'bytes':sum(r.get('bytes',0) for r in rows)}


def file_image(path):
    before=path.lstat()
    if (not stat.S_ISREG(before.st_mode) or before.st_uid!=os.getuid() or before.st_nlink!=1 or
            before.st_mode&0o7000 or before.st_size>MAX_FILE):
        raise ValueError('Browser code needs bounded single-link ordinary files.')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        if archives.stamp(os.fstat(fd))!=archives.stamp(before):raise ValueError('Browser code changed while opening.')
        digest=hashlib.sha256();size=0
        while chunk:=os.read(fd,1024**2):
            size+=len(chunk)
            if size>before.st_size or size>MAX_FILE:raise ValueError('Browser code grew while reading.')
            digest.update(chunk)
        if size!=before.st_size or archives.stamp(os.fstat(fd))!=archives.stamp(before) or archives.stamp(path.lstat())!=archives.stamp(before):
            raise ValueError('Browser code changed while reading.')
        return {'mode':stat.S_IMODE(before.st_mode),'bytes':size,'sha256':digest.hexdigest()}
    finally:os.close(fd)


def inventory(root):
    """Bound all files before copying; hashes include every ordinary mode."""
    root=Path(root);rows=[];total=0
    def visit(path,key):
        nonlocal total
        info=path.lstat()
        if (info.st_uid!=os.getuid() or info.st_mode&0o7000 or len(rows)>=MAX_ENTRIES or
                len(os.fsencode(key))>512):
            raise ValueError('Browser code ownership, modes, paths or entry bound changed.')
        if stat.S_ISDIR(info.st_mode):
            rows.append({'path':key,'kind':'directory','mode':stat.S_IMODE(info.st_mode)})
            for name in sorted(os.listdir(path)):
                if len(os.fsencode(name))>255:raise ValueError('Browser code filename is too long.')
                visit(path/name,key+'/'+name if key else name)
            if archives.stamp(path.lstat())!=archives.stamp(info):raise ValueError('Browser directory changed while reading.')
        elif stat.S_ISREG(info.st_mode):
            if info.st_nlink!=1 or info.st_size>MAX_FILE:raise ValueError('Browser code needs bounded single-link files.')
            value=file_image(path);total+=value['bytes']
            if total>MAX_BYTES:raise ValueError('Browser code exceeds its byte bound.')
            rows.append({'path':key,'kind':'file',**value})
        else:raise ValueError('Browser code cannot contain links, sockets or devices.')
    visit(root,'')
    return {**fingerprint(rows),'rows':rows}


def summary(value):return {k:value[k] for k in ('sha256','entries','bytes')}


def manifest(root):
    path=Path(root)/'manifest.json'
    if path.stat().st_size>65536:raise ValueError('Browser manifest is too large.')
    value=tx.preserve.document(tx.preserve.read(path))
    if (value.get('manifest_version')!=3 or not isinstance(value.get('key'),str) or
            not 1<=len(value['key'])<=8192 or not isinstance(value.get('version'),str) or
            not re.fullmatch(r'\d+(?:\.\d+){1,3}',value['version'])):
        raise ValueError('Use the existing keyed MV3 Browser extension.')
    for key in ('permissions','host_permissions','optional_permissions','optional_host_permissions'):
        items=value.get(key,[])
        if (not isinstance(items,list) or len(items)>128 or
                any(not isinstance(v,str) or not 1<=len(v)<=2048 for v in items) or len(set(items))!=len(items)):
            raise ValueError('Browser permissions must be explicit bounded lists.')
    return value


def copy_code(source,target,expected,after):
    fd=os.open(source,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for row in expected['rows']:
            archives.reserve(target.parent)
            path=target/row['path']
            if row['kind']=='directory':path.mkdir(mode=0o700)
            else:
                opened=archives.source_fd(fd,Path(row['path']))
                with os.fdopen(opened,'rb') as incoming,path.open('xb') as outgoing:
                    remaining=row['bytes']
                    while remaining:
                        chunk=incoming.read(min(remaining,1024**2))
                        if not chunk:raise ValueError('Browser source truncated during staging.')
                        outgoing.write(chunk);remaining-=len(chunk);archives.reserve(target.parent)
                    if incoming.read(1):raise ValueError('Browser source grew during staging.')
                    outgoing.flush()
                    os.fchmod(outgoing.fileno(),row['mode']&~0o022);os.fsync(outgoing.fileno())
        for row in reversed(expected['rows']):
            if row['kind']=='directory':
                path=target/row['path'];path.chmod(after['rows'][0]['mode'] if not row['path'] else row['mode']&~0o022);data.flush(path)
    finally:os.close(fd)
    if inventory(target)!=after or inventory(source)!=expected:
        raise ValueError('Browser code changed while staging; preserve the unpublished slot.')


def archived_before(manifest_record,target,before):
    roots=[r for r in manifest_record['coverage'] if r['path']==str(target) and r['members'] is None]
    if len(roots)!=1:raise ValueError('Capture the complete existing Browser code folder in the bound cold archive.')
    prefix=roots[0]['id'];archived={r['name']:r for r in manifest_record['entries'] if r['name']==prefix or r['name'].startswith(prefix+'/')}
    if len(archived)!=before['entries']:raise ValueError('Cold Browser code inventory differs.')
    for row in before['rows']:
        old=archived.get(prefix+('/'+row['path'] if row['path'] else ''),{})
        if (old.get('kind')!=row['kind'] or old.get('mode')!=row['mode'] or
                row['kind']=='file' and (old.get('sha256'),old.get('stamp',[0,0,0,0])[3])!=(row['sha256'],row['bytes'])):
            raise ValueError('Cold Browser code bytes or modes differ from the current original.')


def prepare(target,incoming,artifact_sha,output,cold_backup,guard):
    require(guard);target=Path(target);incoming=Path(incoming);output=Path(output)
    parent=tx.gate.directory(guard.data/'browser')
    if (target.parent!=parent or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}',target.name) or
            target.resolve()!=target):raise ValueError('Choose an explicit existing unpacked Browser code folder below deployment/browser.')
    tx.gate.directory(target);before_identity=identity(target);before=inventory(target)
    release=tx.incoming_seal(incoming,artifact_sha);source=incoming/'apps/browser/extension';source_inventory=inventory(source)
    old,new=manifest(target),manifest(source)
    if new['version']!=release['deployment'].get('version') or old['key']!=new['key']:
        raise ValueError('Browser identity or incoming product version differs.')
    for key in ('permissions','host_permissions','optional_permissions','optional_host_permissions'):
        if set(old.get(key,[]))!=set(new.get(key,[])):raise ValueError('Browser permission changes need a separately reviewed update.')
    archives.verify_for_guard(cold_backup['root'],cold_backup['sha256'],guard)
    archive=data.backup_manifest(cold_backup,guard);archived_before(archive,target,before)
    if not output.is_absolute() or output.resolve()!=output or output.exists() or output.is_symlink():
        raise ValueError('Choose absent canonical persistent Browser recovery storage.')
    tx.private_directory(output.parent)
    scratch_roots=[Path(os.environ.get('XDG_CACHE_HOME',Path.home()/'.cache'))/'augmentor/harness-build-work']
    if os.environ.get('AUGMENTOR_BUILD_WORKSPACE'):scratch_roots.append(Path(os.environ['AUGMENTOR_BUILD_WORKSPACE']))
    if any(output.is_relative_to(p.resolve()) and not target.is_relative_to(p.resolve()) for p in scratch_roots):
        raise ValueError('Keep owner Browser recovery persistent and outside disposable build scratch.')
    forbidden=[tx.ROOT,guard.home,guard.data,incoming,Path(cold_backup['root']),*(Path(p[k]) for p in guard.pairs for k in ('state','data'))]
    if any(output.is_relative_to(p) or p.is_relative_to(output) for p in forbidden):
        raise ValueError('Keep Browser recovery outside applications, data, source and archive roots.')
    if output.parent.stat().st_dev!=parent.stat().st_dev:raise ValueError('Browser code and its recovery slot must use one filesystem.')
    archives.reserve(output.parent,planned=source_inventory['bytes']+65536)
    # The incoming seal owns bytes; publishing code never grants group/other write.
    after_rows=[dict(r,mode=r['mode']&~0o022) for r in source_inventory['rows']];after_rows[0]['mode']=before['rows'][0]['mode']
    after={**fingerprint(after_rows),'rows':after_rows}
    output.mkdir(mode=0o700);slot=output/'extension';copy_code(source,slot,source_inventory,after)
    if identity(target)!=before_identity or inventory(target)!=before:raise ValueError('The original Browser folder changed during preparation.')
    value={'schema':SCHEMA,'home':str(guard.home),'deploymentData':str(guard.data),'pairs':guard.pairs,
           'originalSelectionSha256':tx.preserve.sha(guard.selection),'coldBackup':cold_backup,'incoming':str(incoming),
           'artifactSha256':artifact_sha,'target':str(target),'parentIdentity':identity(parent),
           'before':{'identity':before_identity,'inventory':summary(before)},
           'after':{'identity':identity(slot),'inventory':summary(after)},
           'incomingInventory':summary(source_inventory),'oldVersion':old['version'],'version':new['version'],
           'extensionKeySha256':tx.preserve.sha(new['key'].encode()),'foreignWriteRemovedFromIncoming':True}
    raw=tx.encoded(value);digest=tx.preserve.sha(raw);tx.atomic(output/'browser.json',raw,exclusive=True)
    tx.atomic(output/'status.json',tx.encoded({'phase':'prepared'}),exclusive=True);data.flush(output);data.flush(output.parent)
    return {'browserCodeSha256':digest,'startupReleased':False,'browserReloaded':False}


def image(path):return {'identity':identity(path),'inventory':summary(inventory(path))}


def inspect(output,digest,guard):
    require(guard);output=tx.private_directory(Path(output));raw=tx.preserve.read(output/'browser.json',private=True)
    if tx.preserve.sha(raw)!=digest:raise ValueError('Browser code journal identity changed.')
    value=tx.preserve.document(raw)
    if (value.get('schema')!=SCHEMA or value.get('home')!=str(guard.home) or value.get('deploymentData')!=str(guard.data) or value.get('pairs')!=guard.pairs):
        raise ValueError('Browser code belongs to another guarded cold cut.')
    target=Path(value['target']);parent=tx.gate.directory(guard.data/'browser')
    if target.parent!=parent or target.resolve()!=target or identity(parent)!=value['parentIdentity']:
        raise ValueError('The Browser code parent changed; preserve it.')
    data.backup_manifest(value['coldBackup'],guard)
    phase=tx.preserve.document(tx.preserve.read(output/'status.json',private=True)).get('phase')
    if phase not in ('prepared','applying','applied','reversing','reversed','released'):raise ValueError('Unknown Browser code recovery phase.')
    current,slot=image(target),image(output/'extension')
    if (current,slot) not in ((value['before'],value['after']),(value['after'],value['before'])):
        raise ValueError('Browser code or its recovery slot changed; preserve both folders.')
    if phase=='released' and (current,slot)!=(value['after'],value['before']):
        raise ValueError('Released Browser code changed; prepare a fresh reviewed update.')
    return value,{'phase':phase}


def exchange(source,target):
    fds=[]
    try:
        for parent in (Path(source).parent,Path(target).parent):
            parent=tx.gate.directory(parent);fds.append(os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW))
            if identity(parent)!=[os.fstat(fds[-1]).st_dev,os.fstat(fds[-1]).st_ino]:raise ValueError('Browser parent changed before exchange.')
        if os.fstat(fds[0]).st_dev!=os.fstat(fds[1]).st_dev:raise ValueError('Browser exchange crossed filesystems.')
        libc=ctypes.CDLL(None,use_errno=True)
        if libc.renameat2(fds[0],os.fsencode(Path(source).name),fds[1],os.fsencode(Path(target).name),2):
            raise OSError(ctypes.get_errno(),'Atomic Browser code exchange refused.')
        for fd in fds:os.fsync(fd)
    finally:
        for fd in fds:os.close(fd)


def owner(output,digest,guard,phases):
    if not (Path(output)/'client-publication.json').is_file():
        raise ValueError('Use the matching client publication for Browser code changes.')
    tx.require_publication_owner(output,guard)
    marker=tx.preserve.document(tx.preserve.read(Path(output)/'client-publication.json',private=True))
    publication=Path(marker['publication']);raw=tx.preserve.read(publication/'publication.json',private=True)
    if (tx.preserve.sha(raw)!=marker['sha256'] or tx.preserve.document(raw).get('browserCode')!={'root':str(output),'sha256':digest} or
            tx.preserve.document(tx.preserve.read(publication/'status.json',private=True)).get('phase') not in phases):
        raise ValueError('Browser code changes require the matching publication and durable intent.')


def settle(output,digest,guard,forward):
    owner(output,digest,guard,('applying',) if forward else ('reversing',));value,status=inspect(output,digest,guard)
    allowed=('prepared','applying','applied') if forward else ('prepared','applying','applied','reversing','reversed')
    if status['phase'] not in allowed:raise ValueError('Released/reversed Browser code requires a fresh reviewed cold cut.')
    tx.atomic(Path(output)/'status.json',tx.encoded({'phase':'applying' if forward else 'reversing'}))
    target=Path(value['target']);desired=value['after' if forward else 'before']
    if image(target)!=desired:exchange(Path(output)/'extension',target)
    inspect(output,digest,guard)
    if image(target)!=desired:raise ValueError('Browser code exchange did not settle; keep startup fenced.')
    tx.atomic(Path(output)/'status.json',tx.encoded({'phase':'applied' if forward else 'reversed'}))
    return {'browserCodeApplied':forward,'browserCodeRestored':not forward,'browserReloaded':False}


def commit(output,digest,guard):return settle(output,digest,guard,True)
def rollback(output,digest,guard):return settle(output,digest,guard,False)


def release(output,digest,guard):
    owner(output,digest,guard,('finalizing','finalized'));value,status=inspect(output,digest,guard)
    if status['phase'] not in ('applied','released') or image(Path(value['target']))!=value['after']:
        raise ValueError('Apply matching Browser code before releasing startup.')
    if status['phase']!='released':tx.atomic(Path(output)/'status.json',tx.encoded({'phase':'released'}))
    return {'browserCodeReleased':True,'oldCodeRestoreAllowed':False,'browserReloaded':False}
