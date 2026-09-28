# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Owned per-user native messaging registration; never edit browser profiles/policy."""
from pathlib import Path
import winreg
from .browser_identity import extension_origin
from .private_files import atomic_json, read_json, require_directory

HOST = 'com.augmentor.agent'
KEYS = tuple(path+'\\NativeMessagingHosts\\'+HOST for path in (
    r'Software\Google\Chrome', r'Software\Chromium', r'Software\Microsoft\Edge'))
VIEW = winreg.KEY_WOW64_64KEY  # HKCU Software is shared; do not invent a WOW6432Node subtree.


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
