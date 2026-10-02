#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Read-only canonical startup/observer inspection in the marked Noble guest.

This cannot prove a connected task, shortcut delivery, consent or desktop input.
Run as the dedicated SSH user after fixture provisioning has completed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys


def output(command,timeout=30):
    return subprocess.check_output(command,text=True,timeout=timeout).strip()


def properties(command):
    return dict(line.split('=',1) for line in output(command).splitlines() if '=' in line)


def main():
    marker=Path('/etc/augmentor-test-vm')
    if (os.geteuid()==0 or os.environ.get('USER')!='augmentor-proof' or not marker.is_file() or
            marker.read_text()!='Isolated Augmentor Ubuntu 24.04 GNOME qualification VM\n' or
            output(['systemd-detect-virt'])!='qemu'):
        raise ValueError('Read only the marked Noble guest as its dedicated ordinary user.')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True)
    parser.add_argument('--session-type',choices=('wayland','x11'),default='wayland');args=parser.parse_args()
    if not re.fullmatch('[a-f0-9]{40}',args.source):raise ValueError('Supply the exact clean installed source identity.')
    data=Path.home()/'.local/share/augmentor'
    selection=json.loads((data/'desktop.json').read_text())
    root=Path(selection['root']);managed=False
    if root!=Path('/usr/lib/augmentor'):
        assert root.is_relative_to(data/'releases') and selection['sourceRef']==args.source
        spec=importlib.util.spec_from_file_location('inspection_deployment',data/'desktop-deployment.py')
        deployment=importlib.util.module_from_spec(spec);spec.loader.exec_module(deployment)
        manifest=deployment.verify(root)
        assert manifest['artifactSha256']==selection['artifactSha256']
        managed=True
    release=json.loads((root/'release.json').read_text())
    assert release['target']=='ubuntu24.04-amd64' and release['source']=={'commit':args.source,'dirty':False}
    assert not output(['dpkg','--verify','augmentor-runtime','augmentor-desktop'])
    assert Path('/sys/module/apparmor/parameters/enabled').read_text().strip()=='Y'
    assert output(['systemctl','is-active','apparmor'])=='active'
    assert selection['root']==str(root)
    spec=importlib.util.spec_from_file_location('noble_python',root/'scripts/linux-python-runtime.py')
    runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
    assert runtime.resolve(root,selection['python'])==selection['python']
    environment=properties(['systemctl','--user','show-environment'])
    assert environment['XDG_CURRENT_DESKTOP']=='ubuntu:GNOME' and environment['XDG_SESSION_TYPE']==args.session_type
    for key in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','XDG_CURRENT_DESKTOP','XDG_RUNTIME_DIR','XDG_SESSION_TYPE','DBUS_SESSION_BUS_ADDRESS'):
        if key in environment:os.environ[key]=environment[key]
    sessions=[]
    for row in output(['loginctl','list-sessions','--no-legend']).splitlines():
        fields=row.split()
        if len(fields)>3 and fields[1]==str(os.getuid()) and fields[3]=='seat0':
            sessions.append(properties(['loginctl','show-session',fields[0],'-p','Type','-p','Class','-p','State','-p','Active','-p','Seat']))
    assert sessions==[{'Type':args.session_type,'Class':'user','State':'active','Active':'yes','Seat':'seat0'}]
    service=properties(['systemctl','--user','show','augmentor-desktop.service','-p','ActiveState','-p','SubState','-p','MainPID'])
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
        client.settimeout(10);client.connect(str(Path(environment['XDG_RUNTIME_DIR'])/'augmentor-linux-pi.sock'))
        client.sendall(b'maintenance.status')
        with client.makefile('rb') as stream:desktop=json.loads(stream.readline(16384))
    assert service['ActiveState']=='active' and service['SubState']=='running'
    assert int(service['MainPID'])==desktop['pid'] and desktop['buildRoot']==str(root)
    arguments=(Path('/proc')/str(desktop['pid'])/'cmdline').read_bytes().split(b'\0')
    assert b'--ensure-running' in arguments and b'--preview' not in arguments
    sys.path.insert(0,str(root/'services/desktop'))
    from gnome import GnomeObserver
    from gi.repository import Gio
    bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
    scene=GnomeObserver(bus).read()
    assert scene['guards']['sessionMode']=='ubuntu' and scene['guards']['parentSessionMode']=='user'
    assert scene['guards']['screenShieldAvailable'] is True and scene['inputQualified'] is False
    from gnome_shortcuts import NativeShortcuts
    shortcuts=NativeShortcuts()
    assert shortcuts.fields==('name','binding','command') and shortcuts.portal_available is False
    extensions=bus.call_sync('org.gnome.Shell','/org/gnome/Shell','org.gnome.Shell.Extensions',
                            'ListExtensions',None,None,Gio.DBusCallFlags.NO_AUTO_START,3000,None).unpack()[0]
    required=('ubuntu-dock@ubuntu.com','ubuntu-appindicators@ubuntu.com','ding@rastersoft.com',
              'tiling-assistant@ubuntu.com','observer@augmentoragent.com')
    assert all(extensions.get(uuid,{}).get('state')==1 for uuid in required)
    packages=output(['dpkg-query','-W','-f=${Package}\t${Version}\n','ubuntu-desktop-minimal','ubuntu-session',
                    'gdm3','gnome-shell','libmutter-14-0','gnome-settings-daemon','xdg-desktop-portal','xdg-desktop-portal-gnome'])
    report={'format':'augmentor-noble-gnome-full-vm-inspection/1','target':release['target'],'source':release['source'],
            'version':release['version'],'sessionType':args.session_type,'waylandSessionTested':args.session_type=='wayland',
            'selection':selection,'pythonRuntimeVerified':True,'packageVerified':True,
            'apparmorEnabled':True,'apparmorServiceActive':True,'graphicalSessions':sessions,'service':service,
            'desktop':desktop,'scene':scene,'ubuntuDefaultExtensionsActive':{uuid:extensions[uuid]['state'] for uuid in required},
            'shortcutProfile':{'fields':list(shortcuts.fields),'savedPortalSchemasAvailable':shortcuts.portal_available,
                               'functionalTested':False},'installedPackages':packages.splitlines(),
            'inspectionSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'canonicalSelection':True,'managedInventoryVerified':managed,'serviceOwnsActualApplication':True,'previewLaunch':False,
            'focusedWindowTested':False,'harnessConnectionTested':False,'modelTurnTested':False,
            'shortcutDeliveryTested':False,'lockRecoveryTested':False,'gnomeInputToolsEnabled':False,
            'standardDesktopInstallerTested':False,'physicalAudioTested':False}
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
