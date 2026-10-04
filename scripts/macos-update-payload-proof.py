#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Retain/inspect a whole development bundle outside its original path.

Only disposable retained-copy replacement; no user installation, app launch,
login registration, model or user data is involved.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import plistlib
import importlib.util

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from lifecycle.macos_payload import verify_bundle
from lifecycle.macos_apply import MacInstallerBackend
from lifecycle.macos_health import verify_local_health
from lifecycle.posix_startup import Startup
from lifecycle.update_journal import UpdateJournal
from platform_adapters import locks
from platform_adapters.paths import private_directory
from platform_adapters.private_files import atomic_json,require_directory,descriptor
from updates.macos_completion import complete_observed
from updates.macos_coordinator import MacCoordinator
from updates.macos_reopen import reopen_observed
from updates.macos_staging import validate_zip


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--artifact',type=Path,required=True)
    args=parser.parse_args()
    if sys.platform!='darwin':parser.error('This proof requires native macOS signatures.')
    if args.app.is_symlink():raise ValueError('Use the original ordinary bundle directory.')
    original=args.app.resolve(strict=True)
    if args.out.is_symlink() or args.out.exists() and any(args.out.iterdir()):raise ValueError('Use a new empty evidence directory.')
    out=require_directory(private_directory(args.out.resolve()))
    with args.artifact.open('rb') as stream:zip_report=validate_zip(stream,'Augmentor Agent Desktop.app')
    release=(original/'Contents/Resources/app/release.json').read_bytes()
    source=verify_bundle(original,release,development=True)
    retained=out/'Retained source.app'
    subprocess.run(['/usr/bin/ditto',str(original),str(retained)],check=True,timeout=180)
    copy=verify_bundle(retained,release,development=True)
    if source!=copy:raise ValueError('The retained whole bundle differs from the original.')
    info=plistlib.loads((retained/'Contents/Info.plist').read_bytes())
    executable=retained/'Contents/MacOS'/info['CFBundleExecutable']
    before=executable.read_bytes()
    if not before:raise ValueError('The retained native executable is empty.')
    try:
        executable.write_bytes(bytes([before[0]^255])+before[1:])
        try:verify_bundle(retained,release,development=True)
        except subprocess.CalledProcessError:pass
        else:raise AssertionError('Mac signature inspection accepted a damaged native executable.')
    finally:executable.write_bytes(before)
    if verify_bundle(original,release,development=True)!=source or verify_bundle(retained,release,development=True)!=copy:
        raise ValueError('The original or restored development bundle changed.')
    candidate=out/'Candidate.app'
    subprocess.run(['/usr/bin/ditto',str(original),str(candidate)],check=True,timeout=180)
    target=verify_bundle(candidate,release,development=True)
    sentinel=out/'retained-user-fixture.txt';sentinel.write_bytes(b'Preserve fixture settings and history.')
    # Short private runtime, independent of any graphical/login registration.
    with tempfile.TemporaryDirectory(prefix='ag-mac-update-',dir='/tmp') as temporary:
        runtime=require_directory(Path(temporary))
        with Startup(runtime,maintenance=True) as gate:
            holder=descriptor(runtime/'installation.lock',writable=True,create=True)
            try:
                locks.flock(holder,locks.LOCK_SH|locks.LOCK_NB)
                with MacInstallerBackend(gate,retained,candidate,release,release,copy,target,development=True) as backend:
                    try:backend.wait_ready()
                    except BlockingIOError:pass
                    else:raise AssertionError('A live installation reader did not block Mac apply readiness.')
            finally:os.close(holder)
        metadata=json.loads(release)
        identity={key:metadata[key] for key in ('version','sourceCommit','target','channel','dataSchema','readableDataSchemas')}
        identity['sha256']=source['sha256']  # Whole retained-bundle fixture identity; never published.
        transaction=require_directory(private_directory(out/'transaction'))
        coordinator=MacCoordinator(retained,candidate,runtime,runtime/'shared',transaction,
            release,release,copy,target,identity,identity,development=True)
        with UpdateJournal(transaction,identity,identity) as journal:
            result=coordinator.prepare_and_apply(journal,lambda _stage:True)
            if journal.record['phase']!='apply-acknowledged' or result['installationComplete'] is not False:
                raise AssertionError('The fixture confused apply with completed installation.')
        backend=coordinator.backend;backup=backend.backup
        if not backup or verify_bundle(backup,release,development=True)!=copy or verify_bundle(retained,release,development=True)!=target:
            raise ValueError('Atomic replacement did not retain the source and exact target.')
        if verify_bundle(original,release,development=True)!=source or sentinel.read_bytes()!=b'Preserve fixture settings and history.':
            raise ValueError('The original bundle or synthetic user state changed.')
        # The retained target is a disposable copy. Its fixed probe uses a new
        # private profile and renders the shared UI without services/providers.
        health=verify_local_health(retained,release,target,development=True)
        if health['rendered'] is not True or health['payloadSHA256']!=target['sha256']:
            raise ValueError('The fixed target health probe did not identify this bundle.')
        try:
            with Startup(runtime,transactions=transaction):pass
        except RuntimeError:pass
        else:raise AssertionError('The pending durable record did not refuse a normal restart.')
        changed={**identity,'sourceCommit':'0'*40}
        try:complete_observed(backend,identity,changed)
        except ValueError:pass
        else:raise AssertionError('Completion adopted a different target identity.')
        if not (transaction/'active.json').is_file():raise AssertionError('Rejected completion removed the pending record.')
        completion=coordinator.complete()
        if not completion['installationComplete'] or (transaction/'active.json').exists():
            raise AssertionError('Verified completion failed to archive the exact attempt.')
        with Startup(runtime,transactions=transaction):pass
        try:coordinator.complete()
        except (ValueError,FileNotFoundError):pass
        else:raise AssertionError('The completed attempt was replayed.')
        if coordinator.plan!={'instances':[],'hadBrowser':False}:
            raise AssertionError('The empty live graph acquired an unobserved reopening target.')
        if reopen_observed(backend,coordinator.plan,completion) is not False:
            raise AssertionError('An empty reopening plan launched a normal application.')
        try:reopen_observed(backend,{'instances':['unobserved'],'hadBrowser':False},completion)
        except ValueError:pass
        else:raise AssertionError('The live coordinator adopted an unobserved instance name.')
    spec=importlib.util.spec_from_file_location('macos_observer_fixture',ROOT/'scripts/macos-observer-handoff-proof.py')
    handoff=importlib.util.module_from_spec(spec);spec.loader.exec_module(handoff)
    handoff_report=handoff.proof(original,retained,out/'isolated-handoff-home')
    report={'passed':True,'schema':'augmentor-macos-source-proof/1','payloadSHA256':source['sha256'],
        'releaseSHA256':source['releaseSHA256'],'entries':len(source['entries']),'bytes':source['bytes'],
        'relocatedWholeBundle':True,'nativeSignatureDamageRefused':True,'originalPreserved':True,
        'installationReaderRefusesReady':True,'atomicSameBuildFixtureApply':True,'sourceBackupRetained':True,
        'pendingLaunchRefused':True,'wrongCompletionRetainsPending':True,'completionArchived':True,
        'completionNotReplayed':True,'syntheticUserStatePreserved':True,
        'coordinatorCapturesEmptyPlan':True,'unobservedReopenRefused':True,
        'packagedZIPBoundary':zip_report,
        'nativeObserverHandoff':handoff_report,
        'offlineTargetHealth':health,
        'scope':'Development whole-bundle retention, same-build isolated apply, durable launch barrier and verified completion; no signed forward update, reopen, login/user install or automatic publisher authority.'}
    atomic_json(out/'report.json',report)
    print(json.dumps(report))


if __name__=='__main__':main()
