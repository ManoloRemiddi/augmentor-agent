#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Authenticated same-build apply for a disposable exact-template installation.

No app components run in this inert fixture. Full graph drain and product UI have
their own proof. The caller retains the actual Setup process before this live
coordinator exits; saved PIDs never authorize production execution.
"""
import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--release',type=Path,required=True)
    parser.add_argument('--observation',type=Path,required=True)
    args=parser.parse_args()
    if sys.platform!='win32':parser.error('Requires native Windows qualification.')
    from lifecycle.installed_source import open_installed_source
    from lifecycle.update_journal import UpdateJournal
    from lifecycle.windows_apply import WindowsApply
    from lifecycle.windows_startup import Startup
    from platform_adapters.windows_identity import private_directory,private_lock_descriptor
    from platform_adapters.private_files import atomic_json
    from platform_adapters import locks
    data=args.data.resolve();observation=private_directory(args.observation.resolve())
    metadata=args.release.read_bytes();release=json.loads(metadata)
    assert release.get('customerDistribution') is False and release.get('qualificationStatus')=='development-candidate'
    with ExitStack() as held:
        lifetime=private_lock_descriptor(data/'run/installation.lock');held.callback(os.close,lifetime)
        locks.flock(lifetime,locks.LOCK_SH|locks.LOCK_NB)
        gate=held.enter_context(Startup(data/'run',maintenance=True))
        source=held.enter_context(open_installed_source(data/'recovery',metadata,target=release['target']))
        journal=held.enter_context(UpdateJournal(data/'updates',source.identity,source.identity))
        for phase in ('preparing','prepared','drained'):journal.advance(phase)
        backend=held.enter_context(WindowsApply(gate,source.installer,source.identity['sha256'],
            observation/'setup.log',qualification_outer_job=True))
        backend.wait_ready();journal.advance('installer-ready');journal.advance('apply-intent')
        backend.authorize();journal.advance('apply-acknowledged')
        atomic_json(observation/'ready.json',{'setupPid':backend.handoff.pid,'coordinatorPid':os.getpid()})
        deadline=time.monotonic()+20
        while not (observation/'observed').exists():
            if time.monotonic()>=deadline:raise TimeoutError('The fixture did not observe actual Setup.')
            time.sleep(.02)
    # Setup requires this actual process exit before acquiring final admission.


if __name__=='__main__':main()
