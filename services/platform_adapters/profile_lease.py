# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Lock the inherited Node descriptor; its open file description owns the lease."""
import fcntl,os,stat,sys
fd=3
info=os.fstat(fd)
if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_nlink!=1 or info.st_mode&0o077:
    raise ValueError('Profile lease needs a private owned regular file.')
try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:sys.exit(3)
# Do not unlock: the parent holds the same open file description after this
# helper exits. Closing/killing the actual Node owner releases the kernel lease.
print('locked',flush=True)
