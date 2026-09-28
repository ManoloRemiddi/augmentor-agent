# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Owned per-user native messaging registration; never edit browser profiles/policy."""
from pathlib import Path
import hashlib
import json
import os
import secrets
import shutil
import stat
import sysconfig
import winreg
from .browser_identity import extension_origin
from .private_files import atomic_json, read_json, require_directory

HOST = 'com.augmentor.agent'
KEYS = tuple(path+'\\NativeMessagingHosts\\'+HOST for path in (
    r'Software\Google\Chrome', r'Software\Chromium', r'Software\Microsoft\Edge'))
VIEW = winreg.KEY_WOW64_64KEY  # HKCU Software is shared; do not invent a WOW6432Node subtree.
INSTALL_KEY = r'Software\Augmentor\Installation'


def installed_root(root, *, key_path=INSTALL_KEY):
    """Require the installer's stable anchor; never register a source/preview path."""
    from .windows_identity import reject_reparse_ancestors
    root = Path(root).absolute()
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ | VIEW) as key:
        identity, identity_kind = winreg.QueryValueEx(key, 'AppId')
        location, location_kind = winreg.QueryValueEx(key, 'Root')
    if identity_kind != winreg.REG_SZ or identity != 'com.augmentor.Agent' or location_kind != winreg.REG_SZ:
        raise ValueError('The installed Augmentor identity is unavailable. Repair the installation.')
    if not isinstance(location, str) or Path(location) != root or not root.is_absolute():
        raise ValueError('Open the installed Augmentor application before preparing your browser.')
    reject_reparse_ancestors(root)
    release = json.loads((root/'release.json').read_text(encoding='utf-8'))
    target = {'win-amd64':'windows-x64','win-arm64':'windows-arm64'}.get(sysconfig.get_platform())
    if not target or release.get('target') != target:
        raise ValueError('The installed companion does not match this Windows runtime.')
    if not all((root/name).is_file() for name in ('Augmentor.exe','AugmentorBrowserHost.exe')):
        raise ValueError('The installed browser companion is incomplete. Repair the installation.')
    return root


def extension_files(directory, *, private=False):
    """Read bounded ordinary files, inspecting directories before descending."""
    from .private_files import descriptor
    from .windows_identity import reject_reparse_ancestors
    root = Path(directory); reject_reparse_ancestors(root)
    result = {}; pending = [root]; total = 0
    while pending:
        folder = pending.pop()
        if private: require_directory(folder)
        for file in folder.iterdir():
            info = file.lstat()
            if getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise ValueError('The extension contains an unexpected link. Existing files were preserved.')
            if stat.S_ISDIR(info.st_mode):
                pending.append(file); continue
            if not stat.S_ISREG(info.st_mode) or info.st_size > 16*1024*1024:
                raise ValueError('The extension contains an unsupported file.')
            total += info.st_size
            if total > 64*1024*1024 or len(result) >= 4096:
                raise ValueError('The extension exceeds its supported size.')
            if private:
                with os.fdopen(descriptor(file), 'rb') as stream: content = stream.read(16*1024*1024+1)
            else: content = file.read_bytes()
            if len(content) != info.st_size: raise ValueError('The extension changed during preparation.')
            result[file.relative_to(root).as_posix()] = content
    if 'manifest.json' not in result: raise ValueError('The browser extension manifest is missing.')
    return result


def prepare_extension(root, browser, *, key_path=INSTALL_KEY, keys=KEYS):
    from .paths import private_directory
    from .private_files import descriptor
    from .windows_browsers import browser_application
    browser_application(browser)
    try: root = installed_root(root, key_path=key_path)
    except FileNotFoundError:
        raise ValueError('Install Augmentor and open that copy before preparing your browser.') from None
    source = root/'apps/browser/extension'
    value = manifest(root/'AugmentorBrowserHost.exe', source/'manifest.json')
    files = extension_files(source)
    hashes = {name:hashlib.sha256(content).hexdigest() for name,content in files.items()}
    identity = hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:16]
    parent = private_directory(Path(os.environ['XDG_DATA_HOME'])/'browser-extensions')
    destination = parent/identity
    if destination.exists() or destination.is_symlink():
        if extension_files(destination,private=True) != files:
            raise ValueError('The prepared extension was edited. Its files were preserved.')
    else:
        # tempfile's default Windows owner can be the Administrators group on
        # an elevated token. Create the staging directory through the same
        # explicit current-user/SYSTEM ACL adapter as persistent data.
        temporary = private_directory(parent/('.prepare-'+secrets.token_hex(16)))
        try:
            for name,content in files.items():
                file = temporary/name; private_directory(file.parent)
                with os.fdopen(descriptor(file,writable=True,exclusive=True), 'wb') as stream:
                    stream.write(content); stream.flush(); os.fsync(stream.fileno())
            temporary.rename(destination)
        finally:
            if temporary.exists(): shutil.rmtree(temporary)
    host = private_directory(Path(os.environ['XDG_DATA_HOME'])/'browser-native-host')/(HOST+'.json')
    result = register(value,host,keys=keys)
    return {**result,'extensionDirectory':str(destination),'extensionId':value['allowed_origins'][0].split('/')[2]}


def manifest(executable, extension_manifest):
    executable = Path(executable)
    if not executable.is_absolute() or executable.name != 'AugmentorBrowserHost.exe' or not executable.is_file():
        raise ValueError('Browser setup requires the installed native companion.')
    # Preserve the stable current/ spelling; resolving the installer junction
    # here would pin the browser to a replaceable version directory.
    return {'name': HOST, 'description': 'Augmentor Agent', 'path': str(executable),
            'type': 'stdio', 'allowed_origins': [extension_origin(Path(extension_manifest))]}


def _value(key):
    try: value, kind = winreg.QueryValueEx(key, '')
    except FileNotFoundError: return None
    if kind != winreg.REG_SZ: raise ValueError('An unfamiliar browser companion registration was preserved.')
    return value


def current(path):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ | VIEW) as key:
            return _value(key)
    except FileNotFoundError: return None


def _remove_value(path, expected):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE | VIEW) as key:
            value = _value(key)
            if value is None: return False
            if value != expected: raise ValueError('A changed browser companion registration was preserved.')
            winreg.DeleteValue(key, '')
            empty = winreg.QueryInfoKey(key)[:2] == (0, 0)
        if empty:
            # A concurrent unrelated value/subkey must never be recursively removed.
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ | VIEW) as key:
                if winreg.QueryInfoKey(key)[:2] != (0, 0): return True
            winreg.DeleteKeyEx(winreg.HKEY_CURRENT_USER, path, VIEW)
        return True
    except FileNotFoundError: return False


def register(value, manifest_path, *, keys=KEYS):
    manifest_path = Path(manifest_path).absolute()
    require_directory(manifest_path.parent)
    expected = str(manifest_path)
    # Preflight all destinations before any mutation.
    for path in keys:
        if current(path) not in (None, expected):
            raise ValueError('Another installation owns the browser companion. Its registration was preserved.')
    exists = manifest_path.exists() or manifest_path.is_symlink()
    if exists and read_json(manifest_path) != value:
        raise ValueError('The existing browser companion manifest differs and was preserved.')
    if not exists: atomic_json(manifest_path, value)
    changed = []
    try:
        for path in keys:
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE | VIEW) as key:
                previous = _value(key)
                if previous == expected: continue
                if previous is not None: raise ValueError('The browser companion registration changed during setup.')
                winreg.SetValueEx(key, '', 0, winreg.REG_SZ, expected)
                changed.append(path)
    except BaseException:
        # Roll back only values written by this attempt, never a later change.
        for path in reversed(changed):
            if current(path) == expected: _remove_value(path, expected)
        if not exists and not any(current(path) == expected for path in keys) and read_json(manifest_path) == value:
            manifest_path.unlink()
        raise
    return {'manifest': expected, 'changed': bool(changed or not exists), 'keys': list(keys)}


def unregister(value, manifest_path, *, keys=KEYS):
    manifest_path = Path(manifest_path).absolute()
    expected = str(manifest_path)
    for path in keys:
        if current(path) not in (None, expected):
            raise ValueError('Another installation owns the browser companion. Its registration was preserved.')
    exists = manifest_path.exists() or manifest_path.is_symlink()
    if exists and read_json(manifest_path) != value:
        raise ValueError('The browser companion manifest changed and was preserved.')
    changed = False
    for path in keys: changed = _remove_value(path, expected) or changed
    if exists:
        # All registry operations succeeded. Refuse an intervening manifest edit.
        if read_json(manifest_path) != value: raise ValueError('The browser companion manifest changed during removal.')
        manifest_path.unlink(); changed = True
    return {'manifest': expected, 'changed': changed}
