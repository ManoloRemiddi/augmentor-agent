# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One companion of each kind per data root, plus a maintenance lifetime lease.

State sockets can differ between launchers; data ownership must not. The shared
lease interoperates with the Node cold-profile transaction's exclusive lease.
"""
import os
from pathlib import Path
import re
import stat
import sys
from platform_adapters import locks


def descriptor(path):
    if sys.platform == 'win32':
        from platform_adapters.windows_identity import private_lock_descriptor
        return private_lock_descriptor(path)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        a, b = os.fstat(fd), path.lstat()
        if not stat.S_ISREG(a.st_mode) or a.st_uid != os.getuid() or a.st_nlink != 1 or a.st_mode & 0o077 or (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino):
            raise ValueError('Shared profile lease needs a private owned regular file.')
        return fd
    except BaseException:
        os.close(fd)
        raise


class SharedProfile:
    def __init__(self, data, component):
        if component not in ('prompts', 'memory'):
            raise ValueError('Unknown shared component.')
        requested = Path(data).absolute()
        if requested.is_symlink():
            raise ValueError('Shared data cannot be a directory link.')
        root = requested.resolve()
        if re.fullmatch(r'\..+\.import-[-a-f0-9]{36}\.(stage|backup)', root.name) or re.search(r'/(native-imports/[a-f0-9]{64}/state|shared-imports/[a-f0-9]{64}/data)$', root.as_posix()):
            raise ValueError('Shared migration evidence copies cannot run as active services.')
        root.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        if sys.platform != 'win32':
            info = root.parent.stat()
            if info.st_uid != os.getuid() or info.st_mode & 0o022:
                raise ValueError('Shared profile parent must be owned and protected from other writers.')
        self.descriptors = []
        try:
            for suffix, operation in [('owner', locks.LOCK_SH), (component, locks.LOCK_EX)]:
                fd = descriptor(root.parent / ('.' + root.name + '.augmentor-' + suffix + '.lock'))
                self.descriptors.append(fd)
                locks.flock(fd, operation | locks.LOCK_NB)
            # Check before creating/opening any data file, including when the
            # first adoption rename succeeded and the original root is absent.
            if (root.parent / ('.' + root.name + '.augmentor-migration.json')).exists():
                raise ValueError('An unfinished shared-profile migration requires inspection.')
        except BaseException:
            self.close()
            raise

    def close(self):
        while self.descriptors:
            os.close(self.descriptors.pop())
