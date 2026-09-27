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
# Comet 153 uses Chrome's native-host compatibility location even though its
# browsing profiles live in Comet. Qualified by a real native-message exchange.
NATIVE_HOST_OVERRIDES = {'ai.perplexity.comet': 'Google/Chrome'}


def browser_application(app):
    """Inspect an app, without starting it or reading a personal browser profile."""
    app = Path(app).expanduser().resolve(strict=True)
    if app.suffix != '.app':
        raise ValueError('Choose a Chromium-based browser application (.app).')
    info = plistlib.loads((app/'Contents/Info.plist').read_bytes())
    executable = info.get('CFBundleExecutable', '')
    if not executable or Path(executable).name != executable:
        raise ValueError('The selected browser has an invalid executable.')
    binary = app/'Contents/MacOS'/executable
    schemes = {scheme.lower() for item in info.get('CFBundleURLTypes', [])
               for scheme in item.get('CFBundleURLSchemes', []) if isinstance(scheme, str)}
    # Chromium forks rename their framework, but retain these engine resources.
    resources = (app/'Contents/Frameworks').glob('*.framework/Resources')
    chromium = any(all((folder/name).is_file() for name in
                      ('chrome_100_percent.pak', 'resources.pak', 'icudtl.dat')) for folder in resources)
    if not {'http', 'https'} <= schemes or not chromium or not binary.is_file() or not os.access(binary, os.X_OK):
        raise ValueError('Choose a Chromium-based browser. This application does not have the required browser engine.')
    return {'app': str(app), 'name': info.get('CFBundleDisplayName') or info.get('CFBundleName') or app.stem,
            'executable': str(binary), 'bundleId': info.get('CFBundleIdentifier', ''),
            'productDirectory': info.get('CrProductDirName'), 'bundleName': info.get('CFBundleName', app.stem)}


def installed_browsers(roots=None):
    found = {}
    for root in roots or (Path('/Applications'), Path.home()/'Applications'):
        # Also include one organizational folder, but never nested helper apps.
        for pattern in ('*.app', '*/*.app'):
            for app in Path(root).glob(pattern):
                try:
                    browser = browser_application(app)
                    found[browser['app']] = browser
                except (OSError, ValueError, plistlib.InvalidFileException):
                    continue
    return sorted(found.values(), key=lambda item: (item['name'].casefold(), item['app']))


def checked_data_directory(directory, support_root):
    """Only ordinary user browser folders below Application Support are writable."""
    directory = Path(directory).absolute(); support_root = Path(support_root).absolute()
    try: relative = directory.relative_to(support_root)
    except ValueError: raise ValueError('Choose a browser data folder inside your Library/Application Support.') from None
    if not 1 <= len(relative.parts) <= 3 or any(part in ('.', '..') for part in relative.parts):
        raise ValueError('The browser data folder is not a supported Application Support location.')
    for path in (support_root, *[support_root.joinpath(*relative.parts[:n]) for n in range(1, len(relative.parts)+1)]):
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise ValueError('The browser data folder contains a link or unexpected file. It was preserved.')
    return directory


def browser_data_directory(browser, support_root, data_directory=None):
    if isinstance(browser, str) and browser in BROWSERS and data_directory is None:
        return checked_data_directory(support_root/BROWSERS[browser], support_root)
    details = browser_application(browser)
    if data_directory is not None:
        directory = checked_data_directory(data_directory, support_root)
        if not (directory/'Local State').is_file():
            raise ValueError('Choose the browser data folder containing Local State, not an individual profile folder.')
        return directory
    if details['bundleId'] in NATIVE_HOST_OVERRIDES:
        return checked_data_directory(support_root/NATIVE_HOST_OVERRIDES[details['bundleId']], support_root)
    # Chromium's declared product directory is authoritative when present.
    product = details['productDirectory']
    defaults = {'com.google.Chrome': 'Google/Chrome', 'com.google.Chrome.forTesting': 'Google/ChromeForTesting',
                'org.chromium.Chromium': 'Chromium'}
    if product or details['bundleId'] in defaults:
        return checked_data_directory(support_root/(product or defaults[details['bundleId']]), support_root)
    # Some forks omit CrProductDirName. Only accept an existing browser
    # data root matching the app metadata; do not guess and silently misregister.
    for name in dict.fromkeys((details['bundleName'], Path(details['app']).stem)):
        directory = checked_data_directory(support_root/name, support_root)
        if (directory/'Local State').is_file(): return directory
    raise ValueError('Open '+details['name']+' once, then try again. If it uses a different data location, choose its browser data folder below.')


def registration_directories(support_root):
    """Include selected forks in removal/recovery without a browser-brand list."""
    candidates = {support_root/value/'NativeMessagingHosts' for value in BROWSERS.values()}
    for depth in range(1, 4):
        candidates.update(support_root.glob('*/'*depth+'NativeMessagingHosts'))
    result = []
    for directory in candidates:
        try:
            checked_data_directory(directory.parent, support_root)
            if not directory.is_symlink(): result.append(directory)
        except ValueError: continue
    return sorted(result)


def prepare_extension(app, browser, support_root, data_directory=None):
    """Prepare a stable unpacked preview without writing inside the application."""
    directory = browser_data_directory(browser, support_root, data_directory)/'NativeMessagingHosts'
    if directory.is_symlink(): raise ValueError('The browser registration directory is linked. It was preserved.')
    value = manifest(app)
    source = app/'Contents/Resources/app/apps/browser/extension'
    files = {}
    for file in sorted(source.rglob('*')):
        if file.is_symlink(): raise ValueError('The bundled extension contains an unexpected link.')
        if file.is_file(): files[file.relative_to(source).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    identity = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()[:16]
    parent = support_root/'Augmentor/browser-extensions'
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if parent.is_symlink(): raise ValueError('The extension data directory is linked. It was preserved.')
    destination = parent/identity
    if destination.exists() or destination.is_symlink():
        if destination.is_symlink() or not destination.is_dir():
            raise ValueError('The prepared extension path changed. It was preserved.')
        observed = {}
        for file in destination.rglob('*'):
            if file.is_symlink(): raise ValueError('The prepared extension was edited. It was preserved.')
            if file.is_file(): observed[file.relative_to(destination).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
        if observed != files: raise ValueError('The prepared extension was edited. It was preserved.')
    else:
        temporary = Path(tempfile.mkdtemp(prefix='.prepare-', dir=parent))
        try:
            shutil.copytree(source, temporary, dirs_exist_ok=True)
            temporary.rename(destination)
        finally:
            if temporary.exists(): shutil.rmtree(temporary)
    result = register(value, directory)
    return {**result, 'extensionDirectory': str(destination), 'extensionId': value['allowed_origins'][0].split('/')[2]}


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
    if directory.is_symlink(): raise ValueError('Refusing to register through a linked native host directory.')
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
    parser.add_argument('--browser', default='chromium', help='Installed browser .app path, or a legacy browser alias.')
    parser.add_argument('--browser-data', type=Path, help='Existing browser data root containing Local State.')
    parser.add_argument('--remove', action='store_true', help='Remove only this app\'s matching registration, retaining a backup.')
    parser.add_argument('--support-root', type=Path,
                        default=Path.home()/'Library/Application Support')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('This registrar is for macOS.')
    result = (unregister if args.remove else register)(manifest(args.app.expanduser()),
                      browser_data_directory(args.browser, args.support_root, args.browser_data)/'NativeMessagingHosts')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
