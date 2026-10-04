# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Retained Mac observer composes fresh authority, stage, apply and completion."""
from contextlib import ExitStack
import hashlib
import os
from pathlib import Path
import platform
import re
import sys

from platform_adapters import locks
from platform_adapters.paths import private_directory,runtime_directory
from platform_adapters.private_files import descriptor,require_directory
from platform_adapters.peer_process import _executable
from lifecycle.macos_payload import verify_bundle
from lifecycle.posix_startup import Startup
from lifecycle.posix_paths import shared_state_directory
from lifecycle.update_journal import artifact
from lifecycle.payload_integrity import _read
from .macos_bootstrap import locations
from .macos_coordinator import MacCoordinator
from .macos_staging import stage_download
from .installation import AutomaticInstallAuthority
from .attempt import attempt_id,write_result
from lifecycle.posix_observer_retention import retain, eligible


def run(observer,source_bundle,release_digest,payload_digest,attempt,bootstrap_fd):
    if sys.platform!='darwin':raise RuntimeError('The Mac observer requires native macOS.')
    attempt_id(attempt);observer=Path(observer).resolve();source_bundle=Path(source_bundle).absolute()
    root=source_bundle/'Contents/Resources/app';bundle,base,transactions=locations(root)
    transactions=require_directory(transactions);updates=require_directory(base/'data/augmentor/updates')
    coordinator=None;candidate=None
    retained=False;verified=False
    def retire(outcome):
        if retained and verified and outcome in ('deferred','target-healthy'):
            try:eligible(observer.parent,outcome,payload_digest)
            except (OSError,ValueError):pass  # Preserve the confirmed installation result.
    try:
        if (any(not isinstance(value,str) or not re.fullmatch('[a-f0-9]{64}',value) for value in (release_digest,payload_digest))
                or type(bootstrap_fd) is not int or bootstrap_fd<3):raise ValueError('Use exact source digests and the inherited original launch descriptor.')
        expected=base/'cache/update-observers'/('mac-'+attempt)/'Observer.app'
        if (observer!=expected or _executable(os.getpid()).resolve()!=(observer/'Contents/Resources/app/python/bin/python3').resolve()
                or Path(__file__).resolve().parents[2]!=observer/'Contents/Resources/app'):
            raise ValueError('The actual updater executable and code must be outside the replaceable source.')
        with ExitStack() as held:
            retain(observer.parent);retained=True
            held.callback(os.close,bootstrap_fd)
            fresh=descriptor(transactions/'bootstrap.lock',writable=True)
            try:
                a,b=os.fstat(bootstrap_fd),os.fstat(fresh)
                if (a.st_dev,a.st_ino)!=(b.st_dev,b.st_ino):raise ValueError('The inherited bootstrap admission belongs to another file.')
            finally:os.close(fresh)
            locks.flock(bootstrap_fd,locks.LOCK_EX|locks.LOCK_NB)
            fd=descriptor(transactions/'observer.lock',writable=True,create=True)
            held.callback(os.close,fd);locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)
            release=_read(observer/'Contents/Resources/app/release.json',65536)
            if hashlib.sha256(release).hexdigest()!=release_digest:raise ValueError('The retained release changed across exec.')
            payload=verify_bundle(observer,release)
            if payload['sha256']!=payload_digest:raise ValueError('The retained payload changed across exec.')
            verified=True
            with ExitStack() as admission:
                admission.enter_context(Startup())
                lifetime=descriptor(runtime_directory()/'installation.lock',writable=True,create=True)
                admission.callback(os.close,lifetime);locks.flock(lifetime,locks.LOCK_SH|locks.LOCK_NB)
                if verify_bundle(bundle,release)!=payload:raise ValueError('The source changed after its actual observer exec.')
                authority=held.enter_context(AutomaticInstallAuthority(root,updates,os_version=platform.mac_ver()[0]))
                candidate=authority.selected
                if len(candidate['artifacts'])!=1 or candidate['artifacts'][0]['role']!='bundle':
                    raise ValueError('This release requires a separate multi-artifact installation plan.')
                stages=require_directory(private_directory(bundle.parent/('.augmentor-stage-'+attempt)))
                target_bundle,target_release,target_payload=stage_download(
                    next(item for item in authority.files if item['artifact']['role']=='bundle'),stages,candidate,team=payload['team'])
            source={key:authority.current[key] for key in ('version','sourceCommit','target','channel','dataSchema','readableDataSchemas')}
            source['sha256']=payload_digest
            item=next(row for row in candidate['artifacts'] if row['role']=='bundle')
            target={key:candidate[key] for key in ('version','sourceCommit','target','channel','dataSchema','readableDataSchemas')}
            target['sha256']=item['sha256']
            shared=shared_state_directory()
            coordinator=MacCoordinator(bundle,target_bundle,runtime_directory(),shared,transactions,release,target_release,
                payload,target_payload,artifact(source),artifact(target))
            result=coordinator.run(authority.check)
            retire('target-healthy')
            return write_result(transactions,attempt,'target-healthy',candidate=candidate,
                transaction=result['transactionId'],reopened=result['reopened'])
    except Exception as error:
        if coordinator is not None and coordinator.completion is not None:
            retire('target-healthy')
            return write_result(transactions,attempt,'target-healthy',candidate=candidate,
                transaction=coordinator.completion['transactionId'],error='The update is installed. Reopen Augmentor normally. '+str(error))
        cancelled=getattr(error,'augmentor_preparation_cancelled',None)
        pending=transactions/'active.json'
        outcome='deferred' if cancelled or coordinator is None and not pending.exists() and not pending.is_symlink() else 'failed'
        retire(outcome)
        write_result(transactions,attempt,outcome,candidate=candidate,error=error)
        raise
