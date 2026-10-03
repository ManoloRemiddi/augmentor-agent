#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Read the real Leap GNOME48 session and independently installed observer.

This source-only proof requires no Augmentor application package and cannot
establish shortcut delivery, consent, input, Stop, harness or speech acceptance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def output(command):return subprocess.check_output(command,text=True,timeout=30).strip()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--source-ref',required=True)
    args=parser.parse_args()
    assert os.geteuid()==1000 and os.environ.get('USER')=='augmentor-proof'
    assert output(['hostname'])=='augmentor-gnome-leap16' and output(['systemd-detect-virt'])=='qemu'
    assert Path('/etc/augmentor-test-vm').read_text()=='Isolated Augmentor openSUSE Leap 16.0 GNOME qualification VM\n'
    assert Path('/sys/fs/selinux/enforce').read_text().strip()=='1'
    fields=dict(row.split('=',1) for row in Path('/etc/os-release').read_text().splitlines() if '=' in row)
    assert fields['ID'].strip('"')=='opensuse-leap' and fields['VERSION_ID'].strip('"')=='16.0'
    assert re.fullmatch('[a-f0-9]{40}',args.source_ref)
    root=args.source_root.resolve();assert root.is_relative_to(Path.home())
    provenance=json.loads((Path.home()/'observer-source.json').read_text())
    assert provenance['source']=={'commit':args.source_ref,'dirty':False}
    assert not Path('/usr/lib/augmentor/release.json').exists()
    environment=dict(row.split('=',1) for row in output(['systemctl','--user','show-environment']).splitlines() if '=' in row)
    assert environment['XDG_SESSION_TYPE']=='wayland' and environment['XDG_CURRENT_DESKTOP']=='GNOME'
    for key in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','XDG_SESSION_TYPE','XDG_CURRENT_DESKTOP','DBUS_SESSION_BUS_ADDRESS'):
        if key in environment:os.environ[key]=environment[key]
    sessions=[]
    for row in output(['loginctl','list-sessions','--no-legend']).splitlines():
        columns=row.split()
        if len(columns)>3 and columns[1]==str(os.getuid()) and columns[3]=='seat0':
            properties=dict(line.split('=',1) for line in output(['loginctl','show-session',columns[0],'-p','Type','-p','Class','-p','State','-p','Active','-p','Seat']).splitlines())
            sessions.append(properties)
    assert sessions==[{'Type':'wayland','Class':'user','State':'active','Active':'yes','Seat':'seat0'}]
    uuid='observer@augmentoragent.com';source=root/'services/desktop/gnome-extension'/uuid
    installed=Path.home()/'.local/share/gnome-shell/extensions'/uuid
    hashes={}
    for name in ('extension.js','metadata.json'):
        assert (source/name).read_bytes()==(installed/name).read_bytes()
        hashes[name]=hashlib.sha256((installed/name).read_bytes()).hexdigest()
    sys.path.insert(0,str(root/'services/desktop'))
    from gnome import GnomeObserver
    from gnome_shortcuts import NativeShortcuts
    from gi.repository import Gio
    bus=Gio.bus_get_sync(Gio.BusType.SESSION,None);observer=GnomeObserver(bus);scene=observer.read()
    assert scene['shellVersion']=='48.4' and scene['inputQualified'] is False
    assert scene['guards']['sessionMode']=='user' and not scene['guards']['locked'] and not scene['guards']['greeter']
    assert scene['guards']['screenShieldAvailable'] is True
    native=NativeShortcuts();assert native.fields==('name','binding','command','enable-in-lockscreen') and native.portal_available
    extensions=bus.call_sync('org.gnome.Shell','/org/gnome/Shell','org.gnome.Shell.Extensions','ListExtensions',None,None,Gio.DBusCallFlags.NO_AUTO_START,3000,None).unpack()[0]
    assert extensions[uuid]['state']==1
    packages=output(['rpm','-q','gnome-shell','mutter','gnome-settings-daemon','gdm','xdg-desktop-portal','xdg-desktop-portal-gnome','python313-pyside6','python313-gst'])
    report={'format':'augmentor-leap-gnome48-source-session-inspection/1','target':'opensuse-leap16.0-x86_64',
            'source':provenance['source'],'realWaylandSessionTested':True,'graphicalSessions':sessions,
            'selinuxEnforcing':True,'observerInstalledSourceMatches':True,'observerSourceSha256':hashes,
            'observerOwner':observer.owner,'observerEpoch':observer.epoch,'scene':scene,'observerExtensionState':extensions[uuid]['state'],
            'actualShortcutProfile':{'fields':list(native.fields),'savedPortalSchemasAvailable':native.portal_available,'functionalTested':False},
            'installedPackages':packages.splitlines(),'inspectionSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'readerSourceSha256':{name:hashlib.sha256((root/'services/desktop'/name).read_bytes()).hexdigest() for name in ('gnome.py','gnome_shortcuts.py')},
            'applicationPackageInstalled':False,'standardDesktopInstallerTested':False,'shortcutDeliveryTested':False,
            'lockRecoveryTested':False,'passwordAuthenticationTested':False,'inputToolsEnabled':False,'visibleStopTested':False,
            'harnessConnectionTested':False,'physicalAudioTested':False,'fullDistroReleaseQualified':False}
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
