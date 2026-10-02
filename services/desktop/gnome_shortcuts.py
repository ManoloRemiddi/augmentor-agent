#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Own two native GNOME launcher bindings; settings success is not grab delivery."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import sys

MEDIA='org.gnome.settings-daemon.plugins.media-keys'
CUSTOM=MEDIA+'.custom-keybinding'
PORTAL='org.gnome.settings-daemon.global-shortcuts'
PREFIX='/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/com-augmentor-agent-'
FIELDS=('name','binding','command')
SYSTEM_SCHEMAS=('org.gnome.desktop.wm.keybindings','org.gnome.mutter.keybindings',
                'org.gnome.mutter.wayland.keybindings','org.gnome.shell.keybindings',MEDIA)
MODIFIERS=('Shift','Control','Alt','Super')


def settings_profile(version,source):
    """Explicit schema generations; readback never proves shortcut delivery.

    GSD 46 assigns custom bindings NORMAL|OVERVIEW (LAUNCHER), excluding
    lock/unlock. GSD 48/50 additionally expose enable-in-lockscreen.
    """
    if not isinstance(version,str) or not re.fullmatch(r'(?:46|48|50)\.\d+(?:\.\d+)?',version):
        raise RuntimeError('The native GNOME shortcut adapter supports GNOME 46, 48 and 50 profiles.')
    custom=source.lookup(CUSTOM,True)
    if not custom or any(not custom.has_key(key) for key in FIELDS):
        raise RuntimeError('Required GNOME custom shortcut settings are unavailable.')
    fields=FIELDS
    if custom.has_key('enable-in-lockscreen'):fields+=('enable-in-lockscreen',)
    elif version.startswith(('48.','50.')):
        raise RuntimeError('Required GNOME lock-screen shortcut setting is unavailable.')
    if any(custom.get_key(key).get_value_type().dup_string()!=('b' if key=='enable-in-lockscreen' else 's') for key in fields):
        raise RuntimeError('GNOME custom shortcut settings have unexpected types.')
    portal=source.lookup(PORTAL,True)
    application=source.lookup(PORTAL+'.application',True)
    if bool(portal)!=bool(application) or (version.startswith(('48.','50.')) and not portal):
        raise RuntimeError('Required GNOME portal shortcut settings are unavailable.')
    if portal and (not portal.has_key('applications') or not application.has_key('shortcuts')):
        raise RuntimeError('GNOME portal shortcut settings are incomplete.')
    if portal and (portal.get_key('applications').get_value_type().dup_string()!='as' or
                   application.get_key('shortcuts').get_value_type().dup_string()!='a(sa{sv})'):
        raise RuntimeError('GNOME portal shortcut settings have unexpected types.')
    return fields,bool(portal)


def instance_name(value):
    if value not in ('main','secondary'):
        raise ValueError('Choose the first or second agent shortcut.')
    return value


@contextmanager
def locked():
    root=Path(os.environ.get('XDG_RUNTIME_DIR',f'/tmp/augmentor-{os.getuid()}'))
    root.mkdir(mode=0o700,parents=True,exist_ok=True)
    info=root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:
        raise RuntimeError('GNOME shortcut changes require your private runtime directory.')
    descriptor=os.open(root/'augmentor-gnome-shortcuts.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        info=os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:
            raise RuntimeError('The GNOME shortcut lock is not owned privately by you.')
        try:fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Another window is saving shortcuts. Try again.') from None
        yield
    finally:os.close(descriptor)


class NativeShortcuts:
    def __init__(self):
        if sys.platform!='linux' or 'GNOME' not in os.environ.get('XDG_CURRENT_DESKTOP','').upper().split(':'):
            raise RuntimeError('GNOME launcher shortcuts require a GNOME session.')
        import gi
        gi.require_version('Gtk','4.0')
        from gi.repository import Gio,GLib,Gtk,Gdk
        self.Gio,self.GLib,self.Gtk,self.Gdk=Gio,GLib,Gtk,Gdk
        self.modifiers=dict(zip(MODIFIERS,(Gdk.ModifierType.SHIFT_MASK,Gdk.ModifierType.CONTROL_MASK,
                                         Gdk.ModifierType.ALT_MASK,Gdk.ModifierType.SUPER_MASK)))
        self.source=Gio.SettingsSchemaSource.get_default()
        self.bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
        def owner(name):
            return self.bus.call_sync('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus',
                'GetNameOwner',GLib.Variant('(s)',(name,)),None,Gio.DBusCallFlags.NO_AUTO_START,500,None).unpack()[0]
        shell=owner('org.gnome.Shell');owner('org.gnome.SettingsDaemon.MediaKeys')
        version=self.bus.call_sync(shell,'/org/gnome/Shell','org.freedesktop.DBus.Properties','Get',
            GLib.Variant('(ss)',('org.gnome.Shell','ShellVersion')),None,
            Gio.DBusCallFlags.NO_AUTO_START,500,None).unpack()[0]
        self.fields,self.portal_available=settings_profile(version,self.source)
        if not Gtk.init_check():raise RuntimeError('GNOME shortcut conversion requires the current graphical display.')
        self.display=Gdk.Display.get_default()
        for schema in (MEDIA,CUSTOM,*SYSTEM_SCHEMAS,'org.gnome.mutter'):
            if not self.source.lookup(schema,True):
                raise RuntimeError('Required GNOME shortcut settings are unavailable.')
        self.parent=Gio.Settings.new(MEDIA)

    def custom(self,path):
        if not re.fullmatch(r'/[A-Za-z0-9_./-]+/',path) or '..' in path or '//' in path:
            raise RuntimeError('GNOME contains an invalid custom shortcut path; review Keyboard Settings.')
        return self.Gio.Settings.new_with_path(CUSTOM,path)

    def launcher(self,name,required=False):
        path=Path.home()/'.local/bin/augmentor-agent'
        if required and (not path.is_file() or not os.access(path,os.X_OK)):
            raise RuntimeError('Install the canonical Augmentor desktop launcher before saving a shortcut.')
        argv=[str(path)] + ([] if name=='main' else ['--instance','secondary'])
        return ' '.join(self.GLib.shell_quote(value) for value in argv)

    def owned(self,name,entry):
        command=entry.get_string('command')
        if command:
            try:_,argv=self.GLib.shell_parse_argv(command)
            except self.GLib.Error:raise RuntimeError('The Augmentor shortcut path has a foreign command; no settings were changed.') from None
            expected=[str(Path.home()/'.local/bin/augmentor-agent')]+([] if name=='main' else ['--instance','secondary'])
            if argv!=expected:
                raise RuntimeError('The Augmentor shortcut path has a foreign command; no settings were changed.')
        elif entry.get_string('name') or entry.get_string('binding'):
            raise RuntimeError('The Augmentor shortcut path is already occupied; no settings were changed.')

    def normalize(self,binding):
        if not isinstance(binding,str) or len(binding)>256 or not binding or binding=='disabled':return []
        bindings=[binding]
        if 'Above_Tab' in binding:
            valid,_,symbols=self.display.map_keycode(49) # evdev KEY_GRAVE plus XKB offset.
            names=[self.Gdk.keyval_name(key) for key in set(symbols)] if valid else []
            bindings=[binding.replace('Above_Tab',name) for name in names if name]
        values=[]
        for value in bindings:
            valid,key,codes,mods=self.Gtk.accelerator_parse_with_keycode(value,self.display)
            if not valid:continue
            if key==self.Gdk.KEY_ISO_Left_Tab:key=self.Gdk.KEY_Tab
            if key==self.Gdk.KEY_Sys_Req and mods&self.Gdk.ModifierType.ALT_MASK:key=self.Gdk.KEY_Print
            values.append((key,frozenset(codes or []),int(mods)&~int(self.Gdk.ModifierType.LOCK_MASK)))
        return values

    def overlaps(self,first,second):
        return any(mods==other_mods and ((key and key==other_key) or bool(codes&other_codes))
                   for key,codes,mods in first for other_key,other_codes,other_mods in second)

    def encode(self,request):
        key=request.get('key',{})
        modifiers=request.get('modifiers',[])
        if not isinstance(key,dict) or not isinstance(modifiers,list) or any(m not in MODIFIERS for m in modifiers) or len(set(modifiers))!=len(modifiers):
            raise ValueError('Unsupported GNOME shortcut combination.')
        if set(key)=={'character'} and isinstance(key['character'],str) and len(key['character'])==1:
            value=self.Gdk.unicode_to_keyval(ord(key['character']))
        elif set(key)=={'symbol'} and isinstance(key['symbol'],str) and len(key['symbol'])<64:
            value=self.Gdk.keyval_from_name(key['symbol'])
        else:raise ValueError('Unsupported GNOME shortcut key.')
        mods=sum(int(self.modifiers[m]) for m in modifiers)
        if not value or not self.Gtk.accelerator_valid(value,self.Gdk.ModifierType(mods)):
            raise ValueError('GNOME cannot assign that key combination. Choose another shortcut.')
        return self.Gtk.accelerator_name(value,self.Gdk.ModifierType(mods))

    def describe(self,binding):
        valid,key,mask=self.Gtk.accelerator_parse(binding)
        if not valid or not key:return None
        mods=int(mask)
        supported=sum(int(value) for value in self.modifiers.values())
        if mods&~supported:raise ValueError('This GNOME binding uses unsupported modifiers. Review Keyboard Settings.')
        character=self.Gdk.keyval_to_unicode(key)
        return {'symbol':self.Gdk.keyval_name(key),'character':chr(character) if character else None,
                'modifiers':[name for name in MODIFIERS if mods&int(self.modifiers[name])],
                'binding':self.Gtk.accelerator_name(key,self.Gdk.ModifierType(mods))}

    def conflicts(self,binding,path):
        requested=self.normalize(binding)
        for schema in SYSTEM_SCHEMAS:
            settings=self.Gio.Settings.new(schema)
            for key in self.source.lookup(schema,True).list_keys():
                value=settings.get_value(key).unpack()
                if schema==MEDIA and key=='custom-keybindings':continue
                values=[value] if isinstance(value,str) else value if isinstance(value,list) else []
                if any(self.overlaps(self.normalize(v),requested) for v in values if isinstance(v,str)):
                    raise ValueError('That shortcut is already assigned in GNOME. Choose another combination.')
        mutter=self.Gio.Settings.new('org.gnome.mutter')
        for key in ('overlay-key','locate-pointer-key'):
            if self.overlaps(self.normalize(mutter.get_string(key)),requested):
                raise ValueError('That shortcut is already assigned in GNOME. Choose another combination.')
        for other in self.parent.get_strv('custom-keybindings'):
            if other!=path and self.overlaps(self.normalize(self.custom(other).get_string('binding')),requested):
                raise ValueError('That shortcut is already assigned to another launcher. Choose another combination.')
        if not self.portal_available:return
        portal=self.Gio.Settings.new(PORTAL)
        for app in portal.get_strv('applications'):
            if not re.fullmatch(r'[A-Za-z0-9_.-]{1,255}',app):
                raise RuntimeError('GNOME contains an invalid portal shortcut identity; review Keyboard Settings.')
            settings=self.Gio.Settings.new_with_path(PORTAL+'.application','/org/gnome/settings-daemon/global-shortcuts/'+app+'/')
            for _,properties in settings.get_value('shortcuts').unpack():
                values=properties.get('shortcuts',[])
                if not isinstance(values,list) or any(not isinstance(value,str) for value in values):
                    raise RuntimeError('GNOME contains an invalid portal binding; review Keyboard Settings.')
                if any(self.overlaps(self.normalize(v),requested) for v in values if isinstance(v,str)):
                    raise ValueError('That shortcut is already assigned to an application. Choose another combination.')

    def read(self,name):
        name=instance_name(name);path=PREFIX+name+'/'
        entry=self.custom(path);self.owned(name,entry)
        binding=entry.get_string('binding') if path in self.parent.get_strv('custom-keybindings') and entry.get_string('command') else ''
        key=self.describe(binding)
        if binding not in ('','disabled') and key is None:
            raise ValueError('This GNOME binding cannot be represented in the editor. Review Keyboard Settings.')
        return {'schema':1,'configured':key is not None,'key':key,'functionalTested':False}

    def save(self,name,request):
        name=instance_name(name);path=PREFIX+name+'/'
        binding=self.encode(request);command=self.launcher(name,required=True)
        with locked():
            entry=self.custom(path);self.owned(name,entry);self.conflicts(binding,path)
            if not self.parent.is_writable('custom-keybindings') or not all(entry.is_writable(key) for key in self.fields):
                raise RuntimeError('GNOME shortcut settings are locked; no assignment was changed.')
            before={key:entry.get_value(key) for key in self.fields}
            added=path not in self.parent.get_strv('custom-keybindings')
            desired={'name':'Augmentor Agent'+(' — Second window' if name=='secondary' else ''),
                     'binding':binding,'command':command}
            if 'enable-in-lockscreen' in self.fields:desired['enable-in-lockscreen']=False
            try:
                entry.delay()
                for key,value in desired.items():
                    variant=self.GLib.Variant('b' if isinstance(value,bool) else 's',value)
                    if not entry.set_value(key,variant):raise RuntimeError('GNOME refused this shortcut assignment.')
                entry.apply();self.Gio.Settings.sync()
                latest=self.parent.get_strv('custom-keybindings')
                if path not in latest and not self.parent.set_strv('custom-keybindings',latest+[path]):
                    raise RuntimeError('GNOME refused this shortcut registration.')
                self.Gio.Settings.sync()
                observed=self.custom(path)
                if any(observed.get_value(key).unpack()!=value for key,value in desired.items()) or path not in self.parent.get_strv('custom-keybindings'):
                    raise RuntimeError('GNOME shortcut settings changed during Save. Reload shortcuts and try again.')
            except Exception:
                # A foreign takeover must survive rollback, including registration.
                observed=self.custom(path)
                current_command=observed.get_string('command')
                if added and current_command==desired['command']:
                    latest=self.parent.get_strv('custom-keybindings')
                    self.parent.set_strv('custom-keybindings',[p for p in latest if p!=path])
                entry.revert()
                if current_command in (desired['command'],before['command'].unpack()):
                    observed.delay()
                    for key,value in before.items():
                        if observed.get_value(key).unpack()==desired[key]:observed.set_value(key,value)
                    observed.apply()
                self.Gio.Settings.sync()
                raise
            return self.read(name)


def main():
    request=json.loads(sys.stdin.read(4097))
    if not isinstance(request,dict) or request.get('schema')!=1:
        raise ValueError('Unknown GNOME shortcut request.')
    backend=NativeShortcuts()
    action=request.get('action');name=instance_name(request.get('instance'))
    if action=='read':return backend.read(name)
    if action=='save':return backend.save(name,request)
    raise ValueError('Unknown GNOME shortcut action.')


if __name__=='__main__':
    try:print(json.dumps(main()))
    except Exception as error:
        print(json.dumps({'schema':1,'error':str(error),'kind':'invalid' if isinstance(error,ValueError) else 'unavailable'}))
        raise SystemExit(1)
