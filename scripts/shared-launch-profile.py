# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Explicit Linux shared-store launch binding; never discover or migrate data."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import pwd

SCHEMA = 'augmentor-shared-launch-binding/1'
DATABASES = ('prompts.sqlite3', 'dual-memory.sqlite3', 'memory.sqlite3')
KNOWN = {*DATABASES, 'hindsight.json', 'hindsight-installation.json', 'shared-imports',
         *(name+tail for name in DATABASES for tail in ('-wal', '-shm', '-journal'))}


def directory(value):
    if not isinstance(value, str) or not value or len(value)>4096 or any(ord(c)<32 for c in value):
        raise ValueError('Choose canonical absolute shared-store paths.')
    path = Path(value)
    if not path.is_absolute() or str(path)!=value or str(path.resolve())!=value:
        raise ValueError('Shared-store paths cannot contain aliases or links.')
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:
        raise ValueError('Shared-store directories must be private and owned.')
    return path


def profile(value, dedicated=True):
    if sys.platform!='linux':
        raise ValueError('Selected shared-store launch binding is qualified only on Linux.')
    if not isinstance(value, dict) or set(value)!={'state','data'}:
        raise ValueError('Choose one explicit shared state/data pair.')
    state, data = (directory(value[key]) for key in ('state','data'))
    if state.is_relative_to(data) or data.is_relative_to(state):
        raise ValueError('Shared state and data must not overlap.')
    if (data.parent/('.'+data.name+'.augmentor-migration.json')).exists():
        raise ValueError('An unfinished shared-store migration requires recovery.')
    for path in (state,data):
        for location in (path,*path.parents):
            if re.fullmatch(r'\..+\.import-[-a-f0-9]{36}\.(stage|backup)',location.name) or re.search(r'/(shared-imports/[a-f0-9]{64}/data|native-imports/[a-f0-9]{64}/state)$',location.as_posix()):
                raise ValueError('Migration evidence cannot be selected as active shared paths.')
    if len(os.fsencode(state/'dual-memory.sock'))>103:
        raise ValueError('The shared Unix socket path is too long.')
    if dedicated:
        if any(child.name not in KNOWN for child in data.iterdir()):
            raise ValueError('Select dedicated shared data, not a mixed application root.')
    for name in DATABASES:
        info=(data/name).lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_nlink!=1 or info.st_mode&0o077:
            raise ValueError('Selected shared databases must be private owned regular files.')
    return dict(value)


def environment(value, initial):
    # A qualified active store may later acquire legitimate engine backups.
    # The strict component inventory is for choosing a new cold target only.
    pair=profile(value,dedicated=False)
    # The selected binding is authoritative for installed product entrypoints.
    # Explicit standalone/developer profile launchers do not use this adapter.
    return {**initial, 'AUGMENTOR_SHARED_STATE':pair['state'], 'AUGMENTOR_SHARED_DATA':pair['data']}


def private_json(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_nlink!=1 or info.st_mode&0o077 or info.st_size>16384:
            raise ValueError('Choose a bounded private owned binding manifest.')
        raw=os.read(fd,16385)
        if len(raw)>16384:raise ValueError('Binding manifest exceeds its bound.')
        return json.loads(raw)
    finally:os.close(fd)


def binding(path, selection_bytes, previous, dedicated_next=True):
    value=private_json(path)
    if not isinstance(value,dict) or set(value)!={'schema','previous','next','selectionSha256','targetSha256'} or value['schema']!=SCHEMA:
        raise ValueError('Unsupported shared launch binding manifest.')
    if value['selectionSha256']!=hashlib.sha256(selection_bytes).hexdigest():
        raise ValueError('Desktop selection changed since binding preparation.')
    if not isinstance(value['targetSha256'],str) or not re.fullmatch('[a-f0-9]{64}',value['targetSha256']):
        raise ValueError('Inspect the exact cold target before choosing its launch binding.')
    profile(value['previous'],dedicated=False);profile(value['next'],dedicated=dedicated_next)
    before,after=value['previous'],value['next']
    if before['data']!=after['data'] and (Path(before['data']).is_relative_to(after['data']) or Path(after['data']).is_relative_to(before['data'])):
        raise ValueError('Previous and next shared data must not overlap.')
    for state in (before['state'],after['state']):
        for data in (before['data'],after['data']):
            if Path(state).is_relative_to(data) or Path(data).is_relative_to(state):
                raise ValueError('Shared state and data cannot overlap across binding pairs.')
    if 'sharedProfile' in previous and previous['sharedProfile']!=value['previous']:
        raise ValueError('The previous shared pair differs from the selected binding.')
    return value


@contextmanager
def launch_lease(data, exclusive=False):
    """Inherited reader lasts through exec; a cold binding change owns the writer.

    Build-only updates keep using the deployment lock and may select a future
    build while clients run. This gate applies to shared-store changes only.
    """
    data=Path(data);data.mkdir(parents=True,mode=0o700,exist_ok=True);directory(str(data))
    path=data/'shared-launch.lock';fd=os.open(path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        a,b=os.fstat(fd),path.lstat()
        if not stat.S_ISREG(a.st_mode) or a.st_uid!=os.getuid() or a.st_mode&0o077 or a.st_nlink!=1 or (a.st_dev,a.st_ino)!=(b.st_dev,b.st_ino):
            raise ValueError('The shared launch gate must be private and owned.')
        try:fcntl.flock(fd,(fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)|fcntl.LOCK_NB)
        except BlockingIOError as error:raise ValueError('Shared launch maintenance or an existing managed client is active.') from error
        os.set_inheritable(fd,not exclusive)
        yield
    finally:os.close(fd)


def assert_no_clients(pairs):
    """Refuse known product clients/companions; do not stop or signal anything.

    Arbitrary old custom scripts are not discoverable. The cold operator must
    still identify and stop all legacy callers before preparing this manifest.
    """
    wanted={v[key] for v in pairs for key in ('state','data')}
    for process in Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name)==os.getpid():continue
        try:
            if process.stat().st_uid!=os.getuid():continue
            args=(process/'cmdline').read_bytes().split(b'\0')
            known=any(a in (b'augmentor_linux',b'augmentor_linux.macos_shortcut_service') or
                      a.endswith((b'/apps/mobile/native_runner.py',b'/apps/mobile/start.py',b'/apps/browser/native-host.mjs',b'/apps/browser/pi-bridge.mjs',b'/apps/browser/codex-bridge.mjs',b'/apps/browser/pipe.mjs',b'/dist/runtime/src/main.js',b'/services/memory/service.py',b'/services/prompt-library/service.py')) for a in args)
            if not known:continue
            env=dict(row.split('=',1) for row in (process/'environ').read_text().split('\0') if '=' in row)
            home=Path(env.get('HOME',pwd.getpwuid(os.getuid()).pw_dir))
            state=env.get('AUGMENTOR_SHARED_STATE',str(Path(env.get('XDG_STATE_HOME',home/'.local/state'))/'augmentor'))
            data=env.get('AUGMENTOR_SHARED_DATA',str(Path(env.get('XDG_DATA_HOME',home/'.local/share'))/'augmentor'))
            cwd=(process/'cwd').resolve()
            state=str((Path(state) if Path(state).is_absolute() else cwd/state).resolve())
            data=str((Path(data) if Path(data).is_absolute() else cwd/data).resolve())
            if state in wanted or data in wanted:
                raise ValueError('Close existing Native, Browser, Harness and companion callers for both shared pairs before changing this binding.')
        except (FileNotFoundError,ProcessLookupError):continue


@contextmanager
def cold(pairs):
    descriptors=[]
    try:
        assert_no_clients(pairs)
        paths=set()
        for pair in pairs:
            data=Path(pair['data']);parent=data.parent.stat()
            if parent.st_uid!=os.getuid() or parent.st_mode&0o022:
                raise ValueError('Shared data parent must be owned and protected from other writers.')
            paths.add(data.parent/('.'+data.name+'.augmentor-owner.lock'))
            paths.update(Path(pair['state'])/(name+'.lock') for name in ('prompts','dual-memory'))
        for path in sorted(paths):
            fd=os.open(path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600);descriptors.append(fd)
            a,b=os.fstat(fd),path.lstat()
            if not stat.S_ISREG(a.st_mode) or a.st_uid!=os.getuid() or a.st_mode&0o077 or a.st_nlink!=1 or (a.st_dev,a.st_ino)!=(b.st_dev,b.st_ino):
                raise ValueError('Shared launch maintenance needs private owned kernel leases.')
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError as error:raise ValueError('Stop both shared companion owners before changing the launch binding.') from error
        assert_no_clients(pairs)
        yield
    finally:
        while descriptors:os.close(descriptors.pop())


def component_fingerprint(pair):
    data=Path(pair['data']);rows=[];total=0
    for name in DATABASES:
        if any((data/(name+tail)).exists() for tail in ('-wal','-shm','-journal')):
            raise ValueError('Recover and cleanly stop SQLite journals before binding inspection.')
    for name in (*DATABASES,'hindsight.json','hindsight-installation.json'):
        path=data/name
        try:fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        except FileNotFoundError:
            if name in DATABASES:raise
            continue
        try:
            before=os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_uid!=os.getuid() or before.st_nlink!=1 or before.st_mode&0o077 or before.st_size>(1024**2 if name.endswith('.json') else 2*1024**3):
                raise ValueError('Binding inspection requires bounded private owned component files.')
            total+=before.st_size
            if total>4*1024**3:raise ValueError('Shared launch components exceed four GiB.')
            digest=hashlib.sha256();size=0
            while chunk:=os.read(fd,1024**2):
                size+=len(chunk)
                if size>before.st_size:raise ValueError('Shared components grew during binding inspection.')
                digest.update(chunk)
            after=os.fstat(fd)
            if size!=before.st_size or (before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_size,after.st_mtime_ns,after.st_ctime_ns):
                raise ValueError('Shared components changed during binding inspection.')
            rows.append({'name':name,'mode':before.st_mode&0o777,'bytes':size,'sha256':digest.hexdigest()})
        finally:os.close(fd)
    return hashlib.sha256(json.dumps(rows,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def verify_target(config,value):
    root=Path(config['root'])
    if component_fingerprint(value['next'])!=value['targetSha256']:
        raise ValueError('Shared target changed since its cold inspection.')
    # Same read-only schema/integrity checker used by the cold export. No service
    # objects, model work or engine clients are constructed.
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
    run=subprocess.run([config['python'],'-I','-B',str(root/'services/companion_import.py')],input=json.dumps({'action':'validate','data':value['next']['data']}),capture_output=True,text=True,env=env,timeout=120)
    if run.returncode:raise ValueError('The selected shared target failed cold database validation.')
    assert_target(value)


def assert_target(value):
    if component_fingerprint(value['next'])!=value['targetSha256']:
        raise ValueError('Shared target changed before launch binding publication.')


if __name__=='__main__':
    if len(sys.argv)!=3 or sys.argv[1]!='inspect':raise SystemExit('Use inspect PRIVATE_STATE_DATA_PAIR_JSON after stopping its callers.')
    pair=profile(private_json(sys.argv[2]),dedicated=False)
    with cold([pair]):print(json.dumps({'schema':'augmentor-shared-launch-inspection/1','sharedProfile':pair,'sha256':component_fingerprint(pair)}))
