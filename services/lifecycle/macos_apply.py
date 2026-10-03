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
    def __init__(self,gate,destination,staged,source_release,target_release,source_payload,target_payload,*,development=False,journal=None):
        if sys.platform!='darwin':raise RuntimeError('Mac installation requires macOS.')
        if not isinstance(gate,Startup) or not gate.maintenance or gate.fd is None:
            raise ValueError('Retain the live startup writer through Mac installation.')
        self.gate=gate;self.destination=Path(destination).absolute();self.staged=Path(staged).absolute()
        self.source_release,self.target_release=source_release,target_release
        self.source_payload,self.target_payload=source_payload,target_payload
        self.development=development;self.fd=None;self.ready=False;self.started=False;self.closed=False;self.backup=None
        self.journal=journal;self.applied=False;self.record_sha256=None
        if self.destination==self.staged or self.staged.is_relative_to(self.destination):raise ValueError('Stage outside the source bundle.')
        if not development and self.destination.parent not in (Path('/Applications'),Path.home()/'Applications'):
            raise ValueError('Use the existing canonical Applications installation.')

    def validate(self):
        if self.closed or self.gate.fd is None:raise ValueError('Mac installation admission is closed.')
        if any(Path(__file__).resolve().is_relative_to(path.resolve()) for path in (self.destination,self.staged)):
            raise ValueError('Run the updater from retained source code outside both replaceable bundles.')
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
        from .update_journal import validate
        from platform_adapters.private_files import read_json
        journal=self.journal
        if (journal is None or journal.fd is None or journal.uncertain or journal.record['phase']!='apply-intent'
                or journal.directory!=self.gate.transactions or validate(read_json(journal.path))!=journal.record):
            raise ValueError('Retain this live apply intent in the persistent startup barrier directory.')
        self.validate()
        script=Path(__file__).resolve().parents[2]/'scripts/install-macos.py'
        spec=importlib.util.spec_from_file_location('augmentor_verified_mac_replace',script)
        installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
        if installer.journal_path(self.destination).exists() or installer.journal_path(self.destination).is_symlink():
            raise ValueError('An earlier native installation needs independent recovery.')
        # The existing installer preserves an exact old bundle and restores it
        # on a confirmed failed promotion rename. It never edits user data.
        self.backup=installer.replace(self.staged,self.destination)
        self.applied=True  # Only the actual successful return can establish this.

    def observe_acknowledgement(self):
        """Original caller seals the exact durable acknowledgement after apply."""
        import hashlib
        from platform_adapters.private_files import descriptor,read_json
        if (not self.applied or self.record_sha256 is not None or self.journal is None or self.journal.fd is None
                or self.journal.uncertain or self.journal.record['phase']!='apply-acknowledged'
                or read_json(self.journal.path)!=self.journal.record):
            raise ValueError('Only this successfully applied attempt can retain its acknowledgement.')
        with os.fdopen(descriptor(self.journal.path),'rb') as stream:
            raw=stream.read(65537)
        if len(raw)>65536:raise ValueError('The update record exceeds its supported size.')
        self.record_sha256=hashlib.sha256(raw).hexdigest()

    def close(self):
        self.closed=True
        if self.fd is not None:os.close(self.fd);self.fd=None

    def __exit__(self,*_):self.close()
