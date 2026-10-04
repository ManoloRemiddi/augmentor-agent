# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One private byte-stream protocol, backed by each OS's authenticated transport."""
import os
from pathlib import Path
import socket
import socketserver
import stat
import sys


if sys.platform == 'win32':
    from .windows_pipe import PipeSocket as LocalSocket, ThreadingPipeServer as ThreadingLocalServer
else:
    class LocalSocket(socket.socket):
        def __init__(self):
            super().__init__(socket.AF_UNIX, socket.SOCK_STREAM)

        def connect(self, address):
            super().connect(os.fspath(address))
            from platform_support import require_same_user
            try:
                require_same_user(self)
            except BaseException:
                self.close()
                raise

    ThreadingLocalServer = socketserver.ThreadingUnixStreamServer


def prepare_endpoint(endpoint):
    """Called only while holding the owning service's exclusive startup lease."""
    if sys.platform == 'win32':
        return  # The kernel owns pipe lifetime; no filesystem entry is removed.
    path = Path(endpoint)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
        raise PermissionError('The service endpoint is not an owned socket.')
    path.unlink()


def cleanup_endpoint(endpoint):
    if sys.platform != 'win32':
        Path(endpoint).unlink(missing_ok=True)
