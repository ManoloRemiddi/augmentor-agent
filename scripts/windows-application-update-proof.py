#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Disposable installed coordinator: observed graph drain and actual Inno apply.

This is a same-build integration proof, not a trusted update entrypoint. It
accepts only development-candidate qualification state and known fixture bytes.
"""
import argparse
from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import sys
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--installer',type=Path,required=True)
    parser.add_argument('--sha256',required=True)
    args=parser.parse_args()
    if sys.platform!='win32':parser.error('Requires the native Windows kernel.')
    root=args.root.resolve();data=args.data.resolve()
    sys.path[:0]=[str(root/'services'),str(root/'apps/native')]
    spec=importlib.util.spec_from_file_location('installed_launcher',root/'scripts/launch-windows.py')
    launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
    release=launcher.preflight(root)
    environment=launcher.configure_qualification(data,release)
    launcher.load_launcher().configure(windows_paths=environment)
    from platform_adapters.windows_identity import private_lock_descriptor
    from platform_adapters.paths import private_directory
    from platform_adapters.private_files import atomic_json
    from platform_adapters import locks
    from lifecycle.update import authorize_update
    from lifecycle.update_journal import UpdateJournal
    from lifecycle.windows_apply import WindowsApply
    from lifecycle.windows_preparation import WindowsPreparation
    import windows_supervisor as owner
    transaction=private_directory(data/'update-proof')
    identity={'version':release['version'],'sourceCommit':release['sourceCommit'],
        'target':release['target'],'channel':'qualification','sha256':args.sha256,
        'dataSchema':1,'readableDataSchemas':[1]}
    with ExitStack() as stack:
        lifetime=private_lock_descriptor(data/'run/installation.lock')
        stack.callback(os.close,lifetime)
        locks.flock(lifetime,locks.LOCK_SH|locks.LOCK_NB)
        journal=stack.enter_context(UpdateJournal(transaction,identity,identity))
        backends=[]
        def backend(gate):
            selected=WindowsApply(gate,args.installer,args.sha256,transaction/'setup.log',qualification_outer_job=True)
            backends.append(selected)
            return selected
        result=authorize_update(journal,
            lambda:WindowsPreparation(root,data/'run',data/'run/shared',owner.managed_directory()),
            backend)
        result['setupPid']=backends[0].handoff.pid
        atomic_json(transaction/'coordinator-result.json',result)
        deadline=time.monotonic()+20
        while not (transaction/'observer-ready').exists():
            if time.monotonic()>=deadline:raise TimeoutError('Fixture did not retain the live Setup process.')
            time.sleep(.02)
    # Return normally. Extracted Setup waits on this actual process before
    # exclusive installation access; no private-runtime code runs after apply.


if __name__=='__main__':main()
