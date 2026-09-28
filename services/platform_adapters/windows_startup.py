# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One per-user login entry; preserve Windows startup-disable state and foreign entries.

The installer supplies its stable current/Augmentor.exe path. Source launches
never register themselves. This module does not write StartupApproved or HKLM.
"""
from pathlib import Path
import subprocess
import winreg

RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
VALUE_NAME = 'Augmentor Agent'


def command(executable):
    path = Path(executable)
    if not path.is_absolute() or path.name != 'Augmentor.exe' or not path.is_file():
        raise ValueError('Login startup requires the installed stable Augmentor executable.')
    # Keep the installer's stable spelling (possibly current/); resolving a
    # version junction here would leave a login entry pinned to an old version.
    value = subprocess.list2cmdline([str(path), '--background'])
    if len(value) > 260: raise ValueError('The installation path is too long for Windows login startup.')
    return value


def current(*, key_path=RUN_KEY):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_QUERY_VALUE) as key:
            value, kind = winreg.QueryValueEx(key, VALUE_NAME)
    except FileNotFoundError: return None
    if kind != winreg.REG_SZ: raise ValueError('An unfamiliar startup entry was preserved.')
    return value


def install(executable, *, key_path=RUN_KEY):
    desired = command(executable)
    previous = current(key_path=key_path)
    if previous == desired: return False  # No write on updates; retain OS/user disable state.
    if previous is not None: raise ValueError('A different startup entry uses the Augmentor name. It was preserved.')
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, desired)
    return True


def remove(executable, *, key_path=RUN_KEY):
    expected = command(executable)  # Called before removing the owned program files.
    previous = current(key_path=key_path)
    if previous is None: return False
    if previous != expected: raise ValueError('A different startup entry was preserved.')
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        winreg.DeleteValue(key, VALUE_NAME)
    return True
