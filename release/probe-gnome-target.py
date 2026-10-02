# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Disposable owned Fedora GTK4 target; never reads or edits application state."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import gi

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--candidate',required=True);args=parser.parse_args()
assert os.getuid()==1000 and os.environ.get('USER')=='augmentor-proof'
assert Path('/etc/augmentor-test-vm').read_text()=='Isolated Augmentor Fedora GNOME qualification VM\n'
assert args.candidate.startswith('gnome-execution-probe-') and '/' not in args.candidate and '..' not in args.candidate
root=Path.home()/args.candidate
assert root.is_dir() and not root.is_symlink() and root.stat().st_uid==os.getuid() and not root.stat().st_mode&0o077
env=dict(row.split('=',1) for row in subprocess.check_output(['systemctl','--user','show-environment'],text=True).splitlines() if '=' in row)
assert env['XDG_CURRENT_DESKTOP']=='GNOME' and env['XDG_SESSION_TYPE']=='wayland'
os.environ.update({key:value for key,value in env.items() if key in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','XDG_CURRENT_DESKTOP','XDG_SESSION_TYPE')})
os.umask(0o077);gi.require_version('Gtk','4.0');from gi.repository import Gtk
state={'format':'augmentor-owned-gtk-target/1','pid':os.getpid(),'clicks':{'center':0,'edge':0},'textA':'','textB':''}
def save():
    temporary=root/'target-state.json.tmp';temporary.write_text(json.dumps(state,indent=2)+'\n');temporary.replace(root/'target-state.json')
application=Gtk.Application(application_id='com.augmentor.OwnedQualificationTarget')
def activate(app):
    window=Gtk.ApplicationWindow(application=app,title='Owned Augmentor GNOME target fixture');window.set_default_size(800,500)
    layout=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12)
    layout.set_margin_top(20);layout.set_margin_bottom(20);layout.set_margin_start(20);layout.set_margin_end(20)
    layout.append(Gtk.Label(label='Disposable qualification target — synthetic data only'))
    for key,label in (('textA','Entry A'),('textB','Entry B')):
        entry=Gtk.Entry();entry.set_placeholder_text(label)
        def changed(widget,name=key):state[name]=widget.get_text();save()
        entry.connect('changed',changed);layout.append(entry)
    password=Gtk.PasswordEntry();password.set_property('placeholder-text','Synthetic password refusal target');layout.append(password)
    center=Gtk.Button(label='Center target');center.set_hexpand(True);center.set_vexpand(True);layout.append(center)
    edge=Gtk.Button(label='Far edge target');edge.set_halign(Gtk.Align.END);edge.set_valign(Gtk.Align.END);layout.append(edge)
    for key,button in (('center',center),('edge',edge)):
        def clicked(_widget,name=key):state['clicks'][name]+=1;save()
        button.connect('clicked',clicked)
    window.set_child(layout);window.present();save()
application.connect('activate',activate);application.run([])
