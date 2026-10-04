# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Shared/exclusive process leases with flock-compatible operation flags.

Unix keeps its existing flock implementation. Windows locks byte zero with the
kernel's LockFileEx, allowing shared lifetime leases and exclusive maintenance.
The caller still owns path validation/ACLs and must keep the file open. These
leases do not substitute for a third-party runtime's different lock protocol.
"""
import os
import sys

LOCK_SH, LOCK_EX, LOCK_NB, LOCK_UN = 1, 2, 4, 8


def flock(file, operation):
    if sys.platform != 'win32':
        import fcntl
        return fcntl.flock(file, operation)
    import ctypes
    from ctypes import wintypes
    import errno
    import msvcrt

    action = operation & ~LOCK_NB
    if action not in (LOCK_SH, LOCK_EX, LOCK_UN) or operation & ~15:
        raise ValueError('Choose one shared, exclusive or unlock operation')
    descriptor = file if isinstance(file, int) else file.fileno()
    handle = msvcrt.get_osfhandle(descriptor)

    class OVERLAPPED(ctypes.Structure):
        _fields_ = [('Internal', ctypes.c_size_t), ('InternalHigh', ctypes.c_size_t),
                    ('Offset', wintypes.DWORD), ('OffsetHigh', wintypes.DWORD),
                    ('hEvent', wintypes.HANDLE)]

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    overlap = OVERLAPPED()
    if action == LOCK_UN:
        function = kernel.UnlockFileEx
        flags = 0
    else:
        function = kernel.LockFileEx
        flags = (2 if action == LOCK_EX else 0) | (1 if operation & LOCK_NB else 0)
    function.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
                        wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(OVERLAPPED)] if action != LOCK_UN else [
                        wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
                        wintypes.DWORD, ctypes.POINTER(OVERLAPPED)]
    function.restype = wintypes.BOOL
    arguments = (handle, flags, 0, 1, 0, ctypes.byref(overlap)) if action != LOCK_UN else (
                handle, 0, 1, 0, ctypes.byref(overlap))
    if not function(*arguments):
        error = ctypes.get_last_error()
        if error in (32, 33):
            raise BlockingIOError(errno.EWOULDBLOCK, 'Another process owns the lease')
        raise ctypes.WinError(error)
