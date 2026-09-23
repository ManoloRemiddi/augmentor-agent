# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Shared lifetime leases prevent package replacement underneath running code."""
import fcntl
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK_ROOT = Path('/run/augmentor')
_leases = []


def configured(component):
    if (ROOT/'fedora-package.json').is_file():
        command=['rpm','-q','--qf','%{VERSION}','augmentor-agent']
        expected=json.loads((ROOT/'release.json').read_text())['version']
    else:
        command=['dpkg-query','-W','-f=${db:Status-Status}','augmentor-'+component]
        expected='installed'
    result=subprocess.run(command,capture_output=True,text=True,timeout=5)
    if result.returncode or result.stdout!=expected:
        raise RuntimeError('Augmentor package configuration is incomplete. Finish the installation before reopening it.')


def hold(component):
    if not (ROOT / 'release.json').is_file():
        return  # Source/developer installations have their own lifecycle.
    release = json.loads((ROOT/'release.json').read_text())
    if sys.platform == 'darwin' and release.get('target','').startswith('macos-'):
        runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/tmp/augmentor-{os.getuid()}'))
        runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
        if runtime.is_symlink() or runtime.stat().st_uid != os.getuid() or runtime.stat().st_mode & 0o077:
            raise RuntimeError('The runtime directory must be private and owned by this user.')
        descriptor = os.open(runtime/'installation.lock', os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1:
                raise RuntimeError('Invalid installation lock file.')
            fcntl.flock(descriptor, fcntl.LOCK_SH|fcntl.LOCK_NB)
        except (OSError, RuntimeError):
            os.close(descriptor)
            raise RuntimeError('Augmentor is being updated. Finish the update before reopening it.')
        os.set_inheritable(descriptor, True)
        _leases.append(descriptor)
        return
    if component=='desktop':
        desktop_version=Path('/usr/share/augmentor/desktop-version')
        if not desktop_version.exists() or desktop_version.read_text().strip()!=json.loads((ROOT/'release.json').read_text())['version']:
            raise RuntimeError('Desktop and runtime package versions differ. Finish installing both packages before reopening Augmentor.')
    for name in (['runtime', 'desktop'] if component == 'desktop' else ['runtime']):
        path = LOCK_ROOT / ('augmentor-' + name)
        descriptor = None
        try:
            descriptor = os.open(str(path) + '.lock', os.O_RDONLY | os.O_NOFOLLOW)
            fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
            if Path(str(path) + '.pending').exists():
                raise RuntimeError('Augmentor is being updated. Finish package configuration before reopening it.')
            configured(name)
        except (OSError, RuntimeError) as error:
            if descriptor is not None:
                os.close(descriptor)
            raise RuntimeError('Augmentor cannot start during package maintenance. Finish the update and try again.') from error
        os.set_inheritable(descriptor, True)
        _leases.append(descriptor)
