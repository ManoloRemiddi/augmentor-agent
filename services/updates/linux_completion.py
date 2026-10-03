# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Independent offline completion for this original managed selection only."""
from contextlib import ExitStack
import hashlib
import os
import subprocess

from lifecycle.macos_payload import snapshot
from lifecycle.payload_integrity import _json,_read
from lifecycle.posix_startup import Startup
from lifecycle.update_journal import UpdateJournal
from platform_adapters import locks
from platform_adapters.private_files import descriptor,read_json
from .linux_managed import ManagedBackend,selection_bytes


def verify_health(plan):
    raw=_read(plan.target/'release.json',65536)
    release=_json(raw,65536)
    result=subprocess.run([plan.proposed['python'],'-I','-B',str(plan.target/'scripts/linux-local-health.py')],
        stdin=subprocess.DEVNULL,capture_output=True,timeout=45)
    if result.returncode:raise RuntimeError('The fixed offline Linux UI health action failed.')
    report=_json(result.stdout,4096)
    if (not isinstance(report,dict) or set(report)!={'schema','releaseSHA256','version','sourceCommit','target',
            'qtPlatform','rendered','width','height','fontCoverage'} or report['schema']!='augmentor-linux-health/1'
            or report['releaseSHA256']!=hashlib.sha256(raw).hexdigest()
            or any(report[key]!=release.get(key) for key in ('version','sourceCommit','target'))
            or report['qtPlatform']!='offscreen' or report['rendered'] is not True or report['fontCoverage'] is not True
            or any(type(report[key]) is not int or not 1<=report[key]<=32768 for key in ('width','height'))):
        raise ValueError('The offline report differs from the applied managed target.')
    return True


def complete_observed(backend):
    if (not isinstance(backend,ManagedBackend) or not backend.closed or not backend.plan.applied
            or backend.plan.closed or backend.plan.fd is None or not backend.record_sha256
            or backend.journal.fd is not None or backend.journal.uncertain):
        raise ValueError('Retain the original successfully applied managed selection and closed journal.')
    plan,journal=backend.plan,backend.journal
    source,target=plan.pair();record=journal.record
    if record['phase']!='apply-acknowledged':raise ValueError('The original selection was not acknowledged.')
    with ExitStack() as held:
        gate=held.enter_context(Startup(backend.gate.path.parent,maintenance=True,transactions=journal.directory))
        fd=descriptor(gate.path.parent/'installation.lock',writable=True,create=True)
        held.callback(os.close,fd);locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)
        def health(current):
            raw,actual=selection_bytes(journal.path)
            if (current!=record or actual!=record or hashlib.sha256(raw).hexdigest()!=backend.record_sha256
                    or read_json(plan.data/'desktop.json')!=plan.proposed
                    or read_json(plan.data/'desktop.previous.json')!=plan.previous):
                raise ValueError('The acknowledged managed selection changed before completion.')
            def immutable():
                if (snapshot(plan.source)!=plan.source_payload or snapshot(plan.target)!=plan.target_payload
                        or plan.tool.verify(plan.source)!=plan.source_manifest or plan.tool.verify(plan.target)!=plan.target_manifest):
                    raise ValueError('The retained managed source or target changed.')
            immutable()
            if plan.registration is not None:plan.registration.verify_applied()
            if plan.services is not None:plan.services.verify_applied()
            if plan.desktop is not None:plan.desktop.verify_applied()
            if verify_health(plan) is not True:raise ValueError('Offline managed target health was not verified.')
            immutable()
            if plan.registration is not None:plan.registration.verify_applied()
            if plan.services is not None:plan.services.verify_applied()
            if plan.desktop is not None:plan.desktop.verify_applied()
            return True
        archive=UpdateJournal.complete_verified(journal.directory,source,target,health)
    return {'transactionId':record['id'],'archive':str(archive),'installationComplete':True,
        'reopened':False,'payloadSHA256':plan.target_payload['sha256']}
