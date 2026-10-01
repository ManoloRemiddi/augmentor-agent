#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Qualify Codex's real Linux store in a disposable D-Bus/keyring session.

Uses synthetic values and a new encrypted keyring. Never connects to the owner's
session bus, changes their default collection or installs a system service.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]


def inside(node):
    import secretstorage
    control = Path(os.environ['XDG_RUNTIME_DIR']) / 'keyring'
    control.mkdir(mode=0o700)
    os.environ['GNOME_KEYRING_CONTROL'] = str(control)
    daemon = subprocess.Popen(['gnome-keyring-daemon', '--foreground', '--components=secrets',
                               '--control-directory', str(control), '--unlock'],
                              stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        daemon.stdin.write(('synthetic-unlock-' + uuid.uuid4().hex + '\n').encode())
        daemon.stdin.close()
        ready = False
        for _ in range(100):
            if daemon.poll() is not None:
                raise RuntimeError('Disposable Secret Service stopped before readiness.')
            # Read only the bus daemon until our service owns its name. Calling
            # ReadAlias earlier can auto-start a competing daemon in empty state.
            owner = subprocess.run(['dbus-send', '--session', '--print-reply',
                                    '--dest=org.freedesktop.DBus', '/org/freedesktop/DBus',
                                    'org.freedesktop.DBus.NameHasOwner', 'string:org.freedesktop.secrets'],
                                   capture_output=True, text=True, check=True, timeout=2)
            if 'boolean true' not in owner.stdout:
                time.sleep(.05)
                continue
            try:
                connection = secretstorage.dbus_init()
                try:
                    ready = not secretstorage.get_default_collection(connection).is_locked()
                finally:
                    connection.close()
            except secretstorage.exceptions.SecretStorageException:
                pass
            if ready:
                break
            time.sleep(.05)
        if not ready:
            raise RuntimeError('Disposable Secret Service did not unlock its new collection.')
        subprocess.run([node, str(ROOT / 'scripts/proof-codex-credentials.mjs')],
                       cwd=ROOT, check=True, timeout=90,
                       env={**os.environ, 'AUGMENTOR_PYTHON': sys.executable})
    finally:
        if daemon.poll() is None:
            daemon.terminate()
            try:
                daemon.wait(timeout=5)
            except subprocess.TimeoutExpired:
                daemon.kill()
                daemon.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', default=shutil.which('node'))
    parser.add_argument('--inside', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.platform != 'linux' or not args.node:
        parser.error('This proof requires Linux and a Node executable.')
    if args.inside:
        inside(args.node)
        return
    with tempfile.TemporaryDirectory(prefix='augmentor-codex-keyring-') as directory:
        root = Path(directory)
        for name in ('run', 'config', 'data', 'state'):
            (root / name).mkdir(mode=0o700)
        env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': directory,
               'LANG': 'C.UTF-8', 'XDG_RUNTIME_DIR': str(root / 'run'),
               'XDG_CONFIG_HOME': str(root / 'config'), 'XDG_DATA_HOME': str(root / 'data'),
               'XDG_STATE_HOME': str(root / 'state'), 'PYTHONDONTWRITEBYTECODE': '1'}
        subprocess.run(['dbus-run-session', '--', sys.executable, str(Path(__file__).resolve()),
                        '--inside', '--node', args.node], env=env, cwd=ROOT, check=True, timeout=110)


if __name__ == '__main__':
    main()
