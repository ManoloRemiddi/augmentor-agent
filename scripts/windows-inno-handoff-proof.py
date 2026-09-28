#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Disposable authenticated Inno coordinator; no customer update/recovery claim."""
import argparse
from contextlib import ExitStack
import ctypes
import json
import msvcrt
import os
from pathlib import Path
import sys
import sysconfig
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))
from lifecycle.windows_startup import Startup
from lifecycle.windows_installer_process import InstallerProcess
from lifecycle.windows_handoff import InstallerHandoff,HELLO
from lifecycle.update_journal import UpdateJournal
from platform_adapters import locks
from platform_adapters.windows_identity import private_lock_descriptor
from platform_adapters.private_files import atomic_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installer',required=True,type=Path)
    parser.add_argument('--sha256',required=True)
    parser.add_argument('--state',required=True,type=Path)
    parser.add_argument('--log',required=True,type=Path)
    parser.add_argument('--authenticated',action='store_true')
    parser.add_argument('--cancel-before-apply',action='store_true')
    parser.add_argument('--crash-before-apply',action='store_true')
    parser.add_argument('--wrong-coordinator',action='store_true')
    parser.add_argument('--journal',type=Path)
    parser.add_argument('--blocked-final-lease',action='store_true')
    args=parser.parse_args()
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    in_job=ctypes.c_int()
    query=kernel.IsProcessInJob
    query.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_int)];query.restype=ctypes.c_int
    if not query(ctypes.c_void_p(-1),None,ctypes.byref(in_job)):raise ctypes.WinError(ctypes.get_last_error())
    with ExitStack() as stack:
        # Model the installed coordinator's lifetime handle. Setup must wait
        # for this actual process to exit, not merely for its APPLY message.
        lifetime=private_lock_descriptor(args.state/'installation.lock')
        stack.callback(os.close,lifetime)
        locks.flock(lifetime,locks.LOCK_SH|locks.LOCK_NB)
        journal=None
        if args.journal:
            # The authenticated cases repair the already selected 0.0.2 fixture
            # with the same artifact. No live Augmentor components exist in
            # this fixture and no signature/publisher trust is inferred here.
            identity={'version':'0.0.2','sourceCommit':subprocess.check_output(
                ['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                'target':{'win-amd64':'windows-x64','win-arm64':'windows-arm64'}[sysconfig.get_platform()],
                'channel':'qualification','sha256':args.sha256,'dataSchema':1,'readableDataSchemas':[1]}
            journal=stack.enter_context(UpdateJournal(args.journal,identity,identity))
            for phase in ('preparing','prepared','drained'):journal.advance(phase)
        gate=stack.enter_context(Startup(args.state,maintenance=True))
        handoff=stack.enter_context(InstallerHandoff(gate)) if args.authenticated else None
        launch=handoff.arguments() if handoff else ['/startupowner='+str(os.getpid()),
            '/startuphandle='+str(msvcrt.get_osfhandle(gate.fd))]
        if args.wrong_coordinator:
            assert handoff is not None and os.getpid()!=1
            launch=[value if not value.startswith('/augmentorcoordinator=') else '/augmentorcoordinator=1' for value in launch]
        with InstallerProcess(args.installer,args.sha256,['/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',
            '/LOG='+str(args.log),*(['/finalleasetimeout=1000'] if args.blocked_final_lease else []),*launch],qualification_outer_job=True) as installer:
            if handoff:
                handoff.bind(installer)
                if args.wrong_coordinator:
                    try:handoff.wait_ready(timeout=5)
                    except TimeoutError:pass
                    else:raise AssertionError('Setup accepted the wrong coordinator PID.')
                    assert not handoff.claimed
                    assert installer.wait(30)!=0
                    return
                handoff.wait_ready(timeout=30)
                if journal:journal.advance('installer-ready')
                from platform_adapters.transport import LocalSocket
                with LocalSocket() as outsider:
                    outsider.settimeout(5);outsider.connect(str(handoff.endpoint))
                    outsider.sendall(HELLO)
                    assert outsider.recv(1)==b'','An unrelated pipe client received handoff authority.'
                assert not handoff.finished.is_set(),'An unrelated pipe client disrupted the prepared installer.'
                if args.crash_before_apply:
                    atomic_json(args.state/'prepared.json', {'pid':handoff.pid})
                    deadline=time.monotonic()+20
                    while not (args.state/'crash-now').exists():
                        if time.monotonic()>=deadline:raise TimeoutError('The fixture did not retain the prepared Setup process.')
                        time.sleep(.02)
                    os._exit(79)  # Deliberate fixture crash, before authorizing any replacement.
                if args.cancel_before_apply:
                    handoff.close()
                    assert installer.wait(30)!=0,'The cancelled installer unexpectedly succeeded.'
                    return
                if journal:journal.advance('apply-intent')
                handoff.authorize()  # Disposable fixture only; no app processes/data are being updated.
                if journal:journal.advance('apply-acknowledged')
            unrelated_refused=False
            try:installer.observe(os.getpid())
            except ValueError:unrelated_refused=True
            assert unrelated_refused,'The installer observation accepted its unrelated coordinator.'
            deadline=time.monotonic()+30
            while not (args.state/'ready.json').exists():
                if installer.poll() is not None:raise RuntimeError('The disposable installer exited before handoff.')
                if time.monotonic()>=deadline:raise TimeoutError('The disposable handoff was not observed.')
                time.sleep(.02)
            ready=json.loads((args.state/'ready.json').read_text(encoding='utf-8'))
            if handoff:assert ready['pid']==handoff.pid
            process=installer.observe(ready['pid'])
            process.Close()
            atomic_json(args.state/'coordinator.json', {'installerPid':installer.pid,
                'setupPid':ready['pid'],'actualSetupInInstallerJob':True,'unrelatedPidRefused':True,
                'coordinatorLifetimeLease':True,
                'outerRunnerJobObserved':bool(in_job.value)})
            while not (args.state/'parent-release').exists():
                if installer.poll() is not None:raise RuntimeError('The disposable installer exited before handoff.')
                if time.monotonic()>=deadline:raise TimeoutError('The disposable handoff was not observed.')
                time.sleep(.02)
    # No wait or termination: the actual independent Setup process retains the
    # duplicated writer. The test separately waits on its exact kernel handle.


if __name__=='__main__':main()
