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
parser.add_argument('--production-adapter',action='store_true')
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
if args.production_adapter:
    paths.update({name:f'/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/com-augmentor-agent-{name}/'
                  for name in ('main','secondary')})
settings={name:Gio.Settings.new_with_path(schema,path) for name,path in paths.items()}
if parent.get_strv('custom-keybindings'):
    raise SystemExit('The ordinary fixture user must have no preexisting custom shortcuts.')
events=out/'activations.txt'
launcher=out/'fixture-launch.py'
launcher.write_text('import sys\nfrom pathlib import Path\nwith Path(sys.argv[1]).open("a") as f: f.write(sys.argv[2]+"\\n")\n')
def configure(name,binding):
    if args.production_adapter and name in ('main','secondary'):
        qt_save(name,'Ctrl+Meta+'+binding.rsplit('>',1)[-1])
        wait(lambda:settings[name].get_string('binding')==binding,'actual native setting after Qt Save')
        return
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
    if args.production_adapter:
        os.environ['QT_QPA_PLATFORM']='offscreen'
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'apps/native'))
        from PySide6.QtWidgets import QApplication,QWidget
        from PySide6.QtGui import QKeySequence,QColor
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from augmentor_linux.shortcut_settings import ShortcutSettings
        from augmentor_linux.shortcuts import current_keys
        application=QApplication([])
        class Owner(QWidget):
            accent=QColor('#50c8a0')
            def call_in_background(self,work,callback):callback(work())
        canonical=Path.home()/'.local/bin/augmentor-agent';canonical.parent.mkdir(parents=True)
        canonical.write_text('#!/usr/bin/python3\nimport sys\nfrom pathlib import Path\n'
            +'name="secondary" if sys.argv[1:]==["--instance","secondary"] else "main"\n'
            +'with Path('+repr(str(events))+').open("a") as f: f.write(name+"\\n")\n')
        canonical.chmod(0o700)
        owner=Owner();form=ShortcutSettings(owner)
        def qt_save(name,text,error=None):
            row=form.rows[name];previous=row['current'].text()
            row['editor'].setKeySequence(QKeySequence(text));application.processEvents()
            assert row['button'].isEnabled(),row['note'].text()
            QTest.mouseClick(row['button'],Qt.MouseButton.LeftButton);application.processEvents()
            if error:
                assert error in row['note'].text(),row['note'].text()
                assert row['current'].text()==previous
            else:
                assert row['note'].text().startswith('Saved.'),row['note'].text()
                assert current_keys(name)==[QKeySequence(text)[0].toCombined()]
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
    if args.production_adapter:configure('main','<Control><Super>F11')
    else:
        settings['main'].set_string('binding','<Control><Super>F11');settings['main'].apply();Gio.Settings.sync()
    time.sleep(1)
    combination(67);time.sleep(.4);assert rows()==['main','secondary'],'Old combination still invokes main'
    combination(87);wait(lambda:rows()==['main','secondary','main'],'changed shortcut delivery')
    settings['secondary'].set_string('binding','');settings['secondary'].apply();Gio.Settings.sync();time.sleep(1)
    combination(68);time.sleep(.4);assert rows()==['main','secondary','main'],'Disabled combination still invokes secondary'
    configure('secondary','<Control><Super>F10')
    daemon.terminate();daemon.wait(timeout=5)
    daemon=subprocess.Popen(['/usr/libexec/gsd-media-keys'],stdout=log,stderr=log)
    wait(owner_is_daemon,'restarted owned MediaKeys daemon');time.sleep(2)
    combination(68);wait(lambda:rows()==['main','secondary','main','secondary'],'persisted shortcut delivery after daemon restart')
    if args.production_adapter:
        qt_save('main','Ctrl+Meta+F12','already assigned to another launcher')
        qt_save('main','Ctrl+Alt+F9','already assigned in GNOME')
        portal=Gio.Settings.new('org.gnome.settings-daemon.global-shortcuts')
        portal_apps=portal.get_strv('applications')
        app_id='com.augmentor.ShortcutFixture'
        app=Gio.Settings.new_with_path('org.gnome.settings-daemon.global-shortcuts.application',
            '/org/gnome/settings-daemon/global-shortcuts/'+app_id+'/')
        app.set_value('shortcuts',GLib.Variant('a(sa{sv})',[('fixture',{'shortcuts':GLib.Variant('as',['<Primary><Super>F8'])})]))
        portal.set_strv('applications',portal_apps+[app_id]);Gio.Settings.sync()
        qt_save('secondary','Ctrl+Meta+F8','already assigned to an application')
        raw_path=paths['foreign'].replace('foreign/','foreign-raw/')
        raw=Gio.Settings.new_with_path(schema,raw_path)
        raw.set_string('binding','<Control><Super>0x4b')
        parent.set_strv('custom-keybindings',parent.get_strv('custom-keybindings')+[raw_path]);Gio.Settings.sync()
        qt_save('main','Ctrl+Meta+F9','already assigned to another launcher')
        previous_command=settings['secondary'].get_string('command')
        settings['secondary'].set_string('command','/usr/bin/false');settings['secondary'].apply();Gio.Settings.sync()
        qt_save('secondary','Ctrl+Meta+F7','foreign command')
        assert settings['secondary'].get_string('command')=='/usr/bin/false'
        settings['secondary'].set_string('command',previous_command);settings['secondary'].apply();Gio.Settings.sync()
        # Fault injection wraps only registration; all owned field writes and
        # rollback use the real dconf backend in this private session.
        import importlib.util
        spec=importlib.util.spec_from_file_location('gnome_backend',Path(__file__).resolve().parents[1]/'services/desktop/gnome_shortcuts.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        backend=module.NativeShortcuts()
        original={key:settings['secondary'].get_value(key).unpack() for key in module.FIELDS}
        parent.set_strv('custom-keybindings',[p for p in parent.get_strv('custom-keybindings') if p!=paths['secondary']]);Gio.Settings.sync()
        concurrent=paths['foreign'].replace('foreign/','foreign-concurrent/')
        class RegistrationFailure:
            first=True
            def __getattr__(self,name):return getattr(parent,name)
            def set_strv(self,key,value):
                if self.first:
                    self.first=False
                    parent.set_strv(key,parent.get_strv(key)+[concurrent]);Gio.Settings.sync()
                    raise RuntimeError('Synthetic registration failure')
                return parent.set_strv(key,value)
        backend.parent=RegistrationFailure()
        try:backend.save('secondary',{'key':{'symbol':'F6'},'modifiers':['Control','Super']})
        except RuntimeError as error:assert str(error)=='Synthetic registration failure',error
        else:raise AssertionError('Registration failure was ignored')
        wait(lambda:original=={key:settings['secondary'].get_value(key).unpack() for key in module.FIELDS},'actual owned field rollback')
        assert concurrent in parent.get_strv('custom-keybindings')
        assert paths['secondary'] not in parent.get_strv('custom-keybindings')
        class ForeignTakeover(RegistrationFailure):
            def set_strv(self,key,value):
                if self.first:
                    self.first=False
                    replacement=Gio.Settings.new_with_path(schema,paths['secondary'])
                    replacement.set_string('name','Foreign takeover')
                    replacement.set_string('command','/usr/bin/false')
                    replacement.set_string('binding','<Control><Super>F5')
                    parent.set_strv(key,value);Gio.Settings.sync()
                    raise RuntimeError('Synthetic foreign takeover')
                return parent.set_strv(key,value)
        backend.parent=ForeignTakeover()
        try:backend.save('secondary',{'key':{'symbol':'F6'},'modifiers':['Control','Super']})
        except RuntimeError as error:assert str(error)=='Synthetic foreign takeover',error
        else:raise AssertionError('Foreign takeover was ignored')
        wait(lambda:settings['secondary'].get_string('command')=='/usr/bin/false','foreign takeover visibility')
        assert paths['secondary'] in parent.get_strv('custom-keybindings')
        assert settings['secondary'].get_string('name')=='Foreign takeover'
        assert settings['secondary'].get_string('binding')=='<Control><Super>F5'
        for key,value in original.items():settings['secondary'].set_value(key,GLib.Variant('b' if isinstance(value,bool) else 's',value))
        settings['secondary'].apply();Gio.Settings.sync()
        parent.set_strv('custom-keybindings',parent.get_strv('custom-keybindings')+[paths['secondary']]);Gio.Settings.sync()
        owner.close()
    assert paths['foreign'] in parent.get_strv('custom-keybindings')
    assert foreign=={key:settings['foreign'].get_value(key).print_(True) for key in settings['foreign'].list_keys()}
    report={'format':'augmentor-gnome-native-shortcut-mechanism/1',
            'proofScriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'compositor':'GNOME Shell 50.5','privateCompositorOwnerMatches':True,
            'ordinaryPrivateUser':True,'syntheticInput':True,'hostInputDevicesMounted':False,
            'twoBindingsDelivered':True,'changedBindingReleasesPrevious':True,
            'emptyBindingDisables':True,'daemonRestartRestores':True,'foreignSettingsPreserved':True,
            'activationEvents':rows(),'productionAdapterTested':args.production_adapter,
            'sharedQtShortcutSettingsSaveTested':args.production_adapter,
            'canonicalLauncherCommandTested':args.production_adapter,
            'conflictRefusalTested':args.production_adapter,
            'systemCustomPortalAndHardwareConflictsTested':args.production_adapter,
            'foreignOwnedPathRefused':args.production_adapter,
            'failedRegistrationRollsBackOwnedValues':args.production_adapter,
            'foreignConcurrentAdditionRetained':args.production_adapter,
            'foreignTakeoverRetained':args.production_adapter,
            'actualAugmentorClosedLaunchTested':False,'focusTested':False,
            'physicalKeyTested':False,'realLoginRebootTested':False,'portalConsentTested':False}
    if args.production_adapter:
        root=Path(__file__).resolve().parents[1]
        report['adapterSourceSha256']={path:hashlib.sha256((root/path).read_bytes()).hexdigest()
            for path in ('services/desktop/gnome_shortcuts.py','apps/native/augmentor_linux/gnome_shortcuts.py',
                         'apps/native/augmentor_linux/shortcuts.py','apps/native/augmentor_linux/shortcut_settings.py')}
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
