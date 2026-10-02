#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Kill shortcut workers only in the marked Mint VM with its synthetic launcher.

No application is installed, no keyboard events are sent and no lock is changed.
This proves native settings/ownership recovery, not complete product acceptance.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child',choices=('intent','fields','registered','committed'))
    parser.add_argument('--instance',choices=('main','secondary'),default='main')
    args=parser.parse_args()
    assert os.geteuid()==1000 and os.environ.get('USER')=='augmentor-proof'
    assert subprocess.check_output(['hostname'],text=True).strip()=='augmentor-mint223-iso'
    assert Path('/etc/augmentor-test-vm').read_text()=='Isolated Augmentor Linux Mint 22.3 Cinnamon ISO qualification VM\n'
    assert not Path('/usr/lib/augmentor').exists()
    launcher=Path.home()/'.local/bin/augmentor-agent'
    assert hashlib.sha256(launcher.read_bytes()).hexdigest()=='381452671cdd64f8ed7cddd933279a99b9c265d250ef694acd7595643d0df849'
    env=dict(row.split('=',1) for row in subprocess.check_output(['systemctl','--user','show-environment'],text=True).splitlines() if '=' in row)
    assert env['XDG_CURRENT_DESKTOP']=='X-Cinnamon' and env['XDG_SESSION_TYPE']=='x11'
    os.environ.update(env)
    helper=Path.home()/'cinnamon-shortcuts-proof/cinnamon_shortcuts.py'
    spec=importlib.util.spec_from_file_location('owned_cinnamon_helper',helper)
    c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
    b=c.NativeShortcuts()
    request={'key':{'symbol':'F12'},'modifiers':['Control','Super']}
    phases={'intent':71,'fields':72,'registered':73,'committed':74}
    if args.child:
        original=b.persist
        def persist(value,path=None):
            if path is None and args.child=='registered':os._exit(73)
            original(value,path)
            if path==b.pending_path and args.child=='intent':os._exit(71)
            if path is None and args.child=='committed':os._exit(74)
        b.persist=persist
        if args.child=='fields':
            class Parent:
                def __init__(self,settings):self.settings=settings
                def __getattr__(self,key):return getattr(self.settings,key)
                def set_strv(self,*_args):os._exit(72)
            b.parent=Parent(b.parent)
        b.save(args.instance,request)
        raise AssertionError('Interruption point was not reached.')
    assert b.pending() is None
    original_mapping=b.mapping();assert set(original_mapping['instances'])=={'main','secondary'}
    assert original_mapping['instances']['main']['binding']==['<Primary><Super>F9']
    assert original_mapping['instances']['secondary']['binding']==['<Primary><Super>F10']
    def fresh():
        # This is a proof driver with long-lived native objects. The actual
        # production frontend uses a fresh helper process for every operation.
        context=b.GLib.MainContext.default()
        deadline=time.monotonic()+.2
        while context.pending() and time.monotonic()<deadline:context.iteration(False)
        return c.NativeShortcuts()
    def snapshot(native):
        return {'mapping':native.mapping(),'ids':[v for v in native.parent.get_strv('custom-list') if v!='__dummy__'],
            'rows':{name:{'effective':native.values(native.custom(row['id'])),'user':native.user_values(native.custom(row['id']))}
                for name,row in native.mapping()['instances'].items()}}
    baseline=snapshot(b)
    report={'format':'augmentor-cinnamon-shortcut-interruption-proof/1','target':'linuxmint22.3-x86_64',
        'helperSha256':hashlib.sha256(helper.read_bytes()).hexdigest(),'driverSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'checks':[],'syntheticLauncherOnly':True,'applicationInstalled':False,'physicalShortcutDeliveryTested':False,
        'inputQualified':False,'sceneObserverTested':False,'publicReleaseQualified':False,'ownerStateChanged':False}
    for phase,code in phases.items():
        result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--child',phase],capture_output=True,text=True,timeout=25)
        assert result.returncode==code,(phase,result.returncode,result.stderr)
        b=fresh();intent=b.pending();assert intent is not None
        try:b.read('main');raise AssertionError('Pending Save was reported as configured.')
        except RuntimeError as error:assert 'interrupted' in str(error)
        with c.locked():b.recover_pending()
        b=fresh();assert b.pending() is None
        if phase=='committed':
            assert b.mapping()['instances']['main']['binding']==['<Primary><Super>F12']
            assert b.read('main')['configured']
            b.save('main',{'key':{'symbol':'F9'},'modifiers':['Control','Super']})
        assert snapshot(fresh())==baseline
        report['checks'].append({'phase':phase,'actualAbruptExit':code,'pendingReadRefused':True,'nativeOwnedRecoveryVerified':True})
    # Repeat registration interruption while allocating a new numeric row.
    # Remove only this fixture's verified secondary row and then recreate it.
    b=fresh();secondary=original_mapping['instances']['secondary'];entry=b.owned(secondary)
    with c.locked():
        ids=b.parent.get_strv('custom-list');assert secondary['id'] in ids
        assert b.parent.set_strv('custom-list',[id for id in ids if id!=secondary['id']])
        entry.delay()
        for key in c.FIELDS:entry.reset(key)
        entry.apply();b.Gio.Settings.sync()
        reduced=json.loads(json.dumps(original_mapping));del reduced['instances']['secondary'];b.persist(reduced)
    result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--child','registered','--instance','secondary'],capture_output=True,text=True,timeout=25)
    assert result.returncode==73,(result.returncode,result.stderr)
    b=fresh();intent=b.pending();assert intent['added'] is True
    allocated=intent['afterMapping']['instances']['secondary']['id']
    with c.locked():b.recover_pending()
    b=fresh();assert b.mapping()==reduced and allocated not in b.parent.get_strv('custom-list')
    assert all(value is None for value in b.user_values(b.custom(allocated)).values())
    b.save('secondary',{'key':{'symbol':'F10'},'modifiers':['Control','Super']})
    assert snapshot(fresh())==baseline
    report['checks'].append({'phase':'new-row-registration','actualAbruptExit':73,'unregisteredRowRemoved':True,'defaultUserValuesRestored':True,'fixtureThenRecreated':True})
    # A changed field after a real interrupted native write must remain foreign.
    result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--child','fields'],capture_output=True,text=True,timeout=25)
    assert result.returncode==72
    b=fresh();intent=b.pending();row=intent['afterMapping']['instances']['main'];entry=b.custom(row['id'])
    assert entry.set_string('name','Synthetic foreign takeover after interruption');b.Gio.Settings.sync()
    try:
        with c.locked():b.recover_pending()
        raise AssertionError('Foreign takeover was overwritten.')
    except RuntimeError as error:assert 'outside Augmentor' in str(error)
    assert entry.get_string('name')=='Synthetic foreign takeover after interruption' and b.pending()==intent
    assert entry.set_string('name',row['name']);b.Gio.Settings.sync()
    with c.locked():b.recover_pending()
    assert snapshot(fresh())==baseline
    report['checks'].append({'phase':'foreign-after-interruption','foreignFieldPreserved':True,'intentRetained':True,'fixtureThenRecovered':True})
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
