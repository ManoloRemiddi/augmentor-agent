#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Register the installed macOS companion without modifying its signed bundle."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import sys
import tempfile
import uuid

BROWSERS = {'chromium': 'Chromium', 'chrome': 'Google/Chrome',
            'chrome-for-testing': 'Google/ChromeForTesting'}


def manifest(app):
    app = app.resolve(strict=True)
    info = plistlib.loads((app/'Contents/Info.plist').read_bytes())
    if info.get('CFBundleIdentifier') not in ('com.augmentor.Agent','com.augmentor.Agent.Companion'):
        raise ValueError('Choose an installed Augmentor desktop or browser companion bundle.')
    launcher = app/'Contents/MacOS/augmentor-browser-host'
    if not launcher.is_file() or not os.access(launcher, os.X_OK):
        raise ValueError('The installed browser companion launcher is missing.')
    extension = app/'Contents/Resources/app/apps/browser/extension/manifest.json'
    key = json.loads(extension.read_text())['key']
    digest = hashlib.sha256(base64.b64decode(key, validate=True)).hexdigest()[:32]
    identity = ''.join(chr(ord('a')+int(n, 16)) for n in digest)
    return {'name': 'com.augmentor.agent', 'description': 'Augmentor · Pi and DSH',
            'path': str(launcher), 'type': 'stdio',
            'allowed_origins': ['chrome-extension://'+identity+'/']}


def register(value, directory):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory/'com.augmentor.agent.json'
    if path.is_symlink():
        raise ValueError('Refusing to replace a symbolic-link native host manifest.')
    payload = json.dumps(value, indent=2)+'\n'
    backup = None
    if path.exists():
        original = path.read_text()
        if original == payload:
            return {'manifest': str(path), 'changed': False, 'backup': None}
        backup = path.with_name(path.name+'.before-'+uuid.uuid4().hex)
        shutil.copy2(path, backup)
    fd, temporary = tempfile.mkstemp(prefix='.augmentor-host-', dir=directory)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return {'manifest': str(path), 'changed': True, 'backup': str(backup) if backup else None}


def unregister(value, directory):
    """Retire only this bundle's unchanged manifest; retain it for rollback."""
    path = directory/'com.augmentor.agent.json'
    if not path.exists() and not path.is_symlink():
        return {'manifest':str(path), 'changed':False, 'backup':None}
    if directory.is_symlink():
        raise ValueError('Refusing to remove a native host through a linked directory.')
    descriptor = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(descriptor) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise ValueError('Refusing to remove an unowned or linked native host manifest.')
        if info.st_size > 131072:
            raise ValueError('The native host manifest changed; it was retained.')
        try:current = json.load(stream)
        except (ValueError,UnicodeError) as error:
            raise ValueError('The native host manifest changed; it was retained.') from error
        if current != value:
            raise ValueError('The native host manifest belongs to another installation or was changed; it was retained.')
        current_info = path.lstat()
        if (current_info.st_dev,current_info.st_ino,current_info.st_mtime_ns,current_info.st_size) != (info.st_dev,info.st_ino,info.st_mtime_ns,info.st_size):
            raise ValueError('The native host manifest changed during removal; it was retained.')
        backup = path.with_name(path.name+'.removed-'+uuid.uuid4().hex)
        path.rename(backup)
    return {'manifest':str(path), 'changed':True, 'backup':str(backup)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app', type=Path)
    parser.add_argument('--browser', choices=BROWSERS, default='chromium')
    parser.add_argument('--remove', action='store_true', help='Remove only this app\'s matching registration, retaining a backup.')
    parser.add_argument('--support-root', type=Path,
                        default=Path.home()/'Library/Application Support')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('This registrar is for macOS.')
    result = (unregister if args.remove else register)(manifest(args.app.expanduser()),
                      args.support_root/BROWSERS[args.browser]/'NativeMessagingHosts')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
