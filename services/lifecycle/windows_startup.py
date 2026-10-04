# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Kernel startup exclusion, distinct from the process lifetime installation lease.

Readers remain held until a component is discoverable. The coordinator's writer
excludes readers and other writers. Neither mode truncates a file or persists a
busy marker; Windows releases exclusion on the last handle's close/process exit.
This primitive does not authorize shutdown, file replacement or an installer.
"""
import ctypes
import os
from pathlib import Path
import sys


def native_ready():
    """Release the compiled launcher's reader, keeping its lifetime lease intact."""
    if sys.platform != 'win32': raise RuntimeError('Windows startup requires Windows.')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    module = kernel.GetModuleHandleW
    module.argtypes = [ctypes.c_wchar_p]; module.restype = ctypes.c_void_p
    symbol = kernel.GetProcAddress
    symbol.argtypes = [ctypes.c_void_p, ctypes.c_char_p]; symbol.restype = ctypes.c_void_p
    handle = module(None)
    address = symbol(handle, b'AugmentorStartupReady')
    if not address:
        filename = kernel.GetModuleFileNameW
        filename.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
        filename.restype = ctypes.c_uint
        path = ctypes.create_unicode_buffer(32768)
        count = filename(handle, path, len(path))
        if not count or count >= len(path): raise ctypes.WinError(ctypes.get_last_error())
        if Path(path.value).name.lower() in ('augmentor.exe', 'augmentorbrowserhost.exe'):
            raise RuntimeError('This native launcher does not support startup coordination.')
        return False  # An explicit source/private-Python qualification process.
    if not ctypes.WINFUNCTYPE(ctypes.c_int)(address)():
        raise RuntimeError('The native startup reservation could not be released.')
    return True


class Startup:
    """Short-lived startup reader; call ready only after control registration."""
    def __init__(self, runtime=None, *, maintenance=False):
        if sys.platform != 'win32': raise RuntimeError('Windows startup requires Windows.')
        from platform_adapters.paths import runtime_directory
        from platform_adapters.windows_identity import private_file_descriptor
        self.fd = None
        self.maintenance = maintenance
        self.path = Path(runtime if runtime is not None else runtime_directory())/'startup.lock'
        self.fd = private_file_descriptor(self.path, writable=maintenance, create=True, share_write=False)

    def ready(self):
        if self.maintenance: raise RuntimeError('A maintenance gate cannot become an application startup.')
        native_ready()
        self.close()

    def close(self):
        if self.fd is not None:
            descriptor, self.fd = self.fd, None
            os.close(descriptor)

    def __enter__(self): return self
    def __exit__(self, *_): self.close()
