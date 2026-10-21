# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Linux lifetime gate for managed DSH startup and configuration maintenance."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import stat
import sys

FENCE='.augmentor-preservation.json'


def directory(path,create=False):
    path=Path(path)
    if not path.is_absolute() or path.resolve()!=path:
        raise ValueError('Choose a canonical DSH home without directory links.')
    if create:path.mkdir(mode=0o700,parents=True,exist_ok=True)
    info=path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o022:
        raise ValueError('The DSH home must be owned and protected from other writers.')
    return path


@contextmanager
def lease(home,exclusive=False):
    if sys.platform!='linux':raise ValueError('DSH configuration maintenance is qualified only on Linux.')
    home=directory(home,create=not exclusive)
    lock=home/'.augmentor-preservation.lock'
    fd=os.open(lock,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    try:
        a,b=os.fstat(fd),lock.lstat()
        if not stat.S_ISREG(a.st_mode) or a.st_uid!=os.getuid() or a.st_mode&0o077 or a.st_nlink!=1 or (a.st_dev,a.st_ino)!=(b.st_dev,b.st_ino):
            raise ValueError('The DSH configuration gate must be private and owned.')
        try:fcntl.flock(fd,(fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)|fcntl.LOCK_NB)
        except BlockingIOError as error:raise ValueError('A managed DSH host or configuration maintenance is active.') from error
        fence=home/FENCE
        if not exclusive and (fence.exists() or fence.is_symlink()):
            raise ValueError('Unfinished DSH configuration maintenance requires recovery.')
        os.set_inheritable(fd,not exclusive)
        yield
    finally:os.close(fd)
