#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Native GSD behavior in a private compositor; not a production input adapter."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--compositor-pid',type=int,required=True)
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args()
if os.geteuid()==0 or not any(Path(p).exists() for p in ('/.dockerenv','/run/.containerenv')):
    raise SystemExit('Only an ordinary user in a disposable container may run this input fixture.')
if Path('/run/systemd/seats').exists() or os.environ.get('WAYLAND_DISPLAY')!='wayland-augmentor':
    raise SystemExit('This proof requires the private headless GNOME discovery fixture.')
command=Path(f'/proc/{args.compositor_pid}/cmdline').read_bytes().split(b'\0')
if not {b'--headless',b'--virtual-monitor',b'1280x800'}.issubset(command):
    raise SystemExit('The expected compositor is not our private virtual-monitor child.')
import gi
from gi.repository import Gio,GLib

out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
def call(dest,path,interface,method,parameters=None):
    return bus.call_sync(dest,path,interface,method,parameters,None,
                         Gio.DBusCallFlags.NO_AUTO_START,3000,None).unpack()
def process_owner(name):
    return call('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus',
                'GetConnectionUnixProcessID',GLib.Variant('(s)',(name,)))[0]
if process_owner('org.gnome.Shell')!=args.compositor_pid:
    raise SystemExit('Session bus compositor does not match our fixture child.')
if subprocess.check_output(['gnome-shell','--version'],text=True).strip()!='GNOME Shell 50.5':
    raise SystemExit('The private Mutter input API is qualified only at GNOME Shell 50.5.')
def wait(predicate,description,timeout=8):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        while GLib.MainContext.default().pending():GLib.MainContext.default().iteration(False)
        if predicate():return
        time.sleep(.05)
    raise RuntimeError('Timed out waiting for '+description)
parent=Gio.Settings.new('org.gnome.settings-daemon.plugins.media-keys')
schema='org.gnome.settings-daemon.plugins.media-keys.custom-keybinding'
paths={name:f'/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/augmentor-proof-{name}/'
       for name in ('main','secondary','foreign')}
settings={name:Gio.Settings.new_with_path(schema,path) for name,path in paths.items()}
if parent.get_strv('custom-keybindings'):
    raise SystemExit('The ordinary fixture user must have no preexisting custom shortcuts.')
events=out/'activations.txt'
launcher=out/'fixture-launch.py'
launcher.write_text('import sys\nfrom pathlib import Path\nwith Path(sys.argv[1]).open("a") as f: f.write(sys.argv[2]+"\\n")\n')
def configure(name,binding):
    entry=settings[name];entry.delay()
    entry.set_string('name','Synthetic '+name)
    entry.set_string('command',shlex.join([sys.executable,str(launcher),str(events),name]))
    entry.set_boolean('enable-in-lockscreen',False)
    entry.set_string('binding',binding);entry.apply();Gio.Settings.sync()
def rows():return events.read_text().splitlines() if events.exists() else []
def owner_is_daemon():
    try:return process_owner('org.gnome.SettingsDaemon.MediaKeys')==daemon.pid
    except GLib.Error:return False
daemon=None;session=None;held=[];log=(out/'media-keys.log').open('w')
try:
    # This property affects only our private software compositor. No Shell.Eval.
    call('org.gnome.Shell','/org/gnome/Shell','org.freedesktop.DBus.Properties','Set',
         GLib.Variant('(ssv)',('org.gnome.Shell','OverviewActive',GLib.Variant('b',False))))
    daemon=subprocess.Popen(['/usr/libexec/gsd-media-keys'],stdout=log,stderr=log,env={**os.environ,'G_MESSAGES_DEBUG':'all'})
    wait(owner_is_daemon,'owned MediaKeys daemon')
    configure('foreign','<Control><Super>F12')
    parent.set_strv('custom-keybindings',[paths['foreign']]);Gio.Settings.sync()
    foreign={key:settings['foreign'].get_value(key).print_(True) for key in settings['foreign'].list_keys()}
    configure('main','<Control><Super>F9');configure('secondary','<Control><Super>F10')
    parent.set_strv('custom-keybindings',[paths[name] for name in ('foreign','main','secondary')]);Gio.Settings.sync()
    assert settings['main'].get_string('binding')=='<Control><Super>F9'
    assert settings['secondary'].get_string('binding')=='<Control><Super>F10'
    # One persistent sender owns this version-pinned private Mutter session.
    session=call('org.gnome.Mutter.RemoteDesktop','/org/gnome/Mutter/RemoteDesktop',
                 'org.gnome.Mutter.RemoteDesktop','CreateSession')[0]
    def input_call(method,parameters=None):
        return call('org.gnome.Mutter.RemoteDesktop',session,
                    'org.gnome.Mutter.RemoteDesktop.Session',method,parameters)
    input_call('Start')
    # Let the compositor attach its newly created virtual keyboard/keymap.
    input_call('NotifyKeyboardKeycode',GLib.Variant('(ub)',(42,True)))
    held.append(42)
    time.sleep(.2)
    input_call('NotifyKeyboardKeycode',GLib.Variant('(ub)',(42,False)))
    held.remove(42)
    time.sleep(.2)
    def combination(code):
        for key in (29,125,code):
            input_call('NotifyKeyboardKeycode',GLib.Variant('(ub)',(key,True)));held.append(key)
            time.sleep(.05)
        time.sleep(.1)
        for key in reversed(held[:]):
            input_call('NotifyKeyboardKeycode',GLib.Variant('(ub)',(key,False)));held.remove(key)
    time.sleep(2) # GSD has no application-facing asynchronous grab acknowledgement.
    print('Fixture overview: '+str(call('org.gnome.Shell','/org/gnome/Shell','org.freedesktop.DBus.Properties','Get',GLib.Variant('(ss)',('org.gnome.Shell','OverviewActive')))),flush=True)
    combination(67);wait(lambda:rows()==['main'],'first configured shortcut delivery')
    combination(68);wait(lambda:rows()==['main','secondary'],'independent second shortcut delivery')
    settings['main'].set_string('binding','<Control><Super>F11');settings['main'].apply();Gio.Settings.sync();time.sleep(1)
    combination(67);time.sleep(.4);assert rows()==['main','secondary'],'Old combination still invokes main'
    combination(87);wait(lambda:rows()==['main','secondary','main'],'changed shortcut delivery')
    settings['secondary'].set_string('binding','');settings['secondary'].apply();Gio.Settings.sync();time.sleep(1)
    combination(68);time.sleep(.4);assert rows()==['main','secondary','main'],'Disabled combination still invokes secondary'
    configure('secondary','<Control><Super>F10')
    daemon.terminate();daemon.wait(timeout=5)
    daemon=subprocess.Popen(['/usr/libexec/gsd-media-keys'],stdout=log,stderr=log)
    wait(owner_is_daemon,'restarted owned MediaKeys daemon');time.sleep(2)
    combination(68);wait(lambda:rows()==['main','secondary','main','secondary'],'persisted shortcut delivery after daemon restart')
    assert paths['foreign'] in parent.get_strv('custom-keybindings')
    assert foreign=={key:settings['foreign'].get_value(key).print_(True) for key in settings['foreign'].list_keys()}
    report={'format':'augmentor-gnome-native-shortcut-mechanism/1',
            'proofScriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'compositor':'GNOME Shell 50.5','privateCompositorOwnerMatches':True,
            'ordinaryPrivateUser':True,'syntheticInput':True,'hostInputDevicesMounted':False,
            'twoBindingsDelivered':True,'changedBindingReleasesPrevious':True,
            'emptyBindingDisables':True,'daemonRestartRestores':True,'foreignSettingsPreserved':True,
            'activationEvents':rows(),'productionAdapterTested':False,'conflictRefusalTested':False,
            'actualAugmentorClosedLaunchTested':False,'focusTested':False,
            'physicalKeyTested':False,'realLoginRebootTested':False,'portalConsentTested':False}
    (out/'custom-shortcuts.json').write_text(json.dumps(report,indent=2)+'\n')
    print('GNOME NATIVE CUSTOM SHORTCUT MECHANISM VERIFIED')
finally:
    if session:
        for key in reversed(held):
            try:input_call('NotifyKeyboardKeycode',GLib.Variant('(ub)',(key,False)))
            except GLib.Error:pass
        try:input_call('Stop')
        except GLib.Error:pass
    if daemon and daemon.poll() is None:
        daemon.terminate()
        try:daemon.wait(timeout=5)
        except subprocess.TimeoutExpired:daemon.kill();daemon.wait(timeout=5)
    log.close()
