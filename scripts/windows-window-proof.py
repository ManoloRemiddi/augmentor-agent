#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual Windows-QPA preview processes: two windows, one owner each, shared UI."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'services'), str(ROOT/'apps/native')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--portable-control-check', action='store_true', help='Check the common command flow on a development host; not Windows evidence.')
    args = parser.parse_args()
    if sys.platform != 'win32' and not args.portable_control_check: parser.error('Requires Windows.')
    from platform_adapters.paths import private_directory
    from platform_adapters.transport import LocalSocket
    from augmentor_linux.instances import ipc_basename
    work = private_directory(Path(tempfile.mkdtemp(prefix='augmentor-windows-ui-')).resolve()/'private')
    args.out.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'QT_QPA_PLATFORM': 'windows' if sys.platform == 'win32' else os.environ.get('QT_QPA_PLATFORM', 'offscreen'), 'QSG_RHI_PREFER_SOFTWARE_RENDERER': '1',
           'PYTHONPATH': str(ROOT/'apps/native'), 'XDG_RUNTIME_DIR': str(private_directory(work/'run')),
           'XDG_CONFIG_HOME': str(private_directory(work/'config')),
           'XDG_DATA_HOME': str(private_directory(work/'data')),
           'XDG_STATE_HOME': str(private_directory(work/'state'))}
    children = []
    options = {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}
    report = {'passed': False, 'platform': sys.platform, 'scope': 'Two Qt preview processes and shared controls; no model, installed launcher or physical-keyboard proof.'}
    def command(name, value):
        with LocalSocket() as peer:
            peer.settimeout(3); peer.connect(str(Path(env['XDG_RUNTIME_DIR'])/(ipc_basename(name)+'.sock')))
            peer.sendall(value.encode()+(b'\n' if sys.platform == 'win32' else b''))
            with peer.makefile('rb') as stream: raw = stream.readline(262145)
        if len(raw)>262144 or not raw.endswith(b'\n'): raise ValueError('Invalid instance response.')
        return json.loads(raw)
    def inspect(name):
        result = command(name, 'ui-test:{"action":"inspect"}')
        if not result.get('ok'): raise RuntimeError('Instance inspection failed: '+str(result.get('error')))
        return result['result']
    def wait_for(check):
        until = time.monotonic()+20
        error = None
        while time.monotonic()<until:
            try:
                value = check()
                if value: return value
            except (OSError, ValueError, KeyError) as caught: error = caught
            if any(child.poll() is not None for child in children):
                raise AssertionError('A preview process exited before readiness: '+str([child.poll() for child in children]))
            time.sleep(.1)
        raise AssertionError('The preview did not answer its instance command: '+repr(error))
    def arguments(name):
        # A failed fixture retains thread stacks in its private log. This is
        # confined to disposable preview launches, never a normal desktop flag.
        bootstrap = "import faulthandler,runpy; faulthandler.enable(); faulthandler.dump_traceback_later(12); runpy.run_module('augmentor_linux',run_name='__main__')"
        return [sys.executable, '-Xutf8', '-B', '-c', bootstrap, '--preview', '--ui-test-control', '--instance', name]
    logs = []
    try:
        for name in ('main', 'secondary'):
            log = (work/(name+'.log')).open('w', encoding='utf-8'); logs.append(log)
            children.append(subprocess.Popen(arguments(name), env=env, stdin=subprocess.DEVNULL,
                stdout=log, stderr=log, **options))
        initial = {name: wait_for(lambda: inspect(name)) for name in ('main','secondary')}
        assert initial['main']['pid'] != initial['secondary']['pid']
        assert all(item['visible'] for item in initial.values())
        command('main','ui-test:'+json.dumps({'action':'draft','expected':'','text':'Keep this draft'}))
        state = command('main','maintenance.close')
        assert state['busy'] and not state['accepted']
        assert inspect('main')['draft'] == 'Keep this draft'
        assert inspect('secondary')['draft'] == ''
        repeated = subprocess.run(arguments('main'), env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, **options)
        assert repeated.returncode == 0, repeated.stderr.decode('utf-8', errors='replace')
        assert inspect('main')['pid'] == initial['main']['pid']
        zoomed = command('main','ui-test:'+json.dumps({'action':'zoom','percent':120}))
        assert zoomed['ok'] and zoomed['result']['uiScale'] == 120
        assert zoomed['result']['fontPixels'] > initial['main']['fontPixels']
        assert inspect('main')['draft'] == 'Keep this draft'
        screenshot = (args.out/'windows-two-window-main.png').resolve()
        command('main','ui-test:'+json.dumps({'action':'capture','path':str(screenshot)}))
        report.update(passed=True, distinctWindows=True, repeatedLaunchPreservedOwner=True,
            draftBlockedMaintenance=True, zoomPreservedDraft=True, initial=initial, zoom=zoomed['result'])
    except BaseException:
        report['childExitCodes'] = [child.poll() for child in children]
        for log in logs: log.flush()
        report['fixtureDiagnostics'] = {name:(work/(name+'.log')).read_text(encoding='utf-8',errors='replace')[-8000:]
                                      for name in ('main','secondary') if (work/(name+'.log')).exists()}
        raise
    finally:
        # Preview has no real controller, so its Close is not normal product
        # Quit. Stop only the exact disposable processes created by this probe.
        for process in children:
            if process.poll() is None: process.kill()
            process.wait(timeout=10)
        for log in logs: log.close()
        (args.out/'windows-two-window.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report),flush=True)


if __name__ == '__main__': main()
