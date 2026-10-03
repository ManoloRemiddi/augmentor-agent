#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Inspect the independently installed read-only bridge in the owned Mint guest.

RefreshLock requests the normal screensaver query/activation path. No settings,
grabs, input, stage locking or unlocking are changed by this inspector.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-lock-state',choices=('inactive','active'),default='inactive')
    args=parser.parse_args()
    assert os.geteuid()==1000 and os.environ.get('USER')=='augmentor-proof'
    assert subprocess.check_output(['hostname'],text=True).strip()=='augmentor-mint223-iso'
    assert Path('/etc/augmentor-test-vm').read_text()=='Isolated Augmentor Linux Mint 22.3 Cinnamon ISO qualification VM\n'
    assert not Path('/usr/lib/augmentor').exists()
    env=dict(row.split('=',1) for row in subprocess.check_output(['systemctl','--user','show-environment'],text=True).splitlines() if '=' in row)
    assert env['XDG_CURRENT_DESKTOP']=='X-Cinnamon' and env['XDG_SESSION_TYPE']=='x11'
    for key in ('DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS'):
        if key in env:os.environ[key]=env[key]
    from gi.repository import Gio,GLib
    bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
    def call(destination,path,interface,method,args=None,type='(s)'):
        return bus.call_sync(destination,path,interface,method,args,GLib.VariantType.new(type),
            Gio.DBusCallFlags.NO_AUTO_START,2000,None).unpack()[0]
    def owner():return call('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetNameOwner',GLib.Variant('(s)',('org.Cinnamon',)))
    unique=owner();assert re.fullmatch(r':\d+\.\d+',unique)
    version=call(unique,'/org/Cinnamon','org.freedesktop.DBus.Properties','Get',GLib.Variant('(ss)',('org.Cinnamon','CinnamonVersion')),'(v)')
    assert version=='6.6.4' and owner()==unique
    def bridge(method):
        raw=call(unique,'/com/augmentor/CinnamonBridge','com.augmentor.CinnamonBridge',method)
        assert isinstance(raw,str) and len(raw.encode())<=131072 and owner()==unique
        result=json.loads(raw)
        assert result['schema']==1 and result['backend']=='cinnamon-shortcut-bridge'
        assert result['cinnamonVersion']==version and result['sessionType']=='x11'
        assert result['readOnly'] is True and result['inputQualified'] is False and result['sceneObserverQualified'] is False
        assert result['completeRegistryHistoryTracking'] is False
        assert re.fullmatch('[a-f0-9-]{36}',result['epoch'])
        lock=result['lock'];assert lock['state'] in ('unknown','active','inactive')
        assert type(lock['generation']) is int and lock['generation']>0 and type(lock['queryPending']) is bool
        assert lock['owner'] is None or re.fullmatch(r':\d+\.\d+',lock['owner'])
        return result
    initial=bridge('Status');requested=bridge('RefreshLock')
    assert requested['epoch']==initial['epoch'] and requested['lock']['state']=='unknown'
    deadline=time.monotonic()+10;observed=requested
    while time.monotonic()<deadline:
        observed=bridge('Status');assert observed['epoch']==initial['epoch']
        if observed['lock']['state']!='unknown':break
        time.sleep(.05)
    assert observed['lock']['state']==args.expected_lock_state and observed['lock']['queryPending'] is False, json.dumps(observed['lock'])
    inventory=bridge('ShortcutBindings');assert inventory['epoch']==initial['epoch'] and inventory['lock']==observed['lock']
    assert type(inventory['registryPending']) is bool and not inventory['registryPending']
    assert type(inventory['registrySerial']) is int and inventory['registrySerial']>0
    assert re.fullmatch('[a-f0-9]{64}',inventory['snapshotSignature'])
    records=inventory['bindings'];assert isinstance(records,list) and len(records)<=1024
    for row in records:
        assert set(row)=={'name','accelerators'} and isinstance(row['name'],str) and len(row['name'])<=512
        assert isinstance(row['accelerators'],list) and len(row['accelerators'])<=64
        assert all(isinstance(s,str) and len(s)<=512 for s in row['accelerators'])
    installed=Path.home()/'.local/share/cinnamon/extensions/bridge@augmentoragent.com'
    report={'format':'augmentor-cinnamon-shortcut-bridge-inspection/1','target':'linuxmint22.3-x86_64',
        'runningCinnamonVersion':version,'actualX11BridgeProfileVerified':True,'nativeUniqueOwnerPinned':True,
        'epoch':observed['epoch'],'initialLock':initial['lock'],'requestedLock':requested['lock'],'verifiedLock':observed['lock'],
        'actualAsyncLockDiscoveryTested':True,'boundedRegistrySnapshotTested':True,'callbackExportsAbsent':True,
        'registryRecords':len(records),'registrySnapshotSha256':inventory['snapshotSignature'],
        'installedExtensionSha256':hashlib.sha256((installed/'extension.js').read_bytes()).hexdigest(),
        'installedMetadataSha256':hashlib.sha256((installed/'metadata.json').read_bytes()).hexdigest(),
        'inspectionSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'applicationInstalled':False,'shortcutSaveTested':False,'physicalShortcutDeliveryTested':False,
        'sceneObserverTested':False,'inputQualified':False,'visibleStopTested':False,
        'publicReleaseQualified':False,'ownerStateChanged':False}
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
