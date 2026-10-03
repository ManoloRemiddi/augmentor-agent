# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Retained Linux observer binds authority, exact staging and live selection."""
from contextlib import ExitStack
import hashlib
import os
from pathlib import Path
import re
import sys

from lifecycle.macos_payload import snapshot
from lifecycle.payload_integrity import _read
from lifecycle.posix_startup import Startup
from lifecycle.posix_paths import shared_state_directory
from platform_adapters import locks
from platform_adapters.paths import private_directory,runtime_directory
from platform_adapters.private_files import descriptor,require_directory
from platform_adapters.peer_process import _executable
from .linux_bootstrap import locations,inspect_source
from .linux_staging import stage_download
from .linux_managed import ManagedPlan
from .linux_coordinator import LinuxCoordinator
from .installation import AutomaticInstallAuthority
from .manager import UpdateManager
from .attempt import attempt_id,write_result


def run(observer,source_root,release_digest,payload_digest,attempt,bootstrap_fd):
    if sys.platform!='linux':raise RuntimeError('The Linux observer requires native Linux.')
    attempt_id(attempt);observer=Path(observer).resolve();source=Path(source_root).absolute()
    data,transactions=locations(source);transactions=require_directory(transactions)
    updates=require_directory(data/'updates');coordinator=None;candidate=None
    try:
        if (any(not isinstance(value,str) or not re.fullmatch('[a-f0-9]{64}',value) for value in (release_digest,payload_digest))
                or type(bootstrap_fd) is not int or bootstrap_fd<3):raise ValueError('Use exact source digests and the original inherited launch descriptor.')
        expected=data/'updates/observers'/('linux-'+attempt)/'Observer'
        if (observer!=expected or Path(__file__).resolve().parents[2]!=observer
                or _executable(os.getpid()).resolve()!=(observer/'python/bin/python3').resolve()):
            raise ValueError('The actual updater executable and code must belong to the retained observer.')
        with ExitStack() as held:
            held.callback(os.close,bootstrap_fd)
            fresh=descriptor(transactions/'bootstrap.lock',writable=True)
            try:
                a,b=os.fstat(bootstrap_fd),os.fstat(fresh)
                if (a.st_dev,a.st_ino)!=(b.st_dev,b.st_ino):raise ValueError('The inherited bootstrap admission belongs to another file.')
            finally:os.close(fresh)
            locks.flock(bootstrap_fd,locks.LOCK_EX|locks.LOCK_NB)
            fd=descriptor(transactions/'observer.lock',writable=True,create=True)
            held.callback(os.close,fd);locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)
            release=_read(observer/'release.json',65536)
            if hashlib.sha256(release).hexdigest()!=release_digest or snapshot(observer)['sha256']!=payload_digest:
                raise ValueError('The retained source changed across exec.')
            with ExitStack() as admission:
                admission.enter_context(Startup())
                lifetime=descriptor(runtime_directory()/'installation.lock',writable=True,create=True)
                admission.callback(os.close,lifetime);locks.flock(lifetime,locks.LOCK_SH|locks.LOCK_NB)
                current,payload=inspect_source(source)
                if current!=release or payload['sha256']!=payload_digest:raise ValueError('The selected source changed after the actual observer exec.')
                authority=held.enter_context(AutomaticInstallAuthority(source,updates,os_version=UpdateManager.os_version(None),
                    distribution=UpdateManager.distribution(None)))
                candidate=authority.selected
                stages=require_directory(private_directory(data/'updates/stages'))
                stage=stages/('linux-'+attempt);stage.mkdir(mode=0o700)
                target,_,_=stage_download(authority.files[0],stage,candidate,data)
            plan=held.enter_context(ManagedPlan(data,source,target))
            coordinator=LinuxCoordinator(plan,runtime_directory(),shared_state_directory(),transactions)
            result=coordinator.run(authority.check)
            from .linux_reopen import reopen_dsh_observed
            reopen_dsh_observed(coordinator.backend,result)
            # Captured desktop/background ownership still requires its own
            # reopening; manager eligibility remains gated until qualification.
            return write_result(transactions,attempt,'target-healthy',candidate=candidate,
                transaction=result['transactionId'],reopened=False)
    except Exception as error:
        if coordinator is not None and coordinator.completion is not None:
            return write_result(transactions,attempt,'target-healthy',candidate=candidate,
                transaction=coordinator.completion['transactionId'],error='The update is installed. Reopen Augmentor normally. '+str(error))
        pending=transactions/'active.json';cancelled=getattr(error,'augmentor_preparation_cancelled',None)
        outcome='deferred' if cancelled or coordinator is None and not pending.exists() and not pending.is_symlink() else 'failed'
        write_result(transactions,attempt,outcome,candidate=candidate,error=error)
        raise
