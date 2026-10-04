#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual private Windows broker, bundled browser, shortcuts and microphone leases.

No physical microphone, transcription model download or personal profile is used.
The runtime is copied unchanged before creating a disposable portable profile.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if sys.platform!='win32':parser.error('Native Windows proof required.')
    project=args.project.resolve()
    sys.path[:0]=[str(project/'services'),str(project/'apps/native')]
    from platform_adapters.windows_identity import private_directory
    with tempfile.TemporaryDirectory(prefix='augmentor-dictation-windows-') as temporary:
        base=private_directory(Path(temporary)/'private');fixture=base/'project'
        # Copy the complete public staged service graph: lifecycle IPC also
        # needs root helpers such as platform_support.py. No user state is copied.
        for name in ('services','components/handy/runtime'):
            shutil.copytree(project/name,fixture/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        target=fixture/'apps/native/augmentor_linux/dictation.py';target.parent.mkdir(parents=True)
        shutil.copy2(project/'apps/native/augmentor_linux/dictation.py',target)
        (fixture/'components/handy/runtime/bin/portable').write_text('Private proof profile\n')
        shutil.copy2(project/'release.json',fixture/'release.json')
        assert json.loads((fixture/'release.json').read_text())['target'].startswith('windows-')
        runtime=private_directory(base/'run')
        state=private_directory(base/'state')
        environment={**os.environ,'AUGMENTOR_DICTATION_STATE':str(state),
                     'PYTHONPATH':str(fixture/'apps/native'),'QT_QPA_PLATFORM':'offscreen',
                     'XDG_RUNTIME_DIR':str(runtime),
                     # A stale inherited supplier path must not override the
                     # component's exact bundled browser selection.
                     'WEBVIEW2_BROWSER_EXECUTABLE_FOLDER':str(base/'missing-global-browser')}
        driver=fixture/'broker-driver.py'
        shutil.copy2(Path(__file__).resolve().parents[1]/'tests/fixtures/handy-broker-driver.py',driver)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        diagnostic_path=args.out.with_name('dictation-startup.log')
        with diagnostic_path.open('wb') as diagnostic:
            child=subprocess.Popen([sys.executable,'-Xutf8','-B',str(driver),str(fixture/'services/dictation/server.py')],
                env=environment,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=diagnostic,
                creationflags=subprocess.CREATE_NO_WINDOW)
        os.environ['AUGMENTOR_DICTATION_STATE']=str(state)
        from augmentor_linux.dictation import request
        try:
            deadline=time.monotonic()+20
            while True:
                if child.poll() is not None:raise RuntimeError('The private broker exited; inspect dictation-startup.log.')
                try:initial=request('status',start=False,timeout=5);break
                except RuntimeError:
                    if time.monotonic()>=deadline:raise
                    time.sleep(.1)
            assert not initial['enabled'] and initial['installed']
            palette={'background':'#162027','foreground':'#edf3f3','accent':'#dbaf99',
                     'border':'#dbaf99','opacity':1,'animated':True,'mode':'dark'}
            request('theme',palette,start=False)
            started=time.monotonic()
            request('enable',{'enabled':True},start=False,timeout=75)
            startup_seconds=round(time.monotonic()-started,3)
            enabled=request('status',start=False)
            assert enabled['enabled'] and enabled['phase']=='setup-needed' and enabled['tray'] is False
            from platform_adapters.windows_identity import private_lock_descriptor
            from platform_adapters import locks
            descriptor=private_lock_descriptor(runtime/'installation.lock')
            try:
                try:locks.flock(descriptor,locks.LOCK_EX|locks.LOCK_NB)
                except BlockingIOError:pass
                else:raise AssertionError('Enabled Handy failed to hold its installation lease.')
            finally:os.close(descriptor)
            assert enabled['theme']==palette and enabled['settings']['shortcut']=='ctrl+space'
            request('settings',{'revision':enabled['revision'],'values':{'shortcut':'ctrl+shift+space'}},start=False)
            assert request('status',start=False)['settings']['shortcut']=='ctrl+shift+space'
            token='a'*32
            request('conversation.acquire',{'token':token,'pid':os.getpid()},start=False)
            try:request('shutdown',start=False)
            except RuntimeError as error:assert 'Nothing was cancelled' in str(error)
            else:raise AssertionError('Maintenance cancelled an active microphone owner.')
            request('conversation.release',{'token':token},start=False)
            request('enable',{'enabled':False},start=False)
            assert request('status',start=False)['phase']=='disabled'
            descriptor=private_lock_descriptor(runtime/'installation.lock')
            try:locks.flock(descriptor,locks.LOCK_EX|locks.LOCK_NB)
            finally:os.close(descriptor)
            request('shutdown',start=False);assert child.wait(timeout=10)==0
            report={'passed':True,'nativeWindows':True,'bundledBrowser':True,'globalBrowserRequired':False,
                    'defaultCtrlSpace':True,'customShortcut':True,'theme':True,'microphoneExclusion':True,
                    'disable':True,'enabledInstallationLease':True,'disabledInstallationLeaseReleased':True,'brokerShutdown':True,'tray':False,'physicalMicrophoneUsed':False,
                    'modelDownloaded':False,'startupSeconds':startup_seconds,
                    'scope':'Copied packaged bytes; setup, IPC and lifecycle. Physical transcription remains separate.'}
            args.out.parent.mkdir(parents=True,exist_ok=True)
            args.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            print(json.dumps(report))
        finally:
            if child.poll() is None:
                try:request('shutdown',start=False)
                except Exception:pass
                try:child.wait(timeout=10)
                except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
            # The copied Microsoft browser can retain mapped metrics briefly.
            deadline=time.monotonic()+30
            while True:
                try:shutil.rmtree(fixture);break
                except OSError:
                    if time.monotonic()>=deadline:raise
                    time.sleep(.1)


if __name__=='__main__':main()
