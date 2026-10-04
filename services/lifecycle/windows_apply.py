# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Windows apply backend for the shared coordinator's verified-artifact boundary.

The caller verifies and retains current/recovery and target artifacts before
draining. This adapter binds bytes and the actual Setup process; it does not
establish publisher trust, download, complete installation or replay recovery.
"""
import os
from pathlib import Path

from platform_adapters.private_files import descriptor, require_directory
from .windows_handoff import InstallerHandoff
from .windows_installer_process import InstallerProcess


class WindowsApply:
    def __init__(self, startup, artifact, sha256, log, *, qualification_outer_job=False):
        self.startup, self.artifact, self.sha256 = startup, Path(artifact), sha256
        self.log = Path(log)
        self.qualification_outer_job = qualification_outer_job
        self.handoff = self.installer = None
        self.entered = self.closed = False

    def __enter__(self):
        if self.entered or self.closed: raise ValueError('Use a fresh Windows apply attempt; never replay a handoff.')
        self.entered = True
        try:
            require_directory(self.log.parent)
            # A unique private log, owned by the actual user even in elevated
            # qualification. Preserve an earlier attempt rather than truncating.
            os.close(descriptor(self.log, writable=True, exclusive=True))
            self.handoff = InstallerHandoff(self.startup).__enter__()
            self.installer = InstallerProcess(self.artifact, self.sha256,
                ['/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
                 '/LOG='+str(self.log), *self.handoff.arguments()],
                qualification_outer_job=self.qualification_outer_job)
            self.handoff.bind(self.installer)
            return self
        except BaseException:
            self.close(); raise

    def wait_ready(self):
        if self.closed or self.handoff is None: raise ValueError('The Windows installer backend is not running.')
        self.handoff.wait_ready(timeout=30)

    def authorize(self):
        if self.closed or self.handoff is None: raise ValueError('The Windows installer backend is not running.')
        self.handoff.authorize()

    def close(self):
        if self.closed: return
        self.closed = True
        try:
            # Cancel/finish the protocol while kernel process observations still
            # exist. Closing observation handles never terminates Setup.
            if self.handoff is not None: self.handoff.close()
        finally:
            if self.installer is not None: self.installer.close()

    def __exit__(self, *_): self.close()
