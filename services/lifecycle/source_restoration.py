# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One live recovery attempt; preserve the original update's exact history.

The independent observer verifies the source artifact before construction, owns
the fresh installer process, observes its exit and retains maintenance admission
during final verification. This journal never launches an installer, trusts saved
PIDs, replays an attempt or establishes publisher trust. Source restoration is a
distinct outcome, not successful installation of the original update's target.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import secrets

from platform_adapters import locks
from platform_adapters.private_files import atomic_json, descriptor, require_directory, replace_file
from .payload_integrity import _json
from .recovery_source import assess_source, MAX_RECORD


def _read(path):
    with os.fdopen(descriptor(path), 'rb') as stream:
        raw = stream.read(MAX_RECORD + 1)
    if len(raw) > MAX_RECORD:
        raise ValueError('The recovery record exceeds its supported size.')
    return raw


class SourceRestoration:
    def __init__(self, directory, record_bytes, release_bytes, installer_digest):
        self.directory = require_directory(Path(directory))
        self.active = self.directory / 'active.json'
        self.original = bytes(record_bytes)
        self.assessment = assess_source(self.original, release_bytes, installer_digest)
        self.record = None
        self.closed = self.uncertain = False
        attempt = secrets.token_hex(24)
        self.path = self.directory / ('restoration-' + attempt + '.json')
        self.archive = self.directory / ('restored-' + self.assessment['transactionId'] + '-' + attempt + '.json')
        try:
            with self._writer():
                if self.path.exists() or self.path.is_symlink() or self.archive.exists() or self.archive.is_symlink():
                    raise ValueError('A recovery attempt already exists. Its records were preserved.')
                self._write({'schema': 'augmentor-source-restoration/1', 'id': attempt,
                    **{key: self.assessment[key] for key in (
                        'transactionId', 'recordSHA256', 'installerSHA256', 'releaseSHA256')},
                    'phase': 'prepared', 'revision': 0, 'updatedAt': '', 'archive': self.archive.name})
        except BaseException:
            self.close()
            raise

    @contextmanager
    def _writer(self):
        if self.closed or self.uncertain:
            raise ValueError('This restoration attempt is closed or uncertain. Fresh observation is required.')
        # The original update created this file. Never create replacement state
        # when the canonical writer or active record is missing.
        fd = descriptor(self.directory / 'writer.lock', writable=True)
        try:
            locks.flock(fd, locks.LOCK_EX | locks.LOCK_NB)
            if _read(self.active) != self.original:
                raise ValueError('The original update record changed. Recovery was not completed.')
            if self.record is not None and _json(_read(self.path), MAX_RECORD) != self.record:
                raise ValueError('The restoration record changed. It was preserved.')
            yield
        finally:
            os.close(fd)

    def _write(self, record):
        record = deepcopy(record)
        record['updatedAt'] = datetime.now(timezone.utc).isoformat()
        try:
            atomic_json(self.path, record)
        except BaseException:
            self.uncertain = True
            raise
        self.record = record

    def _phase(self, expected, phase):
        if self.record['phase'] != expected:
            raise ValueError('A restoration phase cannot be skipped or repeated.')
        record = deepcopy(self.record)
        record['phase'] = phase
        record['revision'] += 1
        self._write(record)

    def apply_intent(self):
        """Durable one-shot intent; release the writer before Setup acquires it."""
        with self._writer():
            self._phase('prepared', 'apply-intent')

    def observed_installer_exit(self, verify_exit):
        """Require fresh live-process evidence, not a persisted exit-code field."""
        if not callable(verify_exit):
            raise ValueError('An independently observed installer exit is required.')
        with self._writer():
            if self.record['phase'] != 'apply-intent':
                raise ValueError('Only this live restoration intent can observe its installer.')
            if verify_exit() is not True:
                self.uncertain = True
                raise ValueError('Installer completion is unverified. The original update remains unresolved.')
            if _read(self.active) != self.original:
                raise ValueError('The original update changed during installer observation.')
            self._phase('apply-intent', 'installed')

    def complete(self, verify_source):
        """Archive unchanged original bytes only after complete source verification.

        The caller holds installation/read admission throughout this call. Its
        callback checks source selection, owned installation metadata, full payload
        inventory and isolated UI health against independently retained source
        bytes. It must not launch another installer needing this writer lock.
        """
        if not callable(verify_source):
            raise ValueError('Independent restored-source verification is required.')
        with self._writer():
            if self.record['phase'] != 'installed':
                raise ValueError('The source installer has not been independently observed completing.')
            if verify_source(deepcopy(self.assessment)) is not True:
                self.uncertain = True
                raise ValueError('Restored source verification failed. The original update remains unresolved.')
            if _read(self.active) != self.original:
                raise ValueError('The original update changed during source verification.')
            if self.archive.exists() or self.archive.is_symlink():
                raise ValueError('A restoration archive already exists. Both records were preserved.')
            # Write the distinct outcome first. Removing active.json can only
            # expose normal startup after this receipt and verification exist.
            self._phase('installed', 'source-restored')
            try:
                replace_file(self.active, self.archive)
            except BaseException:
                self.uncertain = True
                raise
        self.close()
        return self.archive

    def close(self):
        self.closed = True

    def __enter__(self): return self
    def __exit__(self, *_): self.close()
