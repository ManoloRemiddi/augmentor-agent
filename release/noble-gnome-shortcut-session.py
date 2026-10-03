#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bounded guest actions for the marked Noble/Fedora shortcut fixtures.

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
        with client.makefile('rb') as stream:status=json.loads(stream.readline(16384))
        if action.startswith('ui-test:'):
            assert status.get('ok'), status.get('error', 'UI test request failed.')
            status=status['result']
        assert status['buildRoot']==str(ROOT), 'Running app has not adopted the selected artifact.'
        return status


def idle(status):
    return status and status['accepted'] and not any(status[k] for k in ('busy','running','draftPresent','online'))


def qt_operation(root, python, operation):
    """A guarded parent supplies verified native paths before its Qt child exec."""
    if operation not in ('qt-save','app-settings-save'):
        raise ValueError('Unsupported bounded Qt proof operation.')
    env=dict(os.environ)
    marker=root/'linux-python-runtime.json'
    if marker.exists() or marker.is_symlink():
        spec=importlib.util.spec_from_file_location('owned_qt_proof_runtime',root/'scripts/linux-python-runtime.py')
        runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
        env=runtime.environment(root,python,env)
    # The parent already checked the exact guest, security mode, selected source,
    # inventory and interpreter. Run only these two bounded operations; do not
    # relax verified_profile's refusal of inherited loader overrides.
    code='''import importlib.util,json,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('owned_qt_operation',sys.argv[1])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.ROOT=Path(sys.argv[2])
sys.path.insert(0,str(module.ROOT/'services/desktop'))
sys.path.insert(0,str(module.ROOT/'apps/native'))
operation=sys.argv[3]
if operation not in ('qt-save','app-settings-save'):raise ValueError('Unsupported Qt operation')
print(json.dumps(module.qt_save() if operation=='qt-save' else module.app_settings_save()))
'''
    result=subprocess.run([python,'-B','-c',code,str(Path(__file__).resolve()),str(root),operation],
                          env=env,capture_output=True,text=True,timeout=120)
    if result.returncode:raise RuntimeError('Bounded Qt proof child failed: '+result.stderr)
    return json.loads(result.stdout)


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


def app_settings_save():
    """Both already opted-in real windows; no standalone form or UI monkeypatch."""
    from augmentor_linux.gnome_shortcuts import request
    def ui(name, operation, **values):
        result=exchange(name,'ui-test:'+json.dumps({'action':'shortcut-settings','operation':operation,**values}))
        assert result and result['pid']==exchange(name)['pid']
        return result
    def wait(name, predicate, label):
        end=time.monotonic()+15
        while time.monotonic()<end:
            state=ui(name,'inspect')
            if predicate(state):return state
            time.sleep(.05)
        raise RuntimeError('Timed out waiting for actual application '+label)
    def save(window, name, text, conflict=False):
        state=ui(window,'inspect');before=state['rows'][name]['current']
        selected=ui(window,'choose',instance=name,sequence=text,expectedCurrent=before)
        sequence=selected['rows'][name]['sequence'];assert sequence
        ui(window,'save',instance=name,expectedSequence=sequence,expectedCurrent=before)
        state=wait(window,lambda s:not s['rows'][name]['saving'],'asynchronous Save')
        row=state['rows'][name]
        if conflict:
            assert 'already assigned' in row['note'] and row['current']==before,row
        else:assert row['note'].startswith('Saved.'),row
    completed=[]
    try:
        for name in ('main','secondary'):
            assert idle(exchange(name)), 'Both actual windows must be idle and explicitly opted in.'
            assert not ui(name,'inspect')['open'], 'Close existing Settings before the proof.'
        for window in ('main','secondary'):
            ui(window,'open')
            wait(window,lambda s:s['open'] and all(r['ready'] for r in s['rows'].values()),'Settings readback')
            save(window,'main','Ctrl+Alt+Shift+F9');save(window,'secondary','Ctrl+Alt+Shift+F10')
            before={n:request('read',n) for n in ('main','secondary')}
            save(window,'main','Ctrl+Alt+Shift+F12',True)
            save(window,'main','Ctrl+Alt+Shift+F10',True)
            assert {n:request('read',n) for n in before}==before
            ui(window,'close');wait(window,lambda s:not s['open'],'Settings close')
            completed.append(window)
        return {'actualApplicationSettingsWindows':completed,'asyncSaveTested':True,
                'qtSaveMouseClicks':4,'qtConflictMouseClicks':4,'realNativeSettingsReadback':True,
                'foreignConflictRefusedWithoutWrites':True,'instanceConflictRefused':True,
                'bothApplicationProcessesOptedIntoUiTestControl':True}
    finally:
        for name in completed+([window] if 'window' in locals() and window not in completed else []):
            state=ui(name,'inspect')
            if state['open'] and not any(r['saving'] for r in state['rows'].values()):ui(name,'close')


def main():
    global ROOT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('journal-check','prepare','prepare-app-settings','snapshot','states','dismiss','close','restore','qt-save','app-settings-save'))
    parser.add_argument('--instance', choices=('main','secondary'), default='main')
    parser.add_argument('--target', choices=('ubuntu24','fedora44'), default='ubuntu24')
    parser.add_argument('--source', required=True)
    parser.add_argument('--proof-token', required=True)
    args=parser.parse_args()
    assert re.fullmatch('[a-f0-9]{40}',args.source)
    spec=importlib.util.spec_from_file_location('shortcut_qualification',Path(__file__).with_name('gnome-vm-qualification.py'))
    qualification=importlib.util.module_from_spec(spec);spec.loader.exec_module(qualification)
    qualification.proof_identity(args.source,args.proof_token)
    contract=qualification.verified_profile(args.target,args.source)
    ROOT=Path(contract['root']);selection=contract['selection']
    assert contract['python']==sys.executable, 'Use the verified selected interpreter.'
    if args.action=='journal-check':
        qualification.require_new_journal(STATE)
        return {'journalAbsent':True}
    if args.action in ('prepare','prepare-app-settings'):
        qualification.require_new_journal(STATE)
    saved=None
    if args.action=='restore' and os.path.lexists(STATE):
        saved=qualification.read_journal(STATE,args.source,args.proof_token)
    environment=dict(row.split('=',1) for row in command(['systemctl','--user','show-environment']).splitlines() if '=' in row)
    assert environment['XDG_SESSION_TYPE']=='wayland' and environment['XDG_CURRENT_DESKTOP']==qualification.PROFILES[args.target]['desktop']
    for key in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','XDG_CURRENT_DESKTOP','XDG_SESSION_TYPE','DBUS_SESSION_BUS_ADDRESS'):
        if key in environment:os.environ[key]=environment[key]
    sys.path.insert(0,str(ROOT/'services/desktop'))
    sys.path.insert(0,str(ROOT/'apps/native'))
    if args.action=='states':return {'states':{n:exchange(n) for n in ('main','secondary')}}
    if args.action=='snapshot':return snapshot()
    if args.action=='dismiss':return {'dismissed':dismiss(args.instance)}
    if args.action=='close':
        before=exchange(args.instance);assert idle(before)
        result=exchange(args.instance,'maintenance.close');assert result['accepted']
        return {'closeAccepted':True,'before':before}
    # Qt and GTK live in separate processes, matching the production adapter.
    if args.action in ('qt-save','app-settings-save'):
        return qt_operation(ROOT,contract['python'],args.action)
    from gnome_shortcuts import NativeShortcuts,PREFIX
    backend=NativeShortcuts()
    own=[PREFIX+name+'/' for name in ('main','secondary')]
    if args.action=='restore':
        if saved is None:return {'settingsRestored':False,'noPendingSettingsBackup':True}
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
        qualification.read_journal(STATE,args.source,args.proof_token)
        STATE.unlink()
        return {'settingsRestored':True,'foreignEntriesPreserved':True,'proofToken':args.proof_token}
    qualification.require_new_journal(STATE)
    assert idle(exchange())
    actual=args.action=='prepare-app-settings'
    if actual:
        assert idle(exchange('secondary'))
        for name in ('main','secondary'):
            assert not exchange(name,'ui-test:'+json.dumps({'action':'shortcut-settings','operation':'inspect'}))['open']
    else:assert exchange('secondary') is None
    paths=backend.parent.get_strv('custom-keybindings')
    assert FOREIGN not in paths and all((not backend.custom(FOREIGN).get_boolean(k)) if k=='enable-in-lockscreen'
                                       else backend.custom(FOREIGN).get_string(k)=='' for k in backend.fields)
    for name,path in zip(('main','secondary'),own):backend.owned(name,backend.custom(path))
    saved={'source':args.source,'proofToken':args.proof_token,'pathsBefore':paths,'foreignBefore':records(backend,paths),
           'userValues':{p:{k:(v.print_(True) if (v:=backend.custom(p).get_user_value(k)) is not None else None)
                            for k in backend.fields} for p in [*own,FOREIGN]},
           'registeredAfter':paths}
    qualification.create_journal(STATE,saved,args.source,args.proof_token)
    foreign=backend.custom(FOREIGN);foreign.delay()
    for k,v in {'name':'Augmentor qualification conflict','binding':'<Shift><Control><Alt>F12','command':'/usr/bin/true'}.items():foreign.set_string(k,v)
    foreign.apply();backend.parent.set_strv('custom-keybindings',paths+[FOREIGN]);backend.Gio.Settings.sync()
    saved['registeredAfter']=paths+[FOREIGN];qualification.write_journal(STATE,saved,args.source,args.proof_token)
    try:
        reply=qt_operation(ROOT,contract['python'],'app-settings-save' if actual else 'qt-save')
        unrelated=[p for p in paths if p not in own]
        assert records(backend,unrelated)=={p:v for p,v in saved['foreignBefore'].items() if p not in own}
        assert backend.custom(FOREIGN).get_string('command')=='/usr/bin/true'
        return {**reply,'fields':list(backend.fields),'functionalTested':False,
                'main':backend.read('main'),'secondary':backend.read('secondary')}
    finally:
        saved['registeredAfter']=backend.parent.get_strv('custom-keybindings')
        qualification.write_journal(STATE,saved,args.source,args.proof_token)


if __name__=='__main__':print(json.dumps(main()))
