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
                 'updater/WinSparkle.dll', 'dsh/payload.json', 'scripts/launch-windows.py', 'scripts/windows-local-health.py'):
        target = payload/name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'Inert installer template fixture; never execute.\n')
    for name in ('Augmentor.exe', 'AugmentorBrowserHost.exe'):
        shutil.copy2(fixture_executable, payload/name)
    release = {'version':'0.0.1', 'sourceCommit':subprocess.check_output(
        ['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(), 'target':'windows-'+arch,
        'channel':'preview', 'dataSchema':1, 'readableDataSchemas':[1],
        'customerDistribution':False, 'qualificationStatus':'development-candidate'}
    (payload/'release.json').write_text(json.dumps(release), encoding='utf-8')
    # Only the actual native bootstrap/private Python runs at Finish, with a
    # tiny recording script. Other component markers remain inert.
    shutil.copytree(Path(runtime)/'python', payload/'python',
        ignore=shutil.ignore_patterns('site-packages', '__pycache__', '*.pyc'))
    (payload/'python/Lib/site-packages').mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT/'scripts/windows-finish-launch-fixture.py', payload/'scripts/launch-windows.py')
    for name in ('scripts/windows-inspect-payload.py','services/lifecycle/payload_integrity.py',
                 'services/lifecycle/recovery_source.py','services/lifecycle/update_journal.py',
                 'services/platform_adapters/private_files.py','services/platform_adapters/locks.py'):
        target=payload/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/name,target)
    build_spec = importlib.util.spec_from_file_location('template_launcher', ROOT/'scripts/build-windows-launcher.py')
    builder = importlib.util.module_from_spec(build_spec); build_spec.loader.exec_module(builder)
    builder.build_launcher(payload, arch)
    assert not any(payload.glob('*.lib')) and not any(payload.glob('*.exp')) and not (payload/'launcher.obj').exists()
    from lifecycle.payload_integrity import seal_payload
    release=seal_payload(payload)
    spec = importlib.util.spec_from_file_location('template_package', ROOT/'scripts/package-windows.py')
    package = importlib.util.module_from_spec(spec); spec.loader.exec_module(package)
    report = package.build(payload, arch, out/'application-template-package',
        qualification=out/'application-template-private', compiler_path=compiler)
    install = Path(report['installationDirectory'])
    flags = ['/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-']
    stages = []; removal = None
    launch_record = Path(report['qualificationBase'])/'finish-launched.json'
    def run(executable, label, success=True, arguments=()):
        child = OwnedProcess([str(executable), *flags,
            '/LOG='+str(out/('application-template-'+label+'.log')), *arguments], stdin=subprocess.DEVNULL)
        try:
            # Inno's first uninstall process exits before the copied remover
            # finishes. Observe natural exit of the whole disposable range.
            code = child.wait_graceful(timeout=60)
        finally:
            if child.job is not None:
                child.kill(); child.wait(timeout=10)  # Failed fixture cleanup only.
        assert (code == 0) == success, (label,code)
        assert not launch_record.exists(), 'Silent maintenance launched the application.'
    def inspect(executable,label,*,source=False):
        # InitializeSetup deliberately refuses installation after inspection.
        # A nonzero Setup exit alone is not an inspection-success assertion.
        run(executable,label,success=False,arguments=['/augmentorinspect='+('source' if source else '1')])
        log=(out/('application-template-'+label+'.log')).read_text(encoding='utf-8-sig')
        marker='Augmentor independent inspection result: '
        rows=[line.split(marker,1)[1] for line in log.splitlines() if marker in line]
        assert len(rows)==1, log[-8192:]
        result=json.loads(rows[0]);assert result['schema']=='augmentor-payload-inspection/1'
        assert result['releaseSHA256']==hashlib.sha256((payload/'release.json').read_bytes()).hexdigest()
        return result
    try:
        run(report['installer'], 'initial')
        recovery = Path(report['qualificationBase'])/'recovery'
        cached = recovery/(report['sha256']+'.exe')
        receipt = recovery/(report['sha256']+'.release')
        def read_private(path):
            with os.fdopen(descriptor(path),'rb') as stream: return stream.read()
        assert hashlib.sha256(read_private(cached)).hexdigest() == report['sha256']
        release_digest = hashlib.sha256((payload/'release.json').read_bytes()).hexdigest().encode('ascii')
        assert read_private(receipt) == release_digest
        from lifecycle.installed_source import open_installed_source
        with open_installed_source(recovery, (payload/'release.json').read_bytes(), target='windows-'+arch) as source:
            assert source.identity['sha256']==report['sha256'] and source.installer==cached
        selection = recovery/'selected-installer'
        key_path = r'Software\Microsoft\Windows\CurrentVersion\Uninstall'+'\\'+report['applicationId']+'_is1'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ|winreg.KEY_WOW64_64KEY) as key:
            removal = command_executable(winreg.QueryValueEx(key, 'UninstallString')[0])
            repair_command = winreg.QueryValueEx(key, 'ModifyPath')[0]
        assert repair_command == '"'+str(cached)+'"', repair_command
        repair = command_executable(repair_command)
        assert removal.is_relative_to(install)
        # Both kinds of damaged retained bytes refuse BEFORE file replacement;
        # preserve the damaged cache for inspection, then restore this fixture.
        for path in (cached,receipt,selection):
            original = read_private(path)
            changed = b'X'+original[1:]
            with os.fdopen(descriptor(path,writable=True),'wb') as stream: stream.write(changed)
            run(report['installer'], 'corrupt-'+(path.suffix[1:] or 'selection')+'-refusal', success=False)
            assert read_private(path) == changed and (install/'current/Augmentor.exe').is_file()
            with os.fdopen(descriptor(path,writable=True),'wb') as stream: stream.write(original)
        retained_time = cached.stat().st_mtime_ns
        selected_time = selection.stat().st_mtime_ns
        run(report['installer'], 'repair')
        assert cached.stat().st_mtime_ns == retained_time
        assert selection.stat().st_mtime_ns == selected_time
        stages.append('original-installer-retained-and-corrupt-cache-refused')
        assert inspect(cached,'intact-independent-inspection')['complete']
        # Registered repair executes the retained standalone installer after
        # deleting the native app and its interpreter DLLs/version metadata.
        # It must need no executable code from the broken installed payload.
        sentinel = Path(report['qualificationBase'])/'preserve-settings.json'
        atomic_json(sentinel, {'model':'preserve fixture choice','history':['preserve fixture turn']})
        sentinel_bytes = sentinel.read_bytes()
        installed_release = install/'current/release.json'
        installed_release.unlink()
        (install/'current/Augmentor.exe').unlink()
        runtime_libraries = list((install/'current/python').glob('python3*.dll'))
        assert runtime_libraries
        for library in runtime_libraries: library.unlink()
        before_inspection={p.relative_to(install).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in install.rglob('*') if p.is_file()}
        result=inspect(cached,'damaged-independent-inspection')
        assert result['complete'] is False and result['differences']['missing']==len(runtime_libraries)+2, result
        after_inspection={p.relative_to(install).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in install.rglob('*') if p.is_file()}
        assert after_inspection==before_inspection and sentinel.read_bytes()==sentinel_bytes
        stages.append('independent-inspection-without-installed-runtime-or-metadata')
        updates = private_directory(Path(report['qualificationBase'])/'updates')
        pending = updates/'active.json'
        with os.fdopen(descriptor(pending,writable=True,create=True),'wb') as stream:
            stream.write(b'Unresolved fixture update: even malformed state blocks manual repair.\n')
        pending_bytes = pending.read_bytes()
        assert inspect(cached,'pending-independent-inspection')['complete'] is False
        assert pending.read_bytes()==pending_bytes and sentinel.read_bytes()==sentinel_bytes
        run(repair, 'pending-update-repair-refusal', success=False)
        run(removal, 'pending-update-removal-refusal', success=False)
        assert pending.read_bytes() == pending_bytes and not installed_release.exists()
        assert not (install/'current/Augmentor.exe').exists() and sentinel.read_bytes() == sentinel_bytes
        pending.unlink()  # Dispose only this test's synthetic pending record.
        # Independent source assessment uses a real private journal/writer lock
        # with the real cached source and a deliberately synthetic future target.
        # It is not a cross-version apply/rollback proof.
        from lifecycle.update_journal import UpdateJournal
        source_identity={name:release[name] for name in
            ('version','sourceCommit','target','channel','dataSchema','readableDataSchemas')}
        source_identity['sha256']=report['sha256']
        target_identity={**source_identity,'version':'0.0.2','sourceCommit':'e'*40,'sha256':'f'*64}
        with UpdateJournal(updates,source_identity,target_identity) as journal:
            for phase in ('preparing','prepared','drained','installer-ready','apply-intent'):journal.advance(phase)
            pending_bytes=pending.read_bytes()
            run(cached,'source-held-writer-refusal',success=False,arguments=['/augmentorinspect=source'])
            held_log=(out/'application-template-source-held-writer-refusal.log').read_text(encoding='utf-8-sig')
            assert 'exclusive private update snapshot unavailable.' in held_log
            assert 'Augmentor independent inspection result:' not in held_log
            assert pending.read_bytes()==pending_bytes
        assessed=inspect(cached,'recorded-source-inspection',source=True)['recovery']
        assert assessed['recordedSourceMatches'] and not assessed['applyAuthorized']
        assert assessed['phase']=='apply-intent' and assessed['installerSHA256']==report['sha256']
        assert assessed['recordSHA256']==hashlib.sha256(pending_bytes).hexdigest()
        assert pending.read_bytes()==pending_bytes and sentinel.read_bytes()==sentinel_bytes
        assert not installed_release.exists() and not (install/'current/Augmentor.exe').exists()
        alias=updates/'record-alias.json';os.link(pending,alias)
        try:
            run(cached,'source-record-alias-refusal',success=False,arguments=['/augmentorinspect=source'])
            alias_log=(out/'application-template-source-record-alias-refusal.log').read_text(encoding='utf-8-sig')
            assert 'exclusive private update snapshot unavailable.' in alias_log
            assert 'Augmentor independent inspection result:' not in alias_log
            assert pending.read_bytes()==pending_bytes and alias.read_bytes()==pending_bytes
        finally:alias.unlink()
        for label,raw in (
            ('wrong-source',json.dumps({**json.loads(pending_bytes),'source':{**source_identity,'sourceCommit':'e'*40}}).encode()),
            ('malformed-source',b'Unparseable fixture update.')):
            with os.fdopen(descriptor(pending,writable=True),'wb') as stream:
                stream.write(raw);stream.truncate()
            assert pending.read_bytes()==raw, 'The corruption fixture did not write its exact intended bytes.'
            run(cached,label+'-assessment-refusal',success=False,arguments=['/augmentorinspect=source'])
            log=(out/('application-template-'+label+'-assessment-refusal.log')).read_text(encoding='utf-8-sig')
            assert 'stage=9, detail=85;' in log and 'Augmentor independent inspection result:' not in log
            assert pending.read_bytes()==raw, 'Inspection changed the synthetic interrupted record.'
            assert sentinel.read_bytes()==sentinel_bytes, 'Inspection changed the fixture user data.'
        pending.unlink()  # Dispose only this synthetic journal; never customer recovery policy.
        stages.append('independent-recorded-source-assessment-and-live-writer-refusal')
        selected_bytes = read_private(selection)
        from lifecycle.installed_source import PREFIX
        with os.fdopen(descriptor(selection,writable=True),'wb') as stream:
            stream.write(PREFIX+b'0'*64+b'\n'+release_digest+b'\n')
        run(repair, 'unselected-source-repair-refusal', success=False)
        assert not installed_release.exists() and not (install/'current/Augmentor.exe').exists()
        with os.fdopen(descriptor(selection,writable=True),'wb') as stream: stream.write(selected_bytes)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, report['installationKey'], 0,
                            winreg.KEY_READ|winreg.KEY_SET_VALUE|winreg.KEY_WOW64_64KEY) as key:
            registered_root = winreg.QueryValueEx(key, 'Root')
            winreg.DeleteValue(key, 'Root'); winreg.FlushKey(key)
            run(repair, 'unowned-source-repair-refusal', success=False)
            assert not installed_release.exists()
            winreg.SetValueEx(key, 'Root', 0, registered_root[1], registered_root[0]); winreg.FlushKey(key)
        run(repair, 'registered-independent-repair')
        assert installed_release.read_bytes() == (payload/'release.json').read_bytes()
        for path in (install/'current/Augmentor.exe', *runtime_libraries):
            assert path.read_bytes() == (payload/path.relative_to(install/'current')).read_bytes()
        assert read_private(selection) == selected_bytes and cached.stat().st_mtime_ns == retained_time
        assert sentinel.read_bytes() == sentinel_bytes
        # Damaged metadata (rather than an absent file) takes the same exact
        # selected-source path. No foreign/version-only match is accepted.
        installed_release.write_bytes(b'Broken fixture metadata.\n')
        run(repair, 'damaged-metadata-repair')
        assert installed_release.read_bytes() == (payload/'release.json').read_bytes()
        # A lost payload is still the registered installation, not a new user.
        # Preserve a login entry deliberately removed by that user.
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, report['startupKey'], 0,
                            winreg.KEY_READ|winreg.KEY_SET_VALUE|winreg.KEY_WOW64_64KEY) as key:
            winreg.DeleteValue(key, 'Augmentor Agent'); winreg.FlushKey(key)
        shutil.rmtree(install/'current')  # Exact disposable fixture-owned payload.
        absent=inspect(cached,'absent-payload-root-inspection')
        assert absent['complete'] is False and absent['differences']['missing']==absent['files'], absent
        assert not (install/'current').exists() and sentinel.read_bytes()==sentinel_bytes
        run(repair, 'missing-payload-repair')
        assert installed_release.read_bytes() == (payload/'release.json').read_bytes()
        assert inspect(cached,'restored-payload-root-inspection')['complete']
        stages.append('independent-inspection-and-repair-of-missing-payload-root')
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, report['startupKey'], 0,
                            winreg.KEY_READ|winreg.KEY_WOW64_64KEY) as key:
            try: winreg.QueryValueEx(key, 'Augmentor Agent')
            except FileNotFoundError: pass
            else: raise AssertionError('Repair re-enabled the removed login entry.')
        assert sentinel.read_bytes() == sentinel_bytes
        stages.append('registered-independent-repair-and-unresolved-update-refusal')
        run(removal, 'without-browser')
        assert not (install/'current/Augmentor.exe').exists()
        assert hashlib.sha256(read_private(cached)).hexdigest() == report['sha256']
        assert read_private(receipt) == release_digest
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
            if finished:
                time.sleep(.05); continue  # Observe natural exit, not destroyed wizard controls.
            windows = []
            def owned(window, _context):
                try: _thread, pid = win32process.GetWindowThreadProcessId(window)
                except win32gui.error as error:
                    if error.winerror == 1400: return
                    raise
                try: process = win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                except win32api.error: return
                try:
                    if win32job.IsProcessInJob(process, child.job): windows.append(window)
                finally: process.Close()
            win32gui.EnumWindows(owned, None)
            state = []
            for window in windows:
                try: window_class = win32gui.GetClassName(window)
                except win32gui.error as error:
                    if error.winerror == 1400: continue
                    raise
                controls = []
                def collect(control, _context):
                    try:
                        if win32gui.IsWindowVisible(control):
                            controls.append((control, win32gui.GetClassName(control), caption_of(control)))
                    except win32gui.error as error:
                        if error.winerror != 1400: raise
                win32gui.EnumChildWindows(window, collect, None)
                state.append({'class':window_class, 'caption':caption_of(window),
                    'visible':bool(win32gui.IsWindowVisible(window)),
                    'controls':[{'class':kind,'caption':text,'enabled':bool(win32gui.IsWindowEnabled(handle))}
                                for handle,kind,text in controls]})
                if not win32gui.IsWindowVisible(window) or window_class != 'TWizardForm': continue
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
                if finished: break
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
