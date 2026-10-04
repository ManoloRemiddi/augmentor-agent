# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Retire completed full Unix observers only after their kernel holders exit.

Sidecars are cleanup hints, never install/recovery authority. Unknown observers,
changed code and foreign entries survive. No selected release, stage, backup or
user-data directory is a collection target.
"""
import os
from pathlib import Path
import re
import shutil
import sys

from platform_adapters import locks
from platform_adapters.private_files import require_directory, descriptor, atomic_json, read_json
from .payload_integrity import _root
from .macos_payload import snapshot

SCHEMA = 'augmentor-posix-observer-retention/1'
_held = []  # Descriptors deliberately survive Python teardown until OS exit.


def _location(directory):
    if sys.platform not in ('linux', 'darwin'):
        raise RuntimeError('Full observer collection requires native Unix locks.')
    directory = require_directory(Path(directory).absolute())
    require_directory(directory.parent)
    _root(directory)
    if not re.fullmatch(r'(?:linux|mac)-[a-f0-9]{48}', directory.name):
        raise ValueError('Use a private full update observer directory.')
    child = 'Observer' if directory.name.startswith('linux-') else 'Observer.app'
    if {path.name for path in directory.iterdir()} != {child}:
        raise ValueError('Preserve extra or unknown observer contents.')
    _root(directory/child)
    return directory, directory/child


def retain(directory):
    """Acquire during inherited bootstrap exclusion, before it can be released."""
    directory, _ = _location(directory)
    fd = descriptor(directory.parent/(directory.name+'.lock'), writable=True, create=True)
    try:
        locks.flock(fd, locks.LOCK_SH | locks.LOCK_NB)
    except BaseException:
        os.close(fd)
        raise
    _held.append(fd)


def eligible(directory, outcome, payload_sha256):
    directory, _ = _location(directory)
    if outcome not in ('deferred', 'target-healthy'):
        raise ValueError('Preserve unknown update observers.')
    if not isinstance(payload_sha256, str) or not re.fullmatch('[a-f0-9]{64}', payload_sha256):
        raise ValueError('Use the original verified observer payload identity.')
    atomic_json(directory.parent/(directory.name+'.completed.json'), {
        'schema': SCHEMA, 'runtime': directory.name, 'outcome': outcome,
        'payloadSHA256': payload_sha256,
    })


def collect(parent):
    """Caller holds bootstrap exclusion; cleanup failure preserves the tree."""
    parent = require_directory(Path(parent).absolute())
    _root(parent)
    if not shutil.rmtree.avoids_symlink_attacks:
        return 0
    count = 0
    for marker in parent.glob('*.completed.json'):
        name = marker.name.removesuffix('.completed.json')
        if not re.fullmatch(r'(?:linux|mac)-[a-f0-9]{48}', name):
            continue
        fd = None
        try:
            value = read_json(marker)
            if (not isinstance(value, dict) or set(value) != {'schema', 'runtime', 'outcome', 'payloadSHA256'}
                    or value['schema'] != SCHEMA or value['runtime'] != name
                    or value['outcome'] not in ('deferred', 'target-healthy')
                    or not isinstance(value['payloadSHA256'], str)
                    or not re.fullmatch('[a-f0-9]{64}', value['payloadSHA256'])):
                continue
            directory, child = _location(parent/name)
            # Never create a missing lease file during collection: old/unknown
            # observers have no retained exit witness and must remain untouched.
            fd = descriptor(parent/(name+'.lock'), writable=True)
            locks.flock(fd, locks.LOCK_EX | locks.LOCK_NB)
            if snapshot(child)['sha256'] != value['payloadSHA256']:
                continue
            shutil.rmtree(directory)
            marker.unlink()
            count += 1
        except (ValueError, OSError):
            continue
        finally:
            if fd is not None:
                os.close(fd)
        # Keep tiny reusable lock files to avoid unlink/recreate lock races.
    return count
