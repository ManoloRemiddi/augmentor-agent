#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bounded guest actions for the marked Noble shortcut qualification fixture.

This does not synthesize compositor input. The host proof sends keys through
the owned virtual machine's QMP keyboard and observes the production app.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time

ROOT = Path('/usr/lib/augmentor')
STATE = Path.home()/'noble-shortcut-proof-state.json'
FOREIGN = '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/augmentor-proof-conflict/'


def command(argv):
    return subprocess.check_output(argv, text=True, timeout=30).strip()


def exchange(name='main', action='maintenance.status'):
    suffix = '' if name == 'main' else '-secondary'
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(10)
        try:client.connect(str(Path(os.environ['XDG_RUNTIME_DIR'])/('augmentor-linux-pi'+suffix+'.sock')))
        except (FileNotFoundError, ConnectionRefusedError):return None
        client.sendall(action.encode())
        with client.makefile('rb') as stream:return json.loads(stream.readline(16384))


def idle(status):
    return status and status['accepted'] and not any(status[k] for k in ('busy','running','draftPresent','online'))


def records(backend, paths):
    return {p:{k:backend.custom(p).get_value(k).print_(True) for k in backend.fields} for p in paths}


def snapshot():
    from gnome import GnomeObserver
    from gi.repository import Gio
    states = {name:exchange(name) for name in ('main','secondary')}
    scene = GnomeObserver(Gio.bus_get_sync(Gio.BusType.SESSION, None)).read()
    pids = {s['pid'] for s in states.values() if s}
    return {'states':states, 'visible':{name:[w for w in scene['windows'] if state and w['pid']==state['pid']]
            for name,state in states.items()}, 'guards':scene['guards'], 'epoch':scene['epoch'],
            'inputQualified':scene['inputQualified'], 'applicationPids':sorted(pids),
            'servicePid':int(command(['systemctl','--user','show','augmentor-desktop.service','--value','-p','MainPID']))}


def dismiss(name):
    status = exchange(name)
    assert status and not any(status[k] for k in ('running','draftPresent','online'))
    if not status['busy']:return status
    rows = [row.split(None,4) for row in command(['wmctrl','-lp']).splitlines()]
    dialogs = [row for row in rows if int(row[2])==status['pid'] and row[4]=='Connect DSH']
    assert len(dialogs)==1, 'Only the owned unconfigured DSH dialog may be rejected.'
    subprocess.run(['wmctrl','-ic',dialogs[0][0]], check=True, timeout=10)
    deadline = time.monotonic()+15
    while time.monotonic()<deadline:
        after=exchange(name)
        if idle(after):
            assert after['pid']==status['pid'];return after
        time.sleep(.1)
    raise RuntimeError('The owned setup dialog did not close normally.')


def qt_save():
    sys.path.insert(0,str(ROOT/'apps/native'))
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor,QKeySequence
    from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout
    from PySide6.QtTest import QTest
    from augmentor_linux.shortcut_settings import ShortcutSettings
    from augmentor_linux.shortcuts import current_keys
    from augmentor_linux.gnome_shortcuts import request
    os.environ['QT_QPA_PLATFORM']='xcb'
    app=QApplication([]);app.setApplicationName('Augmentor GNOME shortcut proof')
    class Owner(QWidget):
        accent=QColor('#50c8a0')
        def call_in_background(self,work,callback):callback(work())
    owner=Owner();layout=QVBoxLayout(owner);form=ShortcutSettings(owner);layout.addWidget(form)
    owner.show();app.processEvents()
    def save(name,text,conflict=False):
        row=form.rows[name];prior=row['current'].text()
        row['editor'].setKeySequence(QKeySequence(text));app.processEvents()
        assert row['button'].isEnabled(),row['note'].text()
        clicked=[];row['button'].clicked.connect(lambda:clicked.append(True))
        QTest.mouseClick(row['button'],Qt.MouseButton.LeftButton);app.processEvents()
        assert clicked, 'The actual Qt Save button did not receive its mouse event.'
        if conflict:
            assert 'already assigned' in row['note'].text(),row['note'].text()
            assert row['current'].text()==prior
        else:
            assert row['note'].text().startswith('Saved.'),row['note'].text()
            assert current_keys(name)==[QKeySequence(text)[0].toCombined()]
    try:
        save('main','Ctrl+Alt+Shift+F9');save('secondary','Ctrl+Alt+Shift+F10')
        before={n:request('read',n) for n in ('main','secondary')}
        save('main','Ctrl+Alt+Shift+F12',True)
        assert {n:request('read',n) for n in before}==before
        save('main','Ctrl+Alt+Shift+F10',True)
        assert {n:request('read',n) for n in before}==before
        return {'qtSaveMouseClicks':2,'qtConflictMouseClicks':2,'realNativeSettingsReadback':True,
                'foreignConflictRefusedWithoutWrites':True,'instanceConflictRefused':True}
    finally:
        form.close();owner.close();app.processEvents()


def main():
    global ROOT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare','snapshot','states','dismiss','close','restore','qt-save'))
    parser.add_argument('--instance', choices=('main','secondary'), default='main')
    parser.add_argument('--source', required=True)
    args=parser.parse_args()
    assert re.fullmatch('[a-f0-9]{40}',args.source)
    assert os.geteuid()==1000 and os.environ.get('USER')=='augmentor-proof'
    assert Path('/etc/augmentor-test-vm').read_text()=='Isolated Augmentor Ubuntu 24.04 GNOME qualification VM\n'
    assert command(['systemd-detect-virt'])=='qemu'
    assert command(['hostname'])=='augmentor-gnome-ubuntu24-mesa2'
    data=Path.home()/'.local/share/augmentor'
    selection=json.loads((data/'desktop.json').read_text())
    ROOT=Path(selection['root'])
    if ROOT!=Path('/usr/lib/augmentor'):
        assert ROOT.is_relative_to(data/'releases') and selection['sourceRef']==args.source
        spec=importlib.util.spec_from_file_location('shortcut_deployment',data/'desktop-deployment.py')
        deployment=importlib.util.module_from_spec(spec);spec.loader.exec_module(deployment)
        deployment.verify(ROOT)
    release=json.loads((ROOT/'release.json').read_text())
    assert release['target']=='ubuntu24.04-amd64' and release['source']=={'commit':args.source,'dirty':False}
    assert not command(['dpkg','--verify','augmentor-runtime','augmentor-desktop'])
    assert selection['root']==str(ROOT)
    spec=importlib.util.spec_from_file_location('shortcut_python',ROOT/'scripts/linux-python-runtime.py')
    runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
    assert runtime.resolve(ROOT,selection['python'])==selection['python']==sys.executable
    environment=dict(row.split('=',1) for row in command(['systemctl','--user','show-environment']).splitlines() if '=' in row)
    assert environment['XDG_SESSION_TYPE']=='wayland' and environment['XDG_CURRENT_DESKTOP']=='ubuntu:GNOME'
    for key in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','XDG_CURRENT_DESKTOP','XDG_SESSION_TYPE','DBUS_SESSION_BUS_ADDRESS'):
        if key in environment:os.environ[key]=environment[key]
    sys.path.insert(0,str(ROOT/'services/desktop'))
    if args.action=='states':return {'states':{n:exchange(n) for n in ('main','secondary')}}
    if args.action=='snapshot':return snapshot()
    if args.action=='dismiss':return {'dismissed':dismiss(args.instance)}
    if args.action=='close':
        before=exchange(args.instance);assert idle(before)
        result=exchange(args.instance,'maintenance.close');assert result['accepted']
        return {'closeAccepted':True,'before':before}
    # Qt and GTK live in separate processes, matching the production adapter.
    if args.action=='qt-save':return qt_save()
    from gnome_shortcuts import NativeShortcuts,PREFIX
    backend=NativeShortcuts()
    own=[PREFIX+name+'/' for name in ('main','secondary')]
    if args.action=='restore':
        if not STATE.exists():return {'settingsRestored':False,'noPendingSettingsBackup':True}
        saved=json.loads(STATE.read_text())
        assert saved['source']==args.source
        for p in own:backend.owned(p.removeprefix(PREFIX).strip('/'),backend.custom(p))
        current=backend.parent.get_strv('custom-keybindings')
        assert current==saved['registeredAfter'], 'Do not overwrite concurrent settings changes.'
        unrelated=[p for p in saved['pathsBefore'] if p not in own]
        assert records(backend,unrelated)=={p:v for p,v in saved['foreignBefore'].items() if p not in own}
        assert backend.custom(FOREIGN).get_string('command')=='/usr/bin/true'
        for path,values in saved['userValues'].items():
            entry=backend.custom(path);entry.delay()
            for key,value in values.items():
                if value is None:entry.reset(key)
                else:entry.set_value(key,backend.GLib.Variant.parse(None,value,None,None))
            entry.apply()
        backend.parent.set_strv('custom-keybindings',saved['pathsBefore']);backend.Gio.Settings.sync()
        assert backend.parent.get_strv('custom-keybindings')==saved['pathsBefore']
        assert records(backend,saved['pathsBefore'])==saved['foreignBefore']
        STATE.unlink()
        return {'settingsRestored':True,'foreignEntriesPreserved':True}
    assert not STATE.exists(), 'Restore the previous proof before beginning another.'
    assert idle(exchange()) and exchange('secondary') is None
    paths=backend.parent.get_strv('custom-keybindings')
    assert FOREIGN not in paths and all(backend.custom(FOREIGN).get_string(k)=='' for k in backend.fields)
    for name,path in zip(('main','secondary'),own):backend.owned(name,backend.custom(path))
    saved={'source':args.source,'pathsBefore':paths,'foreignBefore':records(backend,paths),
           'userValues':{p:{k:(v.print_(True) if (v:=backend.custom(p).get_user_value(k)) is not None else None)
                            for k in backend.fields} for p in [*own,FOREIGN]},
           'registeredAfter':paths}
    descriptor=os.open(STATE,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'w') as stream:json.dump(saved,stream)
    foreign=backend.custom(FOREIGN);foreign.delay()
    for k,v in {'name':'Augmentor qualification conflict','binding':'<Shift><Control><Alt>F12','command':'/usr/bin/true'}.items():foreign.set_string(k,v)
    foreign.apply();backend.parent.set_strv('custom-keybindings',paths+[FOREIGN]);backend.Gio.Settings.sync()
    saved['registeredAfter']=paths+[FOREIGN];STATE.write_text(json.dumps(saved))
    try:
        result=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'qt-save','--source',args.source],
                              capture_output=True,text=True,timeout=65)
        assert result.returncode==0,result.stderr
        reply=json.loads(result.stdout)
        unrelated=[p for p in paths if p not in own]
        assert records(backend,unrelated)=={p:v for p,v in saved['foreignBefore'].items() if p not in own}
        assert backend.custom(FOREIGN).get_string('command')=='/usr/bin/true'
        return {**reply,'fields':list(backend.fields),'functionalTested':False,
                'main':backend.read('main'),'secondary':backend.read('secondary')}
    finally:
        saved['registeredAfter']=backend.parent.get_strv('custom-keybindings');STATE.write_text(json.dumps(saved))


if __name__=='__main__':print(json.dumps(main()))
