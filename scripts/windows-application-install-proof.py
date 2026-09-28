#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Install/repair/remove the full candidate in compiled-in disposable locations."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
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
    from platform_adapters.private_files import atomic_json
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
