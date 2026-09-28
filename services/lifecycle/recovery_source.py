# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bind an independent installer's identity to an interrupted update's source.

Native admission, a live exclusive journal-writer lock, and a pinned private
record must precede this read-only assessment. The artifact metadata comes from
the independent installer, never from installed code or the selection pointer.
A match neither proves health/publisher trust nor authorizes replay or rollback.
"""
import hashlib

from .payload_integrity import _json
from .update_journal import artifact, validate, recovery_action

MAX_RECORD = 65536


def assess_source(record_bytes, release_bytes, installer_digest):
    record = validate(_json(record_bytes,MAX_RECORD))
    release = _json(release_bytes,65536)
    if not isinstance(release,dict):raise ValueError('Independent release metadata is invalid.')
    source = artifact({key:release.get(key) for key in (
        'version','sourceCommit','target','channel','dataSchema','readableDataSchemas')} |
        {'sha256':installer_digest})
    if source != record['source']:
        raise ValueError('This installer is not the exact recorded previous release.')
    # Preserve the complete durable record. In particular, recorded PIDs and
    # unknown COMMIT/APPLY outcomes are never turned into process commands.
    return {'schema':'augmentor-recovery-source/1','transactionId':record['id'],
        'recordSHA256':hashlib.sha256(record_bytes).hexdigest(),
        'installerSHA256':source['sha256'],
        'releaseSHA256':hashlib.sha256(release_bytes).hexdigest(),
        'phase':record['phase'],'requiredObservation':recovery_action(record),
        'recordedSourceMatches':True,'applyAuthorized':False}
