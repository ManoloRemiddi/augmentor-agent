# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Activate the desktop from a shortcut owner outside the app process."""
import errno
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading


ROOT = Path(__file__).resolve().parents[3]


class DesktopActivation:
    """Coalesce startup requests and never retry an uncertain toggle delivery."""

    def __init__(self, runtime=None, command=None):
        self.runtime = Path(runtime or os.environ.get(
            'XDG_RUNTIME_DIR', f'/tmp/augmentor-{os.getuid()}'))
        native=ROOT.parents[1]/'MacOS/Augmentor Agent Desktop'
        self.command = command or ([str(native)] if sys.platform=='darwin' and native.is_file() else
                                  [sys.executable, '-B', str(ROOT/'scripts/launch-component.py'), 'desktop'])
        self.child = None
        self.lock = threading.Lock()

    def activate(self):
        with self.lock:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(1)
                try:
                    connection.connect(str(self.runtime/'augmentor-linux-pi.sock'))
                except OSError as error:
                    # Only an absent listener proves that launch is appropriate.
                    # Permission errors, timeouts and resource exhaustion do not.
                    if error.errno not in (errno.ENOENT, errno.ECONNREFUSED):
                        raise
                else:
                    # Once connected, a failed send has an unknown outcome.
                    # Launching the app again could toggle the window twice.
                    connection.sendall(b'toggle')
                    return 'delivered'
            if self.child is not None and self.child.poll() is None:
                return 'starting'
            self.child = subprocess.Popen(
                self.command, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return 'launched'
