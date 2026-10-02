#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Read-only identity of the distro Python and Qt packages used by two candidates.

This is a cold-launch drift boundary, not a system transaction lock, complete
dependency closure, repository authentication or a whole Arch snapshot proof.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

MANIFEST = 'system-qt-inventory.json'
ARCH = 'arch20261001-cp314-x86_64-voice'
LEAP = 'leap16-cp313-x86_64-voice'
PROFILES = {
    ARCH: ('arch20261001-x86_64', 'pacman', '6.11.2', (
        'python', 'pyside6', 'shiboken6', 'qt6-base', 'qt6-declarative', 'qt6-svg', 'qt6-wayland')),
    LEAP: ('opensuse-leap16.0-x86_64', 'rpm', '6.9.1', (
        'python313-base', 'python313', 'python313-pyside6', 'python313-shiboken6',
        'libQt6Core6', 'libQt6Gui6', 'libQt6Widgets6', 'libQt6Network6', 'libQt6DBus6',
        'libQt6Svg6', 'libQt6OpenGL6', 'libQt6Quick6', 'libQt6QuickWidgets6',
        'libQt6Qml6', 'libQt6QmlMeta6', 'libQt6QmlModels6', 'libQt6QmlWorkerScript6',
        'libQt6Test6', 'libQt6WaylandClient6', 'libQt6WaylandEglClientHwIntegration6',
        'libQt6WlShellIntegration6', 'qt6-declarative-imports', 'qt6-wayland')),
}


def contract(value):
    profile = value.get('profile')
    stack = value.get('systemQtStack')
    if profile not in PROFILES:
        if stack is not None:
            raise ValueError('This profile cannot declare a distro Qt stack.')
        return None
    target, manager, qt, _ = PROFILES[profile]
    if (not isinstance(stack, dict) or set(stack) != {'format', 'file', 'sha256', 'bytes', 'qtVersion', 'packageManager'}
            or stack.get('format') != 'augmentor-system-qt-stack-contract/1'
            or stack.get('file') != MANIFEST or value.get('target') != target
            or stack.get('packageManager') != manager or stack.get('qtVersion') != qt
            or not isinstance(stack.get('sha256'), str) or not re.fullmatch('[a-f0-9]{64}', stack['sha256'])
            or type(stack.get('bytes')) is not int or not 0 < stack['bytes'] <= 8*1024*1024):
        raise ValueError('This candidate requires its exact distro Python/Qt stack contract.')
    return stack


def query(command):
    # Loader overrides must not inject code into the package-query tools either.
    if any(os.environ.get(key) for key in ('LD_PRELOAD', 'LD_AUDIT', 'LD_LIBRARY_PATH')):
        raise ValueError('Distro Qt verification refuses an unreviewed loader override.')
    env = dict(os.environ, LC_ALL='C')
    result = subprocess.run(command, env=env, text=True, capture_output=True, timeout=30)
    if result.returncode:
        raise ValueError('Distro Qt package query failed: '+result.stderr[-1000:])
    return result.stdout


def packages(profile):
    _, manager, _, names = PROFILES[profile]
    if manager == 'pacman':
        rows = [row.split() for row in query(['/usr/bin/pacman', '-Q', *names]).splitlines()]
        if any(len(row) != 2 for row in rows):
            raise ValueError('Invalid pacman Python/Qt package identity.')
        result = {name: version for name, version in rows}
    else:
        rows = [row.split('\t') for row in query(['/usr/bin/rpm', '-q', '--qf',
            '%{NAME}\t%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\n', *names]).splitlines()]
        if any(len(row) != 2 for row in rows):
            raise ValueError('Invalid RPM Python/Qt package identity.')
        result = {name: version for name, version in rows}
    if len(rows) != len(names) or set(result) != set(names):
        raise ValueError('The complete distro Python/Qt package set is required.')
    return dict(sorted(result.items()))


def scope(raw):
    path = Path(raw.rstrip('/'))
    if not path.is_absolute() or '..' in path.parts or '\\' in raw or '\x00' in raw:
        raise ValueError('Unsafe distro package inventory path.')
    return (path.parts[:3] in (('/', 'usr', 'bin'), ('/', 'usr', 'lib'), ('/', 'usr', 'lib64'))
            and '__pycache__' not in path.parts and path.suffix not in ('.pyc', '.pyo'))


def listed(profile):
    _, manager, _, names = PROFILES[profile]
    command = ['/usr/bin/pacman', '-Qql', *names] if manager == 'pacman' else ['/usr/bin/rpm', '-ql', *names]
    return sorted({row.rstrip('/') for row in query(command).splitlines() if scope(row)})


def regular(path):
    # Hash a no-follow descriptor and refuse concurrent replacement/write.
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError('Distro Python/Qt file ownership or type changed: '+str(path))
    # Nonblocking also refuses a raced replacement by a FIFO without hanging.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_uid != 0 or before.st_mode & 0o022:
            raise ValueError('Distro Python/Qt file ownership or type changed: '+str(path))
        sha = hashlib.file_digest(stream, 'sha256').hexdigest()
        after = os.fstat(stream.fileno())
    current = path.lstat()
    fields = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_mode, info.st_uid)
    if fields(before) != fields(after) or fields(before) != fields(current):
        raise ValueError('Distro Python/Qt file changed during verification: '+str(path))
    return {'type': 'file', 'bytes': before.st_size, 'sha256': sha, 'mode': stat.S_IMODE(before.st_mode)}


def member(path):
    path = Path(path)
    info = path.lstat()
    if info.st_uid != 0:
        raise ValueError('Distro Python/Qt member is not root owned: '+str(path))
    if stat.S_ISLNK(info.st_mode):
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to('/usr'):
            raise ValueError('Distro Python/Qt link escaped /usr: '+str(path))
        target_info = resolved.stat()
        if target_info.st_uid != 0 or target_info.st_mode & 0o022:
            raise ValueError('Distro Python/Qt link target ownership changed: '+str(path))
        target = {'type': 'directory'} if resolved.is_dir() else regular(resolved)
        return {'type': 'link', 'target': os.readlink(path), 'resolved': str(resolved), 'resolvedMember': target}
    if stat.S_ISDIR(info.st_mode) and not info.st_mode & 0o022:
        return {'type': 'directory', 'mode': stat.S_IMODE(info.st_mode)}
    if stat.S_ISREG(info.st_mode):
        return regular(path)
    raise ValueError('Distro Python/Qt member type or permissions changed: '+str(path))


def capture(profile):
    target, manager, qt, _ = PROFILES[profile]
    before = packages(profile)
    paths = listed(profile)
    members = {name: member(Path(name)) for name in paths}
    if not members or packages(profile) != before or listed(profile) != paths:
        raise ValueError('Distro Python/Qt registration changed during capture.')
    return {'format': 'augmentor-system-qt-stack-inventory/1', 'profile': profile,
        'target': target, 'packageManager': manager, 'qtVersion': qt,
        'packages': before, 'members': members,
        'scope': 'Registered /usr/bin and /usr/lib* members of the explicit Python/binding/Qt package set; bytecode caches excluded.',
        'completeDependencyClosure': False, 'wholeDistroSnapshotQualified': False,
        'dependencyMaintenanceQualified': False, 'publicReleaseQualified': False}


def manifest(value, path):
    stack = contract(value)
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != stack['bytes']:
        raise ValueError('Distro Qt manifest size/type changed.')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != stack['sha256']:
        raise ValueError('Distro Qt manifest checksum changed.')
    result = json.loads(data)
    if (result.get('format') != 'augmentor-system-qt-stack-inventory/1'
            or (result.get('profile'), result.get('target'), result.get('packageManager'), result.get('qtVersion'))
                != (value['profile'], value['target'], stack['packageManager'], stack['qtVersion'])
            or set(result.get('packages', {})) != set(PROFILES[value['profile']][3])
            or not isinstance(result.get('members'), dict) or not result['members']
            or any(result.get(key) is not False for key in ('completeDependencyClosure', 'wholeDistroSnapshotQualified', 'dependencyMaintenanceQualified', 'publicReleaseQualified'))):
        raise ValueError('Distro Qt manifest differs from the candidate contract.')
    for name in result['members']:
        if not scope(name) or str(Path(name)) != name:
            raise ValueError('Unsafe distro Qt manifest member.')
    return result


def verify(value, path):
    expected = manifest(value, path)
    profile = value['profile']
    before = packages(profile)
    if before != expected['packages']:
        raise ValueError('Distro Python/Qt package versions changed; qualify a new runtime.')
    paths = listed(profile)
    if paths != sorted(expected['members']):
        raise ValueError('Distro Python/Qt package inventory changed; qualify a new runtime.')
    for name, record in expected['members'].items():
        if member(Path(name)) != record:
            raise ValueError('Distro Python/Qt member changed; qualify a new runtime: '+name)
    if packages(profile) != before or listed(profile) != paths:
        raise ValueError('Distro Python/Qt registration changed during verification.')
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=tuple(PROFILES), required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    # Exclusive output preserves every previous qualification receipt.
    with args.out.open('x') as stream:
        json.dump(capture(args.profile), stream, indent=2, sort_keys=True)
        stream.write('\n')


if __name__ == '__main__':
    main()
