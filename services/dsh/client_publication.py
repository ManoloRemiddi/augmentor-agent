# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Cold-backed matching-client publication; no process discovery or owner restart.

The operator must first adopt/quiesce every real launcher/client. These APIs hold
all declared deployment writers, publish exact reviewed bootstrap bytes and
matching selectors, and run the fixed backend/Native preflight. Optional bound
shared-data adoption exchanges only the three reviewed DB components; it never
replaces mixed application storage. These APIs never launch ordinary clients or
infer owner acceptance. Reverse is available
before finalization; after startup can reopen, a fresh reviewed reverse cut is
required. Missing/foreign recovery bytes are never guessed or overwritten.
"""
from contextlib import contextmanager, ExitStack
import os
from pathlib import Path
import stat
import sys

from . import preservation_transaction as tx
from . import cold_backup as archives
from . import backend_probe as probes
from . import shared_data_adoption as shared_data

SCHEMA='augmentor-dsh-client-publication/2'
MAX_FILES=128
MAX_BYTES=64*1024**2
BOOTSTRAP_NAMES=frozenset(('shared-launch-profile.py','desktop-browser-launch.py','desktop-dsh-launch.py',
    'dsh-profile-gate.py','embed-launch.py','desktop-launch.py','desktop-deployment.py','home-launch.py','autostart.py'))
startup=tx.load('publication_startup_files',tx.ROOT/'scripts/install-desktop-startup.py') if sys.platform=='linux' else None


class _Guard:
    def __init__(self,configuration,deployments):
        self.configuration=configuration
        self.deployments=deployments
        self.qualified=None


@contextmanager
def maintenance(home,data,pairs,additional_deployments=(),*,partial_pairs=()):
    """All declared managed entrypoints share one cold configuration interval."""
    if sys.platform!='linux':raise ValueError('Client publication is qualified only on Linux.')
    data=Path(data)
    if not isinstance(additional_deployments,(tuple,list)) or len(additional_deployments)>4:
        raise ValueError('Declare at most four additional deployment roots.')
    additional=[tx.private_directory(Path(p)) for p in additional_deployments]
    if len(set(additional))!=len(additional) or data in additional:
        raise ValueError('Deployment roots must be distinct.')
    roots=[data,*sorted(additional)]
    if any(a!=b and (a.is_relative_to(b) or b.is_relative_to(a)) for a in roots for b in roots):
        raise ValueError('Deployment roots cannot overlap.')
    with ExitStack() as stack:
        for root in sorted(additional):
            stack.enter_context(tx.shared.launch_lease(root,exclusive=True,preservation_recovery=True))
        configuration=stack.enter_context(tx.maintenance(home,data,pairs,partial_pairs=partial_pairs))
        selections={str(root):tx.preserve.read(root/'desktop.json',private=True) for root in roots}
        yield _Guard(configuration,selections)


def require(guard):
    if not isinstance(guard,_Guard) or not guard.configuration.active:
        raise ValueError('Hold the complete cold client-publication guard.')
    if guard.configuration.probe is not None:
        raise ValueError('Stop the controlled backend before publication.')
    tx.assert_no_dsh(guard.configuration.home)
    tx.shared.assert_no_clients(guard.configuration.pairs)
    for root,expected in guard.deployments.items():
        if tx.preserve.read(Path(root)/'desktop.json',private=True)!=expected:
            raise ValueError('A deployment selection changed outside this publication.')


def snapshot(path):
    path=Path(path)
    if not path.is_absolute() or path.resolve()!=path or path.parent.resolve()!=path.parent:
        raise ValueError('Bootstrap paths cannot contain links or aliases.')
    info=path.parent.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid():
        raise ValueError('Bootstrap parents must already exist and be owned.')
    value=startup.snapshot(path)
    if value is not None and (value[1]&0o7022):
        raise ValueError('Bootstrap files cannot have special or foreign-writable modes.')
    return value


def image(output,row,name):
    digest=row[name+'Sha256']
    if digest is None:return None
    raw=tx.preserve.read(output/name/str(row['index']),private=True)
    if tx.preserve.sha(raw)!=digest:raise ValueError('A retained bootstrap image changed.')
    return raw,row[name+'Mode']


def configuration(output,value,guard):
    base=guard.configuration;directory=Path(value['configuration'])
    raw=tx.preserve.read(directory/'transaction.json',private=True)
    if tx.preserve.sha(raw)!=value['configurationSha256']:
        raise ValueError('Configuration transaction identity changed.')
    record=tx.preserve.document(raw)
    if (record.get('schema')!=tx.SCHEMA or record.get('home')!=str(base.home) or
            record.get('deploymentData')!=str(base.data) or
            record.get('selectionSha256')!=value['originalSelectionSha256'] or
            record.get('coldBackup')!=value['coldBackup'] or
            record.get('artifactSha256')!=value['artifactSha256'] or
            record.get('incoming')!=value['incoming']):
        raise ValueError('Configuration/cold-backup/client publication bindings differ.')
    rows=record.get('files')
    if not isinstance(rows,list) or [r.get('destination') for r in rows]!=list(map(str,tx.destinations(base.home))):
        raise ValueError('The exact configuration inventory is required.')
    for i,row in enumerate(rows):
        for name in ('before','after'):
            if tx.preserve.sha(tx.preserve.read(directory/name/str(i),private=True))!=row[name+'Sha256']:
                raise ValueError('Configuration recovery bytes changed.')
    phase=tx.preserve.document(tx.preserve.read(directory/'status.json',private=True)).get('phase')
    if phase not in ('prepared','applying','applied','reversing','reversed'):
        raise ValueError('Unknown configuration recovery phase.')
    tx.targets(record)
    return directory,record


def fences(guard):
    base=guard.configuration
    # Deployment first at prepare; primary last at removal.
    return [base.data/tx.shared.PRESERVATION_FENCE,
            *(Path(p)/tx.shared.PRESERVATION_FENCE for p in guard.deployments if Path(p)!=base.data),
            base.home/tx.gate.FENCE]


def check_fences(value,guard,create=False):
    expected=tx.fence_identity(Path(value['configuration']),value['configurationSha256'])
    for path in fences(guard):
        if path.exists() or path.is_symlink():
            if tx.preserve.document(tx.preserve.read(path,private=True))!=expected:
                raise ValueError('A publication startup fence changed; retain it for inspection.')
        elif create:tx.atomic(path,tx.encoded(expected),exclusive=True)


def inspect(output,digest,guard):
    require(guard);output=tx.private_directory(Path(output))
    raw=tx.preserve.read(output/'publication.json',private=True)
    if tx.preserve.sha(raw)!=digest:raise ValueError('Client publication identity changed.')
    value=tx.preserve.document(raw)
    if value.get('schema')!=SCHEMA or value.get('deployments')!=list(guard.deployments):
        raise ValueError('Hold the exact declared deployment guards.')
    rows=value.get('files')
    if (not isinstance(rows,list) or not 1<=len(rows)<=MAX_FILES or
            [r.get('index') for r in rows]!=list(range(len(rows))) or
            len({r.get('path') for r in rows})!=len(rows)):
        raise ValueError('Invalid bounded client publication inventory.')
    for row in rows:
        before=image(output,row,'before');after=image(output,row,'after')
        if after is None or snapshot(Path(row['path'])) not in (before,after):
            raise ValueError('A bootstrap/selection file was edited; preserve its current bytes.')
    directory,record=configuration(output,value,guard)
    status=tx.preserve.document(tx.preserve.read(output/'status.json',private=True))
    if status.get('phase') not in ('prepared','applying','publishing','applied','finalizing','finalized','reversing','reversed'):
        raise ValueError('Unknown client publication phase.')
    publication_owner(output,digest,value,guard,allow_missing=status['phase']=='prepared')
    adoption(value,guard)
    check_fences(value,guard)
    return value,status,directory,record


def publication_owner(output,digest,value,guard,allow_missing=False,create=False):
    expected={'schema':SCHEMA,'publication':str(output),'sha256':digest}
    roots=[Path(value['configuration'])]
    if value.get('sharedAdoption') is not None:roots.append(Path(value['sharedAdoption']['root']))
    for root in roots:
        marker=root/'client-publication.json'
        if marker.exists() or marker.is_symlink():
            if tx.preserve.document(tx.preserve.read(marker,private=True))!=expected:
                raise ValueError('Configuration/data belongs to another client publication; preserve it.')
        elif create:tx.atomic(marker,tx.encoded(expected),exclusive=True)
        elif not allow_missing:raise ValueError('The linked client-publication ownership marker is missing.')
    return expected


@contextmanager
def configuration_owner(output,digest,value,guard):
    expected=publication_owner(output,digest,value,guard)
    base=guard.configuration;prior=getattr(base,'client_publication',None)
    base.client_publication=expected
    try:yield
    finally:base.client_publication=prior


def archive_file_images(backup):
    root=Path(backup['root']);archives.verify(root,backup['sha256'])
    receipt=tx.preserve.document(tx.preserve.read(root/'complete.json',private=True))
    manifest=archives.read_manifest(root,receipt['manifestSha256'])
    paths={r['id']:Path(r['path']) for r in manifest['coverage']}
    # An entry's archive name is root-id/relative-name.
    result={}
    for row in manifest['entries']:
        if row['kind']=='file':
            name=row['name'].split('/',1)
            result[str(paths[name[0]]/name[1])]=(row['sha256'],row['mode'])
    return result


def prospective_selections(configuration_root,configuration_sha,guard):
    """Read-only renderer input; never authorizes writing a selector or launcher."""
    require(guard)
    cfg,status=tx.inspect(configuration_root,configuration_sha,guard.configuration)
    if status['phase']!='prepared':raise ValueError('Render matching startup from the prepared original cut.')
    _,release=tx.validate_suppliers(Path(configuration_root),cfg,guard.configuration)
    return _selections(release,guard,guard.configuration.pairs[0])


def _selections(release,guard,pair):
    result={}
    for root,raw in guard.deployments.items():
        previous=tx.preserve.document(raw);selected=dict(release['deployment'])
        for key in ('dshService','dshHome','dshEndpoint'):
            if key in previous:selected[key]=previous[key]
        selected['sharedProfile']=pair;result[root]=selected
    return result


def adoption(value,guard):
    reference=value.get('sharedAdoption')
    if reference is None:return None
    if not isinstance(reference,dict) or set(reference)!={'root','sha256'}:
        raise ValueError('Bind the exact prepared shared-data adoption receipt.')
    record,status=shared_data.inspect(reference['root'],reference['sha256'],guard.configuration)
    if (record['coldBackup']!=value['coldBackup'] or record['originalSelectionSha256']!=value['originalSelectionSha256'] or
            record['target']!=guard.configuration.pairs[0]):
        raise ValueError('Shared-data and client publication cold cuts differ.')
    return record,status


def prepare(configuration_root,configuration_sha,output,guard,bootstrap=(),target_pair=None,*,shared_adoption=None,previous_pairs=None):
    """Bind immutable client bytes to an already cold-backed, prepared config cut.

    bootstrap is an exact operator-reviewed list of (path, bytes, ordinary mode).
    It must not contain data/profile payloads. Selectors are generated here from
    the verified incoming artifact, rather than accepted as arbitrary JSON.
    """
    require(guard);base=guard.configuration
    cfg,status=tx.inspect(configuration_root,configuration_sha,base)
    if status['phase']!='prepared' or 'coldBackup' not in cfg:
        raise ValueError('Prepare configuration with a current verified cold archive first.')
    marker=Path(configuration_root)/'client-publication.json'
    if marker.exists() or marker.is_symlink():raise ValueError('Recover the linked client publication first.')
    hashes=archive_file_images(cfg['coldBackup'])
    plan,release=tx.validate_suppliers(Path(configuration_root),cfg,base)
    pair=base.pairs[0] if target_pair is None else tx.shared.profile(target_pair,dedicated=False)
    if pair not in base.pairs:raise ValueError('Hold the cold gate for the selected target pair.')
    # The primary owns the backend; keep its guarded authoritative store pair.
    if pair!=base.pairs[0]:raise ValueError('Primary backend/shared-store migration needs its own qualified cut.')
    linked=adoption({'sharedAdoption':shared_adoption,'coldBackup':cfg['coldBackup'],
                     'originalSelectionSha256':cfg['selectionSha256']},guard)
    if linked is not None and linked[1]['phase']!='prepared':raise ValueError('Bind a prepared shared-data adoption before publication.')
    previous_pairs={} if previous_pairs is None else previous_pairs
    if not isinstance(previous_pairs,dict) or set(previous_pairs)-set(guard.deployments):
        raise ValueError('Declare existing shared pairs only for the exact guarded deployments.')
    for root,raw in guard.deployments.items():
        recorded=tx.preserve.document(raw).get('sharedProfile')
        if recorded is None:
            previous=base.pairs[0] if Path(root)==base.data else previous_pairs.get(root)
            if previous is None:raise ValueError('Declare the actual existing shared pair for a legacy deployment.')
            if root in previous_pairs and previous_pairs[root]!=previous:raise ValueError('The declared primary pair differs from the guarded store.')
        else:
            previous=recorded
            if root in previous_pairs and previous_pairs[root]!=recorded:raise ValueError('The declared previous pair differs from its selection.')
        previous=tx.shared.profile(previous,dedicated=False,allow_missing=previous in base.partial_pairs)
        if previous not in base.pairs:raise ValueError('Hold every previous shared pair before changing a deployment.')
        if previous!=pair and (linked is None or previous not in linked[0]['sources']):
            raise ValueError('Bind the source shared-data adoption before switching this deployment to the common store.')
    output=Path(output)
    if not output.is_absolute() or output.resolve()!=output or output.exists() or output.is_symlink():
        raise ValueError('Choose absent canonical client-publication storage.')
    tx.private_directory(output.parent)
    forbidden=[base.home,Path(cfg['incoming']),tx.ROOT,Path(configuration_root),Path(cfg['coldBackup']['root']),
               *(Path(p) for p in guard.deployments),*(Path(p[k]) for p in base.pairs for k in ('state','data'))]
    if shared_adoption is not None:forbidden.append(Path(shared_adoption['root']))
    if any(output.is_relative_to(p) or p.is_relative_to(output) for p in forbidden):
        raise ValueError('Keep client backups outside code, data, archives and configuration recovery roots.')
    writes=[];selections=_selections(release,guard,pair)
    for root,raw in guard.deployments.items():
        path=Path(root)/'desktop.json'
        if hashes.get(str(path))!=(tx.preserve.sha(raw),snapshot(path)[1]):
            raise ValueError('The cold archive does not contain the current deployment selection.')
        previous_path=Path(root)/'desktop.previous.json';before_previous=snapshot(previous_path)
        expected_previous=(tx.preserve.sha(before_previous[0]),before_previous[1]) if before_previous else None
        if hashes.get(str(previous_path))!=expected_previous:
            raise ValueError('The previous deployment selection differs from the bound cold archive.')
        selected=selections[root]
        writes.extend([(Path(root)/'desktop.previous.json',raw,0o600,True),
                       (path,tx.encoded(selected),0o600,True)])
    if not isinstance(bootstrap,(list,tuple)):raise ValueError('Use explicit reviewed bootstrap files.')
    for entry in bootstrap:
        if not isinstance(entry,(list,tuple)) or len(entry)!=3:raise ValueError('Use path, bytes and mode for each bootstrap file.')
        path,raw,mode=entry;path=Path(path)
        helper=any(path.parent==Path(root) and path.name in BOOTSTRAP_NAMES for root in guard.deployments)
        protected=forbidden[:5]  # Home, code, configuration and archive roots.
        if any(path.is_relative_to(p) for p in protected) or not helper and any(path.is_relative_to(p) for p in forbidden[5:]):
            raise ValueError('Bootstrap writes cannot replace app, profile, archive or shared-store payloads.')
        writes.append((path,raw,mode,False))
    if not 1<=len(writes)<=MAX_FILES or len({p for p,_,_,_ in writes})!=len(writes):
        raise ValueError('Bootstrap/selector paths must be unique and bounded.')
    images=[];total=0
    for path,raw,mode,selector in writes:
        if not isinstance(raw,bytes) or len(raw)>4*1024**2 or type(mode) is not int or mode not in (0o600,0o644,0o700,0o755):
            raise ValueError('Bootstrap images must be bounded bytes with ordinary protected modes.')
        before=snapshot(path);total+=len(raw)+(len(before[0]) if before else 0)
        if total>MAX_BYTES:raise ValueError('Client backup bytes exceed their bound.')
        images.append((path,before,(raw,mode),selector))
    archives.reserve(output.parent,planned=total)
    output.mkdir(mode=0o700)
    for name in ('before','after'):(output/name).mkdir(mode=0o700)
    rows=[]
    for i,(path,before,after,selector) in enumerate(images):
        archives.reserve(output)
        row={'index':i,'path':str(path),'selector':selector}
        for name,value in [('before',before),('after',after)]:
            row[name+'Sha256']=tx.preserve.sha(value[0]) if value else None
            row[name+'Mode']=value[1] if value else None
            if value:tx.atomic(output/name/str(i),value[0],exclusive=True)
        rows.append(row)
    value={'schema':SCHEMA,'configuration':str(configuration_root),'configurationSha256':configuration_sha,
           'originalSelectionSha256':cfg['selectionSha256'],'coldBackup':cfg['coldBackup'],
           'incoming':cfg['incoming'],'artifactSha256':cfg['artifactSha256'],
           'deployments':list(guard.deployments),'files':rows,'sharedAdoption':shared_adoption,
           'previousPairs':{root:tx.preserve.document(raw).get('sharedProfile') or previous_pairs.get(root,base.pairs[0]) for root,raw in guard.deployments.items()}}
    raw=tx.encoded(value);digest=tx.preserve.sha(raw)
    tx.atomic(output/'publication.json',raw,exclusive=True)
    tx.atomic(output/'status.json',tx.encoded({'phase':'prepared'}),exclusive=True)
    fd=os.open(output.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)
    publication_owner(output,digest,value,guard,create=True)
    check_fences(value,guard,create=True)
    return {'publicationSha256':digest,'startupFenced':True,'activationComplete':False}


def write_image(output,row,name,guard):
    path=Path(row['path']);before=image(output,row,'before');after=image(output,row,'after')
    now=snapshot(path)
    if now not in (before,after):raise ValueError('A concurrent client/bootstrap edit was preserved.')
    desired=before if name=='before' else after
    if now!=desired:
        if desired is None:
            path.unlink();fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:os.fsync(fd)
            finally:os.close(fd)
        else:startup.atomic_bytes(path,*desired)
    if row['selector'] and path.name=='desktop.json':
        guard.deployments[str(path.parent)]=desired[0]
        if path.parent==guard.configuration.data:
            # Rebind only after our exact original/target CAS publication. The
            # configuration API itself still refuses arbitrary pointer changes.
            guard.configuration.selection=desired[0]


def restore_selectors(output,value,guard):
    for row in reversed(value['files']):
        if row['selector']:write_image(output,row,'before',guard)
    if tx.preserve.sha(guard.configuration.selection)!=value['originalSelectionSha256']:
        raise ValueError('The original guarded selector was not restored.')


def apply(output,digest,guard,environment,cwd):
    output=Path(output);value,status,directory,record=inspect(output,digest,guard)
    if status['phase'] not in ('prepared','applying','publishing','applied'):
        raise ValueError('A reversed/finalized publication cannot be reapplied.')
    guard.qualified=None
    archive_file_images(value['coldBackup'])
    publication_owner(output,digest,value,guard,create=True)
    check_fences(value,guard,create=True)
    tx.atomic(output/'status.json',tx.encoded({'phase':'applying'}))
    # Recovery first brings only our selectors back to the original cut. It
    # never relabels arbitrary current bytes or weakens tx.require's invariant.
    restore_selectors(output,value,guard)
    with configuration_owner(output,digest,value,guard):
        tx.commit(directory,value['configurationSha256'],guard.configuration)
        if value['sharedAdoption'] is not None:
            reference=value['sharedAdoption'];shared_data.commit(reference['root'],reference['sha256'],guard.configuration)
    for row in value['files']:
        if not row['selector']:write_image(output,row,'after',guard)
    with probes.backend_probe(directory,value['configurationSha256'],guard.configuration,environment,cwd) as (handle,_):
        backend=handle.preflight();native=handle.native_adapter_preflight(directory)
        if backend.get('homeIdentityMatches') is not True or backend.get('productVersion')!=tx.preserve.document(tx.preserve.read(directory/'stage-plan.json',private=True))['candidateVersion'] or native.get('candidateNativeAdapterMatched') is not True:
            raise ValueError('The actual replacement backend and candidate client did not match.')
    require(guard)
    linked=adoption(value,guard)
    if linked is not None and linked[1]['phase']!='applied':raise ValueError('Apply every shared component before selecting clients.')
    tx.validate_suppliers(directory,record,guard.configuration)
    tx.atomic(output/'status.json',tx.encoded({'phase':'publishing'}))
    for row in value['files']:
        if row['selector']:write_image(output,row,'after',guard)
    tx.atomic(output/'status.json',tx.encoded({'phase':'applied','backend':backend,'native':native}))
    guard.qualified=digest
    return {'matchingClientsSelected':True,'startupFenced':True,'activationComplete':False}


def remove_fences(value,guard):
    check_fences(value,guard)
    for path in reversed(fences(guard)):
        check_fences(value,guard)
        if path.exists():
            path.unlink();fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:os.fsync(fd)
            finally:os.close(fd)


def finalize(output,digest,guard,environment,cwd):
    output=Path(output);value,status,_,record=inspect(output,digest,guard)
    archive_file_images(value['coldBackup'])
    if status['phase']=='finalized':
        linked=adoption(value,guard)
        if linked is not None and linked[1]['phase']!='released':raise ValueError('Finalized client publication has unreleased shared data.')
        if any(snapshot(Path(r['path']))!=image(output,r,'after') for r in value['files']) or tx.targets(record)!=[r['afterSha256'] for r in record['files']]:
            raise ValueError('Finalized client/configuration bytes changed.')
        tx.validate_suppliers(Path(value['configuration']),record,guard.configuration)
        if any(p.exists() or p.is_symlink() for p in fences(guard)):
            raise ValueError('Finalized publication has an unexpected startup fence.')
    else:
        if status['phase'] not in ('applied','finalizing'):
            raise ValueError('Apply matching configuration/clients before finalization.')
        # Once finalizing intent is durable, ordinary startup may already have
        # opened. Never reapply old DB snapshots or replay configuration work.
        if status['phase']=='applied' and guard.qualified!=digest:apply(output,digest,guard,environment,cwd)
        value,status,_,record=inspect(output,digest,guard)
        if any(snapshot(Path(r['path']))!=image(output,r,'after') for r in value['files']):
            raise ValueError('All matching client bytes must be selected before reopening startup.')
        if tx.targets(record)!=[r['afterSha256'] for r in record['files']]:
            raise ValueError('Matching configuration changed before finalization.')
        tx.validate_suppliers(Path(value['configuration']),record,guard.configuration)
        tx.atomic(output/'status.json',tx.encoded({'phase':'finalizing'}))
        if value['sharedAdoption'] is not None:
            reference=value['sharedAdoption']
            with configuration_owner(output,digest,value,guard):
                shared_data.release(reference['root'],reference['sha256'],guard.configuration)
        remove_fences(value,guard)
        tx.atomic(output/'status.json',tx.encoded({'phase':'finalized'}))
    return {'clientPublicationComplete':True,'startupFenced':False,'activationComplete':False,
            'ordinaryClientsStarted':False,'ownerContinuationVerified':False}


def rollback(output,digest,guard):
    output=Path(output);value,status,directory,_=inspect(output,digest,guard)
    if status['phase'] in ('finalizing','finalized'):
        raise ValueError('Startup may have reopened; prepare a fresh reviewed cold reverse cut.')
    archive_file_images(value['coldBackup'])
    publication_owner(output,digest,value,guard,create=True)
    check_fences(value,guard,create=True)
    tx.atomic(output/'status.json',tx.encoded({'phase':'reversing'}))
    restore_selectors(output,value,guard)
    for row in reversed(value['files']):
        if not row['selector']:write_image(output,row,'before',guard)
    with configuration_owner(output,digest,value,guard):
        if value['sharedAdoption'] is not None:
            reference=value['sharedAdoption'];shared_data.rollback(reference['root'],reference['sha256'],guard.configuration)
        tx.rollback(directory,value['configurationSha256'],guard.configuration)
    remove_fences(value,guard)
    tx.atomic(output/'status.json',tx.encoded({'phase':'reversed'}))
    return {'clientConfigurationRestored':True,'startupFenced':False,'dataRestored':value['sharedAdoption'] is not None}
