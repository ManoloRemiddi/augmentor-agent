# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Read installed browser registrations; accept a user-selected Chromium executable.

Discovery is a convenience, not a browser-brand allowlist. Inspection never runs
the selected executable or reads its profile. A real extension handshake remains
the final compatibility check.
"""
import ctypes
from ctypes import wintypes
from pathlib import Path
import re
import winreg


def command_executable(command):
    if not isinstance(command, str) or not command.strip() or '\x00' in command or len(command)>32767:
        raise ValueError('Invalid registered browser command.')
    parse = ctypes.WinDLL('shell32', use_last_error=True).CommandLineToArgvW
    parse.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    parse.restype = ctypes.POINTER(wintypes.LPWSTR)
    free = ctypes.WinDLL('kernel32', use_last_error=True).LocalFree
    free.argtypes = [wintypes.HLOCAL]; free.restype = wintypes.HLOCAL
    count = ctypes.c_int()
    arguments = parse(command, ctypes.byref(count))
    if not arguments: raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not count.value: raise ValueError('The browser command is empty.')
        path = Path(arguments[0])
        if not path.is_absolute() or path.suffix.casefold() != '.exe':
            raise ValueError('The browser command does not name an absolute executable.')
        return path
    finally: free(arguments)


def browser_application(app):
    import win32api
    app = Path(app).expanduser().resolve(strict=True)
    if app.suffix.casefold() != '.exe' or not app.is_file() or app.drive.startswith('\\\\'):
        raise ValueError('Choose a locally installed Chromium browser executable (.exe).')
    # Chrome/Edge and forks can place resources beside the executable or in a
    # single version child directory, with a renamed *_100_percent.pak file.
    candidates = [app.parent, *(p for p in app.parent.iterdir() if p.is_dir() and re.fullmatch(r'\d+(?:\.\d+){1,4}', p.name))]
    resources = next((folder for folder in candidates if
        all((folder/name).is_file() for name in ('resources.pak', 'icudtl.dat')) and
        any(path.is_file() for path in folder.glob('*_100_percent.pak'))), None)
    if resources is None: raise ValueError('The selected application does not contain the required Chromium browser resources.')
    try:
        translations = win32api.GetFileVersionInfo(str(app), r'\VarFileInfo\Translation')
        labels = {}
        for language, codepage in translations:
            for key in ('ProductName', 'FileDescription', 'ProductVersion'):
                try:
                    value = win32api.GetFileVersionInfo(str(app), f'\\StringFileInfo\\{language:04x}{codepage:04x}\\{key}')
                    if isinstance(value, str) and value.strip(): labels.setdefault(key, value.strip())
                except win32api.error: pass
        name = labels.get('ProductName') or labels.get('FileDescription')
        if not name: raise ValueError('The selected executable has no product identity.')
    except win32api.error as error: raise ValueError('The selected executable has no readable product identity.') from error
    return {'app': str(app), 'executable': str(app), 'name': name,
            'version': labels.get('ProductVersion'), 'engineResources': str(resources)}


def _string(hive, path, name, view):
    with winreg.OpenKey(hive, path, 0, winreg.KEY_READ | view) as key:
        value, kind = winreg.QueryValueEx(key, name)
    if kind != winreg.REG_SZ or not isinstance(value, str): raise ValueError('Unexpected browser registration.')
    return value


def installed_browsers(*, hives=None, registered_path=r'Software\RegisteredApplications', classes_path=r'Software\Classes'):
    hives = hives or (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE)
    found = {}
    for hive in hives:
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(hive, registered_path, 0, winreg.KEY_READ | view) as registered:
                    values = [winreg.EnumValue(registered, index) for index in range(min(winreg.QueryInfoKey(registered)[1], 4096))]
            except OSError: continue
            for _label, capabilities, kind in values:
                if kind != winreg.REG_SZ or not isinstance(capabilities, str) or not capabilities.casefold().startswith('software\\'): continue
                try:
                    identifiers = [_string(hive, capabilities+r'\URLAssociations', protocol, view) for protocol in ('https', 'http')]
                    if any(not re.fullmatch(r'[A-Za-z0-9_.-]{1,256}', value) for value in identifiers): continue
                    paths = []
                    for identifier in identifiers:
                        command = None
                        for source in hives:
                            try:
                                command = _string(source, classes_path+'\\'+identifier+r'\shell\open\command', '', view); break
                            except (OSError, ValueError): continue
                        if command is None: raise ValueError('Missing browser launch registration.')
                        paths.append(command_executable(command))
                    if paths[0] != paths[1]: continue
                    details = browser_application(paths[0])
                    found.setdefault(details['app'].casefold(), details)
                except (OSError, ValueError): continue
    return sorted(found.values(), key=lambda item: (item['name'].casefold(), item['app'].casefold()))
