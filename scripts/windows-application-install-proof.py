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
        result = subprocess.run(list(map(str,command)), timeout=timeout)
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
        assert (install/'current/release.json').read_bytes() == (args.root/'release.json').read_bytes()
        for relative in ('Augmentor.exe','AugmentorBrowserHost.exe','python/python.exe','node/node.exe',
                         'powershell/pwsh.exe','dsh/payload.json'):
            assert package.digest(install/'current'/relative)==package.digest(args.root/relative)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,registry,0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY) as key:
            removal = command_executable(winreg.QueryValueEx(key,'UninstallString')[0])
            assert winreg.QueryValueEx(key,'DisplayName')[0]=='Augmentor Agent'
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
        # Delete one installer-owned file, repair the identical build, then
        # launch its actual executable again. No source checkout launch.
        owned=install/'current/scripts/launch-windows.py'; owned.unlink()
        setup('repair')
        assert owned.read_bytes()==(args.root/'scripts/launch-windows.py').read_bytes()
        child=open_preview(); ready(); close_preview(); child=None
        assert shortcut.is_file() and sentinel.read_bytes()==sentinel_bytes
        stages.append('same-build-repair-and-installed-relaunch')
        # Exercise the shared decision coordinator against installed binaries,
        # an actual background owner/window, and the actual packaged Setup.
        # Identical artifact repair isolates transport/process integration from
        # the separately unfinished N-to-N+1 trust/recovery policy.
        cache=private_directory(data/'cache')
        artifact=cache/'qualified-installer.exe'
        with os.fdopen(descriptor(artifact,writable=True,exclusive=True),'wb') as target, Path(report['installer']).open('rb') as source:
            shutil.copyfileobj(source,target);target.flush();os.fsync(target.fileno())
        run([executable,'--qualification-root',data,'--background'],timeout=30)
        child=open_preview();ready()
        coordinator_log=(out/'coordinator.log').open('w',encoding='utf-8')
        coordinator=subprocess.Popen([str(install/'current/python/python.exe'),'-I','-Xutf8','-B',
            str(ROOT/'scripts/windows-application-update-proof.py'),'--root',str(install/'current'),
            '--data',str(data),'--installer',str(artifact),'--sha256',report['sha256']],
            stdout=subprocess.DEVNULL,stderr=coordinator_log)
        coordinator_log.close()
        transaction=data/'update-proof';result_path=transaction/'coordinator-result.json'
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
        release=report['release']
        identity={'version':release['version'],'sourceCommit':release['sourceCommit'],'target':release['target'],
            'channel':'qualification','sha256':report['sha256'],'dataSchema':1,'readableDataSchemas':[1]}
        def local_health(_record):
            nonlocal child
            assert package.digest(artifact)==report['sha256']
            for directory,_names,files in os.walk(args.root):
                for filename in files:
                    source=Path(directory)/filename
                    assert package.digest(install/'current'/source.relative_to(args.root))==package.digest(source)
            child=open_preview();ready();close_preview();child=None
            return True
        archive=UpdateJournal.complete_verified(transaction,identity,identity,local_health)
        assert read_json(archive)['phase']=='complete' and not (transaction/'active.json').exists()
        report['archivedUpdate']=archive.name
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
        run([removal,*flags,'/LOG='+str(out/'uninstall.log')])
        assert not executable.exists() and not shortcut.exists()
        try: key=winreg.OpenKey(winreg.HKEY_CURRENT_USER,registry,0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY)
        except FileNotFoundError: pass
        else: key.Close();raise AssertionError('The application registration survived uninstall.')
        assert sentinel.read_bytes()==sentinel_bytes
        stages.append('software-removed-persistent-data-retained')
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
        (out/'installed-application.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':report['passed'],'stages':stages}))


if __name__=='__main__': main()
