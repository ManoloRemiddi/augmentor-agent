#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Install a single selected desktop deployment, with backups; do not restart work."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time
import base64
import importlib.util
import stat

ROOT = Path(__file__).resolve().parents[1]


def install(root, python, node, dsh_service=None, enable=True, register_browser=False, expected_hosts=None):
    data = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))/'augmentor'
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (data/'deployment.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        spec=importlib.util.spec_from_file_location('startup_shared_launch',ROOT/'scripts/shared-launch-profile.py')
        shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
        with shared.launch_lease(data,exclusive=True):
            return _install(root, python, node, dsh_service, enable, register_browser, expected_hosts)


def _install(root, python, node, dsh_service=None, enable=True, register_browser=False, expected_hosts=None):
    root = Path(root).resolve()
    # A venv interpreter is often a symlink; resolving it loses that environment.
    python, node = (Path(p).absolute() for p in (python, node))
    for path in (root/'apps/native/augmentor_linux/window.py', root/'release/product.json', python, node):
        if not path.is_file(): raise ValueError('Missing deployment file: '+str(path))
    if '--ensure-running' not in (root/'apps/native/augmentor_linux/window.py').read_text():
        raise ValueError('Deploy the startup-capable native surface before activating its launcher.')
    data = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))
    config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))
    state = Path(os.environ.get('XDG_STATE_HOME', Path.home()/'.local/state'))
    binary = Path.home()/'.local/bin'
    launch = data/'augmentor/desktop-launch.py'
    entry = binary/'augmentor-agent'
    # These are desktop/systemd field escaping, not shell quoting.
    def field(path): return '"'+str(path).replace('\\','\\\\').replace('"','\\"').replace('$','\\$').replace('`','\\`')+'"'
    def desktop(command, name, terminal=False, extra=''):
        return '# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0\n[Desktop Entry]\nType=Application\nName='+name+'\nExec='+command+'\nIcon=com.augmentor.Agent\nTerminal='+str(terminal).lower()+'\nCategories=Utility;\nStartupWMClass=Augmentor Agent\n'+extra
    old = data/'applications/com.augmentor.Agent.desktop'
    shortcuts = ''.join(line+'\n' for line in old.read_text().splitlines() if line.startswith('X-KDE-Shortcuts=')) if old.exists() else ''
    secondary = data/'applications/com.augmentor.Agent.secondary.desktop'
    secondary_keys = ''.join(line+'\n' for line in secondary.read_text().splitlines() if line.startswith('X-KDE-Shortcuts=')) if secondary.exists() else ''
    manifest = {'root':str(root), 'python':str(python), 'node':str(node), 'dshService':dsh_service,
                'version':json.loads((root/'release/product.json').read_text())['version'],
                'windowSha256':hashlib.sha256((root/'apps/native/augmentor_linux/window.py').read_bytes()).hexdigest()}
    manifest['files'] = {name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in (
        'apps/native/augmentor_linux/window.py', 'apps/native/augmentor_linux/controller.py',
        'services/recovery/__init__.py', 'services/recovery/decode-zstd.mjs',
        'services/recovery/repair-telemetry.mjs', 'services/recovery/zstd-frames.mjs') if (root/name).is_file()}
    descriptor = data/'augmentor/desktop.json'
    if descriptor.exists():
        selected = json.loads(descriptor.read_text())
        if selected.get('releaseId'):
            if any(selected[key] != manifest[key] for key in ('root', 'python', 'node', 'dshService')):
                raise ValueError('A managed release is selected. Use augmentor-update stage/activate to change it.')
            manifest = selected
        if 'sharedProfile' in selected:
            spec=importlib.util.spec_from_file_location('retained_shared_launch',ROOT/'scripts/shared-launch-profile.py')
            shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
            manifest['sharedProfile']=shared.profile(selected['sharedProfile'],dedicated=False)
    if dsh_service:
        shared = Path(os.environ.get('AUGMENTOR_SHARED_CONFIG', config/'augmentor'))
        selected = json.loads((shared/'harnesses.json').read_text())['dsh']
        manifest.update(dshEndpoint=selected['endpoint'], dshHome=str(Path(selected['home']).resolve()))
    files = {
        data/'augmentor/shared-launch-profile.py':(ROOT/'scripts/shared-launch-profile.py').read_text(),
        data/'augmentor/desktop-browser-launch.py':(ROOT/'scripts/desktop-browser-launch.py').read_text(),
        data/'augmentor/desktop-dsh-launch.py':(ROOT/'scripts/desktop-dsh-launch.py').read_text(),
        data/'augmentor/embed-launch.py':(ROOT/'scripts/embed-launch.py').read_text(),
        launch:(ROOT/'scripts/desktop-launch.py').read_text(),
        data/'augmentor/desktop-deployment.py':(ROOT/'scripts/desktop-deployment.py').read_text(),
        data/'augmentor/desktop.json':json.dumps(manifest, indent=2)+'\n',
        entry:'#!/bin/sh\nexec /usr/bin/python3 '+shlex.quote(str(launch))+' "$@"\n',
        binary/'augmentor-recover':'#!/bin/sh\nexec /usr/bin/python3 '+shlex.quote(str(launch))+' --recover\n',
        binary/'augmentor-mobile-managed':'#!/bin/sh\nexec /usr/bin/python3 '+shlex.quote(str(launch))+' --mobile "$@"\n',
        binary/'augmentor-update':'#!/bin/sh\nexec /usr/bin/python3 '+shlex.quote(str(data/'augmentor/desktop-deployment.py'))+' "$@"\n',
        old:desktop(field(entry), 'Augmentor Agent', extra=shortcuts),
        secondary:desktop(field(entry)+' --instance secondary', 'Augmentor Agent — Second window', extra=secondary_keys),
        data/'applications/com.augmentor.Agent.recover.desktop':desktop(field(entry)+' --recover-window', 'Augmentor Agent — Recover connection', terminal=True),
        config/'autostart/com.augmentor.Agent.desktop':desktop(field(entry)+' --autostart', 'Augmentor Agent', extra='X-KDE-autostart-phase=2\n'),
        config/'systemd/user/augmentor-desktop.service':
            '[Unit]\nDescription=Augmentor Agent desktop\nPartOf=graphical-session.target\nAfter=graphical-session.target\nStartLimitIntervalSec=0\n\n'
            '[Service]\nType=exec\nExecStart=/usr/bin/python3 '+field(launch)+' --service-run\nRestart=on-failure\nRestartSec=5\nTimeoutStopSec=15\nUMask=0077\n\n'
            '[Install]\nWantedBy=graphical-session.target\n',
    }
    expectations={}
    if register_browser:
        browsers=('chromium','google-chrome','google-chrome-beta','BraveSoftware/Brave-Browser')
        if expected_hosts is not None and (not isinstance(expected_hosts,dict) or set(expected_hosts)!=set(browsers)):
            raise ValueError('Record the exact expected per-user Browser host hashes for every supported registration.')
        key=json.loads((root/'apps/browser/extension/manifest.json').read_text())['key']
        identity=''.join(chr(ord('a')+int(v,16)) for v in hashlib.sha256(base64.b64decode(key,validate=True)).hexdigest()[:32])
        host_entry=binary/'augmentor-browser-host-managed'
        launcher='#!/bin/sh\nexec /usr/bin/python3 '+shlex.quote(str(data/'augmentor/desktop-browser-launch.py'))+' "$@"\n'
        if host_entry.exists() and (host_entry.is_symlink() or host_entry.read_text()!=launcher):
            raise ValueError('The managed Browser launcher name is occupied; preserve its owner before registration.')
        files[host_entry]=launcher
        expectations[host_entry]=hashlib.sha256(host_entry.read_bytes()).hexdigest() if host_entry.exists() else None
        native={'name':'com.augmentor.agent','description':'Augmentor Agent managed deployment','path':str(host_entry),'type':'stdio','allowed_origins':['chrome-extension://'+identity+'/']}
        for browser in browsers:
            path=config/browser/'NativeMessagingHosts/com.augmentor.agent.json'
            actual=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() and not path.is_symlink() else None
            if path.is_symlink() or path.exists() and (expected_hosts is None or expected_hosts[browser]!=actual) or not path.exists() and expected_hosts is not None and expected_hosts[browser] is not None:
                raise ValueError('Browser registration changed or needs explicit adoption; prepare its exact current hashes first.')
            files[path]=json.dumps(native,indent=2)+'\n'
            expectations[path]=actual
    # Retire the hard-coded login script and old voice shortcut as aliases so
    # cached KDE launch paths cannot select another build.
    files[data/'augmentor/autostart.py'] = '#!/usr/bin/python3\nimport os\nos.execv('+repr(str(entry))+', ['+repr(str(entry))+', "--autostart"])\n'
    files[binary/'augmentor-voice-preview'] = '#!/bin/sh\nexec '+shlex.quote(str(entry))+' "$@"\n'
    global_entry = data/'kglobalaccel/com.augmentor.Agent.desktop'
    if global_entry.exists(): files[global_entry] = files[old]
    global_secondary = data/'kglobalaccel/com.augmentor.Agent.secondary.desktop'
    if global_secondary.exists(): files[global_secondary] = files[secondary]
    backup = Path(tempfile.mkdtemp(prefix='startup-'+time.strftime('%Y%m%d-') , dir=_directory(state/'augmentor-recovery')))
    write_startup_files(files,backup,binary,expectations)
    if enable:
        subprocess.run(['systemctl','--user','daemon-reload'], check=True)
        subprocess.run(['systemctl','--user','enable','augmentor-desktop.service'], check=True)
    print('Startup installed; existing windows were not restarted. Backup: '+str(backup))
    return manifest


def snapshot(path):
    if path.is_symlink():raise ValueError('Startup files cannot be symbolic links.')
    if not path.exists():return None
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_nlink!=1 or info.st_size>4*1024**2:
        raise ValueError('Startup records must be bounded owned regular files.')
    return path.read_bytes(),stat.S_IMODE(info.st_mode)


def atomic_bytes(path,content,mode):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(content);stream.flush();os.fchmod(stream.fileno(),mode);os.fsync(stream.fileno())
        os.replace(name,path)
        parent=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(parent)
        finally:os.close(parent)
    finally:
        if os.path.exists(name):os.unlink(name)


def write_startup_files(files,backup,binary,expectations):
    before={path:snapshot(path) for path in files}
    for path,expected in expectations.items():
        actual=hashlib.sha256(before[path][0]).hexdigest() if before[path] else None
        if actual!=expected:raise ValueError('Browser registration changed during startup preparation.')
    for index,(path,value) in enumerate(before.items()):
        if value is not None:
            dest=backup/(str(index)+'-'+path.name);dest.write_bytes(value[0]);dest.chmod(value[1])
    (backup/'paths.json').write_text(json.dumps([str(p) for p in files],indent=2)+'\n')
    written=[]
    try:
        for path,content in files.items():
            if snapshot(path)!=before[path]:raise ValueError('Startup or Browser registration changed before writing.')
            encoded=content.encode();atomic_bytes(path,encoded,0o700 if path.parent==binary else 0o600);written.append((path,encoded))
    except BaseException:
        changed=False
        for path,encoded in reversed(written):
            now=snapshot(path)
            if now is None or now[0]!=encoded:changed=True;continue
            if before[path] is None:path.unlink()
            else:atomic_bytes(path,*before[path])
        if changed:raise ValueError('Startup failed; concurrent edits were preserved. Inspect backup: '+str(backup))
        raise


def _directory(path):
    path.mkdir(parents=True, exist_ok=True, mode=0o700); return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--node', type=Path, required=True)
    parser.add_argument('--dsh-service')
    parser.add_argument('--register-browser',action='store_true',help='Opt in to per-user hosts following the selected deployment; retain current code/settings backups.')
    parser.add_argument('--expected-browser-hosts',type=Path,help='Private JSON object of exact current host-file hashes (null for absent). Required to replace existing registrations.')
    args = parser.parse_args()
    expected=None
    if args.expected_browser_hosts:
        path=args.expected_browser_hosts;info=path.lstat()
        if path.is_symlink() or not path.is_file() or info.st_uid!=os.getuid() or info.st_mode&0o077 or info.st_nlink!=1 or info.st_size>16384:
            raise SystemExit('Use a bounded private owned Browser host expectation record.')
        expected=json.loads(path.read_text())
    install(args.root, args.python, args.node, args.dsh_service, register_browser=args.register_browser, expected_hosts=expected)
