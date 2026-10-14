#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Own one original-provider scratch directory before any document is copied.

No document input, directory scan, model, network or persistent recovery state.
The native supervisor/broker hold a shared directory lease until they exit.
"""
import ctypes
import fcntl
import json
import os
from pathlib import Path
import resource
import secrets
import select
import shutil
import signal
import stat
import sys


def interrupted(_signum, _frame):
    raise InterruptedError('Office scratch owner interrupted.')


def main():
    owner = int(sys.argv[1])
    parent = Path(sys.argv[2])
    if owner <= 1 or os.getppid() != owner or not parent.is_absolute() or not shutil.rmtree.avoids_symlink_attacks:
        raise ValueError('Unconfirmed scratch owner.')
    owner_fd = os.pidfd_open(owner)
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    root_fd = None
    name = None
    try:
        if os.getppid() != owner or select.select([owner_fd], [], [], 0)[0]:
            raise InterruptedError('Scratch owner exited before allocation.')
        if ctypes.CDLL(None).prctl(15, ctypes.c_char_p(b'aug-office-temp'), 0, 0, 0) != 0:
            raise ValueError('Scratch process identity unavailable.')
        name = 'dsh-office-to-pdf-' + secrets.token_hex(12)
        os.mkdir(name, 0o700, dir_fd=parent_fd)
        root_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent_fd)
        identity = os.fstat(root_fd)
        if identity.st_uid != os.getuid() or stat.S_IMODE(identity.st_mode) != 0o700:
            raise ValueError('Invalid private scratch directory.')
        # Readiness means both exact owner and cleanup authority are established.
        if os.getppid() != owner or select.select([owner_fd], [], [], 0)[0]:
            raise InterruptedError('Scratch owner exited before readiness.')
        print(json.dumps({'directory': str(parent / name), 'dev': str(identity.st_dev), 'ino': str(identity.st_ino)}), flush=True)
        control = b''
        while True:
            ready, _, _ = select.select([owner_fd, 0], [], [])
            if owner_fd in ready:
                break
            chunk = os.read(0, 3)
            if not chunk:
                break
            control += chunk
            if control == b'R\n':
                break
            if len(control) >= 2:
                raise ValueError('Invalid scratch release.')
    finally:
        # A shared lease inherited by the trusted native broker prevents early
        # deletion while native descendants still hold the authorized snapshot.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        if root_fd is not None:
            fcntl.flock(root_fd, fcntl.LOCK_EX)
            current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            original = os.fstat(root_fd)
            if not stat.S_ISDIR(current.st_mode) or current.st_uid != os.getuid() or stat.S_IMODE(current.st_mode) != 0o700 or (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino):
                raise ValueError('Office scratch identity changed.')
            shutil.rmtree(name, dir_fd=parent_fd)
            os.close(root_fd)
        os.close(parent_fd)
        os.close(owner_fd)
    print(json.dumps({'released': True}), flush=True)


if __name__ == '__main__':
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024**2, 256 * 1024**2))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        main()
    except BaseException:
        sys.exit(1)
