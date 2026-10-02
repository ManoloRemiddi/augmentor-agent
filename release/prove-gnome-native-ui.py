#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual preview-window activation through installed launchers, in private GNOME.

No harness/model requests. Initial processes are explicitly preview fixtures;
repeat GSD invocations execute the unmodified canonical production launcher.
This does not qualify service startup, login, or closed-application launch.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--compositor-pid',type=int,required=True)
p.add_argument('--out',type=Path,required=True)
p.add_argument('--platform',choices=('wayland','xcb'),required=True)
a=p.parse_args()
ROOT=Path(__file__).resolve().parents[1]
if os.geteuid()==0 or not Path('/.dockerenv').exists() or Path('/run/systemd/seats').exists() or os.environ.get('WAYLAND_DISPLAY')!='wayland-augmentor':
    raise SystemExit('Only the ordinary private GNOME container fixture may run this proof.')
if not {b'--headless',b'--virtual-monitor',b'1280x800'}.issubset(Path(f'/proc/{a.compositor_pid}/cmdline').read_bytes().split(b'\0')):
    raise SystemExit('Not our private compositor.')
import gi
from gi.repository import Gio,GLib
bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
def call(destination,path,interface,method,params=None):
    return bus.call_sync(destination,path,interface,method,params,None,Gio.DBusCallFlags.NO_AUTO_START,3000,None).unpack()
owner=call('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetConnectionUnixProcessID',GLib.Variant('(s)',('org.gnome.Shell',)))[0]
if owner!=a.compositor_pid or subprocess.check_output(['gnome-shell','--version'],text=True).strip()!='GNOME Shell 50.5':
    raise SystemExit('Only the owned Shell 50.5 fixture is qualified for this synthetic input.')
sys.path.insert(0,str(ROOT/'services/desktop'))
from gnome import GnomeObserver
observer=GnomeObserver(bus)
a.out.mkdir(parents=True,exist_ok=True)
source_paths=('release/prove-gnome-native-ui.py','release/prove-gnome-discovery.py',
              'scripts/install-desktop-startup.py','scripts/desktop-launch.py',
              'apps/native/augmentor_linux/window.py','services/desktop/gnome_shortcuts.py',
              'services/desktop/gnome.py','services/desktop/gnome-extension/observer@augmentoragent.com/extension.js',
              'services/desktop/gnome-extension/observer@augmentoragent.com/metadata.json',
              'release/gnome-native-ui.Dockerfile')
hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in source_paths}
for name in ('extension.js','metadata.json'):
    copied=Path.home()/'.local/share/gnome-shell/extensions/observer@augmentoragent.com'/name
    if hashlib.sha256(copied.read_bytes()).hexdigest()!=hashes['services/desktop/gnome-extension/observer@augmentoragent.com/'+name]:
        raise SystemExit('Loaded observer differs from the recorded source.')
node=Path('/usr/lib/augmentor/node/bin/node')
node_version=subprocess.check_output([str(node),'--version'],text=True).strip()
if node_version!='v24.19.0':raise SystemExit('Use the fixture with the pinned product Node runtime.')
def wait(predicate,label,timeout=12):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        result=predicate()
        if result:return result
        time.sleep(.05)
    raise RuntimeError('Timed out waiting for '+label)
def exchange(name,command):
    suffix='' if name=='main' else '-secondary'
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
        client.settimeout(2)
        try:client.connect(str(Path(os.environ['XDG_RUNTIME_DIR'])/('augmentor-linux-pi'+suffix+'.sock')))
        except (FileNotFoundError,ConnectionRefusedError):return None
        client.sendall(command.encode())
        with client.makefile('rb') as stream:return json.loads(stream.readline(16384))
def inspect(name):
    value=exchange(name,'ui-test:{"action":"inspect"}')
    if not value:return None
    if not value['ok']:raise RuntimeError(value['error'])
    return value['result']
processes=[];logs=[];session=None;held=[];report=None
try:
    call('org.gnome.Shell','/org/gnome/Shell','org.freedesktop.DBus.Properties','Set',
         GLib.Variant('(ssv)',('org.gnome.Shell','OverviewActive',GLib.Variant('b',False))))
    environment={**os.environ,'PYTHONPATH':str(ROOT/'apps/native'),'QT_QPA_PLATFORM':a.platform}
    if a.platform=='xcb':
        auth=list(Path(os.environ['XDG_RUNTIME_DIR']).glob('.mutter-Xwaylandauth.*'))
        if len(auth)!=1 or auth[0].stat().st_uid!=os.getuid():raise RuntimeError('Private compositor XWayland authority is ambiguous or missing.')
        environment['XAUTHORITY']=str(auth[0])
        os.environ['XAUTHORITY']=str(auth[0])
    # Only the disposable HOME is configured, using the unchanged installer.
    spec=importlib.util.spec_from_file_location('startup',ROOT/'scripts/install-desktop-startup.py')
    startup=importlib.util.module_from_spec(spec);spec.loader.exec_module(startup)
    startup.install(ROOT,Path(sys.executable),node,enable=False)
    daemon_log=(a.out/'native-ui-media-keys.log').open('w');logs.append(daemon_log)
    daemon=subprocess.Popen(['/usr/libexec/gsd-media-keys'],stdout=daemon_log,stderr=daemon_log,env=environment)
    processes.append(daemon)
    def owned_daemon():
        try:return call('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetConnectionUnixProcessID',GLib.Variant('(s)',('org.gnome.SettingsDaemon.MediaKeys',)))[0]==daemon.pid
        except GLib.Error:return False
    wait(owned_daemon,'owned MediaKeys daemon')
    from gnome_shortcuts import NativeShortcuts
    shortcuts=NativeShortcuts()
    for name,key in (('main','F9'),('secondary','F10')):
        shortcuts.save(name,{'key':{'symbol':key},'modifiers':['Control','Super']})
        log=(a.out/(name+'-ui.log')).open('w');logs.append(log)
        process=subprocess.Popen([sys.executable,'-m','augmentor_linux','--preview','--ui-test-control','--instance',name],env=environment,stdout=log,stderr=log)
        processes.append(process)
        wait(lambda:inspect(name),'actual '+name+' UI socket')
        wait(lambda:((observer.read().get('window') or {}).get('pid')==process.pid),'actual '+name+' compositor focus')
    session=call('org.gnome.Mutter.RemoteDesktop','/org/gnome/Mutter/RemoteDesktop','org.gnome.Mutter.RemoteDesktop','CreateSession')[0]
    def input_call(method,params=None):return call('org.gnome.Mutter.RemoteDesktop',session,'org.gnome.Mutter.RemoteDesktop.Session',method,params)
    def key(code,pressed):
        input_call('NotifyKeyboardKeycode',GLib.Variant('(ub)',(code,pressed)))
        if pressed:held.append(code)
        else:held.remove(code)
    def combination(code):
        for k in (29,125,code):key(k,True);time.sleep(.05)
        time.sleep(.1)
        for k in reversed(held[:]):key(k,False)
    input_call('Start');key(42,True);time.sleep(.2);key(42,False);time.sleep(2)
    snapshots=[]
    def snapshot(label):
        scene=observer.read();value={'step':label,'main':inspect('main'),'secondary':inspect('secondary'),'focused':scene['window']}
        snapshots.append(value);return value
    initial=snapshot('both initially open')
    # Main is visible but secondary currently has focus. Preserve existing
    # product toggle semantics: first shortcut hides, next restores and focuses.
    combination(67);wait(lambda:not inspect('main')['visible'],'main hide through production canonical launcher')
    snapshot('main hidden')
    combination(67);wait(lambda:inspect('main')['visible'],'main restore through production canonical launcher')
    time.sleep(.7);main_restored=snapshot('main restored')
    key(30,True);key(30,False);time.sleep(.3);main_typed=snapshot('main composer key')
    combination(68);wait(lambda:not inspect('secondary')['visible'],'secondary hide')
    snapshot('secondary hidden')
    combination(68);wait(lambda:inspect('secondary')['visible'],'secondary restore')
    time.sleep(.7);secondary_restored=snapshot('secondary restored')
    key(48,True);key(48,False);time.sleep(.3);secondary_typed=snapshot('secondary composer key')
    same_pids=all(row[name]['pid']==initial[name]['pid'] for row in snapshots for name in ('main','secondary'))
    checks={'independentExistingProcesses':same_pids,'bothHideRestoreDelivered':True,
            'mainRestoreFocus':(main_restored['focused'] or {}).get('pid')==initial['main']['pid'],
            'secondaryRestoreFocus':(secondary_restored['focused'] or {}).get('pid')==initial['secondary']['pid'],
            'mainComposerReceivesKey':main_typed['main']['draft']=='a' and main_typed['secondary']['draft']=='',
            'secondaryComposerReceivesKey':secondary_typed['secondary']['draft']=='b' and secondary_typed['main']['draft']=='a'}
    assert hashes=={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in source_paths},'Source changed during proof'
    report={'format':'augmentor-gnome-existing-native-ui-proof/1','shellVersion':'50.5','platform':a.platform,
            'privateCompositorOwnerMatches':True,'syntheticInput':True,'hostInputDevicesMounted':False,
            'canonicalProductionLauncherTested':True,'initialPreviewProcesses':True,'nodeVersion':node_version,
            'pythonVersion':sys.version.split()[0],
            'packages':subprocess.check_output(['rpm','-q','gnome-shell','mutter','gnome-settings-daemon','python3-pyside6','qt6-qtbase','python3-gobject','gtk4'],text=True).splitlines(),
            'serviceStartupTested':False,'closedAppLaunchTested':False,'actualLoginRebootTested':False,
            'modelRequestsTested':False,'inputQualified':False,'checks':checks,'snapshots':snapshots,'sourceSha256':hashes}
    (a.out/'native-ui.json').write_text(json.dumps(report,indent=2)+'\n')
    if not all(checks.values()):raise RuntimeError('Native GNOME activation failed: '+json.dumps(checks))
    print('PRIVATE GNOME EXISTING AUGMENTOR UI ACTIVATION VERIFIED')
finally:
    if session:
        for code in reversed(held):
            try:input_call('NotifyKeyboardKeycode',GLib.Variant('(ub)',(code,False)))
            except GLib.Error:pass
        try:input_call('Stop')
        except GLib.Error:pass
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
    for log in logs:log.close()
