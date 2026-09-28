#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Install/repair/remove the full candidate in compiled-in disposable locations."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'services'), str(ROOT/'apps/native')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--arch', choices=('x64','arm64'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'win32': parser.error('Native Windows installation proof required.')
    import winreg
    from platform_adapters.windows_identity import private_directory
    from platform_adapters.windows_browsers import command_executable
    from platform_adapters.private_files import atomic_json, descriptor, read_json
    from platform_adapters.transport import LocalSocket
    from platform_adapters.processes import OwnedProcess
    from augmentor_linux.instances import ipc_basename
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('windows_package', ROOT/'scripts/package-windows.py')
    package = importlib.util.module_from_spec(spec); spec.loader.exec_module(package)
    report = package.build(args.root, args.arch, out/'package', qualification=out/'qualification')
    data = Path(report['qualificationBase']); install = Path(report['installationDirectory'])
    executable = install/'current/Augmentor.exe'
    sentinel = private_directory(data/'data')/'retained-settings.json'
    atomic_json(sentinel, {'model':'fixture preserve selection', 'history':['fixture retained turn']})
    sentinel_bytes = sentinel.read_bytes()
    registry = 'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\'+report['applicationId']+'_is1'
    flags = ['/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-']
    child = None; removal = None; stages = []
    def run(command, *, success=True, timeout=300):
        argv = list(map(str,command))
        process = OwnedProcess(argv, stdin=subprocess.DEVNULL)
        try:
            # The original uninstaller can exit to permit its own deletion
            # while copied Uninstall still owns maintenance. Wait for the whole
            # fixture range to exit normally before inspecting or reinstalling.
            result = subprocess.CompletedProcess(argv, process.wait_graceful(timeout=timeout))
        finally:
            if process.job is not None:
                process.kill(); process.wait(timeout=10)  # Failed fixture cleanup only.
        assert (result.returncode == 0) == success, (str(command[0]), result.returncode, success)
        return result
    def setup(label, *extra, success=True):
        return run([report['installer'],*flags,'/LOG='+str(out/(label+'.log')),*extra], success=success)
    def command(value):
        with LocalSocket() as peer:
            peer.settimeout(5); peer.connect(str(data/'run'/(ipc_basename('main')+'.sock')))
            peer.sendall(value.encode()+b'\n')
            with peer.makefile('rb') as stream: result=stream.readline(262145)
        assert len(result)<=262144 and result.endswith(b'\n')
        return json.loads(result)
    def inspect(): return command('ui-test:{"action":"inspect"}')['result']
    def ready():
        deadline = time.monotonic()+30
        while time.monotonic()<deadline:
            assert child.poll() is None, 'Installed Augmentor exited before readiness.'
            try:
                state = inspect()
                if state['visible']: return state
            except (OSError, ValueError, KeyError): pass
            time.sleep(.1)
        raise AssertionError('Installed Augmentor did not become ready.')
    def open_preview():
        return subprocess.Popen([str(executable),'--qualification-root',str(data),'--preview','--ui-test-control'],
            env={**os.environ,'QT_QPA_PLATFORM':'windows','QSG_RHI_PREFER_SOFTWARE_RENDERER':'1'},
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    def close_preview():
        result = command('maintenance.close')
        assert result.get('accepted'), result
        assert child.wait(timeout=20)==0
    try:
        setup('initial')
        cached_installer = data/'recovery'/(report['sha256']+'.exe')
        cached_receipt = data/'recovery'/(report['sha256']+'.release')
        assert package.digest(cached_installer)==report['sha256']
        with os.fdopen(descriptor(cached_receipt),'rb') as stream:
            assert stream.read(65)==package.digest(args.root/'release.json').encode('ascii')
        cached_time=cached_installer.stat().st_mtime_ns
        from lifecycle.installed_source import open_installed_source
        with open_installed_source(data/'recovery', (install/'current/release.json').read_bytes(), target='windows-'+args.arch) as source:
            assert source.identity['sha256']==report['sha256']
            source_identity=source.identity
        selection_bytes=(data/'recovery/selected-installer').read_bytes()
        stages.append('original-full-installer-retained')
        assert (install/'current/release.json').read_bytes() == (args.root/'release.json').read_bytes()
        assert not any((install/'current').glob('*.lib')) and not any((install/'current').glob('*.exp'))
        assert not (install/'current/launcher.obj').exists()
        for relative in ('Augmentor.exe','AugmentorBrowserHost.exe','python/python.exe','node/node.exe',
                         'powershell/pwsh.exe','dsh/payload.json'):
            assert package.digest(install/'current'/relative)==package.digest(args.root/relative)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,registry,0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY) as key:
            removal = command_executable(winreg.QueryValueEx(key,'UninstallString')[0])
            assert winreg.QueryValueEx(key,'DisplayName')[0]=='Augmentor Agent'
            repair_command=winreg.QueryValueEx(key,'ModifyPath')[0]
            assert repair_command=='"'+str(cached_installer)+'"', repair_command
        assert removal.is_relative_to(install)
        from win32com.shell import shell,shellcon
        shortcut=Path(shell.SHGetFolderPath(0,shellcon.CSIDL_PROGRAMS,0,0))/(report['applicationId']+'.lnk')
        assert shortcut.is_file()
        import pythoncom
        link_object=pythoncom.CoCreateInstance(shell.CLSID_ShellLink,None,pythoncom.CLSCTX_INPROC_SERVER,shell.IID_IShellLink)
        link_object.QueryInterface(pythoncom.IID_IPersistFile).Load(str(shortcut))
        assert Path(link_object.GetPath(shell.SLGP_RAWPATH)[0]).resolve()==executable.resolve()
        shortcut_arguments=link_object.GetArguments()
        report['shortcutArguments']=shortcut_arguments
        assert shortcut_arguments=='--qualification-root "'+str(data)+'"', repr(shortcut_arguments)
        del link_object
        from platform_adapters.windows_browser import installed_root
        assert installed_root(install/'current',key_path=report['installationKey'])==install/'current'
        # Exercise the installed browser-preparation adapter with a synthetic
        # Chromium resource layout and real PE identity. It never runs this
        # fixture executable or modifies a browser's actual registry/profile.
        browser=out/'unlisted browser';browser.mkdir()
        shutil.copy2(executable,browser/'ChromiumFixture.exe')
        for name in ('resources.pak','icudtl.dat','fixture_100_percent.pak'):
            (browser/name).write_bytes(b'fixture')
        from platform_adapters.windows_browser import prepare_extension
        from unittest.mock import patch
        with patch.dict(os.environ,{'XDG_DATA_HOME':str(data/'data')}):
            prepared=prepare_extension(install/'current',browser/'ChromiumFixture.exe',
                key_path=report['installationKey'],keys=report['browserKeys'])
        browser_manifest=Path(prepared['manifest'])
        assert str(browser_manifest)==report['browserManifest']
        browser_manifest_bytes=browser_manifest.read_bytes()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,report['installationKey']) as key:
            assert winreg.QueryValueEx(key,'BrowserManifestSHA256')==(package.digest(browser_manifest),winreg.REG_SZ)
        startup_command=subprocess.list2cmdline([str(executable),'--qualification-root',str(data),'--background'])
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,report['startupKey'],0,winreg.KEY_READ|winreg.KEY_SET_VALUE) as key:
            assert winreg.QueryValueEx(key,'Augmentor Agent')==(startup_command,winreg.REG_SZ)
            winreg.SetValueEx(key,'Unrelated',0,winreg.REG_SZ,'preserve this fixture entry')
            startup_timestamp=winreg.QueryInfoKey(key)[2]
        report['startupCommand']=startup_command
        stages.append('initial-full-payload-install')
        child = open_preview(); state=ready(); assert state['pid']==child.pid
        command('ui-test:'+json.dumps({'action':'draft','expected':'','text':'Preserve this installed draft'}))
        setup('busy-repair',success=False)
        run([removal,*flags,'/LOG='+str(out/'busy-uninstall.log')],success=False)
        assert child.poll() is None and inspect()['draft']=='Preserve this installed draft'
        assert sentinel.read_bytes()==sentinel_bytes
        stages.append('busy-install-and-removal-preserve-live-draft')
        command('ui-test:'+json.dumps({'action':'draft','expected':'Preserve this installed draft','text':''}))
        close_preview(); child=None
        # Break the installed executable, interpreter and identity, then repair
        # through the standalone installer registered with Windows. This must
        # work without running any code in the damaged installed application.
        owned=install/'current/scripts/launch-windows.py'; owned.unlink()
        executable.unlink()
        (install/'current/release.json').unlink()
        runtime_libraries=list((install/'current/python').glob('python3*.dll'))
        assert runtime_libraries
        for library in runtime_libraries: library.unlink()
        run([command_executable(repair_command),*flags,'/LOG='+str(out/'repair.log')])
        assert owned.read_bytes()==(args.root/'scripts/launch-windows.py').read_bytes()
        for relative in ('Augmentor.exe','release.json',*[str(path.relative_to(install/'current')) for path in runtime_libraries]):
            assert package.digest(install/'current'/relative)==package.digest(args.root/relative)
        child=open_preview(); ready(); close_preview(); child=None
        assert shortcut.is_file() and sentinel.read_bytes()==sentinel_bytes
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,report['startupKey'],0,winreg.KEY_READ|winreg.KEY_SET_VALUE) as key:
            assert winreg.QueryValueEx(key,'Augmentor Agent')==(startup_command,winreg.REG_SZ)
            assert winreg.QueryInfoKey(key)[2]==startup_timestamp, 'Repair rewrote the login key.'
            # Model a user removing login startup. Coordinated application must
            # not restore that preference just because a new build is applied.
            winreg.DeleteValue(key,'Augmentor Agent')
        stages.append('same-build-repair-and-installed-relaunch')
        stages.append('registered-repair-without-installed-runtime-or-metadata')
        # Exercise the shared decision coordinator against installed binaries,
        # an actual background owner/window, and the actual packaged Setup.
        # Identical artifact repair isolates transport/process integration from
        # the separately unfinished N-to-N+1 trust/recovery policy.
        artifact=cached_installer
        # Exercise the exact installer-created command without a command shell.
        subprocess.run(startup_command,check=True,timeout=30)
        child=open_preview();ready()
        coordinator_log=(out/'coordinator.log').open('w',encoding='utf-8')
        coordinator=subprocess.Popen([str(install/'current/python/python.exe'),'-I','-Xutf8','-B',
            str(ROOT/'scripts/windows-application-update-proof.py'),'--root',str(install/'current'),
            '--data',str(data),'--installer',str(artifact),'--sha256',report['sha256']],
            stdout=subprocess.DEVNULL,stderr=coordinator_log)
        coordinator_log.close()
        transaction=data/'updates';result_path=transaction/'coordinator-result.json'
        deadline=time.monotonic()+90
        while not result_path.exists():
            assert coordinator.poll() is None, 'The installed coordinator failed; inspect coordinator.log.'
            if time.monotonic()>=deadline:raise TimeoutError('The installed coordinator did not authorize Setup.')
            time.sleep(.05)
        result=read_json(result_path)
        assert result['coordinatorMustExit'] and not result['installationComplete']
        assert child.wait(timeout=10)==0;child=None
        journal=read_json(transaction/'active.json')
        assert journal['phase']=='apply-acknowledged'
        assert {'WindowParticipant','OwnerParticipant'} <= {step['kind'] for step in journal['steps']}, journal['steps']
        assert journal['steps'][-1]['kind']=='OwnerParticipant' and journal['steps'][-1]['phase']=='exited'
        import win32api,win32con,win32event,win32process
        setup_process=win32api.OpenProcess(win32con.SYNCHRONIZE|win32con.PROCESS_QUERY_INFORMATION,False,result['setupPid'])
        try:
            assert win32event.WaitForSingleObject(setup_process,0)==win32event.WAIT_TIMEOUT
            (transaction/'observer-ready').touch()
            assert coordinator.wait(timeout=30)==0
            assert win32event.WaitForSingleObject(setup_process,300000)==win32event.WAIT_OBJECT_0
            assert win32process.GetExitCodeProcess(setup_process)==0
        finally:setup_process.Close()
        assert (install/'current/release.json').read_bytes()==(args.root/'release.json').read_bytes()
        assert sentinel.read_bytes()==sentinel_bytes
        # Independent local health does not depend on a provider being online.
        # For this known-built artifact compare every payload file, then launch
        # and close the actual installed Qt app before completing its journal.
        from lifecycle.update_journal import UpdateJournal
        def local_health(_record):
            nonlocal child
            assert package.digest(artifact)==report['sha256']
            for directory,_names,files in os.walk(args.root):
                for filename in files:
                    source=Path(directory)/filename
                    assert package.digest(install/'current'/source.relative_to(args.root))==package.digest(source)
            child=open_preview();ready();close_preview();child=None
            return True
        archive=UpdateJournal.complete_verified(transaction,source_identity,source_identity,local_health)
        assert read_json(archive)['phase']=='complete' and not (transaction/'active.json').exists()
        report['archivedUpdate']=archive.name
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,report['startupKey'],0,winreg.KEY_READ|winreg.KEY_SET_VALUE) as key:
            try: winreg.QueryValueEx(key,'Augmentor Agent')
            except FileNotFoundError: pass
            else: raise AssertionError('Coordinated apply restored removed login startup.')
            # Restore only this disposable entry to exercise exact owned removal.
            winreg.SetValueEx(key,'Augmentor Agent',0,winreg.REG_SZ,startup_command)
        stages.append('installed-graph-drain-durable-apply-setup-exit-and-relaunch')
        # Inno must not follow a requested custom replacement directory.
        other=out/'foreign';other.mkdir();foreign=other/'untouched.txt';foreign.write_text('preserve')
        setup('custom-path-refusal','/DIR='+str(other),success=False)
        assert list(other.iterdir())==[foreign] and foreign.read_text()=='preserve'
        stages.append('custom-replacement-path-refused')
        import _winapi
        link=install/'current/redirected-fixture'
        _winapi.CreateJunction(str(other),str(link))
        try:
            setup('junction-repair-refusal',success=False)
            run([removal,*flags,'/LOG='+str(out/'junction-removal-refusal.log')],success=False)
            assert executable.is_file() and foreign.read_text()=='preserve'
        finally: os.rmdir(link)
        stages.append('redirected-tree-repair-and-removal-refused')
        # A changed manifest is preserved before removal changes startup or
        # application files. Only restore this exact test-created file afterward.
        def write_manifest(content):
            with os.fdopen(descriptor(browser_manifest,writable=True),'wb') as stream:
                stream.write(content);stream.truncate();stream.flush();os.fsync(stream.fileno())
        write_manifest(browser_manifest_bytes+b' ')
        run([removal,*flags,'/LOG='+str(out/'changed-browser-removal-refusal.log')],success=False)
        assert executable.is_file() and browser_manifest.read_bytes()==browser_manifest_bytes+b' '
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,report['startupKey']) as key:
            assert winreg.QueryValueEx(key,'Augmentor Agent')==(startup_command,winreg.REG_SZ)
        write_manifest(browser_manifest_bytes)
        run([removal,*flags,'/LOG='+str(out/'uninstall.log')])
        assert not executable.exists() and not shortcut.exists()
        try: key=winreg.OpenKey(winreg.HKEY_CURRENT_USER,registry,0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY)
        except FileNotFoundError: pass
        else: key.Close();raise AssertionError('The application registration survived uninstall.')
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,report['startupKey']) as key:
            assert winreg.QueryInfoKey(key)[:2]==(0,1)
            assert winreg.QueryValueEx(key,'Unrelated')==('preserve this fixture entry',winreg.REG_SZ)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,report['installationKey']) as key:
            assert winreg.QueryInfoKey(key)[:2]==(0,0), 'Owned installation anchor survived removal.'
        for key_path in report['browserKeys']:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,key_path) as key:
                assert winreg.QueryInfoKey(key)[:2]==(0,0), 'An owned browser pointer survived removal.'
        assert browser_manifest.read_bytes()==browser_manifest_bytes
        assert sentinel.read_bytes()==sentinel_bytes
        assert package.digest(cached_installer)==report['sha256']
        assert cached_installer.stat().st_mtime_ns==cached_time
        assert (data/'recovery/selected-installer').read_bytes()==selection_bytes
        stages.append('software-removed-persistent-data-retained')
        # These two keys are synthetic qualification locations. Never remove a
        # real Run key, StartupApproved state or another application's values.
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER,report['startupKey'])
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER,report['installationKey'])
        for key_path in report['browserKeys']:winreg.DeleteKey(winreg.HKEY_CURRENT_USER,key_path)
        report.update(passed=True,stages=stages,scope='Full installed payload and native Qt preview; no model, physical input, signed update or rollback claim.')
    finally:
        # Only this disposable preview may be closed on failure. Never clean a
        # personal app or force-stop a test whose accepted work is unknown.
        if child is not None and child.poll() is None:
            try:
                draft=inspect().get('draft','')
                if draft: command('ui-test:'+json.dumps({'action':'draft','expected':draft,'text':''}))
                close_preview()
            except Exception: pass
        report.setdefault('passed',False);report['stages']=stages
        if not report['passed']:
            # Only logs from this compiled-in, disposable preview. Preserve a
            # bounded stack/error sample when its process fails to exit.
            report['fixtureDiagnostics']={path.name:path.read_text(encoding='utf-8',errors='replace')[-12000:]
                for path in (data/'state/logs').glob('desktop.*.log')}
        (out/'installed-application.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':report['passed'],'stages':stages}))


if __name__=='__main__': main()
