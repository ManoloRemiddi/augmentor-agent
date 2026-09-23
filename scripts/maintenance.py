#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Prepare this user's Augmentor for package update or removal; preserve all data."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'apps/native'))
from augmentor_linux.pi_client import Connection, socket_path


def location(kind, fallback):
    return Path(os.environ.get('XDG_'+kind+'_HOME',Path.home()/fallback))


def identity(pid):
    try:
        path=Path('/proc')/str(pid)
        if path.stat().st_uid != os.getuid():
            return None
        return (path/'stat').read_text().rsplit(')',1)[1].split()[19]
    except FileNotFoundError:
        return None


def wait_exit(pid, start, timeout=20):
    deadline=time.monotonic()+timeout
    while start is not None and identity(pid)==start:
        # An unreaped child is already stopped and holds no files/leases.
        if (Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[0]=='Z':
            return
        if time.monotonic()>deadline:
            raise RuntimeError('A component did not close. Finish closing Augmentor before retrying.')
        time.sleep(.05)


def ui_call(command):
    path=Path(os.environ.get('XDG_RUNTIME_DIR',f'/tmp/augmentor-linux-pi-{os.getuid()}'))/'augmentor-linux-pi.sock'
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
        client.settimeout(3)
        try:client.connect(str(path))
        except (FileNotFoundError,ConnectionRefusedError):return None
        client.sendall(command.encode())
        try:
            with client.makefile('rb') as stream:value=stream.readline(8193)
            return json.loads(value)
        except (ValueError,socket.timeout):
            raise RuntimeError('This older Augmentor window needs to be closed manually before maintenance.')


def companion_call(endpoint, method):
    state=Path(os.environ.get('AUGMENTOR_SHARED_STATE',location('STATE','.local/state')/'augmentor'))
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
        client.settimeout(20)
        try:client.connect(str(state/endpoint))
        except (FileNotFoundError,ConnectionRefusedError):return None
        client.sendall((json.dumps({'protocol':'augmentor-prompts/1','id':uuid.uuid4().hex,'method':method})+'\n').encode())
        with client.makefile('rb') as stream:response=json.loads(stream.readline(8193))
        if response.get('error'):raise RuntimeError('Shared service did not accept its health check: '+endpoint)
        return response['result']


def prompt_call():
    return companion_call('prompts.sock','host.describe')


def memory_call():
    return companion_call('dual-memory.sock','memory.dual.describe')


def stop_companions():
    for describe, executable in ((prompt_call,'prompt-library'),(memory_call,'memory')):
        status=describe()
        if not status:continue
        pid=status['pid'];start=identity(pid)
        # Match the owner and executable before signalling a reported PID.
        arguments=(Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
        if start is None or not any(arg.endswith(('/services/'+executable+'/service.py').encode()) for arg in arguments):
            raise RuntimeError('Shared service process identity changed; retry maintenance.')
        os.kill(pid,signal.SIGTERM);wait_exit(pid,start)


def desktop_call(method):
    path=Path(os.environ.get('XDG_RUNTIME_DIR',f'/run/user/{os.getuid()}'))/'augmentor-desktop.sock'
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
        client.settimeout(10)
        try:client.connect(str(path))
        except (FileNotFoundError,ConnectionRefusedError):return None
        client.sendall((json.dumps({'protocol':'augmentor-desktop/1','method':method})+'\n').encode())
        with client.makefile('rb') as stream:response=json.loads(stream.readline(8193))
        if not response.get('ok'):raise RuntimeError(response.get('error','Desktop executor did not accept maintenance.'))
        return response['result']


def browser_processes():
    result=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            if path.stat().st_uid!=os.getuid():continue
            args=(path/'cmdline').read_bytes().split(b'\0')
            if any(arg==str(ROOT/'apps/browser'/name).encode() for arg in args for name in ('native-host.mjs','pi-bridge.mjs','pipe.mjs')):
                result.append(int(path.name))
        except FileNotFoundError:pass
    return result


def prepare(component):
    if component=='all':
        sys.path.insert(0,str(ROOT/'services'))
        from dsh.setup import current,http
        configuration=current()
        if configuration:
            try:status=http(configuration['endpoint'],'/api/augmentor-product')
            except (OSError,ValueError):status=None
            if status and status.get('protocol')=='augmentor-dsh/1':
                raise RuntimeError('Close the connected DSH host before updating Augmentor. No tasks were cancelled.')
    # Check every connected execution owner before closing anything.
    if component=='all' and browser_processes():
        raise RuntimeError('Disconnect Augmentor in the browser and let its active task finish before preparing maintenance.')
    desktop=desktop_call('status')
    if desktop and (desktop.get('active') or desktop.get('busy')):raise RuntimeError('Stop desktop control before preparing maintenance. Nothing was cancelled.')
    ui=ui_call('maintenance.status')
    if ui and ui.get('busy'):
        raise RuntimeError('Finish or stop the active chat and close open dialogs before maintenance.')
    runtimes=[]
    try:
        if component=='all':
            endpoints=[('Pi',socket_path(),'augmentor-pi/1')]
            for label,endpoint,protocol in endpoints:
                try:connection=Connection(endpoint,protocol)
                except (FileNotFoundError,ConnectionRefusedError):continue
                runtimes.append((connection,None))
                status=connection.call('host.describe');runtimes[-1]=(connection,status)
                if status.get('activeTurns'):raise RuntimeError('Finish or stop active '+label+' tasks before maintenance. Nothing was cancelled.')
        if desktop:
            start=identity(desktop['pid']);desktop_call('shutdown');wait_exit(desktop['pid'],start)
        if ui:
            start=identity(ui['pid'])
            if not ui_call('maintenance.close').get('accepted'):
                raise RuntimeError('The app became busy. Nothing was cancelled.')
            wait_exit(ui['pid'],start)
        for connection,status in runtimes:
            start=identity(status['pid']);connection.call('host.shutdown');wait_exit(status['pid'],start)
    finally:
        for connection,_ in runtimes:connection.close()
    if component=='all':
        stop_companions()


def backup(include_data=True):
    state=location('STATE','.local/state');data=location('DATA','.local/share');config=location('CONFIG','.config')
    destination=state/'augmentor-release-backups'/(time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
    destination.mkdir(parents=True,mode=0o700)
    sources=[(Path(os.environ.get('AUGMENTOR_PI_CONFIG',config/'augmentor-pi')),'config/pi'),(config/'augmentor-linux','config/dsh'),
             (Path(os.environ.get('AUGMENTOR_SHARED_CONFIG',config/'augmentor')),'config/shared'),
             (Path(os.environ.get('AUGMENTOR_PI_STATE',state/'augmentor-pi')),'state/pi'),(state/'augmentor-linux','state/dsh'),(Path(os.environ.get('AUGMENTOR_OPENCODE_STATE',state/'augmentor-opencode')),'state/opencode'),
             (Path(os.environ.get('AUGMENTOR_SHARED_DATA',data/'augmentor')),'data/shared'),(Path(os.environ.get('AUGMENTOR_SHARED_STATE',state/'augmentor')),'state/shared')]
    for path,name in sources if include_data else []:
        if path.exists():
            shutil.copytree(path,destination/name,symlinks=True,ignore=lambda folder,names:[n for n in names if (Path(folder)/n).is_socket()])
    (destination/'release.json').write_text((ROOT/'release/product.json').read_text())
    return destination


def owned_integrations(component):
    data=location('DATA','.local/share');config=location('CONFIG','.config')
    result=[];conflicts=[]
    for identity_name in ('com.augmentor.Agent.desktop','com.augmentor.LinuxPi.desktop'):
        for folder in ('applications','kglobalaccel'):
            path=data/folder/identity_name
            if not path.exists() and not path.is_symlink():continue
            if path.is_symlink():conflicts.append(str(path));continue
            text=path.read_text()
            executable=next((line[5:] for line in text.splitlines() if line.startswith('Exec=')),'')
            legacy=str(data/'augmentor-pi/app/scripts/augmentor-linux')
            if 'Copyright © 2026 Manolo Remiddi' in text and executable in ('augmentor-agent','/usr/bin/augmentor-agent',legacy,'"'+legacy+'"'):
                result.append(path)
            else:conflicts.append(str(path))
    if component=='all':
        for browser in ('chromium','google-chrome','google-chrome-beta','BraveSoftware/Brave-Browser'):
            path=config/browser/'NativeMessagingHosts/com.augmentor.agent.json'
            if not path.exists() and not path.is_symlink():continue
            try:
                value=json.loads(path.read_text())
                expected=json.loads(Path('/etc/chromium/native-messaging-hosts/com.augmentor.agent.json').read_text())
                allowed_paths={'/usr/bin/augmentor-browser-host',str(ROOT/'scripts/augmentor-browser-host'),str(data/'augmentor-pi/app/scripts/augmentor-browser-host')}
                if path.is_symlink() or value.get('name')!=expected['name'] or value.get('allowed_origins')!=expected['allowed_origins'] or value.get('path') not in allowed_paths:
                    raise ValueError('Different native host registration')
                result.append(path)
            except (OSError,ValueError):conflicts.append(str(path))
    if conflicts:
        raise RuntimeError('These integrations differ from Augmentor-owned files; no integrations were changed: '+', '.join(conflicts))
    return result


def remove_integrations(component,destination):
    paths=owned_integrations(component)
    copies=destination/'integrations';copies.mkdir(mode=0o700)
    record=[]
    for n,path in enumerate(paths):
        name=str(n);shutil.copy2(path,copies/name)
        record.append({'path':str(path),'backup':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    (copies/'manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    # Clear only our KDE components. An unavailable session bus leaves no active
    # binding; remove persisted sections so the next login cannot restore them.
    kde=location('CONFIG','.config')/'kglobalshortcutsrc'
    identities={path.name for path in paths if path.suffix=='.desktop'}
    if kde.exists() and not kde.is_symlink():
        shutil.copy2(kde,copies/'kglobalshortcutsrc')
        lines=[];skip=False
        for line in kde.read_text().splitlines(keepends=True):
            if line.startswith('['):skip=line.strip().strip('[]') in identities
            if not skip:lines.append(line)
        temporary=kde.with_name(kde.name+'.augmentor-'+uuid.uuid4().hex)
        temporary.write_text(''.join(lines));temporary.chmod(kde.stat().st_mode & 0o777);temporary.replace(kde)
    for name in identities:
        try:
            subprocess.run(['gdbus','call','--session','--dest','org.kde.kglobalaccel','--object-path','/kglobalaccel','--method','org.kde.KGlobalAccel.setShortcut',f"['{name}','_launch','Augmentor Agent','Show or hide Augmentor Agent']",'[]','6'],capture_output=True,timeout=5,check=False)
        except (FileNotFoundError,subprocess.TimeoutExpired):pass
    for path in paths:path.unlink()
    return [str(path) for path in paths]


def migrate_integrations(destination):
    """Replace only recognized legacy entrypoints; retain the actual legacy app."""
    paths=owned_integrations('all')
    data=location('DATA','.local/share')
    old_name='com.augmentor.LinuxPi.desktop';new_name='com.augmentor.Agent.desktop'
    old=[path for path in paths if path.name==old_name]
    canonical=[path for path in paths if path.name==new_name]
    shortcut=None
    for path in old:
        shortcut=next((line.split('=',1)[1] for line in path.read_text().splitlines() if line.startswith('X-KDE-Shortcuts=')),shortcut)
    copies=destination/'migration';copies.mkdir(mode=0o700)
    record=[]
    targets=list(paths)+[data/place/new_name for place in ('applications','kglobalaccel') if old and not canonical]
    originals={path:(path.read_bytes(),path.stat().st_mode & 0o777) if path.exists() else None for path in targets}
    for n,(path,value) in enumerate(originals.items()):
        if value is not None:(copies/str(n)).write_bytes(value[0])
        record.append({'path':str(path),'backup':str(n) if value is not None else None})
    (copies/'manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    live=False
    try:
        if old and not canonical:
            template=Path('/usr/share/applications/com.augmentor.Agent.desktop').read_text()
            for place in ('applications','kglobalaccel'):
                path=data/place/new_name;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(template+('X-KDE-Shortcuts='+shortcut+'\n' if shortcut else ''));path.chmod(0o744)
        if old:
            from augmentor_linux.shortcuts import call
            old_action=f"['{old_name}','_launch','Augmentor Agent','Show or hide Augmentor Agent']"
            try:call('shortcut',old_action);live=True
            except (RuntimeError,FileNotFoundError):pass
            if live:
                call('setShortcut',old_action,'[]','6')
                if shortcut and not canonical:
                    from PySide6.QtGui import QKeySequence
                    from augmentor_linux.shortcuts import save_shortcut
                    save_shortcut(QKeySequence(shortcut))
            for path in old:path.unlink()
        for path in paths:
            if path.suffix=='.json':
                value=json.loads(path.read_text());value['path']='/usr/bin/augmentor-browser-host'
                temporary=path.with_name(path.name+'.augmentor-'+uuid.uuid4().hex)
                temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.chmod(0o600);temporary.replace(path)
    except Exception:
        for path,value in originals.items():
            if value is None:path.unlink(missing_ok=True)
            else:path.write_bytes(value[0]);path.chmod(value[1])
        if live and shortcut:
            from PySide6.QtGui import QKeySequence
            call('setShortcut',old_action,str([QKeySequence(shortcut)[0].toCombined()]),'6')
        raise
    return {'legacyAppPreserved':True,'shortcutMigrated':bool(old and shortcut and not canonical),'shortcutActiveInThisLogin':live,'nativeHostRegistrations':sum(p.suffix=='.json' for p in paths)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','status','migrate','diagnostics'])
    parser.add_argument('--output',type=Path,help='Save a metadata-only diagnostics report as a new private file.')
    parser.add_argument('--component',choices=['desktop','all'],default='all')
    parser.add_argument('--remove',action='store_true',help='Back up and remove owned per-user launchers/shortcuts; all also removes browser registrations.')
    args=parser.parse_args()
    if os.getuid()==0:raise SystemExit('Run this command as your ordinary desktop user, not root.')
    os.umask(0o077)
    try:
        if args.action=='diagnostics':
            sys.path.insert(0,str(ROOT/'services'))
            from support.report import report
            value=json.dumps(report(),indent=2)+'\n'
            if args.output:
                with args.output.open('x') as file:file.write(value)
            else:print(value,end='')
            return
        if args.action=='status':
            print(json.dumps({'ui':ui_call('maintenance.status'),'browserProcesses':browser_processes(),'prompts':prompt_call(),'memory':memory_call(),'desktop':desktop_call('status')}));return
        if args.remove or args.action=='migrate':owned_integrations(args.component) # Conflict check before stopping.
        prepare(args.component)
        destination=backup(args.component=='all')
        if args.action=='migrate':
            if args.component!='all':raise RuntimeError('Migration requires all components to be idle.')
            print(json.dumps({'migrated':migrate_integrations(destination),'backup':str(destination)}));return
        removed=remove_integrations(args.component,destination) if args.remove else []
        print(json.dumps({'prepared':True,'backup':str(destination),'removedIntegrations':removed,'dataPreserved':True}))
    except (OSError,RuntimeError) as error:
        raise SystemExit(str(error))


if __name__=='__main__':main()
