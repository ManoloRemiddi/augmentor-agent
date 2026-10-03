# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Complete a live successful Mac apply after exact offline target health.

No saved receipt, phase or PID can reconstruct the original backend observation.
Unknown outcomes stay pending; this path cannot replace or restore applications.
"""
from contextlib import ExitStack
import hashlib
import os
import sys

from lifecycle.macos_apply import MacInstallerBackend
from lifecycle.macos_health import verify_local_health
from lifecycle.macos_payload import verify_bundle
from lifecycle.payload_integrity import _json
from lifecycle.posix_startup import Startup
from lifecycle.update_journal import UpdateJournal,artifact,validate
from platform_adapters import locks
from platform_adapters.private_files import descriptor,require_directory


def complete_observed(backend,source,target):
    if sys.platform!='darwin':raise RuntimeError('Mac completion requires native macOS.')
    if (not isinstance(backend,MacInstallerBackend) or not backend.closed or not backend.applied
            or not backend.started or not backend.backup or not backend.record_sha256 or backend.journal is None
            or backend.journal.fd is not None or backend.journal.uncertain):
        raise ValueError('Retain the original successfully returned apply and closed journal before completion.')
    source,target=artifact(source),artifact(target)
    record=backend.journal.record
    if record['source']!=source or record['target']!=target or record['phase']!='apply-acknowledged':
        raise ValueError('Completion must identify the original observed release pair.')
    for identity,raw in ((source,backend.source_release),(target,backend.target_release)):
        release=_json(raw,65536)
        if any(identity[key]!=release.get(key) for key in ('version','sourceCommit','target','channel','dataSchema','readableDataSchemas')):
            raise ValueError('The retained release bytes differ from the transaction identity.')
        if not backend.development and release.get('automaticInstallQualified') is not True:
            raise ValueError('This public release has not qualified automatic installation.')
    transactions=require_directory(backend.journal.directory)
    with ExitStack() as held:
        gate=held.enter_context(Startup(backend.gate.path.parent,maintenance=True,transactions=transactions))
        lifetime=descriptor(gate.path.parent/'installation.lock',writable=True,create=True)
        held.callback(os.close,lifetime);locks.flock(lifetime,locks.LOCK_EX|locks.LOCK_NB)
        def health(current):
            with os.fdopen(descriptor(transactions/'active.json'),'rb') as stream:
                raw=stream.read(65537)
            if (len(raw)>65536 or validate(_json(raw,65536))!=current or current!=record
                    or hashlib.sha256(raw).hexdigest()!=backend.record_sha256):
                raise ValueError('The acknowledged transaction changed before independent completion.')
            if verify_bundle(backend.backup,backend.source_release,development=backend.development)!=backend.source_payload:
                raise ValueError('The retained source recovery differs from the original verified bundle.')
            report=verify_local_health(backend.destination,backend.target_release,backend.target_payload,
                development=backend.development)
            if report['payloadSHA256']!=backend.target_payload['sha256']:
                raise ValueError('Independent health did not verify the exact applied target.')
            return True
        archive=UpdateJournal.complete_verified(transactions,source,target,health)
    return {'transactionId':record['id'],'archive':str(archive),'installationComplete':True,
        'reopened':False,'payloadSHA256':backend.target_payload['sha256']}
