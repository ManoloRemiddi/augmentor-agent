# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Private managed-runtime records, with kernel validation before reading secrets."""
import json
import os
from pathlib import Path
import secrets
import stat
import sys


def require_directory(path):
    if sys.platform == 'win32':
        from .windows_identity import require_private_directory
        return require_private_directory(path)
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Setup needs a private data directory owned by this user.')
    return path


def descriptor(path, *, writable=False, create=False, exclusive=False):
    if sys.platform == 'win32':
        from .windows_identity import private_file_descriptor
        return private_file_descriptor(path, writable=writable, create=create, exclusive=exclusive)
    flags = (os.O_RDWR if writable else os.O_RDONLY) | os.O_NOFOLLOW
    if create: flags |= os.O_CREAT
    if exclusive: flags |= os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or
                info.st_mode & 0o077 or info.st_nlink != 1):
            raise ValueError('Setup needs an ordinary private file owned by this user.')
        return fd
    except BaseException:
        os.close(fd)
        raise


def read_json(path):
    with os.fdopen(descriptor(path), 'r', encoding='utf-8') as stream:
        raw = stream.read(16*1024*1024+1)
    if len(raw) > 16*1024*1024:
        raise ValueError('The private setup record exceeds its supported size.')
    return json.loads(raw)


def atomic_json(path, value):
    path = Path(path)
    require_directory(path.parent)
    temporary = path.with_name('.'+path.name+'.'+secrets.token_hex(16)+'.tmp')
    fd = descriptor(temporary, writable=True, exclusive=True)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, indent=2); stream.write('\n')
            stream.flush(); os.fsync(stream.fileno())
        if path.exists() or path.is_symlink():
            os.close(descriptor(path))
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
