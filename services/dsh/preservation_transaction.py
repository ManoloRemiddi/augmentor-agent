# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Internal cold configuration journal, not a complete installed activation API.

Only the four reviewed integration/configuration files are replaced. Applied
transactions retain profile and deployment startup fences until orchestration
qualifies matching clients. This module deliberately exposes no command to
release those forward-activation fences.
Full owner-store backup/client adoption remains an outer activation prerequisite.
"""
from contextlib import contextmanager
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import stat
import sys
import uuid

from . import preserve

ROOT=Path(__file__).resolve().parents[2]
SCHEMA='augmentor-dsh-configuration-transaction/3'
ASSETS=('integration/browser/dist/index.js','integration/browser/package.json',
        'integration/ownership.json','cordis.patch.yml')


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


if sys.platform=='linux':
    gate=load('dsh_transaction_profile_gate',ROOT/'scripts/dsh-profile-gate.py')
    shared=load('dsh_transaction_shared_gate',ROOT/'scripts/shared-launch-profile.py')
    deployment=load('dsh_transaction_deployment',ROOT/'scripts/desktop-deployment.py')
else:gate=shared=deployment=None  # Keep non-Linux test/import discovery usable.


def private_directory(path):
    path=gate.directory(path)
    if path.stat().st_mode&0o077:raise ValueError('Transaction storage must be private.')
    return path


def atomic(path,data,mode=0o600,exclusive=False):
    """Use the checked parent descriptor; never follow a replaced parent link."""
    parent=gate.directory(path.parent)
    fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    name='.'+path.name+'-'+uuid.uuid4().hex
    try:
        stream=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
        with os.fdopen(stream,'wb') as output:
            output.write(data);output.flush();os.fchmod(output.fileno(),mode);os.fsync(output.fileno())
        a,b=os.fstat(fd),parent.stat()
        if (a.st_dev,a.st_ino)!=(b.st_dev,b.st_ino):raise ValueError('Configuration parent changed during publication.')
        if exclusive:
            # Linux no-replace rename publishes a complete single-link file.
            # link/unlink would leave an unrecoverable two-link fence if killed.
            libc=ctypes.CDLL(None,use_errno=True)
            if libc.renameat2(fd,os.fsencode(name),fd,os.fsencode(path.name),1):
                raise OSError(ctypes.get_errno(),'Exclusive transaction publication failed.')
        else:os.replace(name,path.name,src_dir_fd=fd,dst_dir_fd=fd)
        os.fsync(fd)
    finally:
        try:os.unlink(name,dir_fd=fd)
        except FileNotFoundError:pass
        os.close(fd)


def encoded(value):return (json.dumps(value,indent=2)+'\n').encode()


def assert_no_dsh(home):
    """Known legacy hosts also veto maintenance; arbitrary custom callers need inventory."""
    for process in Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name)==os.getpid():continue
        try:
            if process.stat().st_uid!=os.getuid():continue
            args=(process/'cmdline').read_bytes().split(b'\0')
            if not any(a==b'dsh' or a.endswith((b'/dsh',b'/dsh.cmd')) or b'/@deepseek-ai/dsh/' in a for a in args):continue
            env=dict(row.split('=',1) for row in (process/'environ').read_text().split('\0') if '=' in row)
            base=Path(env.get('HOME',pwd.getpwuid(os.getuid()).pw_dir))
            selected=Path(env.get('DSH_HOME',base/'.dsh'))
            if not selected.is_absolute():selected=(process/'cwd').resolve()/selected
            if selected.resolve()==home:raise ValueError('Stop the existing DSH host before configuration maintenance.')
        except (FileNotFoundError,ProcessLookupError):continue


class _Guard:
    def __init__(self,home,data,selection,pairs,launch_fd):
        self.home=home;self.data=data;self.selection=selection;self.pairs=pairs
        self.launch_fd=launch_fd;self.active=True;self.probe=None


@contextmanager
def maintenance(home,data,pairs):
    """Hold DSH/profile, managed-client and shared companion gates together."""
    if sys.platform!='linux':raise ValueError('Configuration maintenance is qualified only on Linux.')
    home=gate.directory(home);data=private_directory(data)
    if not isinstance(pairs,list) or not pairs:raise ValueError('Identify the selected shared pair before maintenance.')
    pairs=[shared.profile(pair,dedicated=False) for pair in pairs]
    raw=preserve.read(data/'desktop.json',private=True);selected=preserve.document(raw)
    expected=selected.get('sharedProfile') or {
        'state':str(Path(os.environ.get('AUGMENTOR_SHARED_STATE',Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'augmentor')).resolve()),
        'data':str(Path(os.environ.get('AUGMENTOR_SHARED_DATA',Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'augmentor')).resolve())}
    if pairs[0]!=expected:raise ValueError('The maintenance pair differs from the selected shared profile.')
    with gate.lease(home,exclusive=True),shared.launch_lease(data,exclusive=True,preservation_recovery=True) as launch_fd,shared.cold(pairs):
        assert_no_dsh(home)
        if preserve.read(data/'desktop.json',private=True)!=raw:raise ValueError('The desktop selection changed before maintenance.')
        guard=_Guard(home,data,raw,pairs,launch_fd)
        try:yield guard
        finally:
            try:
                if guard.probe is not None:guard.probe.close()
            finally:guard.active=False


def require(guard,home):
    if not isinstance(guard,_Guard) or not guard.active or guard.home!=home:
        raise ValueError('Hold the cold maintenance gates for this exact DSH home.')
    if guard.probe is not None:raise ValueError('Stop the controlled backend before changing configuration.')
    if preserve.read(guard.data/'desktop.json',private=True)!=guard.selection:
        raise ValueError('The desktop selection changed during configuration maintenance.')
    assert_no_dsh(home)


def destinations(home):
    target=home/'profiles/web/augmentor-product'
    return (target/'browser/dist/index.js',target/'browser/package.json',target/'ownership.json',home/'profiles/web/cordis.patch.yml')


def incoming_seal(root,digest):
    if not isinstance(digest,str) or not re.fullmatch('[a-f0-9]{64}',digest):raise ValueError('Bind the reviewed immutable incoming artifact.')
    value=deployment.verify(root)
    if value['artifactSha256']!=digest or value['deployment']['root']!=str(root):
        raise ValueError('Incoming immutable identity changed.')
    return value


def prepare(stage,stage_sha,output,artifact_sha,guard,*,cold_backup=None):
    stage=Path(stage);output=Path(output);home=guard.home;require(guard,home)
    preserve.verify(stage,stage_sha);plan=preserve.document(preserve.read(stage/'plan.json',private=True))
    if Path(plan['home'])!=home:raise ValueError('Stage and maintenance home differ.')
    incoming=Path(plan['incoming']);seal=incoming_seal(incoming,artifact_sha)
    if seal['deployment'].get('version')!=plan['candidateVersion']:raise ValueError('Incoming product version differs from the stage.')
    if output.resolve()!=output or not output.is_absolute() or output.exists() or output.is_symlink():raise ValueError('Choose absent canonical transaction storage.')
    private_directory(output.parent)
    if any(output.is_relative_to(p) or p.is_relative_to(output) for p in (home,incoming,stage,guard.data,ROOT)):
        raise ValueError('Keep transaction backups outside application/profile/deployment/stage/checkout roots.')
    if any(p.exists() or p.is_symlink() for p in fence_paths(guard)):
        raise ValueError('Recover the existing configuration transaction first.')
    if cold_backup is not None:
        from . import cold_backup as archives
        if not isinstance(cold_backup,dict) or set(cold_backup)!={'root','sha256'}:
            raise ValueError('Bind the exact cold archive before preparing client publication.')
        archives.verify_for_guard(Path(cold_backup['root']),cold_backup['sha256'],guard)
        archive=Path(cold_backup['root'])
        if output.is_relative_to(archive) or archive.is_relative_to(output):
            raise ValueError('Keep configuration recovery storage separate from its cold archive.')
    rows=[];originals=[];candidates=[]
    for asset,path in zip(ASSETS,destinations(home)):
        original=preserve.read(path);candidate=preserve.read(stage/asset,private=True);mode=path.stat().st_mode&0o777
        if mode&0o022:raise ValueError('Configuration files must be protected from other writers.')
        if preserve.sha(original)!=plan['ownerInputs'].get(str(path)) or preserve.sha(candidate)!=plan['assets'][asset]:
            raise ValueError('Configuration or staged bytes changed before backup.')
        rows.append({'destination':str(path),'beforeSha256':preserve.sha(original),'afterSha256':preserve.sha(candidate),'mode':mode})
        originals.append(original);candidates.append(candidate)
    value={'schema':SCHEMA,'home':str(home),'incoming':str(incoming),'artifactSha256':artifact_sha,
           'deploymentData':str(guard.data),'selectionSha256':preserve.sha(guard.selection),
           'stagePlanSha256':stage_sha,'files':rows}
    if cold_backup is not None:value['coldBackup']=dict(cold_backup)
    output.mkdir(mode=0o700)
    for name in ('before','after'):(output/name).mkdir(mode=0o700)
    for index,(before,after) in enumerate(zip(originals,candidates)):
        atomic(output/'before'/str(index),before,exclusive=True);atomic(output/'after'/str(index),after,exclusive=True)
    atomic(output/'stage-plan.json',preserve.read(stage/'plan.json',private=True),exclusive=True)
    raw=encoded(value);atomic(output/'transaction.json',raw,exclusive=True);digest=preserve.sha(raw)
    atomic(output/'status.json',encoded({'phase':'prepared'}),exclusive=True)
    # Revalidate after durable backups and before publishing the startup fence.
    preserve.verify(stage,stage_sha);require(guard,home)
    parent=os.open(output.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(parent)  # Persist the new backup directory entry before its fence.
    finally:os.close(parent)
    # Deployment first: all managed clients remain blocked after controller
    # death, even if their old selection lacks explicit DSH-home metadata.
    for fence in fence_paths(guard):
        atomic(fence,encoded(fence_identity(output,digest)),exclusive=True)
    return {'transactionSha256':digest,'configurationApplied':False,'activationComplete':False}


def fence_paths(guard):return (guard.data/shared.PRESERVATION_FENCE,guard.home/gate.FENCE)


def fence_identity(output,digest):return {'schema':SCHEMA,'transaction':str(output),'sha256':digest}


def inspect_fences(output,digest,guard,allow_missing=False):
    present=[]
    for fence in fence_paths(guard):
        exists=fence.exists() or fence.is_symlink()
        if exists:
            if preserve.document(preserve.read(fence,private=True))!=fence_identity(output,digest):
                raise ValueError('Configuration fence changed; preserve it for inspection.')
        elif not allow_missing:raise ValueError('Configuration startup fence is incomplete; recover before applying.')
        present.append(exists)
    return present


def inspect(output,digest,guard,recovery=False):
    output=private_directory(output);raw=preserve.read(output/'transaction.json',private=True)
    if preserve.sha(raw)!=digest:raise ValueError('Transaction identity changed.')
    value=preserve.document(raw)
    if value.get('schema')!=SCHEMA or value.get('home')!=str(guard.home) or value.get('deploymentData')!=str(guard.data) or value.get('selectionSha256')!=preserve.sha(guard.selection):
        raise ValueError('Transaction binding differs from cold maintenance.')
    require(guard,guard.home)
    rows=value.get('files');expected=destinations(guard.home)
    if not isinstance(rows,list) or len(rows)!=4 or [row.get('destination') for row in rows]!=list(map(str,expected)):
        raise ValueError('The exact four-file transaction inventory is required.')
    for index,row in enumerate(rows):
        if type(row.get('mode')) is not int or row['mode']&~0o777 or row['mode']&0o022:raise ValueError('Transaction mode changed.')
        for name,key in [('before','beforeSha256'),('after','afterSha256')]:
            if preserve.sha(preserve.read(output/name/str(index),private=True))!=row.get(key):raise ValueError('Recovery copy changed; preserve it for inspection.')
    if preserve.sha(preserve.read(output/'stage-plan.json',private=True))!=value.get('stagePlanSha256'):raise ValueError('Transaction stage provenance changed.')
    status=preserve.document(preserve.read(output/'status.json',private=True))
    if status.get('phase') not in ('prepared','applying','applied','reversing','reversed'):raise ValueError('Unknown transaction phase.')
    inspect_fences(output,digest,guard,allow_missing=recovery or status['phase']=='reversed')
    return value,status


def targets(value):
    result=[]
    for row in value['files']:
        path=Path(row['destination']);digest=preserve.sha(preserve.read(path))
        if digest not in (row['beforeSha256'],row['afterSha256']) or path.stat().st_mode&0o777!=row['mode']:
            raise ValueError('A configuration file was edited; recovery will not replace it.')
        result.append(digest)
    return result


def require_publication_owner(output,guard):
    """Once linked, configuration mutations belong to the full client journal."""
    marker=Path(output)/'client-publication.json'
    if marker.exists() or marker.is_symlink():
        owner=preserve.document(preserve.read(marker,private=True))
        if not isinstance(owner,dict) or getattr(guard,'client_publication',None)!=owner:
            raise ValueError('Use the bound client publication to change this linked configuration.')


def commit(output,digest,guard):
    """Apply/resume configuration only; retain the fence for client orchestration."""
    output=Path(output);require_publication_owner(output,guard);value,status=inspect(output,digest,guard)
    if status['phase'] not in ('prepared','applying','applied'):raise ValueError('A reversing transaction cannot be applied.')
    validate_suppliers(output,value,guard)
    targets(value);atomic(output/'status.json',encoded({'phase':'applying'}))
    for index,row in enumerate(value['files']):
        require(guard,guard.home);current=targets(value)
        if current[index]!=row['afterSha256']:
            atomic(Path(row['destination']),preserve.read(output/'after'/str(index),private=True),row['mode'])
    if targets(value)!=[row['afterSha256'] for row in value['files']]:raise ValueError('Configuration publication did not settle.')
    atomic(output/'status.json',encoded({'phase':'applied'}))
    return {'configurationApplied':True,'startupFenced':True,'activationComplete':False}


def validate_suppliers(output,value,guard):
    incoming=Path(value['incoming']);release=incoming_seal(incoming,value['artifactSha256'])
    plan=preserve.document(preserve.read(output/'stage-plan.json',private=True));changed=set(destinations(guard.home))
    for alias,target in plan.get('aliasBindings',{}).items():
        if str(Path(alias).resolve())!=target:raise ValueError('A retained package alias changed before apply.')
    for name,expected in plan['ownerInputs'].items():
        path=Path(name)
        if path in changed:continue
        actual=None if expected is None and not path.exists() and not path.is_symlink() else preserve.sha(preserve.read(path,system_supplier=name in plan.get('systemSupplierInputs',[])))
        if actual!=expected:raise ValueError('An owner or supplier input changed before apply.')
    return plan,release


def rollback(output,digest,guard):
    """Restore exact config bytes/modes; never restore databases or replay writes."""
    output=Path(output);require_publication_owner(output,guard);value,status=inspect(output,digest,guard,recovery=True);targets(value)
    if status['phase']=='reversed' and not any(inspect_fences(output,digest,guard,allow_missing=True)):
        if targets(value)!=[row['beforeSha256'] for row in value['files']]:raise ValueError('Reversed configuration changed.')
        return {'configurationRestored':True,'startupFenced':False}
    # Preparation may die between the two markers. Reverse alone may complete
    # that protection under the cold writer before changing configuration.
    for fence,exists in zip(fence_paths(guard),inspect_fences(output,digest,guard,allow_missing=True)):
        if not exists:atomic(fence,encoded(fence_identity(output,digest)),exclusive=True)
    atomic(output/'status.json',encoded({'phase':'reversing'}))
    for index in reversed(range(4)):
        require(guard,guard.home);row=value['files'][index];current=targets(value)
        if current[index]!=row['beforeSha256']:
            atomic(Path(row['destination']),preserve.read(output/'before'/str(index),private=True),row['mode'])
    if targets(value)!=[row['beforeSha256'] for row in value['files']]:raise ValueError('Configuration reverse did not settle.')
    atomic(output/'status.json',encoded({'phase':'reversed'}))
    # Deployment last: interrupted removal must not reopen managed clients.
    # A later reverse checks both identities before completing its own markers.
    for fence in reversed(fence_paths(guard)):
        inspect_fences(output,digest,guard,allow_missing=True)
        fence.unlink();fd=os.open(fence.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(fd)
        finally:os.close(fd)
    return {'configurationRestored':True,'startupFenced':False}
