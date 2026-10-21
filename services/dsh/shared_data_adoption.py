# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Offline component adoption under the existing cold client-publication guard.

Keep the canonical mixed application root and memory authority. Build three DBs
with the existing pure merger, archive the complete dedicated source, then swap
only known components. No service/model/engine objects or whole-root replacement.
The client journal owns mutations; this module alone cannot reopen startup.
"""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat

from . import preservation_transaction as tx
from . import cold_backup as archives

SCHEMA='augmentor-shared-data-adoption/1'
DATABASES=('prompts.sqlite3','dual-memory.sqlite3','memory.sqlite3')
OPTIONAL=archives.OPTIONAL
MAX_ENTRIES=100000
MAX_BYTES=4*1024**3
merger=tx.load('cold_shared_data_merger',tx.ROOT/'services/companion_import.py')


def require(guard):
    tx.require(guard,guard.home)
    tx.shared.assert_no_clients(guard.pairs)


def flush(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)


def file_image(path):
    """Bounded content/mode identity without following a replaced leaf."""
    path=Path(path);before=path.lstat()
    if (not stat.S_ISREG(before.st_mode) or before.st_uid!=os.getuid() or
            before.st_mode&0o7000 or before.st_size>MAX_BYTES):
        raise ValueError('Adoption needs owned regular bounded files without special modes.')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        opened=os.fstat(fd)
        if archives.stamp(opened)!=archives.stamp(before):raise ValueError('Adoption file changed while opening.')
        size=0;digest=hashlib.sha256()
        while chunk:=os.read(fd,1024**2):
            size+=len(chunk)
            if size>before.st_size:raise ValueError('Adoption file grew while reading.')
            digest.update(chunk)
        if size!=before.st_size or archives.stamp(os.fstat(fd))!=archives.stamp(before) or archives.stamp(path.lstat())!=archives.stamp(before):
            raise ValueError('Adoption file changed while reading.')
        return {'mode':stat.S_IMODE(before.st_mode),'bytes':size,'sha256':digest.hexdigest()}
    finally:os.close(fd)


def optional_image(path):
    try:return file_image(path)
    except FileNotFoundError:return None


def inventory(root):
    """Same row order/JSON digest as runtime stateInventory (valid UTF-8 names)."""
    root=Path(root);rows=[];total=0
    def visit(path,key):
        nonlocal total
        info=path.lstat()
        if info.st_uid!=os.getuid() or info.st_mode&0o7000 or len(rows)>=MAX_ENTRIES:
            raise ValueError('Adoption inventory ownership, modes or entry bound changed.')
        if stat.S_ISDIR(info.st_mode):
            rows.append({'path':key,'kind':'directory','mode':stat.S_IMODE(info.st_mode)})
            names=sorted(os.listdir(path),key=lambda s:s.encode('utf-16-be'))
            for name in names:visit(path/name,key+'/'+name if key else name)
        elif stat.S_ISREG(info.st_mode):
            value=file_image(path);total+=value['bytes']
            if total>MAX_BYTES:raise ValueError('Shared source inventory exceeds four GiB.')
            rows.append({'path':key,'kind':'file','mode':value['mode'],'bytes':value['bytes'],'sha256':value['sha256']})
        else:raise ValueError('Shared source/archive contains a link, socket or unsupported object.')
    visit(root,'')
    raw=json.dumps(rows,separators=(',',':'),ensure_ascii=False).encode()
    return {'sha256':hashlib.sha256(raw).hexdigest(),'entries':len(rows),'bytes':total,'rows':rows}


def copy_inventory(source,target,expected):
    """Only unpublished images; preserve ordinary modes and all nested history."""
    target=Path(target)
    fd=os.open(source,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for row in expected['rows']:
            archives.reserve(target.parent if not target.exists() else target)
            path=target/row['path']
            if row['kind']=='directory':path.mkdir(mode=row['mode'])
            else:
                source_fd=archives.source_fd(fd,Path(row['path']))
                with os.fdopen(source_fd,'rb') as incoming,path.open('xb') as outgoing:
                    shutil.copyfileobj(incoming,outgoing,1024**2);outgoing.flush();os.fchmod(outgoing.fileno(),row['mode']);os.fsync(outgoing.fileno())
    finally:os.close(fd)
    for row in reversed(expected['rows']):
        if row['kind']=='directory':
            path=target/row['path'];path.chmod(row['mode']);flush(path)
    if inventory(target)!=expected:raise ValueError('Shared source copy differs; retain the unpublished stage.')


def backup_manifest(backup,guard):
    root=Path(backup['root']);key=(str(root),backup['sha256'])
    current=[archives.stamp((root/name).lstat()) for name in ('data.tar','manifest.json','complete.json')]
    cached=getattr(guard,'shared_adoption_archive',None)
    if cached is not None and cached[:2]==(key,current):return cached[2]
    archives.verify(root,backup['sha256'])
    receipt=tx.preserve.document(tx.preserve.read(root/'complete.json',private=True))
    if (receipt['home']!=str(guard.home) or receipt['deploymentData']!=str(guard.data) or
            receipt['sharedProfiles']!=guard.pairs or receipt.get('partialSharedProfiles')!=guard.partial_pairs):
        raise ValueError('Shared adoption must use the same complete cold archive and guarded pairs.')
    manifest=archives.read_manifest(root,receipt['manifestSha256'])
    if [archives.stamp((root/name).lstat()) for name in ('data.tar','manifest.json','complete.json')]!=current:
        raise ValueError('Cold archive identity changed during shared-adoption verification.')
    guard.shared_adoption_archive=(key,current,manifest)
    return manifest


def verify_backup_components(manifest,source,target,source_inventory):
    full=[r for r in manifest['coverage'] if r['path']==source['data'] and r['members'] is None]
    if len(full)!=1:raise ValueError('Capture the complete dedicated shared source, including its nested import history.')
    source_rows={r['name']:r for r in manifest['entries'] if r['name']==full[0]['id'] or r['name'].startswith(full[0]['id']+'/')}
    if len(source_rows)!=source_inventory['entries']:raise ValueError('Cold source inventory differs from the reviewed source.')
    for row in source_inventory['rows']:
        name=full[0]['id']+('/'+row['path'] if row['path'] else '');old=source_rows.get(name,{})
        if old.get('kind')!=row['kind'] or old.get('mode')!=row['mode'] or row['kind']=='file' and (old.get('sha256'),old['stamp'][3])!=(row['sha256'],row['bytes']):
            raise ValueError('Cold source bytes/modes differ from the reviewed source.')
    paths={r['id']:Path(r['path']) for r in manifest['coverage']};files={}
    for row in manifest['entries']:
        if row['kind']=='file':
            parts=row['name'].split('/',1)
            files[str(paths[parts[0]]/parts[1])]={'mode':row['mode'],'bytes':row['stamp'][3],'sha256':row['sha256']}
    for name in (*DATABASES,*OPTIONAL):
        if files.get(str(Path(target['data'])/name))!=optional_image(Path(target['data'])/name):
            raise ValueError('Cold target components differ from the reviewed target.')


def prepare(source,output,cold_backup,guard,*,map_default_person=False):
    require(guard)
    if type(map_default_person) is not bool:raise ValueError('Choose an explicit source-person mapping policy.')
    sources=source if isinstance(source,list) else [source]
    if not 1<=len(sources)<=4:raise ValueError('Choose one to four explicitly guarded shared source pairs.')
    sources=[tx.shared.profile(p,allow_missing=p in guard.partial_pairs) for p in sources];target=guard.pairs[0]
    if any(p not in guard.pairs or p==target for p in sources):raise ValueError('Hold all distinct source and canonical target shared pairs.')
    pairs=[target,*sources]
    for i,pair in enumerate(pairs):
        for previous in pairs[:i]:
            if any(Path(a).is_relative_to(b) or Path(b).is_relative_to(a) for a in pair.values() for b in previous.values()):
                raise ValueError('Source and canonical target shared paths must not overlap.')
    archives.verify_for_guard(cold_backup['root'],cold_backup['sha256'],guard)
    manifest=backup_manifest(cold_backup,guard);cuts=[]
    for pair in sources:
        before=inventory(Path(pair['data']));verify_backup_components(manifest,pair,target,before)
        partial=pair in guard.partial_pairs
        merger.validate(pair['data'],allow_missing=partial);cuts.append({'source':pair,'inventory':before,'sha256':before['sha256'],'partial':partial})
    if len({c['sha256'] for c in cuts})!=len(cuts):raise ValueError('Identical source cuts need one explicit deduplicated import plan.')
    merger.validate(target['data'])
    output=Path(output);destination=Path(target['data']);imports=destination/'shared-imports'
    if not output.is_absolute() or output.resolve()!=output or output.exists() or output.is_symlink():
        raise ValueError('Choose absent canonical persistent shared-adoption storage.')
    tx.private_directory(output.parent)
    forbidden=[tx.ROOT,guard.home,guard.data,Path(cold_backup['root']),Path(tx.preserve.document(guard.selection)['root']),
               *(Path(p[k]) for p in guard.pairs for k in ('state','data'))]
    if any(output.is_relative_to(p) or p.is_relative_to(output) for p in forbidden):
        raise ValueError('Keep shared-adoption recovery outside applications, profiles and the cold archive.')
    if output.parent.stat().st_dev!=destination.stat().st_dev:
        raise ValueError('Shared-adoption images and canonical data must use the same filesystem.')
    existing=imports.exists() or imports.is_symlink()
    if existing:tx.private_directory(imports)
    if any((imports/c['sha256']).exists() or (imports/c['sha256']).is_symlink() for c in cuts):
        raise ValueError('A source cut is already archived; do not replay its import.')
    if existing and any(imports.iterdir()):
        full=[r for r in manifest['coverage'] if r['path']==str(imports) and r['members'] is None]
        if len(full)!=1:raise ValueError('Include existing canonical shared-import history in the reviewed cold archive.')
    components={name:file_image(destination/name) for name in DATABASES}
    engine={name:optional_image(destination/name) for name in OPTIONAL}
    planned=3*sum(c['inventory']['bytes'] for c in cuts)+2*sum(r['bytes'] for r in components.values())+sum(r['bytes'] for r in engine.values() if r)
    archives.reserve(output.parent,planned=planned)
    output.mkdir(mode=0o700);images=output/'images';images.mkdir(mode=0o700)
    (images/'shared-imports').mkdir(mode=0o700)
    for name in (*DATABASES,*OPTIONAL):
        expected=components[name] if name in DATABASES else engine[name]
        if expected is None:continue
        path=images/name;shutil.copyfile(destination/name,path);path.chmod(expected['mode']);flush(path)
        if file_image(path)!=expected:raise ValueError('Target changed during offline preparation.')
    for source_cut in cuts:
        cut=source_cut['sha256'];before=source_cut['inventory'];archive=images/'shared-imports'/cut;archive.mkdir(mode=0o700)
        copy_inventory(source_cut['source']['data'],archive/'data',before)
        changes=merger.merge(archive/'data',images,cut,map_default_person,allow_missing_source=source_cut['partial'])
        receipt={'schema':'augmentor-shared-profile-import/1','sourceSha256':cut,'sourceArchive':'shared-imports/'+cut+'/data',
                 'sourceRetained':True,'mapDefaultPerson':map_default_person,**{k:v for k,v in changes.items() if k!='schema'},
                 'targetConfigurationPreserved':True,'engineCopiedOrCalled':False,'modelWorkSubmitted':False}
        tx.atomic(archive/'receipt.json',tx.encoded(receipt),exclusive=True)
        source_cut.update(receipt=receipt,archiveInventory=inventory(archive))
    for source_cut in cuts:
        if (inventory(images/'shared-imports'/source_cut['sha256']/'data')!=source_cut['inventory'] or
                inventory(Path(source_cut['source']['data']))!=source_cut['inventory']):
            raise ValueError('Shared source/archive changed during merge; do not publish.')
    rows=[]
    for name in DATABASES:
        flush(images/name);rows.append({'name':name,'before':components[name],'after':file_image(images/name)})
    if any(optional_image(images/name)!=engine[name] or optional_image(destination/name)!=engine[name] for name in OPTIONAL):
        raise ValueError('Canonical engine configuration changed during the merge.')
    if any(file_image(destination/name)!=components[name] for name in DATABASES):raise ValueError('Canonical databases changed during the merge.')
    relatives=['shared-imports/'+c['sha256'] for c in cuts] if existing else ['shared-imports']
    moves=[{'relative':relative,'inventory':inventory(images/relative)} for relative in relatives]
    for move in moves:
        for row in move['inventory']['rows']:
            if row['kind']=='file':flush(images/move['relative']/row['path'])
        for row in reversed(move['inventory']['rows']):
            if row['kind']=='directory':flush(images/move['relative']/row['path'])
    flush(images);archives.reserve(output)
    value={'schema':SCHEMA,'home':str(guard.home),'deploymentData':str(guard.data),'pairs':guard.pairs,
           'sources':sources,'target':target,'coldBackup':cold_backup,'originalSelectionSha256':tx.preserve.sha(guard.selection),
           'cuts':cuts,'components':rows,'engine':engine,'archiveMoves':moves,
           'mergerSha256':file_image(Path(merger.__file__))['sha256'],
           'targetIdentity':[destination.stat().st_dev,destination.stat().st_ino]}
    raw=tx.encoded(value);digest=tx.preserve.sha(raw)
    if len(raw)>tx.preserve.LIMIT:raise ValueError('Shared-adoption metadata exceeds its four MiB bound; retain the unpublished stage.')
    tx.atomic(output/'adoption.json',raw,exclusive=True);tx.atomic(output/'status.json',tx.encoded({'phase':'prepared'}),exclusive=True)
    flush(output);flush(output.parent)
    return {'sharedAdoptionSha256':digest,'sourceRetained':True,'targetModified':False,'engineCopiedOrCalled':False}


def tree_or_none(path):
    if not path.exists() and not path.is_symlink():return None
    return inventory(path)


def inspect(output,digest,guard):
    require(guard);output=tx.private_directory(Path(output));raw=tx.preserve.read(output/'adoption.json',private=True)
    if tx.preserve.sha(raw)!=digest:raise ValueError('Shared-adoption identity changed.')
    value=tx.preserve.document(raw)
    if (value.get('schema')!=SCHEMA or value.get('home')!=str(guard.home) or value.get('deploymentData')!=str(guard.data) or
            value.get('pairs')!=guard.pairs or value.get('target')!=guard.pairs[0] or
            not isinstance(value.get('sources'),list) or not 1<=len(value['sources'])<=4 or
            any(p not in guard.pairs or p==value['target'] for p in value['sources']) or
            [r.get('name') for r in value.get('components',[])]!=list(DATABASES)):
        raise ValueError('Shared adoption belongs to another guarded cold cut.')
    target=Path(value['target']['data']);images=output/'images';tx.private_directory(images)
    if [target.stat().st_dev,target.stat().st_ino]!=value['targetIdentity']:
        raise ValueError('The canonical mixed application root was replaced; preserve it.')
    backup_manifest(value['coldBackup'],guard)
    status=tx.preserve.document(tx.preserve.read(output/'status.json',private=True))
    if status.get('phase') not in ('prepared','applying','applied','reversing','reversed','released'):
        raise ValueError('Unknown shared-adoption recovery phase.')
    tx.shared.component_fingerprint(value['target'])
    if status['phase']=='released':
        # New ordinary work may exist. Never compare it to, or restore, the old
        # merged DB after-image. The archived cut and original slots stay exact.
        for row in value['components']:
            if file_image(images/row['name'])!=row['before']:raise ValueError('Original component recovery bytes changed.')
        for cut in value['cuts']:
            if inventory(target/'shared-imports'/cut['sha256'])!=cut['archiveInventory']:
                raise ValueError('The retained shared import history changed.')
        merger.validate(target)
        return value,status
    for cut in value['cuts']:
        if inventory(Path(cut['source']['data']))!=cut['inventory']:
            raise ValueError('Shared source changed after the reviewed cold cut; preserve its new work.')
    for name,expected in value['engine'].items():
        if optional_image(target/name)!=expected or optional_image(images/name)!=expected:
            raise ValueError('Canonical engine configuration changed; preserve it.')
    for row in value['components']:
        current,slot=file_image(target/row['name']),file_image(images/row['name'])
        if (current,slot) not in ((row['before'],row['after']),(row['after'],row['before'])):
            raise ValueError('A shared database or its recovery slot was edited; preserve every component.')
    for move in value['archiveMoves']:
        current=tree_or_none(target/move['relative']);slot=tree_or_none(images/move['relative'])
        if (current,slot) not in ((None,move['inventory']),(move['inventory'],None)):
            raise ValueError('Shared archive publication differs; preserve the existing history.')
    return value,status


def rename(source,target,flags):
    """Linux exchange/no-replace, durable in both existing parent directories."""
    source,target=Path(source),Path(target);fds=[]
    try:
        for parent in (source.parent,target.parent):
            tx.private_directory(parent);fds.append(os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW))
        if os.fstat(fds[0]).st_dev!=os.fstat(fds[1]).st_dev:raise ValueError('Adoption rename crossed filesystems.')
        libc=ctypes.CDLL(None,use_errno=True)
        if libc.renameat2(fds[0],os.fsencode(source.name),fds[1],os.fsencode(target.name),flags):
            raise OSError(ctypes.get_errno(),'Atomic shared-adoption publication refused.')
        for fd in fds:os.fsync(fd)
    finally:
        for fd in fds:os.close(fd)


def owner(output,guard):
    if not (Path(output)/'client-publication.json').is_file():raise ValueError('Use a bound client publication for shared data adoption.')
    tx.require_publication_owner(output,guard)


def settle(output,digest,guard,forward):
    owner(output,guard);value,status=inspect(output,digest,guard)
    allowed=('prepared','applying','applied') if forward else ('prepared','applying','applied','reversing','reversed')
    if status['phase'] not in allowed:raise ValueError('Released/reversed shared data cannot be reapplied or automatically restored.')
    if forward:archives.reserve(Path(output))
    tx.atomic(Path(output)/'status.json',tx.encoded({'phase':'applying' if forward else 'reversing'}))
    target=Path(value['target']['data']);images=Path(output)/'images'
    # Every component and recovery byte was checked before the first mutation.
    for row in value['components'] if forward else reversed(value['components']):
        inspect(output,digest,guard)
        desired=row['after' if forward else 'before']
        if file_image(target/row['name'])!=desired:rename(images/row['name'],target/row['name'],2)
    inspect(output,digest,guard)
    for move in value['archiveMoves'] if forward else reversed(value['archiveMoves']):
        inspect(output,digest,guard);relative=move['relative']
        source,destination=(images/relative,target/relative) if forward else (target/relative,images/relative)
        if source.exists():rename(source,destination,1)
    value,_=inspect(output,digest,guard)
    if any(file_image(target/r['name'])!=r['after' if forward else 'before'] for r in value['components']):
        raise ValueError('Shared components did not settle; keep startup fenced.')
    tx.atomic(Path(output)/'status.json',tx.encoded({'phase':'applied' if forward else 'reversed'}))
    return {'sharedDataApplied':forward,'sharedComponentsRestored':not forward,'startupFenced':True,'modelWorkSubmitted':False}


def commit(output,digest,guard):return settle(output,digest,guard,True)
def rollback(output,digest,guard):return settle(output,digest,guard,False)


def release(output,digest,guard):
    """Only durable client finalizing intent can let later ordinary work exist."""
    owner(output,guard);value,status=inspect(output,digest,guard)
    marker=tx.preserve.document(tx.preserve.read(Path(output)/'client-publication.json',private=True))
    publication=Path(marker['publication']);raw=tx.preserve.read(publication/'publication.json',private=True)
    if (tx.preserve.sha(raw)!=marker['sha256'] or tx.preserve.document(raw).get('sharedAdoption')!={'root':str(output),'sha256':digest} or
            tx.preserve.document(tx.preserve.read(publication/'status.json',private=True))['phase'] not in ('finalizing','finalized')):
        raise ValueError('Shared data release requires durable client finalizing intent.')
    if status['phase']=='released':return {'released':True,'oldDataRestoreAllowed':False}
    if status['phase']!='applied':raise ValueError('Apply every shared component before reopening startup.')
    target=Path(value['target']['data'])
    if (any(file_image(target/r['name'])!=r['after'] for r in value['components']) or
            any(tree_or_none(target/m['relative'])!=m['inventory'] for m in value['archiveMoves'])):
        raise ValueError('Shared adoption is incomplete; keep startup fenced.')
    tx.atomic(Path(output)/'status.json',tx.encoded({'phase':'released'}))
    return {'released':True,'oldDataRestoreAllowed':False}
