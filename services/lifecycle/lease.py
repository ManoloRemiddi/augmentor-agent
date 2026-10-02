# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Shared lifetime leases prevent package replacement underneath running code."""
import fcntl
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK_ROOT = Path('/run/augmentor')
PERSISTENT_PENDING = Path('/var/lib/augmentor-package-maintenance/pending.json')
_leases = []


def configured(component):
    receipt=ROOT/'linux-package.json'
    if receipt.exists() or receipt.is_symlink():
        value=json.loads(receipt.read_text());release=json.loads((ROOT/'release.json').read_text())
        manager={'opensuse-leap16.0-x86_64':'rpm','arch20261001-x86_64':'pacman'}.get(value.get('target'))
        package=value.get('package',{})
        if (receipt.is_symlink() or value.get('format')!='augmentor-linux-package-receipt/1' or not manager
                or value.get('manager')!=manager or value.get('target')!=release.get('target')
                or value.get('source')!=release.get('source') or value.get('version')!=release.get('version')
                or package.get('name')!='augmentor-agent' or package.get('architecture')!='x86_64'
                or not isinstance(package.get('versionRelease'),str)):
            raise RuntimeError('Invalid explicit Linux package identity.')
        if manager=='rpm':
            command=['rpm','-q','--qf','%{NAME}\n%{VERSION}-%{RELEASE}\n%{ARCH}','augmentor-agent']
            expected='augmentor-agent\n'+package['versionRelease']+'\nx86_64'
        else:
            command=['pacman','-Qi','augmentor-agent']
            expected={'Name':'augmentor-agent','Version':package['versionRelease'],'Architecture':'x86_64'}
    elif (ROOT/'fedora-package.json').is_file():
        command=['rpm','-q','--qf','%{VERSION}','augmentor-agent']
        expected=json.loads((ROOT/'release.json').read_text())['version']
    else:
        command=['dpkg-query','-W','-f=${db:Status-Status}','augmentor-'+component]
        expected='installed'
    options={'env':{**os.environ,'LC_ALL':'C'}} if isinstance(expected,dict) else {}
    result=subprocess.run(command,capture_output=True,text=True,timeout=5,**options)
    if isinstance(expected,dict):
        fields=re.findall(r'^(Name|Version|Architecture)\s*:\s*(\S+)\s*$',result.stdout,re.M)
        matches=len(fields)==3 and dict(fields)==expected
    else:matches=result.stdout==expected
    if result.returncode or not matches:
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
            if (PERSISTENT_PENDING.exists() or PERSISTENT_PENDING.is_symlink()
                    or Path(str(path) + '.pending').exists()):
                raise RuntimeError('Augmentor is being updated. Finish package configuration before reopening it.')
            configured(name)
        except (OSError, RuntimeError) as error:
            if descriptor is not None:
                os.close(descriptor)
            raise RuntimeError('Augmentor cannot start during package maintenance. Finish the update and try again.') from error
        os.set_inheritable(descriptor, True)
        _leases.append(descriptor)
