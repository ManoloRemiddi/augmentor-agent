#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Execute the exact application Inno script with a small fixture payload.

The Finish check runs the real native bootstrap/private Python with a recording
script. Other component markers are inert. No shared GUI, DSH, actual-browser or
full-runtime qualification is claimed; the full-payload proof remains required.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import time
import winreg

ROOT = Path(__file__).resolve().parents[1]


def prove(out, arch, compiler, fixture_executable, runtime):
    from platform_adapters.processes import OwnedProcess
    from platform_adapters.private_files import atomic_json, descriptor
    from platform_adapters.windows_identity import private_directory
    from platform_adapters.windows_browsers import command_executable
    import os
    out = Path(out)
    payload = out/'application-template-payload'
    payload.mkdir()
    # The installer only copies these markers. Runtime intake/launch is proved
    # elsewhere against the actual assembled product, never against this tree.
    for name in ('node/node.exe', 'powershell/pwsh.exe',
                 'updater/WinSparkle.dll', 'dsh/payload.json', 'scripts/launch-windows.py'):
        target = payload/name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'Inert installer template fixture; never execute.\n')
    for name in ('Augmentor.exe', 'AugmentorBrowserHost.exe'):
        shutil.copy2(fixture_executable, payload/name)
    release = {'version':'0.0.1', 'sourceCommit':subprocess.check_output(
        ['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(), 'target':'windows-'+arch,
        'customerDistribution':False, 'qualificationStatus':'development-candidate'}
    (payload/'release.json').write_text(json.dumps(release), encoding='utf-8')
    # Only the actual native bootstrap/private Python runs at Finish, with a
    # tiny recording script. Other component markers remain inert.
    shutil.copytree(Path(runtime)/'python', payload/'python',
        ignore=shutil.ignore_patterns('site-packages', '__pycache__', '*.pyc'))
    (payload/'python/Lib/site-packages').mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT/'scripts/windows-finish-launch-fixture.py', payload/'scripts/launch-windows.py')
    build_spec = importlib.util.spec_from_file_location('template_launcher', ROOT/'scripts/build-windows-launcher.py')
    builder = importlib.util.module_from_spec(build_spec); build_spec.loader.exec_module(builder)
    builder.build_launcher(payload, arch)
    spec = importlib.util.spec_from_file_location('template_package', ROOT/'scripts/package-windows.py')
    package = importlib.util.module_from_spec(spec); spec.loader.exec_module(package)
    report = package.build(payload, arch, out/'application-template-package',
        qualification=out/'application-template-private', compiler_path=compiler)
    install = Path(report['installationDirectory'])
    flags = ['/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-']
    stages = []; removal = None
    launch_record = Path(report['qualificationBase'])/'finish-launched.json'
    def run(executable, label, success=True):
        child = OwnedProcess([str(executable), *flags,
            '/LOG='+str(out/('application-template-'+label+'.log'))], stdin=subprocess.DEVNULL)
        try:
            # Inno's first uninstall process exits before the copied remover
            # finishes. Observe natural exit of the whole disposable range.
            code = child.wait_graceful(timeout=60)
        finally:
            if child.job is not None:
                child.kill(); child.wait(timeout=10)  # Failed fixture cleanup only.
        assert (code == 0) == success, (label,code)
        assert not launch_record.exists(), 'Silent maintenance launched the application.'
    try:
        run(report['installer'], 'initial')
        key_path = r'Software\Microsoft\Windows\CurrentVersion\Uninstall'+'\\'+report['applicationId']+'_is1'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ|winreg.KEY_WOW64_64KEY) as key:
            removal = command_executable(winreg.QueryValueEx(key, 'UninstallString')[0])
        assert removal.is_relative_to(install)
        run(report['installer'], 'repair')
        run(removal, 'without-browser')
        assert not (install/'current/Augmentor.exe').exists()
        stages.append('actual-template-repair-and-removal-without-browser')
        run(report['installer'], 'reinstall')
        manifest = Path(report['browserManifest'])
        private_directory(manifest.parent)
        atomic_json(manifest, {'name':'com.augmentor.agent', 'description':'Inert template fixture',
            'type':'stdio', 'path':str(install/'current/AugmentorBrowserHost.exe'),
            'allowed_origins':['chrome-extension://'+'a'*32+'/']})
        original = manifest.read_bytes()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, report['installationKey'], 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, 'BrowserManifestSHA256', 0, winreg.REG_SZ, hashlib.sha256(original).hexdigest())
            winreg.FlushKey(key)
        for key_path in report['browserKeys']:
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, '', 0, winreg.REG_SZ, str(manifest)); winreg.FlushKey(key)
        def write(content):
            with os.fdopen(descriptor(manifest, writable=True), 'wb') as stream:
                stream.write(content); stream.truncate(); stream.flush(); os.fsync(stream.fileno())
        write(original+b' ')
        run(removal, 'edited-browser-refusal', success=False)
        assert (install/'current/Augmentor.exe').is_file() and manifest.read_bytes() == original+b' '
        write(original)
        run(removal, 'owned-browser-removal')
        assert not (install/'current/Augmentor.exe').exists() and manifest.read_bytes() == original
        for key_path in [report['installationKey'], report['startupKey'], *report['browserKeys']]:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                assert winreg.QueryInfoKey(key)[:2] == (0,0), key_path
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
        stages.append('actual-template-edited-browser-refusal-and-owned-removal')
        interactive_finish(report['installer'], out/'application-template-interactive.log')
        launched = json.loads(launch_record.read_text(encoding='utf-8'))
        assert Path(launched['executable']) == install/'current/Augmentor.exe'
        assert launched['platform'] == {'x64':'win-amd64', 'arm64':'win-arm64'}[arch]
        launch_record.unlink()  # Fixture-owned observation; silent removal must not recreate it.
        run(removal, 'after-interactive')
        assert not (install/'current/Augmentor.exe').exists()
        for key_path in (report['installationKey'], report['startupKey']):
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
        stages.append('interactive-finish-native-startup-and-silent-no-launch')
        return {'passed':True, 'stages':stages, 'scope':'Exact Inno script and native bootstrap/private Python; no shared GUI, DSH or browser launch.'}
    finally:
        (out/'application-template-result.json').write_text(json.dumps({
            'stages':stages, 'scope':'Exact Inno script and native bootstrap/private Python; no shared GUI, DSH or browser launch.'}, indent=2)+'\n', encoding='utf-8')


def interactive_finish(installer, log):
    """Drive only this disposable installer's actual visible wizard buttons."""
    import ctypes
    from ctypes import wintypes
    import win32api, win32con, win32gui, win32job, win32process
    from platform_adapters.processes import OwnedProcess
    send = ctypes.WinDLL('user32', use_last_error=True).SendMessageTimeoutW
    send.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_void_p,
                    wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]
    send.restype = ctypes.c_ssize_t
    def caption_of(handle):
        # GetWindowText does not retrieve another process's control text.
        # WM_GETTEXT is a marshalled system message; bound both buffer and wait.
        buffer = ctypes.create_unicode_buffer(4096); result = ctypes.c_size_t()
        if not send(handle, win32con.WM_GETTEXT, len(buffer), buffer,
                    win32con.SMTO_ABORTIFHUNG | win32con.SMTO_BLOCK, 200, ctypes.byref(result)):
            return None
        return buffer.value
    child = OwnedProcess([str(installer), '/SP-', '/NORESTART', '/LANG=english', '/LOG='+str(log)],
        stdin=subprocess.DEVNULL)
    deadline = time.monotonic()+120
    clicked = set(); finished = False
    observations = []; last_state = None
    try:
        while not child.drained():
            if time.monotonic() >= deadline: raise TimeoutError('The disposable installer wizard did not complete.')
            windows = []
            def owned(window, _context):
                _thread, pid = win32process.GetWindowThreadProcessId(window)
                try: process = win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                except win32api.error: return
                try:
                    if win32job.IsProcessInJob(process, child.job): windows.append(window)
                finally: process.Close()
            win32gui.EnumWindows(owned, None)
            state = []
            for window in windows:
                controls = []
                def collect(control, _context):
                    if win32gui.IsWindowVisible(control):
                        controls.append((control, win32gui.GetClassName(control), caption_of(control)))
                win32gui.EnumChildWindows(window, collect, None)
                state.append({'class':win32gui.GetClassName(window), 'caption':caption_of(window),
                    'visible':bool(win32gui.IsWindowVisible(window)),
                    'controls':[{'class':kind,'caption':text,'enabled':bool(win32gui.IsWindowEnabled(handle))}
                                for handle,kind,text in controls]})
                if not win32gui.IsWindowVisible(window) or win32gui.GetClassName(window) != 'TWizardForm': continue
                # Different pages can reuse the same Next button. Retain visible
                # text to avoid clicking twice while the previous event is queued.
                page = tuple(sorted((kind, text) for _handle, kind, text in controls if text))
                # The pinned modern wizard renders Next without the legacy >.
                for caption in ('Finish', 'Install', 'Next', 'Next >'):
                    buttons = [handle for handle, kind, text in controls
                        if kind == 'TNewButton' and text and text.replace('&','') == caption and win32gui.IsWindowEnabled(handle)]
                    if len(buttons) != 1 or (page,caption) in clicked: continue
                    clicked.add((page,caption))
                    win32gui.PostMessage(buttons[0], win32con.BM_CLICK, 0, 0)
                    observations.append({'clicked':caption})
                    if caption == 'Finish': finished = True
                    break
            if state != last_state:
                observations.append({'windows':state}); last_state = state
                observations = observations[-40:]
            time.sleep(.05)
        assert child.wait_graceful(timeout=5) == 0 and finished
    finally:
        Path(log).with_suffix('.json').write_text(json.dumps({
            'finished':finished, 'observations':observations}, indent=2)+'\n', encoding='utf-8')
        if child.job is not None:
            child.kill(); child.wait(timeout=10)  # Failed disposable wizard only.
