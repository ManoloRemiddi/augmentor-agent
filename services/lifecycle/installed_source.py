# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Read the exact native-installer selection; no publisher/health claim or apply.

The caller supplies bytes from the independently identified installed release
and its actual OS/CPU. The native installer binds those bytes to its retained
source. These private receipts are distinct from signed update-bundle metadata.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from platform_adapters.private_files import descriptor, require_directory
from .release_bundle import MAX_INSTALLER, MAX_MANIFEST, _object
from .update_journal import artifact

PREFIX = b'augmentor-installer-selection/1\n'
RECORD_BYTES = len(PREFIX)+130


def _held(path):
    if sys.platform == 'win32':
        from platform_adapters.windows_identity import private_file_descriptor
        return private_file_descriptor(path, share_write=False)
    return descriptor(path)


@dataclass
class InstalledSource:
    installer: Path
    identity: dict
    release_digest: str
    fd: int | None

    def close(self):
        if self.fd is not None: os.close(self.fd); self.fd = None

    def __enter__(self): return self
    def __exit__(self, *_): self.close()


@dataclass
class RecordedSource(InstalledSource):
    """Held candidate from a journal, still requiring independent assessment.

    The receipt's release digest must match the installer's embedded metadata.
    Neither this object nor a saved journal authorizes execution or restoration.
    """
    record_digest: str
    transaction_id: str


def _open_retained(recovery, digest, *, expected_release=None):
    with os.fdopen(_held(recovery/(digest+'.release')), 'rb') as receipt:
        raw = receipt.read(65)
        if not re.fullmatch(rb'[a-f0-9]{64}', raw):
            raise ValueError('The retained installer receipt is invalid. Preserve it for repair.')
        release_digest = raw.decode('ascii')
        if expected_release is not None and release_digest != expected_release:
            raise ValueError('The retained installer receipt differs from the selected build.')
    installer = recovery/(digest+'.exe'); pinned = _held(installer)
    try:
        with os.fdopen(os.dup(pinned), 'rb') as stream:
            if (not 0 < os.fstat(stream.fileno()).st_size <= MAX_INSTALLER or
                    hashlib.file_digest(stream,'sha256').hexdigest() != digest):
                raise ValueError('The retained original installer is damaged. Preserve it for repair.')
        return installer, release_digest, pinned
    except BaseException:
        os.close(pinned); raise


def open_recorded_source(recovery, record_bytes, *, target):
    """Find only the journal's exact source, independent of installed selection.

    The caller holds fresh maintenance/writer admission and supplies the pinned
    active record. This lookup performs no directory scan, fallback, journal
    mutation or process launch. A returned receipt is raw identity, not trust:
    independently extracted metadata and actual installer bytes must still pass
    assess_source against the same record before any recovery decision.
    """
    from .payload_integrity import _json
    from .recovery_source import MAX_RECORD
    from .update_journal import validate

    record = validate(_json(record_bytes, MAX_RECORD))
    identity = artifact(record['source'])
    if target not in ('windows-x64','windows-arm64') or identity['target'] != target:
        raise ValueError('The recorded recovery source targets a different OS or CPU.')
    recovery = require_directory(Path(recovery))
    installer, release_digest, pinned = _open_retained(recovery, identity['sha256'])
    return RecordedSource(installer, identity, release_digest, pinned,
                          hashlib.sha256(record_bytes).hexdigest(), record['id'])


def open_installed_source(recovery, release_bytes, *, target):
    """Pin exact retained bytes before creating a new update journal.

    Call under the product's current-installation observation/admission scope.
    A record mismatch means inspect/repair, never pick another cached executable.
    Selection alone cannot identify health after interrupted replacement, and
    neither receipt ownership nor SHA-256 establishes publisher trust.
    """
    recovery = require_directory(Path(recovery))
    if not isinstance(release_bytes, bytes) or not 0 < len(release_bytes) <= MAX_MANIFEST:
        raise ValueError('The identified installed release metadata is required.')
    with os.fdopen(_held(recovery/'selected-installer'), 'rb') as selected:
        raw = selected.read(RECORD_BYTES+1)
        if not re.fullmatch(re.escape(PREFIX)+rb'[a-f0-9]{64}\n[a-f0-9]{64}\n', raw):
            raise ValueError('The installer selection is invalid. Preserve it for repair.')
        digest, release_digest = raw[len(PREFIX):].decode('ascii').splitlines()
        if hashlib.sha256(release_bytes).hexdigest() != release_digest:
            raise ValueError('The selected installer does not match the identified application.')
        try: release = json.loads(release_bytes.decode('utf-8'), object_pairs_hook=_object)
        except (UnicodeError, ValueError, RecursionError):
            raise ValueError('The identified application metadata is invalid.') from None
        if not isinstance(release, dict): raise ValueError('The identified application metadata is invalid.')
        identity = artifact({name:release.get(name) for name in (
            'version','sourceCommit','target','channel','dataSchema','readableDataSchemas')} | {'sha256':digest})
        if target not in ('windows-x64','windows-arm64') or identity['target'] != target:
            raise ValueError('The retained installation targets a different OS or CPU.')
        installer, _, pinned = _open_retained(recovery, digest, expected_release=release_digest)
        return InstalledSource(installer, identity, release_digest, pinned)
