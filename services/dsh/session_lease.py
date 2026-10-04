# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Match DSH 0.1.5-rc.1's history writer lease, never an Augmentor app lease.

Reviewed session-persistence-jsonl lib/index.js SHA256:
7d0640c9fc4be6c703b77605fdee6af519c542fae28a6cd4489353309812f062
POSIX uses flock on session.lock. Windows uses a count-one Local semaphore named
from SHA256(Node path.resolve(lockPath).toLowerCase()). Do not substitute a file
lock on Windows: it would not exclude the actual harness writer.
"""
from contextlib import contextmanager
import errno
import hashlib
import ntpath
import os
from pathlib import Path
import stat
import sys


def windows_name(path):
    text = os.fspath(path)
    if not ntpath.isabs(text): raise ValueError('A session lease requires an absolute history path.')
    # Lexical normalization matches Node path.resolve; realpath would expand
    # short names/junctions and produce a different name from the actual writer.
    normalized = ntpath.normpath(ntpath.abspath(text)).lower()
    return 'Local\\dsh-session-lock-'+hashlib.sha256(normalized.encode('utf-8')).hexdigest()


@contextmanager
def session_write_lease(path):
    path = Path(path)
    if sys.platform == 'win32':
        import win32event
        from platform_adapters.windows_identity import reject_reparse_ancestors
        reject_reparse_ancestors(path.parent)
        handle = win32event.CreateSemaphore(None, 1, 1, windows_name(path))
        held = False
        try:
            result = win32event.WaitForSingleObject(handle, 0)
            if result == win32event.WAIT_TIMEOUT:
                raise BlockingIOError(errno.EWOULDBLOCK, 'The harness owns this history.')
            if result != win32event.WAIT_OBJECT_0: raise OSError('The harness history lease could not be acquired.')
            held = True
            yield
        finally:
            try:
                if held: win32event.ReleaseSemaphore(handle, 1)
            finally: handle.Close()
    else:
        import fcntl
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid():
                raise ValueError('The history lease is not an ordinary owned file.')
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            current = path.stat()
            if (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino):
                raise ValueError('The history lease changed before acquisition.')
            yield
        finally:
            os.close(descriptor)
