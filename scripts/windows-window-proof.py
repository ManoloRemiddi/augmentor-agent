#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual Windows-QPA preview processes: two windows, one owner each, shared UI."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import struct
import sys
import tempfile
import time
import secrets

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'services'), str(ROOT/'apps/native')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--launcher', type=Path, help='Exercise the assembled native executable with disposable data.')
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
    children = [];participants=[]
    options = {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}
    report = {'passed': False, 'platform': sys.platform, 'scope': 'Two Qt preview processes and shared controls; no model, installed launcher or physical-keyboard proof.'}
    report['nativeLauncher'] = bool(args.launcher)
    if args.launcher:
        import win32api
        import xml.etree.ElementTree as ET
        executable = str(args.launcher.resolve())
        release = json.loads((args.launcher.resolve().parent/'release.json').read_text(encoding='utf-8'))
        version = win32api.GetFileVersionInfo(executable, '\\')
        major, minor, patch = map(int, release['version'].split('.'))
        assert version['FileVersionMS'] == major << 16 | minor
        assert version['FileVersionLS'] == patch << 16
        library = win32api.LoadLibraryEx(executable, 0, 2 | 32)
        try:
            manifest = ET.fromstring(win32api.LoadResource(library, 24, 1))
            assert manifest.find('.//{urn:schemas-microsoft-com:asm.v3}requestedExecutionLevel').get('level') == 'asInvoker'
            assert manifest.find('.//{http://schemas.microsoft.com/SMI/2016/WindowsSettings}dpiAwareness').text == 'PerMonitorV2,PerMonitor'
            icon = win32api.LoadResource(library, 14, 101)
            assert struct.unpack_from('<HHH', icon) == (0, 1, 7)
            report['embeddedResources'] = {'version': release['version'], 'iconSizes': 7, 'elevation': 'asInvoker', 'dpi': 'PerMonitorV2'}
        finally: win32api.FreeLibrary(library)
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
        if args.launcher:
            return [str(args.launcher.resolve()), '--qualification-root', str(work),
                    '--preview', '--ui-test-control', '--instance', name]
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
        report['initial'] = initial
        assert [initial[name]['pid'] for name in ('main','secondary')] == [child.pid for child in children], 'The desktop left its native launch process.'
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
        from augmentor_linux.shortcut_activation import DesktopActivation
        activation = DesktopActivation(env['XDG_RUNTIME_DIR'], arguments('main'))
        if sys.platform == 'win32': assert inspect('main')['visible'], 'Clicking the native app must show the existing window.'
        elif not inspect('main')['visible']:
            # The existing Linux launcher toggles on repeat invocation.
            activation.activate(); wait_for(lambda: inspect('main')['visible'])
        assert activation.activate() == 'delivered'
        wait_for(lambda: not inspect('main')['visible'])
        assert inspect('secondary')['visible']
        assert activation.activate() == 'delivered'
        wait_for(lambda: inspect('main')['visible'])
        zoomed = command('main','ui-test:'+json.dumps({'action':'zoom','percent':120}))
        report['zoomResponse'] = zoomed
        assert zoomed['ok'] and zoomed['result']['uiScale'] == 120, zoomed
        assert zoomed['result']['fontPixels'] > initial['main']['fontPixels']
        assert inspect('main')['draft'] == 'Keep this draft'
        screenshot = (args.out/'windows-two-window-main.png').resolve()
        command('main','ui-test:'+json.dumps({'action':'capture','path':str(screenshot)}))
        token = secrets.token_hex(24)
        if sys.platform=='win32':
            from lifecycle.windows_components import discover_windows
            selected_root=args.launcher.resolve().parent if args.launcher else ROOT
            participants=discover_windows(selected_root,Path(env['XDG_RUNTIME_DIR']))
            assert {item.pid for item in participants}=={initial[name]['pid'] for name in ('main','secondary')}
            assert next(item for item in participants if item.pid==initial['main']['pid']).initial['draftPresent']
            secondary=next(item for item in participants if item.pid==initial['secondary']['pid'])
            assert secondary.control('prepare',token)['phase']=='prepared'
            assert secondary.control('cancel',token)['phase']=='ready'
            try:discover_windows(work/'different-build',Path(env['XDG_RUNTIME_DIR']))
            except ValueError:pass
            else:raise AssertionError('Discovery adopted a window from a different application build.')
            assert inspect('main')['draft']=='Keep this draft'
            report['kernelVerifiedDiscovery']=True
        def maintenance(name,action):
            return command(name,'maintenance:'+json.dumps({'method':'host.maintenance.'+action,
                'params':{} if action=='status' else {'token':token}}))
        assert not maintenance('main','prepare')['ok'], 'An unsent draft must refuse preparation.'
        prepared = maintenance('secondary','prepare')
        assert prepared['ok'] and prepared['result']['phase']=='prepared', prepared
        refused = command('secondary','ui-test:'+json.dumps({'action':'draft','expected':'','text':'Must not enter'}))
        assert not refused['ok'] and inspect('secondary')['draft']=='', refused
        assert not command('secondary','voice')['ok']
        assert inspect('main')['draft']=='Keep this draft'
        assert maintenance('secondary','cancel')['result']['phase']=='ready'
        accepted = command('secondary','ui-test:'+json.dumps({'action':'draft','expected':'','text':'Restored input'}))
        assert accepted['ok'] and inspect('secondary')['draft']=='Restored input', accepted
        command('secondary','ui-test:'+json.dumps({'action':'draft','expected':'Restored input','text':''}))
        assert maintenance('secondary','prepare')['ok']
        assert maintenance('secondary','commit')['result']['phase']=='closing'
        assert children[1].wait(timeout=10)==0, 'The prepared preview window did not close normally.'
        if sys.platform=='win32':
            assert secondary.exited()
            try:secondary.control('status')
            except (FileNotFoundError,ValueError):pass
            else:raise AssertionError('An exited window observation accepted a later request.')
        report.update(passed=True, distinctWindows=True, repeatedLaunchPreservedOwner=True,
            draftBlockedMaintenance=True, zoomPreservedDraft=True, shortcutActivationToggle=True,
            reversibleWindowAdmission=True, preparedPreviewExitCode=0, initial=initial, zoom=zoomed['result'])
    except BaseException:
        report['childExitCodes'] = [child.poll() for child in children]
        for log in logs: log.flush()
        report['fixtureDiagnostics'] = {name:(work/(name+'.log')).read_text(encoding='utf-8',errors='replace')[-8000:]
                                      for name in ('main','secondary') if (work/(name+'.log')).exists()}
        for path in (work/'state/logs').glob('desktop.*.log'):
            report['fixtureDiagnostics'][path.name] = path.read_text(encoding='utf-8', errors='replace')[-8000:]
        raise
    finally:
        for participant in participants:participant.close()
        # The remaining preview retains its deliberate draft. Fault cleanup
        # stops only the exact disposable processes created by this probe.
        for process in children:
            if process.poll() is None: process.kill()
            process.wait(timeout=10)
        for log in logs: log.close()
        (args.out/'windows-two-window.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report),flush=True)


if __name__ == '__main__': main()
