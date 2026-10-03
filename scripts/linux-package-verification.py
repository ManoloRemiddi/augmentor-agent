#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Read-only installer verification of native package guards and final outcomes.

Imports separately supplied checked public guard code, never installed app code.
Never begins/finalizes maintenance or repairs pending records. The manager's own
hooks remain responsible for durable intent and verified transaction completion.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import stat
import subprocess

GUARD_FILES = {
    '/usr/lib/augmentor-package-guard/lifecycle.py': 'linux-package-guard.py',
    '/usr/lib/augmentor-package-guard/can-remove.py': 'arch-guard/can-remove.py',
    '/usr/share/libalpm/hooks/augmentor-agent-pre.hook': 'arch-guard/augmentor-agent-pre.hook',
    '/usr/share/libalpm/hooks/augmentor-agent-post.hook': 'arch-guard/augmentor-agent-post.hook',
    '/usr/share/libalpm/hooks/augmentor-guard-remove.hook': 'arch-guard/augmentor-guard-remove.hook',
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def query(command):
    if any(os.environ.get(key) for key in ('LD_PRELOAD', 'LD_AUDIT', 'LD_LIBRARY_PATH')):
        raise ValueError('Native package verification refuses an unreviewed loader override.')
    result = subprocess.run(command, capture_output=True, text=True, timeout=30,
                            env={**os.environ, 'LC_ALL': 'C'})
    if result.returncode:
        raise ValueError('Cannot verify native package state: '+result.stderr[-1000:])
    return result.stdout


def verify_guard(manifest, references=None):
    expected = manifest['guardPackage']
    references = Path(references or Path(__file__).parent)
    fields = query(['/usr/bin/pacman', '-Qi', expected['name']])
    values = {}
    for row in fields.splitlines():
        if ':' in row:
            key, value = row.split(':', 1)
            if key.strip() in ('Name', 'Version', 'Architecture'):
                if key.strip() in values:
                    raise ValueError('Duplicate installed guard identity field.')
                values[key.strip()] = value.strip()
    if values != {'Name': expected['name'], 'Version': expected['versionRelease'], 'Architecture': expected['architecture']}:
        raise ValueError('The independent Arch guard is not installed at its checked identity.')
    hook_dirs = query(['/usr/bin/pacman-conf', 'HookDir']).splitlines()
    if [str(Path(value)) for value in hook_dirs] != ['/etc/pacman.d/hooks']:
        raise ValueError('Custom pacman hook directories need separate guard qualification before application installation.')
    overrides = Path('/etc/pacman.d/hooks')
    if overrides.exists() or overrides.is_symlink():
        info = overrides.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError('Unsafe pacman hook override directory.')
    for raw, relative in GUARD_FILES.items():
        installed = Path(raw)
        info = installed.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022
                or info.st_nlink != 1 or sha(installed) != sha(references/relative)):
            raise ValueError('An installed independent guard file differs: '+raw)
        for directory in installed.parents:
            info = directory.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
                raise ValueError('Unsafe independent guard directory: '+str(directory))
        if installed.parent == Path('/usr/share/libalpm/hooks'):
            override = Path('/etc/pacman.d/hooks')/installed.name
            if override.exists() or override.is_symlink():
                raise ValueError('An independent guard hook is masked by an override: '+str(override))
    query(['/usr/bin/pacman', '-Qkk', expected['name']])
    return {'verifiedIndependentGuard': True, 'hookOverridesAbsent': True}


def verify_payload(manifest, app, references=None):
    references = Path(references or Path(__file__).parent)
    spec = importlib.util.spec_from_file_location('installer_public_guard', references/'linux-package-guard.py')
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    target = manifest['target']
    manager = guard.host(target)
    guard.APP = Path(app)
    for path in (guard.STATE/'pending.json', guard.RUN/'augmentor-runtime.pending', guard.RUN/'augmentor-desktop.pending'):
        if path.exists() or path.is_symlink():
            raise ValueError('Native package maintenance is unresolved; complete verified recovery before setup.')
    if manager == 'pacman':
        verify_guard(manifest, references)
    value = guard.receipt(target, manager)
    if (value['source'] != {'commit': manifest['sourceCommit'], 'dirty': False}
            or value['version'] != manifest['version'] or value['package'] != manifest['nativePackage']):
        raise ValueError('The registered native package differs from this complete bundle.')
    audit = ['/usr/bin/pacman', '-Qkk', 'augmentor-agent'] if manager == 'pacman' else ['/usr/bin/rpm', '-V', 'augmentor-agent']
    query(audit)
    return {'verifiedNativeOutcome': True, 'pendingAbsent': True,
            'completeAppInventoryPassed': True, 'nativePackageAuditPassed': True, 'package': value['package']}
