# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Retire only completed temporary code after all runtime holders have exited.

Markers are cleanup hints, never install/recovery authority. Unknown attempts and
foreign/linked entries are preserved. The shared kernel lease is deliberately an
integer descriptor retained until OS process exit, including interpreter teardown.
"""
import os
from pathlib import Path
import re
import shutil
import sys

from platform_adapters import locks
from platform_adapters.private_files import require_directory,atomic_json,read_json
from .payload_integrity import _root,_scan

SCHEMA='augmentor-observer-retention/1'
_held=[]


def _lock(path):
    if sys.platform=='win32':
        from platform_adapters.windows_identity import private_lock_descriptor
        return private_lock_descriptor(path)
    from platform_adapters.private_files import descriptor
    return descriptor(path,writable=True,create=True)


def _runtime(root):
    root=require_directory(Path(root).absolute());_root(root)
    if not re.fullmatch('observer-[a-f0-9]{48}',root.name):
        raise ValueError('Use a freshly staged observer runtime.')
    return root


def retain(root):
    root=_runtime(root)
    fd=_lock(root.parent/(root.name+'.lock'))
    try:locks.flock(fd,locks.LOCK_SH|locks.LOCK_NB)
    except BaseException:os.close(fd);raise
    _held.append(fd)


def eligible(root, outcome):
    root=_runtime(root)
    if outcome not in ('deferred','target-healthy'):raise ValueError('Preserve unknown update runtimes.')
    atomic_json(root.parent/(root.name+'.completed.json'),{'schema':SCHEMA,'runtime':root.name,'outcome':outcome})


def collect(parent):
    """Called under bootstrap exclusion; no source/user-data trees are traversed."""
    parent=require_directory(Path(parent).absolute());_root(parent)
    count=0
    for marker in parent.glob('observer-*.completed.json'):
        name=marker.name.removesuffix('.completed.json')
        if not re.fullmatch('observer-[a-f0-9]{48}',name):continue
        fd=None
        try:
            value=read_json(marker)
            if (not isinstance(value,dict) or set(value)!={'schema','runtime','outcome'} or value['schema']!=SCHEMA or
                    value['runtime']!=name or value['outcome'] not in ('deferred','target-healthy')):continue
            root=_runtime(parent/name)
            fd=_lock(parent/(name+'.lock'))
            locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)
            # Refuse reparse/symbolic/hard links before any deletion. This tree
            # contains copied public code only, never conversations or settings.
            _scan(root)
            shutil.rmtree(root)
            marker.unlink();count+=1
        except (ValueError,OSError):continue  # A live/unknown/edited tree remains private.
        finally:
            if fd is not None:os.close(fd)
        # Keep the tiny lock file: unlinking a reusable lock creates races.
    return count
