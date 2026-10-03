# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Live SDK launch inventory; unavailable shutdown protocols defer replacement.

These servers belong to their application owners. No saved PID or command grants
permission to close/restart them. A kernel-held registration blocks Windows
preparation before any desktop/companion shutdown; exited registrations do not.
"""
import os
from pathlib import Path
import secrets
import sys

from platform_adapters import locks
from platform_adapters.paths import private_directory
from platform_adapters.private_files import descriptor,atomic_json,require_directory

_held=[]  # Integer descriptors stay open until actual OS process exit.


def _lock(path):
    if sys.platform=='win32':
        from platform_adapters.windows_identity import private_lock_descriptor
        return private_lock_descriptor(path)
    return descriptor(path,writable=True,create=True)


def retain(runtime, root, component):
    if component not in ('native','register','embed'):raise ValueError('Unsupported SDK launch component.')
    directory=require_directory(private_directory(Path(runtime)/'sdk-launches'))
    name=secrets.token_hex(24)
    fd=_lock(directory/(name+'.lock'))
    try:
        locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)
        atomic_json(directory/(name+'.json'),{'schema':'augmentor-sdk-launch/1','root':str(Path(root).absolute()),'component':component})
    except BaseException:os.close(fd);raise
    _held.append(fd)


def require_closed(runtime):
    """Caller holds the startup writer, excluding new registered SDK launches."""
    from .admission import MaintenanceBusy
    directory=Path(runtime)/'sdk-launches'
    if not directory.exists():return
    require_directory(directory)
    import re
    for path in directory.iterdir():
        if not re.fullmatch('[a-f0-9]{48}\\.lock',path.name):continue
        # This is live lock inventory only. Neither JSON contents nor a stale
        # filename authorizes adopting, terminating or restarting an app.
        fd=_lock(path)
        try:
            try:locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)
            except (BlockingIOError,PermissionError) as error:
                raise MaintenanceBusy('A running SDK application still uses Augmentor. Close its app server before installing the update.') from error
        finally:os.close(fd)
