#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Native launch-fence fixture only; no publisher authority, drain or installer.

Two inert processes exercise the production private-pipe/kernel exit fence. The
test's release file merely delays a disposable launcher's exit; the updater's
decision still uses its retained kernel process, never that file or a saved PID.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))


def parent(args):
    from lifecycle.windows_update_observer import CoordinatorObserver
    from platform_adapters.private_files import atomic_json
    with CoordinatorObserver(args.observer_endpoint,args.observer_parent,args.observer_nonce,
                             allow_transfer=False) as peer:
        try:peer.transfer(None)
        except ValueError:pass
        else:raise AssertionError('A read-only launch fence permitted capability transfer.')
        try:
            peer.wait_bootstrap(timeout=10)
            result={'sourceExitedSuccessfully':True}
        except (ValueError,TimeoutError,ConnectionError) as error:
            result={'sourceExitedSuccessfully':False,'error':str(error)}
        atomic_json(args.output/'parent-result.json',result)


def launcher(args):
    from lifecycle.windows_installer_process import InstallerProcess
    from lifecycle.windows_update_observer import ObservationServer
    from platform_adapters.private_files import atomic_json
    digest=hashlib.sha256(args.python.read_bytes()).hexdigest()
    with ObservationServer(args.output,digest,args.python.stat().st_size) as observer:
        with InstallerProcess(args.python,digest,['-I','-Xutf8','-B',str(Path(__file__).resolve()),
                '--role','parent','--output',str(args.output),*observer.arguments()],
                qualification_outer_job=True,allow_child_breakaway=True) as child:
            observer.bind(child);observer.release_bootstrap()
            atomic_json(args.output/'bound.json',{'actualPrimaryAuthenticated':True})
            deadline=time.monotonic()+10
            while not (args.output/'allow-fixture-exit').exists():
                if time.monotonic()>=deadline:raise TimeoutError('The fixture controller did not release its inert launcher.')
                time.sleep(.02)
    return args.exit_code


def prove(runtime, output):
    """Use the exact private Python/pywin32 already qualified by our template."""
    from platform_adapters.paths import private_directory
    from platform_adapters.private_files import read_json
    results=[]
    for code in (0,7):
        attempt=private_directory(Path(output)/('exit-'+str(code)))
        with (attempt/'launcher.log').open('wb') as log:
            child=subprocess.Popen([str(Path(runtime)/'python/python.exe'),'-I','-Xutf8','-B',
                str(Path(__file__).resolve()),'--role','launcher','--output',str(attempt),
                '--python',str(Path(runtime)/'python/python.exe'),'--exit-code',str(code)],
                stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
            deadline=time.monotonic()+20
            while not (attempt/'bound.json').exists():
                if child.poll() is not None or time.monotonic()>=deadline:
                    raise AssertionError('The disposable launch fence did not bind; see its private fixture log.')
                time.sleep(.02)
            assert read_json(attempt/'bound.json')=={'actualPrimaryAuthenticated':True}
            # Confirm the external process has no permission to proceed while
            # the actual, deliberately delayed source launcher is still alive.
            time.sleep(.15)
            assert child.poll() is None and not (attempt/'parent-result.json').exists()
            (attempt/'allow-fixture-exit').write_bytes(b'Release only this inert fixture launcher.\n')
            assert child.wait(timeout=15)==code
            deadline=time.monotonic()+15
            while not (attempt/'parent-result.json').exists():
                if time.monotonic()>=deadline:raise AssertionError('The inert parent did not observe actual launcher exit.')
                time.sleep(.02)
        result=read_json(attempt/'parent-result.json')
        assert result['sourceExitedSuccessfully']==(code==0),result
        results.append(result)
    return {'scope':'Native launch fence only; no installation authorization.','results':results}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role',choices=('launcher','parent'),required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--python',type=Path)
    parser.add_argument('--exit-code',type=int,choices=(0,7),default=0)
    parser.add_argument('--observer-endpoint',type=Path)
    parser.add_argument('--observer-parent',type=int)
    parser.add_argument('--observer-nonce')
    args=parser.parse_args()
    if sys.platform!='win32':parser.error('Requires Windows; disposable fixture only.')
    if args.role=='parent':parent(args);return 0
    return launcher(args)


if __name__=='__main__':raise SystemExit(main())
