# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Short-lived Unix startup readers exclude maintenance discovery writers.

Use ready() after publishing a component's control endpoint/registration. This
gate is distinct from lifetime leases and never authorizes file replacement.
"""
import os
import ctypes
from pathlib import Path
import sys

from platform_adapters import locks
from platform_adapters.paths import private_directory, runtime_directory
from platform_adapters.private_files import descriptor, require_directory


class Startup:
    def __init__(self, runtime=None, *, maintenance=False):
        if sys.platform not in ('linux','darwin'):raise RuntimeError('Unix startup requires Linux or macOS.')
        if type(maintenance) is not bool:raise ValueError('Choose startup or maintenance exclusion.')
        self.fd=None;self.maintenance=maintenance
        directory=require_directory(private_directory(runtime if runtime is not None else runtime_directory()))
        self.path=Path(directory)/'startup.lock'
        fd=descriptor(self.path,writable=True,create=True)
        try:locks.flock(fd,(locks.LOCK_EX if maintenance else locks.LOCK_SH)|locks.LOCK_NB)
        except BaseException:os.close(fd);raise
        self.fd=fd

    def ready(self):
        if self.maintenance:raise RuntimeError('A maintenance writer cannot become an application startup.')
        if sys.platform=='darwin':
            try:ready=ctypes.CDLL(None).AugmentorStartupReady
            except AttributeError:pass  # Independent Python helper/source process.
            else:
                ready.argtypes=[];ready.restype=ctypes.c_int
                if ready()!=1:raise RuntimeError('The native startup reservation could not be released.')
        self.close()

    def handoff(self):
        """Caller immediately execs the fixed Node host, which closes on readiness."""
        if self.maintenance or self.fd is None:raise RuntimeError('Only a live startup reader can transfer through exec.')
        os.set_inheritable(self.fd,True)
        return self.fd

    def close(self):
        if self.fd is not None:
            fd,self.fd=self.fd,None
            os.close(fd)

    def __enter__(self):return self
    def __exit__(self,*_):self.close()
