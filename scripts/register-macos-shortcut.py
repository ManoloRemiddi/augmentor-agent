#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Manage the installed desktop's per-user login shortcut service."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import stat
import subprocess
import sys
import tempfile
import time

LABEL = 'com.augmentor.Agent.shortcut'


def definition(app):
    root = app/'Contents/Resources/app'
    base = Path.home()/'Library/Application Support/Augmentor'
    environment = {key:os.environ.get(key, str(base/child)) for key, child in (
        ('XDG_CONFIG_HOME','config'), ('XDG_DATA_HOME','data'), ('XDG_STATE_HOME','state'))}
    environment['XDG_RUNTIME_DIR'] = os.environ.get('XDG_RUNTIME_DIR', f'/tmp/augmentor-{os.getuid()}')
    return {'Label': LABEL,
            'ProgramArguments': [str(root/'python/bin/python3'), '-I', '-B',
                                 str(root/'scripts/launch-component.py'), 'shortcut-service'],
            'EnvironmentVariables': environment, 'RunAtLoad': True, 'KeepAlive': True,
            'ThrottleInterval': 10, 'LimitLoadToSessionType': 'Aqua', 'ProcessType': 'Interactive'}


def validate(app):
    if app.is_symlink() or not app.is_dir():raise ValueError('Choose an installed application directory.')
    info = plistlib.loads((app/'Contents/Info.plist').read_bytes())
    if info.get('CFBundleIdentifier') != 'com.augmentor.Agent':
        raise ValueError('This is not Augmentor Agent Desktop.')
    root = app/'Contents/Resources/app'
    for relative in ('python/bin/python3', 'scripts/launch-component.py',
                     'apps/native/augmentor_linux/macos_shortcut_service.py'):
        if not (root/relative).is_file():raise ValueError('Install a candidate with shortcut-service support first.')
    subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(app)], check=True)


def control(*arguments):
    return subprocess.run(['/bin/launchctl', *arguments], capture_output=True, text=True, timeout=30)


def manage(app, action, directory=None):
    directory = directory or Path.home()/'Library/LaunchAgents'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise ValueError('LaunchAgents must be an owned directory without group or public write access.')
    path = directory/(LABEL+'.plist')
    expected = definition(app)
    exists = path.exists() or path.is_symlink()
    if exists:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise ValueError('Refusing an unowned or linked shortcut registration.')
        if plistlib.loads(path.read_bytes()) != expected:
            raise ValueError('A different shortcut registration exists. Remove it using its original application path and environment first.')
    target = f'gui/{os.getuid()}/{LABEL}'
    state = control('print', target)
    if state.returncode not in (0, 113):
        raise RuntimeError(state.stderr.strip() or 'Could not inspect the login service.')
    loaded = state.returncode == 0
    if loaded and (not exists or f'path = {path}' not in [line.strip() for line in state.stdout.splitlines()]):
        raise ValueError('The loaded service does not belong to this registration.')
    if action == 'status':
        return {'registered': exists, 'loaded': loaded, 'path': str(path)}
    if action in ('stop', 'remove'):
        if loaded:
            result = control('bootout', target)
            if result.returncode:raise RuntimeError(result.stderr.strip() or 'Could not stop the shortcut service.')
            deadline = time.monotonic()+30
            while True:
                state = control('print', target)
                if state.returncode == 113:break
                if state.returncode != 0 or time.monotonic() >= deadline:
                    raise RuntimeError('Shortcut service shutdown has not completed. Registration was retained; retry stop before restarting or updating.')
                time.sleep(0.1)
        if action == 'remove' and exists:path.unlink()
        return {'registered': action != 'remove' and exists, 'loaded': False, 'path': str(path)}
    if not exists:
        if action != 'install':raise ValueError('Install the shortcut registration before starting it.')
        descriptor, temporary = tempfile.mkstemp(prefix='.augmentor-shortcut-', dir=directory)
        try:
            with os.fdopen(descriptor, 'wb') as stream:
                plistlib.dump(expected, stream);stream.flush();os.fsync(stream.fileno())
            # Exclusive link makes a concurrent registration a refusal, not an overwrite.
            os.link(temporary, path)
        finally:Path(temporary).unlink(missing_ok=True)
    if not loaded:
        result = control('bootstrap', f'gui/{os.getuid()}', str(path))
        if result.returncode:
            raise RuntimeError((result.stderr.strip() or 'Could not start the shortcut service.') +
                               ' Registration was retained; use start to retry or remove to unregister.')
    return {'registered': True, 'loaded': True, 'path': str(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app', type=Path)
    parser.add_argument('action', choices=('install','start','stop','remove'))
    args = parser.parse_args()
    if sys.platform != 'darwin' or os.getuid() == 0:
        parser.error('Run as the ordinary logged-in macOS user.')
    app = args.app.expanduser().absolute()
    # Stopping/removing must remain possible after the app is moved or damaged.
    if args.action in ('install','start'):validate(app)
    print(json.dumps(manage(app, args.action)))


if __name__ == '__main__':main()
