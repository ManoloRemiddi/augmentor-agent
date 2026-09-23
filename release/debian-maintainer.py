#!/usr/bin/python3 -I
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Standalone dpkg hook. Never executes code or reads settings from user homes."""
import fcntl
import json
import os
from pathlib import Path
import sys

COMPONENT = '@COMPONENT@'
HOOK = '@HOOK@'
VERSION = '@VERSION@'
directory=Path('/run/augmentor')
directory.mkdir(mode=0o755,exist_ok=True)
if directory.is_symlink() or not directory.is_dir() or directory.stat().st_uid!=0 or directory.stat().st_mode & 0o022:
    raise SystemExit('The Augmentor maintenance directory must be owned by root and writable only by root.')
base = directory / ('augmentor-' + COMPONENT)
pending = Path(str(base) + '.pending')
lock = Path(str(base) + '.lock')


def legacy_processes():
    """Older releases have no leases; identify exact owned executable arguments."""
    result = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            arguments = (entry / 'cmdline').read_bytes().split(b'\0')
            native = b'augmentor_linux' in arguments or b'/usr/bin/augmentor-agent' in arguments
            owned = any(arg.startswith(b'/usr/lib/augmentor/') for arg in arguments[1:])
            if (native if COMPONENT == 'desktop' and action!='upgrade' else native or owned):
                result.append(entry.name)
        except (FileNotFoundError, ProcessLookupError):
            pass
    return result


def begin():
    if COMPONENT=='desktop' and HOOK=='preinst':
        release=Path('/usr/lib/augmentor/release.json')
        if not release.is_file() or json.loads(release.read_text()).get('version')!=VERSION:
            raise SystemExit('Configure the matching Augmentor runtime package before the desktop package.')
    runtime_descriptor=None
    if COMPONENT=='desktop' and action=='upgrade':
        runtime_lock=directory/'augmentor-runtime.lock'
        if runtime_lock.exists():
            runtime_descriptor=os.open(runtime_lock,os.O_RDONLY|os.O_NOFOLLOW)
            try:fcntl.flock(runtime_descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise SystemExit('Augmentor is still open. Run augmentor-maintenance prepare before upgrading either package.')
    descriptor = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o644)
    os.fchmod(descriptor, 0o644)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        running = legacy_processes()
        if running:
            raise RuntimeError('running process IDs: ' + ', '.join(running))
        with pending.open('w') as stream:
            stream.write('Package maintenance is in progress. Run dpkg --configure -a after an interrupted upgrade.\n')
    except (BlockingIOError, RuntimeError) as error:
        raise SystemExit('Augmentor is still open. In each affected login, run augmentor-maintenance prepare, close its browser connection, then retry the package operation. ' + str(error))
    finally:
        os.close(descriptor)
        if runtime_descriptor is not None:os.close(runtime_descriptor)


action = sys.argv[1] if len(sys.argv) > 1 else ''
if HOOK == 'preinst' and action in ('install', 'upgrade'):
    begin()
elif HOOK == 'prerm' and action in ('remove', 'upgrade', 'deconfigure'):
    begin()
elif HOOK == 'postinst' or (HOOK == 'postrm' and action in ('remove', 'purge', 'abort-install', 'abort-upgrade')):
    pending.unlink(missing_ok=True)
# Retain the inode used for leases across remove/reinstall and package upgrades.
