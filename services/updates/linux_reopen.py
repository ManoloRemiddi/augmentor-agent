# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Restart the original owned DSH service after verified managed completion.

Only this live observer can start the fixed migrated unit once. A completed
archive or saved PID alone cannot reconstruct reopening authority.
"""
from contextlib import ExitStack,contextmanager
import os
import subprocess
import sys
import time

from lifecycle.macos_payload import snapshot
from lifecycle.posix_components import discover_sockets,window_executable
from lifecycle.posix_startup import Startup
from lifecycle.update_journal import validate
from platform_adapters import locks
from platform_adapters.private_files import descriptor,read_json
from .linux_managed import ManagedBackend
from .linux_services import UNIT
from .posix_reopen import validate_plan


@contextmanager
def completed_selection(backend,completion):
    if sys.platform!='linux':raise RuntimeError('Owned Linux reopening requires Linux.')
    if (not isinstance(backend,ManagedBackend) or not backend.closed or not backend.plan.applied
            or backend.plan.closed or backend.plan.fd is None or not backend.record_sha256
            or backend.journal.fd is not None or backend.journal.uncertain
            or not isinstance(completion,dict) or completion.get('installationComplete') is not True
            or completion.get('transactionId')!=backend.journal.record['id']
            or completion.get('payloadSHA256')!=backend.plan.target_payload['sha256']):
        raise ValueError('Retain the original healthy managed update for one-shot reopening.')
    plan=backend.plan
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
            if plan.registration is not None:plan.registration.verify_applied()
        immutable();yield immutable


def reopen_dsh_observed(backend,completion):
    if getattr(backend,'service_reopening_started',False):
        raise ValueError('Retain the original healthy managed update for one-shot reopening.')
    with completed_selection(backend,completion) as immutable:
        plan=backend.plan;service=plan.services
        if service is None:return False
        if (not service.bound or not service.drained or not service.reloaded
                or service.registration is not plan.registration):
            raise ValueError('The original owned DSH service was not migrated and reloaded.')
        service.verify_applied()
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
                    immutable();backend.service_reopened=True;return True
            finally:
                for peer in peers:peer.close()
            if time.monotonic()>=deadline:raise TimeoutError('The restarted target did not register its original live control peer.')
            time.sleep(.1)


def reopen_desktop_observed(backend,captured,completion):
    captured=validate_plan(captured)
    if (captured!=getattr(backend,'reopen_plan',None)
            or getattr(backend,'desktop_reopening_started',False)):
        raise ValueError('Use the original captured desktop graph for one-shot reopening.')
    with completed_selection(backend,completion) as immutable:
        plan=backend.plan;desktop=plan.desktop
        if (desktop is None or not desktop.bound or not desktop.drained
                or desktop.registration is not plan.registration
                or tuple(captured['instances'])!=desktop.instances
                or desktop.was_running!=('main' in captured['instances'])):
            raise ValueError('Retain the original migrated desktop owner and captured instances.')
        if plan.services is not None and not getattr(backend,'service_reopened',False):
            raise ValueError('Observe target DSH reopening before reopening the desktop.')
        desktop.verify_applied()
        from .posix_dictation_reopen import reopen
        dictation_reopened=reopen(backend,captured,plan.target,backend.gate.path.parent,immutable)
        if not captured['instances']:return dictation_reopened
        # Normal launch commands only; no command, environment or PID is loaded
        # from an archive. The stable launcher has migrated with exact backups.
        environment={key:value for key,value in os.environ.items()
            if not key.startswith(('PYTHON','NODE_')) and key!='AUGMENTOR_UNIX_STARTUP_FD'}
        processes={}
        backend.desktop_reopening_started=True
        for name in sorted(captured['instances'],key=lambda name:name!='main'):
            immutable()
            if name=='main':
                subprocess.run(['/usr/bin/systemctl','--user','start','augmentor-desktop.service'],
                    stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=20)
            else:
                processes[name]=subprocess.Popen(['/usr/bin/python3','-I','-B',str(desktop.launcher),
                    '--ensure-running','--instance',name],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,env=environment,close_fds=True,start_new_session=True)
        deadline=time.monotonic()+60
        while True:
            peers=discover_sockets(backend.gate.path.parent,
                r'augmentor-linux-pi(?:-[a-z][a-z0-9-]{0,31})?\.sock',plan.target,window_executable(plan.target),kind='window')
            try:
                observed={}
                for peer in peers:
                    name=peer.endpoint.stem
                    name='main' if name=='augmentor-linux-pi' else name[len('augmentor-linux-pi-'):]
                    if name in observed or name not in captured['instances']:
                        raise ValueError('The target window graph differs from the original captured instances.')
                    if name=='main':
                        state=desktop.query();desktop.verify_state(state,running=True)
                        pid=int(state['MainPID'])
                    else:
                        child=processes[name]
                        if child.poll() is not None:raise ValueError('A reopened target window exited unexpectedly.')
                        pid=child.pid
                    if peer.process.pid!=pid or peer.process.exited():
                        raise ValueError('The reopened window differs from its actual target owner.')
                    status=peer.exchange('maintenance.status')
                    if status.get('sessionRestoreError'):raise ValueError('A reopened window could not restore its saved conversation.')
                    observed[name]=status.get('online') is True and status.get('repairing') is False
                immutable()
                if set(observed)==set(captured['instances']) and all(observed.values()):
                    # Recheck kernel observations after immutable-tree inspection.
                    if any(peer.process.exited() for peer in peers):raise ValueError('A target window exited during reopening verification.')
                    if 'main' in observed:
                        current=desktop.query();desktop.verify_state(current,running=True)
                        main=next(peer for peer in peers if peer.endpoint.name=='augmentor-linux-pi.sock')
                        if main.process.pid!=int(current['MainPID']):raise ValueError('The target desktop owner changed during verification.')
                    backend.desktop_reopened=True;return True
            finally:
                for peer in peers:peer.close()
            if time.monotonic()>=deadline:raise TimeoutError('Captured target windows did not reconnect and restore their saved state.')
            time.sleep(.1)
