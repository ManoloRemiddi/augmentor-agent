#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Read-only selected-artifact guards for the owned GNOME qualification guests.

This is test instrumentation, not a runtime selector. It never installs,
activates or launches the application and cannot adopt a different interpreter.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess

PROFILES = {
    'ubuntu24': {'marker': 'Isolated Augmentor Ubuntu 24.04 GNOME qualification VM\n',
                 'hostname': 'augmentor-gnome-ubuntu24-mesa2',
                 'os': ('ubuntu', '24.04'), 'target': 'ubuntu24.04-amd64',
                 'desktop': 'ubuntu:GNOME'},
    'fedora44': {'marker': 'Isolated Augmentor Fedora GNOME qualification VM\n',
                 'hostname': 'augmentor-gnome-fedora44',
                 'os': ('fedora', '44'), 'target': 'fedora44-x86_64',
                 'desktop': 'GNOME'},
}


def proof_identity(source, token):
    if (not isinstance(source, str) or not re.fullmatch('[a-f0-9]{40}', source)
            or not isinstance(token, str) or not re.fullmatch('[a-f0-9]{64}', token)):
        raise ValueError('Use the exact clean source and retained one-run proof token.')


def require_new_journal(path):
    if os.path.lexists(path):
        raise ValueError('A settings journal already exists; recover its original run explicitly.')


def journal_data(stream, source, token):
    proof_identity(source, token)
    info = os.fstat(stream.fileno())
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('The settings journal must be a private ordinary-user file.')
    raw = stream.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError('The settings journal exceeds its bound.')
    saved = json.loads(raw)
    if saved.get('source') != source or saved.get('proofToken') != token:
        raise ValueError('The settings journal belongs to another run or source; it was preserved.')
    return saved


def read_journal(path, source, token):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'r') as stream:
        return journal_data(stream, source, token)


def create_journal(path, saved, source, token):
    proof_identity(source, token)
    if saved.get('source') != source or saved.get('proofToken') != token:
        raise ValueError('The new settings journal must belong to this exact run.')
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'w') as stream:
        json.dump(saved, stream);stream.flush();os.fsync(stream.fileno())


def write_journal(path, saved, source, token):
    proof_identity(source, token)
    if saved.get('source') != source or saved.get('proofToken') != token:
        raise ValueError('The settings journal update must belong to this exact run.')
    # Validate through the same descriptor before modifying it. A stale cleanup
    # must never truncate another run's journal, even at the same source SHA.
    with os.fdopen(os.open(path, os.O_RDWR | os.O_NOFOLLOW), 'r+') as stream:
        journal_data(stream, source, token)
        stream.seek(0);json.dump(saved, stream);stream.truncate()
        stream.flush();os.fsync(stream.fileno())


def output(argv):
    return subprocess.check_output(argv, text=True, timeout=30).strip()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_selection(data, target, source):
    """Verify the selected root and runtime without changing selection or state."""
    if target not in PROFILES or not isinstance(source, str) or not re.fullmatch('[a-f0-9]{40}', source):
        raise ValueError('Supply an explicit supported target and exact clean source identity.')
    selection = json.loads((data/'desktop.json').read_text())
    root = Path(selection['root'])
    if not root.is_absolute() or root != root.resolve():
        raise ValueError('The selected artifact root is not canonical.')
    managed = root != Path('/usr/lib/augmentor')
    if managed:
        if not root.is_relative_to(data/'releases') or selection.get('sourceRef') != source:
            raise ValueError('The selected managed artifact does not match the requested source.')
        deployment = load(data/'desktop-deployment.py', 'owned_qualification_deployment')
        inventory = deployment.verify(root)
        if inventory['artifactSha256'] != selection.get('artifactSha256'):
            raise ValueError('The selected artifact hash differs from its verified inventory.')
    release = json.loads((root/'release.json').read_text())
    if release.get('source') != {'commit': source, 'dirty': False} or release.get('target') != PROFILES[target]['target']:
        raise ValueError('The selected clean release has a different source or target.')
    python = selection.get('python')
    if not isinstance(python, str) or not Path(python).is_absolute():
        raise ValueError('The selected interpreter is invalid.')
    if target == 'ubuntu24':
        runtime = load(root/'scripts/linux-python-runtime.py', 'owned_qualification_runtime')
        if runtime.resolve(root, python) != python:
            raise ValueError('The selected interpreter differs from the verified runtime.')
    else:
        # Fedora's reviewed package intentionally uses its native system runtime,
        # and must not inherit a Noble/Leap managed runtime or an arbitrary Python.
        if (root/'linux-python-runtime.json').exists() or (root/'linux-python-runtime.json').is_symlink():
            raise ValueError('The Fedora fixture requires the native system Python contract.')
        if python != '/usr/bin/python3':
            raise ValueError('The Fedora fixture requires the selected native system interpreter.')
    return {'root': str(root), 'python': python, 'selection': selection,
            'release': release, 'managedInventoryVerified': managed, 'pythonRuntimeVerified': True}


def verified_profile(target, source):
    """Check the marked ordinary-user guest before reading its installed code."""
    if target not in PROFILES:
        raise ValueError('Unsupported qualification target.')
    profile = PROFILES[target]
    if (os.geteuid() != 1000 or os.environ.get('USER') != 'augmentor-proof'
            or Path('/etc/augmentor-test-vm').read_text() != profile['marker']
            or output(['hostname']) != profile['hostname']
            or output(['systemd-detect-virt']) != 'qemu'):
        raise ValueError('Use only the marked ordinary-user owned GNOME qualification guest.')
    if (os.environ.get('LD_PRELOAD') or os.environ.get('LD_AUDIT') or os.environ.get('LD_LIBRARY_PATH')):
        raise ValueError('Qualification refuses inherited loader overrides.')
    system = {}
    for line in Path('/etc/os-release').read_text().splitlines():
        key, _, value = line.partition('=')
        system[key] = value.strip('"')
    if (system.get('ID'), system.get('VERSION_ID')) != profile['os']:
        raise ValueError('The guest OS does not match the explicit qualification target.')
    if target == 'fedora44':
        if output(['getenforce']) != 'Enforcing':
            raise ValueError('Fedora qualification requires enforcing SELinux.')
        subprocess.run(['rpm', '-V', 'augmentor-agent'], check=True, timeout=30)
    else:
        if (Path('/sys/module/apparmor/parameters/enabled').read_text().strip() != 'Y'
                or output(['systemctl', 'is-active', 'apparmor']) != 'active'):
            raise ValueError('Ubuntu qualification requires active AppArmor.')
        if output(['dpkg', '--verify', 'augmentor-runtime', 'augmentor-desktop']):
            raise ValueError('The registered Ubuntu packages differ from their inventories.')
    return verify_selection(Path.home()/'.local/share/augmentor', target, source)
