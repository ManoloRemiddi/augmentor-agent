# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Activate the desktop from a shortcut owner outside the app process."""
import errno
from pathlib import Path
import subprocess
import sys
import threading
from .instances import validate_name, ipc_basename
from .platform_runtime import LocalSocket, runtime_directory


ROOT = Path(__file__).resolve().parents[3]


class DesktopActivation:
    """Coalesce startup requests and never retry an uncertain toggle delivery."""

    def __init__(self, runtime=None, command=None, instance='main'):
        self.instance = validate_name(instance)
        self.runtime = Path(runtime) if runtime is not None else runtime_directory()
        self.command = command or [sys.executable, '-B', str(ROOT/'scripts/launch-component.py'), 'desktop']
        if command is None and sys.platform == 'win32' and (ROOT/'Augmentor.exe').is_file():
            self.command = [str(ROOT/'Augmentor.exe')]
        elif command is None and sys.platform == 'darwin' and len(ROOT.parents) > 1:
            native = ROOT.parents[1]/'MacOS/Augmentor Agent Desktop'
            if native.is_file():
                self.command = [str(native)]
        if self.instance != 'main' or sys.platform == 'win32':
            self.command = [*self.command, '--instance', self.instance]
        self.child = None
        self.lock = threading.Lock()

    def activate(self):
        with self.lock:
            with LocalSocket() as connection:
                connection.settimeout(1)
                try:
                    connection.connect(str(self.runtime/(ipc_basename(self.instance)+'.sock')))
                except OSError as error:
                    # Only an absent listener proves that launch is appropriate.
                    # Permission errors, timeouts and resource exhaustion do not.
                    if not isinstance(error, FileNotFoundError) and error.errno not in (errno.ENOENT, errno.ECONNREFUSED):
                        raise
                else:
                    if sys.platform == 'win32':
                        from .windows_focus import allow_foreground
                        allow_foreground(connection)
                    # Once connected, a failed send has an unknown outcome.
                    # Launching the app again could toggle the window twice.
                    connection.sendall(b'toggle\n' if sys.platform=='win32' else b'toggle')
                    return 'delivered'
            if self.child is not None and self.child.poll() is None:
                return 'starting'
            self.child = subprocess.Popen(
                self.command, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                **({'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform=='win32' else {'start_new_session':True}),
            )
            return 'launched'
