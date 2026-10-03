# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Owned Fedora GTK4 input fixture; synthetic text and native widget receipts only.

Never use on an owner's desktop. The existing historical capture/accessibility
targets remain unchanged. Ctrl+S writes only this fixture's private saved file.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',required=True)
    parser.add_argument('--backend',choices=('wayland','x11'),required=True)
    args=parser.parse_args()
    if (os.getuid()!=1000 or os.environ.get('USER')!='augmentor-proof'
            or Path('/etc/augmentor-test-vm').read_text()!='Isolated Augmentor Fedora GNOME qualification VM\n'
            or subprocess.check_output(['systemd-detect-virt'],text=True).strip()!='qemu'
            or subprocess.check_output(['getenforce'],text=True).strip()!='Enforcing'):
        raise RuntimeError('This target requires the dedicated ordinary-user Fedora GNOME QEMU fixture.')
    if not re.fullmatch(r'gnome-execution-probe-input-[A-Za-z0-9_-]{1,64}',args.candidate):
        raise RuntimeError('Invalid owned input candidate.')
    root=Path.home()/args.candidate
    if not root.is_dir() or root.is_symlink() or root.stat().st_uid!=os.getuid() or root.stat().st_mode&0o077:
        raise RuntimeError('The candidate directory must be private and owned.')
    for name in ('input-target-state.json','input-target-saved.json'):
        if (root/name).exists() or (root/name).is_symlink():raise RuntimeError('Use a fresh target directory; existing receipts are never overwritten.')
    env=dict(row.split('=',1) for row in subprocess.check_output(['systemctl','--user','show-environment'],text=True).splitlines() if '=' in row)
    if env.get('XDG_CURRENT_DESKTOP')!='GNOME' or env.get('XDG_SESSION_TYPE')!='wayland':raise RuntimeError('A normal GNOME Wayland session is required.')
    os.environ.update({key:value for key,value in env.items() if key in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','XDG_CURRENT_DESKTOP','XDG_SESSION_TYPE')})
    os.environ['GDK_BACKEND']=args.backend;os.umask(0o077)
    import gi
    gi.require_version('Gtk','4.0')
    from gi.repository import Gtk,Gdk
    start=(Path('/proc')/str(os.getpid())/'stat').read_text().rsplit(')',1)[1].split()[19]
    state={'format':'augmentor-owned-gnome-input-target/1','pid':os.getpid(),'startTime':start,
        'requestedBackend':args.backend,'displayType':None,'presented':False,
        'textA':'','textB':'','clicks':{'center':0,'edge':0},'saveChordCount':0}
    def write(name,value):
        temporary=root/(name+'.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(root/name)
    def save():write('input-target-state.json',state)
    save()
    application=Gtk.Application(application_id='com.augmentor.OwnedInputTarget.'+args.candidate.replace('-','_'))
    def activate(app):
        window=Gtk.ApplicationWindow(application=app,title='Owned Augmentor GNOME input fixture');window.set_default_size(800,550)
        layout=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12)
        layout.set_margin_top(20);layout.set_margin_bottom(20);layout.set_margin_start(20);layout.set_margin_end(20)
        layout.append(Gtk.Label(label='Owned synthetic input fixture — Ctrl+S saves the two text areas'))
        buffers={}
        for name,label in (('textA','Text A'),('textB','Text B')):
            layout.append(Gtk.Label(label=label));view=Gtk.TextView();view.set_size_request(-1,65)
            buffer=view.get_buffer();buffers[name]=buffer
            def changed(current,key=name):
                state[key]=current.get_text(current.get_start_iter(),current.get_end_iter(),False);save()
            buffer.connect('changed',changed);layout.append(view)
        password=Gtk.PasswordEntry();password.set_property('placeholder-text','Synthetic password refusal target');layout.append(password)
        center=Gtk.Button(label='Center target');center.set_hexpand(True);center.set_vexpand(True);layout.append(center)
        edge=Gtk.Button(label='Far edge target');edge.set_halign(Gtk.Align.END);edge.set_valign(Gtk.Align.END);layout.append(edge)
        for name,button in (('center',center),('edge',edge)):
            def clicked(_widget,key=name):state['clicks'][key]+=1;save()
            button.connect('clicked',clicked)
        keys=Gtk.EventControllerKey();keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        def pressed(_controller,keyval,_keycode,modifiers):
            if keyval not in (Gdk.KEY_s,Gdk.KEY_S) or not modifiers&Gdk.ModifierType.CONTROL_MASK:return False
            if modifiers&(Gdk.ModifierType.ALT_MASK|Gdk.ModifierType.SUPER_MASK):return False
            state['saveChordCount']+=1
            # These bytes come from the actual widget buffers at the native key
            # callback, never from a requested input string or portal reply.
            write('input-target-saved.json',{'format':'augmentor-owned-gnome-input-saved/1',
                'pid':state['pid'],'startTime':start,'saveChordCount':state['saveChordCount'],
                **{name:buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter(),False) for name,buffer in buffers.items()}})
            save();return True
        keys.connect('key-pressed',pressed);window.add_controller(keys)
        window.set_child(layout);window.present()
        state['displayType']=Gdk.Display.get_default().__gtype__.name
        if state['displayType']!={'wayland':'GdkWaylandDisplay','x11':'GdkX11Display'}[args.backend]:raise RuntimeError('The actual GTK display differs from the requested native backend.')
        state['presented']=True;save()
    application.connect('activate',activate);application.run([])


if __name__=='__main__':main()
