# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""OS primitives shared by local services. Unsupported platforms fail closed."""
import ctypes
import os
import socket
import struct
import sys


def peer_uid(connection):
    """Return the kernel-authenticated owner of a connected Unix socket."""
    if sys.platform == 'linux':
        credentials = connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        return struct.unpack('3i', credentials)[1]
    if sys.platform == 'darwin':
        libc = ctypes.CDLL(None, use_errno=True)
        getpeereid = libc.getpeereid
        getpeereid.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint)]
        getpeereid.restype = ctypes.c_int
        uid, gid = ctypes.c_uint(), ctypes.c_uint()
        if getpeereid(connection.fileno(), ctypes.byref(uid), ctypes.byref(gid)) != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))
        return uid.value
    raise RuntimeError('Private local services are not supported on this platform.')


def require_same_user(connection):
    if peer_uid(connection) != os.getuid():
        raise PermissionError('This companion belongs to a different user.')
