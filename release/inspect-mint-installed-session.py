#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Read the stock, installed Mint22.3 Cinnamon X11 fixture after normal login.

No app is installed or enabled. Authentication through the actual UI is recorded
separately by the owned VM driver; this inspector does not authenticate or unlock.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess


def output(args):return subprocess.check_output(args,text=True,timeout=30).strip()


def main():
    assert os.geteuid()==1000 and os.environ.get('USER')=='augmentor-proof'
    assert output(['hostname'])=='augmentor-mint223-iso' and output(['systemd-detect-virt'])=='qemu'
    assert Path('/etc/augmentor-test-vm').read_text()=='Isolated Augmentor Linux Mint 22.3 Cinnamon ISO qualification VM\n'
    fields=dict(row.split('=',1) for row in Path('/etc/os-release').read_text().splitlines() if '=' in row)
    assert fields['ID'].strip('"')=='linuxmint' and fields['VERSION_ID'].strip('"')=='22.3'
    assert not Path('/usr/lib/augmentor').exists()
    mount=output(['findmnt','--target','/','--noheadings','--output','SOURCE,FSTYPE'])
    assert mount=='/dev/vda2 ext4'
    assert all(word not in Path('/proc/mounts').read_text() for word in ('iso9660','squashfs'))
    assert 'boot=casper' not in Path('/proc/cmdline').read_text()
    sessions=[]
    for row in output(['loginctl','list-sessions','--no-legend']).splitlines():
        columns=row.split()
        if len(columns)>3 and columns[1]=='1000' and columns[3]=='seat0':
            values=dict(line.split('=',1) for line in output(['loginctl','show-session',columns[0],'-p','Type','-p','Class','-p','State','-p','Active','-p','Seat','-p','LockedHint']).splitlines())
            sessions.append(values)
    assert sessions==[{'Type':'x11','Class':'user','State':'active','Active':'yes','Seat':'seat0','LockedHint':'no'}]
    environment=dict(row.split('=',1) for row in output(['systemctl','--user','show-environment']).splitlines() if '=' in row)
    assert environment['XDG_CURRENT_DESKTOP']=='X-Cinnamon' and environment['DISPLAY']==':0'
    for key in ('DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','XDG_SESSION_TYPE','XDG_CURRENT_DESKTOP','DBUS_SESSION_BUS_ADDRESS'):
        if key in environment:os.environ[key]=environment[key]
    from gi.repository import Gio,GLib
    source=Gio.SettingsSchemaSource.get_default()
    parent=source.lookup('org.cinnamon.desktop.keybindings',True)
    custom=source.lookup('org.cinnamon.desktop.keybindings.custom-keybinding',True)
    assert parent and custom
    assert parent.get_key('custom-list').get_value_type().dup_string()=='as'
    for name in ('name','command'):assert custom.get_key(name).get_value_type().dup_string()=='s'
    assert custom.get_key('binding').get_value_type().dup_string()=='as'
    bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
    def owner():
        return bus.call_sync('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus',
            'GetNameOwner',GLib.Variant('(s)',('org.cinnamon.ScreenSaver',)),
            GLib.VariantType.new('(s)'),Gio.DBusCallFlags.NONE,3000,None).unpack()[0]
    screensaver_owner=owner();assert screensaver_owner.startswith(':')
    active=bus.call_sync(screensaver_owner,'/org/cinnamon/ScreenSaver','org.cinnamon.ScreenSaver',
        'GetActive',None,GLib.VariantType.new('(b)'),Gio.DBusCallFlags.NONE,3000,None).unpack()[0]
    assert owner()==screensaver_owner and active is False, 'Cinnamon ScreenSaver is active or its owner changed.'
    groups=output(['id','-nG']).split();assert 'nopasswdlogin' not in groups
    status=output(['sudo','passwd','-S','augmentor-proof']).split();assert status[0:2]==['augmentor-proof','P']
    assert Path('/sys/module/apparmor/parameters/enabled').read_text().strip()=='Y'
    package_args=['dpkg-query','-W','cinnamon','muffin','cinnamon-screensaver','base-files','openssh-server']
    versions=dict(line.split('\t',1) for line in output(package_args).splitlines())
    assert versions['cinnamon']=='6.6.4+zena' and versions['muffin']=='6.6.1+zena' and versions['cinnamon-screensaver']=='6.6.1+zena'
    assert output(['dpkg','-V','cinnamon','muffin','cinnamon-screensaver'])==''
    pam=Path('/etc/pam.d/cinnamon-screensaver')
    assert '@include common-auth' in pam.read_text()
    protected=output(['sudo','/usr/bin/python3','-I','-c',
        "import hashlib,json;from pathlib import Path;root=Path('/var/log/augmentor-fixture-installed'); assert Path('/etc/augmentor-test-vm').read_text()=='Isolated Augmentor Linux Mint 22.3 Cinnamon ISO qualification VM\\n'; print(json.dumps({str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and not p.is_symlink()}))"])
    fingerprints=json.loads(protected);assert 'before-ssh.txt' in fingerprints and 'after-ssh.txt' in fingerprints
    assert any(name.startswith('installer-preserved/') for name in fingerprints)
    report={'format':'augmentor-mint-installed-cinnamon-session-inspection/1','target':'linuxmint22.3-x86_64',
        'realInstalledX11SessionTested':True,'graphicalSessions':sessions,'installedPackages':versions,
        'isoNotMounted':True,'notLiveCasperSession':True,'rootMount':mount,'apparmorKernelEnabled':True,
        'actualCinnamonShortcutSchema':{'custom-list':'as','name':'s','command':'s','binding':'as'},
        'usablePasswordAccountVerified':True,'nopasswdloginGroupAbsent':True,'installedPamCommonAuthVerified':True,
        'unchangedCinnamonPackageFilesVerified':True,'baselineAndInstallerLogFingerprints':fingerprints,
        'actualScreenSaverOwnerVerified':True,'screenSaverActive':active,
        'inspectionSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'bootId':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'applicationInstalled':False,'passwordUnlockTested':False,'shortcutDeliveryTested':False,
        'observerTested':False,'inputToolsEnabled':False,'visibleStopTested':False,'browserTested':False,
        'physicalAudioTested':False,'publicReleaseQualified':False,'ownerStateChanged':False}
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
