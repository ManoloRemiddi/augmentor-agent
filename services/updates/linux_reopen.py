# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Restart the original owned DSH service after verified managed completion.

Only this live observer can start the fixed migrated unit once. A completed
archive or saved PID alone cannot reconstruct reopening authority.
"""
from contextlib import ExitStack
import os
import subprocess
import sys
import time

from lifecycle.macos_payload import snapshot
from lifecycle.posix_components import discover_sockets
from lifecycle.posix_startup import Startup
from lifecycle.update_journal import validate
from platform_adapters import locks
from platform_adapters.private_files import descriptor,read_json
from .linux_managed import ManagedBackend
from .linux_services import UNIT


def reopen_dsh_observed(backend,completion):
    if sys.platform!='linux':raise RuntimeError('Owned Linux reopening requires Linux.')
    if (not isinstance(backend,ManagedBackend) or not backend.closed or not backend.plan.applied
            or backend.plan.closed or backend.plan.fd is None or not backend.record_sha256
            or backend.journal.fd is not None or backend.journal.uncertain
            or not isinstance(completion,dict) or completion.get('installationComplete') is not True
            or completion.get('transactionId')!=backend.journal.record['id']
            or completion.get('payloadSHA256')!=backend.plan.target_payload['sha256']
            or getattr(backend,'service_reopening_started',False)):
        raise ValueError('Retain the original healthy managed update for one-shot reopening.')
    plan=backend.plan;service=plan.services
    if service is None:return False
    if (not service.bound or not service.drained or not service.reloaded
            or service.registration is not plan.registration):
        raise ValueError('The original owned DSH service was not migrated and reloaded.')
    archive=backend.journal.directory/('completed-'+completion['transactionId']+'.json')
    if completion.get('archive')!=str(archive):raise ValueError('Completion names another original archive.')
    with ExitStack() as held:
        held.enter_context(Startup(backend.gate.path.parent,transactions=backend.journal.directory))
        fd=descriptor(backend.gate.path.parent/'installation.lock',writable=True,create=True)
        held.callback(os.close,fd);locks.flock(fd,locks.LOCK_SH|locks.LOCK_NB)
        record=validate(read_json(archive));original=backend.journal.record
        if (record['phase']!='complete' or record['revision']!=original['revision']+3
                or any(record[key]!=original[key] for key in ('schema','id','source','target','steps'))):
            raise ValueError('The exact observed update was not completed.')
        def immutable():
            if (read_json(plan.data/'desktop.json')!=plan.proposed
                    or read_json(plan.data/'desktop.previous.json')!=plan.previous
                    or snapshot(plan.source)!=plan.source_payload or snapshot(plan.target)!=plan.target_payload
                    or plan.tool.verify(plan.source)!=plan.source_manifest or plan.tool.verify(plan.target)!=plan.target_manifest):
                raise ValueError('The completed managed selection or retained artifacts changed.')
            plan.registration.verify_applied()
        immutable();service.verify_applied()
        backend.service_reopening_started=True  # No retry after a start outcome becomes uncertain.
        subprocess.run(['/usr/bin/systemctl','--user','start',UNIT],stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=20)
        deadline=time.monotonic()+30
        while True:
            state=service.query();service.verify_state(state,running=True)
            peers=discover_sockets(backend.gate.path.parent,r'augmentor-dsh-[1-9][0-9]{0,19}\.sock',
                plan.target,plan.proposed['node'],kind='dsh')
            try:
                if peers:
                    if len(peers)!=1 or peers[0].process.pid!=int(state['MainPID']) or peers[0].process.exited():
                        raise ValueError('The restarted service differs from the actual target socket peer.')
                    immutable()
                    plan.tool.check(plan.proposed,connected=True)
                    current=service.query();service.verify_state(current,running=True)
                    if current['MainPID']!=state['MainPID'] or peers[0].process.exited():
                        raise ValueError('The restarted target exited or changed during live health.')
                    immutable();return True
            finally:
                for peer in peers:peer.close()
            if time.monotonic()>=deadline:raise TimeoutError('The restarted target did not register its original live control peer.')
            time.sleep(.1)
