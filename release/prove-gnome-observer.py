#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Read-only observer qualification against owned windows in a private Shell."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--compositor-pid',type=int,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
ROOT=Path(__file__).resolve().parents[1]
SOURCE_PATHS=('services/desktop/gnome.py','services/desktop/gnome-extension/observer@augmentoragent.com/extension.js',
              'services/desktop/gnome-extension/observer@augmentoragent.com/metadata.json',
              'release/prove-gnome-observer.py','release/prove-gnome-discovery.py')
source_hashes={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in SOURCE_PATHS}
if os.geteuid()==0 or not Path('/.dockerenv').exists() or Path('/run/systemd/seats').exists() or os.environ.get('WAYLAND_DISPLAY')!='wayland-augmentor':
    raise SystemExit('Only the ordinary private GNOME container fixture may run this proof.')
command=Path(f'/proc/{a.compositor_pid}/cmdline').read_bytes().split(b'\0')
if not {b'--headless',b'--virtual-monitor',b'1280x800'}.issubset(command):raise SystemExit('Not our private compositor.')
import gi
gi.require_version('Gtk','4.0')
from gi.repository import Gio,GLib,Gtk
bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
pid=bus.call_sync('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetConnectionUnixProcessID',
    GLib.Variant('(s)',('org.gnome.Shell',)),None,0,1000,None).unpack()[0]
if pid!=a.compositor_pid:raise SystemExit('Shell bus owner is not our private child.')
for name in ('extension.js','metadata.json'):
    copied=Path.home()/'.local/share/gnome-shell/extensions/observer@augmentoragent.com'/name
    if hashlib.sha256(copied.read_bytes()).hexdigest()!=source_hashes['services/desktop/gnome-extension/observer@augmentoragent.com/'+name]:
        raise SystemExit('Loaded extension files differ from the reported source.')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services/desktop'))
from gnome import GnomeObserver

def wait(predicate,description,timeout=12):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        while GLib.MainContext.default().pending():GLib.MainContext.default().iteration(False)
        result=predicate()
        if result:return result
        time.sleep(.05)
    raise RuntimeError('Timed out waiting for '+description)

def call(method,signature,args):
    return bus.call_sync('org.gnome.Shell','/org/gnome/Shell','org.gnome.Shell',method,GLib.Variant(signature,args),None,0,1000,None)

observer=GnomeObserver(bus)
initial=observer.read()
if initial['shellVersion']!='50.5':raise SystemExit('Private Mutter fixture input is qualified only for Shell 50.5.')
Gtk.init()
first=Gtk.Window(title='Augmentor observer fixture A');first.set_default_size(420,300);first.set_child(Gtk.Entry())
second=Gtk.Window(title='Augmentor observer fixture B');second.set_default_size(300,180);second.set_child(Gtk.Entry())
input_session=None;held=[]
def input_call(method,params=None):
    return bus.call_sync('org.gnome.Mutter.RemoteDesktop',input_session,'org.gnome.Mutter.RemoteDesktop.Session',method,params,None,0,1000,None)
def key(code,pressed):
    input_call('NotifyKeyboardKeycode',GLib.Variant('(ub)',(code,pressed)))
    if pressed:held.append(code)
    else:held.remove(code)
try:
    # Closing the fixture overview changes only this owned private Shell.
    bus.call_sync('org.gnome.Shell','/org/gnome/Shell','org.freedesktop.DBus.Properties','Set',
        GLib.Variant('(ssv)',('org.gnome.Shell','OverviewActive',GLib.Variant('b',False))),None,0,1000,None)
    first.present()
    scene=wait(lambda: (s if ((s:=observer.read()).get('window') or {}).get('title')=='Augmentor observer fixture A' else None),'first real Wayland window focus')
    identity=scene['window']['id'];assert scene['window']['pid']==os.getpid()
    assert scene['compositorOwner']==observer.owner
    assert scene['inputQualified'] is False
    second.present()
    other=wait(lambda: (s if ((s:=observer.read()).get('window') or {}).get('title')=='Augmentor observer fixture B' else None),'second same-process window focus')
    assert other['window']['id']!=identity
    # Wayland correctly refuses an old window's untokened present() request.
    # Exercise actual focus change with synthetic Alt+Escape on our owned private
    # Mutter connection. The production observer exposes no activation method.
    input_session=bus.call_sync('org.gnome.Mutter.RemoteDesktop','/org/gnome/Mutter/RemoteDesktop',
        'org.gnome.Mutter.RemoteDesktop','CreateSession',None,None,0,1000,None).unpack()[0]
    input_call('Start');key(42,True);time.sleep(.2);key(42,False);time.sleep(.2)
    key(56,True);key(1,True);time.sleep(.1);key(1,False);key(56,False)
    restored=wait(lambda: (s if ((s:=observer.read()).get('window') or {}).get('id')==identity else None),'focus restored')
    assert restored['serial']>scene['serial'],'Focus away/back did not advance serial'
    before=restored['window']['geometry'];first.set_default_size(480,340)
    resized=wait(lambda: (s if (s:=observer.read())['window']['geometry']!=before else None),'native window resize')
    assert resized['serial']>restored['serial']
    geometry=resized['window']['geometry']
    def window_point():
        result=observer.inspect_point(identity,geometry['x']+geometry['width']/2,geometry['y']+geometry['height']/2)
        if result['windowMatches']:return result
        return None
    try:point=wait(window_point,'settled window point picking')
    except RuntimeError:
        print('Point diagnostics: '+json.dumps(observer.inspect_point(identity,geometry['x']+geometry['width']/2,geometry['y']+geometry['height']/2)),flush=True)
        raise
    chrome=observer.inspect_point(identity,640,10)
    assert chrome['blocked'] and not chrome['windowMatches'],chrome
    second.close()
    wait(lambda:len([w for w in observer.read()['windows'] if w['title'].startswith('Augmentor observer fixture')])==1,'same-process second window removal')
    first.close()
    wait(lambda:not any(w['id']==identity for w in observer.read()['windows']),'first identity removal')
    first=Gtk.Window(title='Augmentor observer fixture A');first.set_default_size(420,300);first.present()
    reopened=wait(lambda:(s if ((s:=observer.read()).get('window') or {}).get('title')=='Augmentor observer fixture A' else None),'reopened window')
    assert reopened['window']['id']!=identity,'Closed window identity was reused'
    # Public extension lifecycle on our private Shell only.
    subprocess.run(['gnome-extensions','disable','observer@augmentoragent.com'],check=True,timeout=5)
    try:observer.read()
    except GLib.Error:pass
    else:raise AssertionError('Disabled observer continued answering')
    subprocess.run(['gnome-extensions','enable','observer@augmentoragent.com'],check=True,timeout=5)
    try:observer.read()
    except RuntimeError as error:assert 'restarted' in str(error),error
    else:raise AssertionError('Old epoch accepted observer restart')
    fresh=GnomeObserver(bus).read();assert fresh['epoch']!=initial['epoch']
    assert source_hashes=={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in SOURCE_PATHS},'Source changed during proof'
    report={'format':'augmentor-gnome-observer-proof/1','privateCompositorOwnerMatches':True,
        'ordinaryPrivateUser':True,'waylandWindowObserved':True,'sameProcessWindowsDistinct':True,
        'focusAwayAndBackSerialAdvances':True,'resizeObserved':True,'windowAndChromePointPickingTested':True,
        'closeReopenFreshIdentity':True,'disableAndRestartEpochFenced':True,
        'inputQualified':False,'portalConsentTested':False,'actualLoginRebootTested':False,
        'syntheticInput':True,'hostInputDevicesMounted':False,
        'xwaylandTested':False,'fullActorCompositionTrackingTested':False,
        'shellVersion':initial['shellVersion'],'guards':initial['guards'],
        'sourceSha256':source_hashes}
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'observer.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PRIVATE GNOME OBSERVER VERIFIED')
finally:
    if input_session:
        for code in reversed(held):
            try:input_call('NotifyKeyboardKeycode',GLib.Variant('(ub)',(code,False)))
            except GLib.Error:pass
        try:input_call('Stop')
        except GLib.Error:pass
    first.close();second.close()
