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

ROOT = Path(__file__).resolve().parents[1]


def install(root, python, node, dsh_service=None, enable=True):
    data = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))/'augmentor'
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (data/'deployment.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _install(root, python, node, dsh_service, enable)


def _install(root, python, node, dsh_service=None, enable=True):
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
    if dsh_service:
        shared = Path(os.environ.get('AUGMENTOR_SHARED_CONFIG', config/'augmentor'))
        selected = json.loads((shared/'harnesses.json').read_text())['dsh']
        manifest.update(dshEndpoint=selected['endpoint'], dshHome=str(Path(selected['home']).resolve()))
    files = {
        launch:(ROOT/'scripts/desktop-launch.py').read_text(),
        data/'augmentor/desktop-deployment.py':(ROOT/'scripts/desktop-deployment.py').read_text(),
        data/'augmentor/desktop.json':json.dumps(manifest, indent=2)+'\n',
        entry:'#!/bin/sh\nexec /usr/bin/python3 '+shlex.quote(str(launch))+' "$@"\n',
        binary/'augmentor-recover':'#!/bin/sh\nexec /usr/bin/python3 '+shlex.quote(str(launch))+' --recover\n',
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
    # Retire the hard-coded login script and old voice shortcut as aliases so
    # cached KDE launch paths cannot select another build.
    files[data/'augmentor/autostart.py'] = '#!/usr/bin/python3\nimport os\nos.execv('+repr(str(entry))+', ['+repr(str(entry))+', "--autostart"])\n'
    files[binary/'augmentor-voice-preview'] = '#!/bin/sh\nexec '+shlex.quote(str(entry))+' "$@"\n'
    global_entry = data/'kglobalaccel/com.augmentor.Agent.desktop'
    if global_entry.exists(): files[global_entry] = files[old]
    global_secondary = data/'kglobalaccel/com.augmentor.Agent.secondary.desktop'
    if global_secondary.exists(): files[global_secondary] = files[secondary]
    backup = Path(tempfile.mkdtemp(prefix='startup-'+time.strftime('%Y%m%d-') , dir=_directory(state/'augmentor-recovery')))
    for index, (path, content) in enumerate(files.items()):
        if path.exists(): shutil.copy2(path, backup/(str(index)+'-'+path.name))
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name+'.new')
        temporary.write_text(content); temporary.chmod(0o700 if path.parent == binary else 0o600)
        os.replace(temporary, path)
    (backup/'paths.json').write_text(json.dumps([str(p) for p in files], indent=2)+'\n')
    if enable:
        subprocess.run(['systemctl','--user','daemon-reload'], check=True)
        subprocess.run(['systemctl','--user','enable','augmentor-desktop.service'], check=True)
    print('Startup installed; existing windows were not restarted. Backup: '+str(backup))
    return manifest


def _directory(path):
    path.mkdir(parents=True, exist_ok=True, mode=0o700); return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--node', type=Path, required=True)
    parser.add_argument('--dsh-service')
    args = parser.parse_args()
    install(args.root, args.python, args.node, args.dsh_service)
