# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One-shot atomic Mac bundle replacement after observed graph drain.

Caller stages verified bytes on the destination volume, retains exact source
recovery, coordinates owned launchd registrations, and supplies fresh authority
through authorize_update. This backend alone cannot authorize an update.
"""
import importlib.util
import os
from pathlib import Path
import sys

from platform_adapters import locks
from platform_adapters.private_files import descriptor,require_directory
from .macos_payload import verify_bundle
from .posix_startup import Startup


class MacInstallerBackend:
    def __init__(self,gate,destination,staged,source_release,target_release,source_payload,target_payload,*,development=False):
        if sys.platform!='darwin':raise RuntimeError('Mac installation requires macOS.')
        if not isinstance(gate,Startup) or not gate.maintenance or gate.fd is None:
            raise ValueError('Retain the live startup writer through Mac installation.')
        self.gate=gate;self.destination=Path(destination).absolute();self.staged=Path(staged).absolute()
        self.source_release,self.target_release=source_release,target_release
        self.source_payload,self.target_payload=source_payload,target_payload
        self.development=development;self.fd=None;self.ready=False;self.started=False;self.closed=False;self.backup=None
        if self.destination==self.staged or self.staged.is_relative_to(self.destination):raise ValueError('Stage outside the source bundle.')
        if not development and self.destination.parent not in (Path('/Applications'),Path.home()/'Applications'):
            raise ValueError('Use the existing canonical Applications installation.')

    def validate(self):
        if self.closed or self.gate.fd is None:raise ValueError('Mac installation admission is closed.')
        before=verify_bundle(self.destination,self.source_release,development=self.development)
        after=verify_bundle(self.staged,self.target_release,development=self.development,team=before['team'])
        if before!=self.source_payload or after!=self.target_payload:
            raise ValueError('The source or candidate changed after independent inspection.')
        if before['component']!=after['component']:raise ValueError('The candidate belongs to another component.')
        if self.destination.parent.stat().st_dev!=self.staged.parent.stat().st_dev:
            raise ValueError('Stage the application on its destination volume before preparation.')
        if not os.access(self.destination.parent,os.W_OK|os.X_OK):
            raise PermissionError('This application needs OS-authorized manual installation.')

    def __enter__(self):
        if self.closed or self.fd is not None:raise ValueError('Use a fresh Mac installation backend.')
        return self

    def wait_ready(self):
        if self.ready or self.started:raise ValueError('Mac installation readiness is one-shot.')
        self.validate()
        require_directory(self.gate.path.parent)
        fd=descriptor(self.gate.path.parent/'installation.lock',writable=True,create=True)
        try:locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)
        except BaseException:os.close(fd);raise
        self.fd=fd;self.ready=True

    def authorize(self):
        if self.closed or not self.ready or self.fd is None or self.started:raise ValueError('Mac apply was not ready or was already attempted.')
        self.started=True  # Unknown outcomes never permit another call.
        self.validate()
        script=Path(__file__).resolve().parents[2]/'scripts/install-macos.py'
        spec=importlib.util.spec_from_file_location('augmentor_verified_mac_replace',script)
        installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
        if installer.journal_path(self.destination).exists() or installer.journal_path(self.destination).is_symlink():
            raise ValueError('An earlier native installation needs independent recovery.')
        # The existing installer preserves an exact old bundle and restores it
        # on a confirmed failed promotion rename. It never edits user data.
        self.backup=installer.replace(self.staged,self.destination)

    def close(self):
        self.closed=True
        if self.fd is not None:os.close(self.fd);self.fd=None

    def __exit__(self,*_):self.close()
