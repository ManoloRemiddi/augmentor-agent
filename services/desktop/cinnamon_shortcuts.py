#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Own numeric Cinnamon custom rows through a fresh, read-only bridge snapshot.

No capture/input permission is granted. Settings and native-grab readback are
distinct from actual physical shortcut delivery. Run GTK3 in this helper process.
"""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import time

PARENT='org.cinnamon.desktop.keybindings'
CUSTOM=PARENT+'.custom-keybinding'
FIELDS=('name','command','binding')
PREFIX='/org/cinnamon/desktop/keybindings/custom-keybindings/'
SYSTEM_SCHEMAS=(PARENT,PARENT+'.wm',PARENT+'.media-keys')
MODIFIERS=('Shift','Control','Alt','Super')


class OwnershipCommittedError(RuntimeError):
    """The new ownership file is installed; rolling back settings would orphan it."""


def instance_name(value):
    if value not in ('main','secondary'):raise ValueError('Choose the first or second agent shortcut.')
    return value


def private_directory(path):
    if not path.is_absolute():raise RuntimeError('Shortcut storage requires an absolute private directory.')
    path.mkdir(mode=0o700,parents=True,exist_ok=True);info=path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:
        raise RuntimeError('Cinnamon shortcut storage is not privately owned by you.')
    return path


@contextmanager
def locked():
    root=private_directory(Path(os.environ.get('XDG_RUNTIME_DIR',f'/tmp/augmentor-{os.getuid()}')))
    descriptor=os.open(root/'augmentor-cinnamon-shortcuts.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        info=os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077 or info.st_nlink!=1:
            raise RuntimeError('The Cinnamon shortcut lock is not privately owned by you.')
        try:fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Another window is saving shortcuts. Try again.') from None
        yield
    finally:os.close(descriptor)


class NativeShortcuts:
    def __init__(self):
        if sys.platform!='linux' or 'X-CINNAMON' not in os.environ.get('XDG_CURRENT_DESKTOP','').upper().split(':'):
            raise RuntimeError('Cinnamon launcher shortcuts require a Cinnamon session.')
        import gi
        gi.require_version('Gtk','3.0')
        from gi.repository import Gio,GLib,Gtk,Gdk
        self.Gio,self.GLib,self.Gtk,self.Gdk=Gio,GLib,Gtk,Gdk
        if not Gtk.init_check()[0]:raise RuntimeError('Cinnamon shortcut conversion requires your graphical display.')
        self.display=Gdk.Display.get_default();self.source=Gio.SettingsSchemaSource.get_default()
        self.modifiers=dict(zip(MODIFIERS,(Gdk.ModifierType.SHIFT_MASK,Gdk.ModifierType.CONTROL_MASK,
            Gdk.ModifierType.MOD1_MASK,Gdk.ModifierType.SUPER_MASK)))
        for schema in (*SYSTEM_SCHEMAS,CUSTOM):
            if not self.source.lookup(schema,True):raise RuntimeError('Required Cinnamon shortcut settings are unavailable.')
        parent=self.source.lookup(PARENT,True);custom=self.source.lookup(CUSTOM,True)
        if parent.get_key('custom-list').get_value_type().dup_string()!='as' or any(
                custom.get_key(key).get_value_type().dup_string()!=('as' if key=='binding' else 's') for key in FIELDS):
            raise RuntimeError('Cinnamon shortcut settings have unsupported types.')
        self.parent=Gio.Settings.new(PARENT);self.bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
        self.owner=self.native_owner()
        version=self.bus.call_sync(self.owner,'/org/Cinnamon','org.freedesktop.DBus.Properties','Get',
            GLib.Variant('(ss)',('org.Cinnamon','CinnamonVersion')),GLib.VariantType.new('(v)'),
            Gio.DBusCallFlags.NO_AUTO_START,2000,None).unpack()[0]
        if version!='6.6.4' or self.native_owner()!=self.owner:
            raise RuntimeError('The Cinnamon shortcut adapter requires the reviewed 6.6.4 X11 profile.')
        self.epoch=None;self.bridge('Status')
        state=Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))
        self.state=state/'augmentor-shortcuts/cinnamon.json'

    def native_owner(self):
        owner=self.bus.call_sync('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus',
            'GetNameOwner',self.GLib.Variant('(s)',('org.Cinnamon',)),self.GLib.VariantType.new('(s)'),
            self.Gio.DBusCallFlags.NO_AUTO_START,500,None).unpack()[0]
        if not re.fullmatch(r':\d+\.\d+',owner):raise RuntimeError('Cinnamon has an invalid session owner.')
        return owner

    def bridge(self,method):
        if self.native_owner()!=self.owner:raise RuntimeError('Cinnamon restarted. Reload shortcuts and try again.')
        raw=self.bus.call_sync(self.owner,'/com/augmentor/CinnamonBridge','com.augmentor.CinnamonBridge',method,
            None,self.GLib.VariantType.new('(s)'),self.Gio.DBusCallFlags.NO_AUTO_START,2000,None).unpack()[0]
        if not isinstance(raw,str) or len(raw.encode())>131072 or self.native_owner()!=self.owner:
            raise RuntimeError('Cinnamon returned an invalid shortcut observation.')
        value=json.loads(raw)
        if not isinstance(value,dict) or not isinstance(value.get('lock'),dict):
            raise RuntimeError('Cinnamon returned an invalid shortcut observation.')
        lock=value['lock']
        if (type(value.get('schema')) is not int or value['schema']!=1 or value.get('backend')!='cinnamon-shortcut-bridge' or
                value.get('cinnamonVersion')!='6.6.4' or value.get('sessionType')!='x11' or
                value.get('readOnly') is not True or value.get('inputQualified') is not False or
                value.get('sceneObserverQualified') is not False or value.get('completeRegistryHistoryTracking') is not False or
                not isinstance(value.get('epoch'),str) or not re.fullmatch(r'[a-f0-9-]{36}',value['epoch']) or
                lock.get('state') not in ('unknown','active','inactive') or type(lock.get('generation')) is not int or
                lock['generation']<1 or type(lock.get('queryPending')) is not bool or
                (lock.get('owner') is not None and (not isinstance(lock['owner'],str) or not re.fullmatch(r':\d+\.\d+',lock['owner']))) or
                (lock['state']!='unknown' and lock.get('owner') is None)):
            raise RuntimeError('Cinnamon returned an invalid shortcut observation.')
        if self.epoch is not None and value['epoch']!=self.epoch:
            raise RuntimeError('The Cinnamon shortcut bridge restarted. Reload shortcuts and try again.')
        self.epoch=value['epoch']
        if method=='ShortcutBindings':
            records=value.get('bindings')
            if (not isinstance(records,list) or len(records)>1024 or type(value.get('registryPending')) is not bool or
                    type(value.get('registrySerial')) is not int or not 1<=value['registrySerial']<=2**53-1 or
                    not isinstance(value.get('snapshotSignature'),str) or not re.fullmatch(r'[a-f0-9]{64}',value['snapshotSignature'])):
                raise RuntimeError('Cinnamon returned an invalid shortcut inventory.')
            for row in records:
                if (not isinstance(row,dict) or set(row)!= {'name','accelerators'} or not isinstance(row['name'],str) or
                        len(row['name'])>512 or not isinstance(row['accelerators'],list) or len(row['accelerators'])>64 or
                        any(not isinstance(s,str) or len(s)>512 for s in row['accelerators'])):
                    raise RuntimeError('Cinnamon returned an invalid shortcut inventory.')
        return value

    def snapshot(self):
        self.bridge('RefreshLock');deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            status=self.bridge('Status');lock=status['lock']
            if lock['state']=='active':raise RuntimeError('Unlock Cinnamon before changing a shortcut.')
            if lock['state']=='inactive' and not lock['queryPending']:
                value=self.bridge('ShortcutBindings')
                if value['lock']!=lock or value['registryPending']:
                    raise RuntimeError('Cinnamon shortcuts changed while checking. Try again.')
                return value
            if not lock['queryPending']:raise RuntimeError('Cinnamon lock state is unknown. Try a fresh shortcut check.')
            time.sleep(.02)
        raise RuntimeError('Cinnamon lock verification timed out. Try again.')

    def private_json(self,path,limit):
        private_directory(path.parent)
        descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(descriptor,'rb') as stream:
            info=os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077 or info.st_nlink!=1:
                raise RuntimeError('Cinnamon shortcut ownership is not privately stored.')
            raw=stream.read(limit+1)
        if len(raw)>limit:raise RuntimeError('Cinnamon shortcut ownership is too large.')
        return json.loads(raw)

    def mapping(self):
        if not self.state.exists() and not self.state.is_symlink():return {'schema':1,'instances':{}}
        return self.valid_mapping(self.private_json(self.state,32768))

    def valid_mapping(self,value):
        if (not isinstance(value,dict) or type(value.get('schema')) is not int or value['schema']!=1 or
                set(value)!={'schema','instances'} or not isinstance(value.get('instances'),dict) or set(value['instances'])-{'main','secondary'}):
            raise RuntimeError('Cinnamon shortcut ownership is invalid.')
        ids=[]
        for name,row in value['instances'].items():
            if (not isinstance(row,dict) or set(row)!={'id',*FIELDS} or not isinstance(row['id'],str) or not re.fullmatch(r'custom\d{1,5}',row['id']) or
                    not isinstance(row['name'],str) or not isinstance(row['command'],str) or not isinstance(row['binding'],list) or
                    any(not isinstance(s,str) or len(s)>256 for s in row['binding'])):
                raise RuntimeError('Cinnamon shortcut ownership is invalid.')
            ids.append(row['id'])
        if len(ids)!=len(set(ids)):raise RuntimeError('Cinnamon shortcut ownership contains duplicate rows.')
        return value

    @property
    def pending_path(self):return self.state.with_name('cinnamon.pending.json')

    def persist(self,value,path=None):
        path=path or self.state;private_directory(path.parent)
        descriptor,name=tempfile.mkstemp(prefix='.cinnamon-',dir=path.parent)
        try:
            with os.fdopen(descriptor,'w') as stream:
                json.dump(value,stream);stream.write('\n');stream.flush();os.fsync(stream.fileno())
            Path(name).replace(path)
            try:
                descriptor=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
                try:os.fsync(descriptor)
                finally:os.close(descriptor)
            except OSError as error:
                if path!=self.state:
                    raise RuntimeError('Shortcut recovery intent was stored, but its durability was not confirmed. No new assignment was made. Retry Save to recover.') from error
                raise OwnershipCommittedError('The assignment and ownership were saved, but durability could not be confirmed. Retry Save to finish owned recovery.') from error
        finally:Path(name).unlink(missing_ok=True)

    def pending(self):
        if not self.pending_path.exists() and not self.pending_path.is_symlink():return None
        value=self.private_json(self.pending_path,131072)
        if (not isinstance(value,dict) or set(value)!={'schema','instance','beforeMapping','afterMapping','beforeUser','beforeEffective','added'} or
                type(value['schema']) is not int or value['schema']!=1 or value['instance'] not in ('main','secondary') or
                type(value['added']) is not bool):raise RuntimeError('Cinnamon shortcut recovery intent is invalid.')
        before=self.valid_mapping(value['beforeMapping']);after=self.valid_mapping(value['afterMapping'])
        name=value['instance'];row=after['instances'].get(name)
        if (row is None or {k:v for k,v in before['instances'].items() if k!=name}!=
                {k:v for k,v in after['instances'].items() if k!=name} or
                (name in before['instances'] and before['instances'][name]['id']!=row['id'])):
            raise RuntimeError('Cinnamon shortcut recovery intent changes unrelated ownership.')
        for field in ('beforeUser','beforeEffective'):
            fields=value[field]
            if not isinstance(fields,dict) or set(fields)!=set(FIELDS):raise RuntimeError('Cinnamon shortcut recovery fields are invalid.')
            for key,data in fields.items():
                if data is None and field=='beforeUser':continue
                if key=='binding':
                    if not isinstance(data,list) or len(data)>64 or any(not isinstance(s,str) or len(s)>512 for s in data):
                        raise RuntimeError('Cinnamon shortcut recovery fields are invalid.')
                elif not isinstance(data,str) or len(data)>32768:raise RuntimeError('Cinnamon shortcut recovery fields are invalid.')
        return value

    def clear_pending(self):
        self.pending_path.unlink()
        descriptor=os.open(self.state.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)

    def user_values(self,entry):
        return {key:value.unpack() if value is not None else None for key in FIELDS
            for value in (entry.get_user_value(key),)}

    def restore_intent(self,intent):
        """Restore only the exact intended row; retain uncertain/foreign state."""
        row=intent['afterMapping']['instances'][intent['instance']];entry=self.custom(row['id'])
        desired={key:row[key] for key in FIELDS}
        if self.values(entry)==desired:
            entry.delay()
            for key,value in intent['beforeUser'].items():
                if value is None:entry.reset(key)
                elif not entry.set_value(key,self.GLib.Variant('as' if key=='binding' else 's',value)):
                    entry.revert();raise RuntimeError('Cinnamon refused shortcut recovery. Intent was retained.')
            entry.apply();self.Gio.Settings.sync()
        if self.user_values(self.custom(row['id']))!=intent['beforeUser'] or self.values(self.custom(row['id']))!=intent['beforeEffective']:
            raise RuntimeError('Interrupted shortcut settings changed outside Augmentor. Recovery intent was retained; no foreign settings were changed.')
        ids=self.parent.get_strv('custom-list')
        if intent['added']:ids=[value for value in ids if value!=row['id']]
        ids=[value for value in ids if value!='__dummy__'] if '__dummy__' in ids else ids+['__dummy__']
        if not self.parent.set_strv('custom-list',ids):raise RuntimeError('Cinnamon refused shortcut recovery registration. Intent was retained.')
        self.Gio.Settings.sync()

    def recover_pending(self):
        intent=self.pending()
        if intent is None:return
        mapping=self.mapping();row=intent['afterMapping']['instances'][intent['instance']]
        if mapping==intent['afterMapping']:
            self.owned(row)
            if row['id'] not in self.parent.get_strv('custom-list'):
                raise RuntimeError('Interrupted shortcut registration changed outside Augmentor. Recovery intent was retained.')
        elif mapping==intent['beforeMapping']:self.restore_intent(intent)
        else:raise RuntimeError('Shortcut ownership changed during interruption. Recovery intent was retained.')
        self.clear_pending()

    def custom(self,id):
        if not isinstance(id,str) or not re.fullmatch(r'custom\d{1,5}',id):
            raise RuntimeError('Cinnamon contains an unsupported custom shortcut ID. Review Keyboard Settings.')
        return self.Gio.Settings.new_with_path(CUSTOM,PREFIX+id+'/')

    def values(self,entry):return {key:entry.get_value(key).unpack() for key in FIELDS}

    def owned(self,row):
        entry=self.custom(row['id'])
        if self.values(entry)!={key:row[key] for key in FIELDS}:
            raise RuntimeError('That Cinnamon shortcut was changed outside Augmentor. No foreign settings were changed.')
        return entry

    def launcher(self,name):
        path=Path.home()/'.local/bin/augmentor-agent'
        if not path.is_file() or not os.access(path,os.X_OK):
            raise RuntimeError('Install the canonical Augmentor desktop launcher before saving a shortcut.')
        argv=[str(path)]+([] if name=='main' else ['--instance','secondary'])
        command=' '.join(self.GLib.shell_quote(value) for value in argv)
        if self.GLib.shell_parse_argv(command)[1]!=argv:raise RuntimeError('The canonical shortcut command cannot be represented.')
        return command

    def normalize(self,binding):
        if not isinstance(binding,str) or not binding or binding=='disabled' or len(binding)>512:return []
        values=[binding]
        if 'Above_Tab' in binding:
            valid,_keys,symbols=self.Gdk.Keymap.get_for_display(self.display).get_entries_for_keycode(49)
            values=[binding.replace('Above_Tab',self.Gdk.keyval_name(key)) for key in set(symbols)] if valid else []
        result=[]
        for value in values:
            key,codes,mods=self.Gtk.accelerator_parse_with_keycode(value)
            if not key and not codes:continue
            if key==self.Gdk.KEY_ISO_Left_Tab:key=self.Gdk.KEY_Tab
            if key==self.Gdk.KEY_Sys_Req and mods&self.Gdk.ModifierType.MOD1_MASK:key=self.Gdk.KEY_Print
            result.append((key,frozenset(codes or []),int(mods)&~int(self.Gdk.ModifierType.LOCK_MASK)))
        return result

    def overlaps(self,first,second):
        return any(mods==other_mods and ((key and key==other_key) or bool(codes&other_codes))
            for key,codes,mods in first for other_key,other_codes,other_mods in second)

    def encode(self,request):
        key=request.get('key',{});modifiers=request.get('modifiers',[])
        if (not isinstance(key,dict) or not isinstance(modifiers,list) or any(m not in MODIFIERS for m in modifiers) or
                len(modifiers)!=len(set(modifiers))):raise ValueError('Unsupported Cinnamon shortcut combination.')
        if set(key)=={'character'} and isinstance(key['character'],str) and len(key['character'])==1:
            value=self.Gdk.unicode_to_keyval(ord(key['character']))
        elif set(key)=={'symbol'} and isinstance(key['symbol'],str) and len(key['symbol'])<64:
            value=self.Gdk.keyval_from_name(key['symbol'])
        else:raise ValueError('Unsupported Cinnamon shortcut key.')
        mods=self.Gdk.ModifierType(sum(int(self.modifiers[m]) for m in modifiers))
        if not value or not self.Gtk.accelerator_valid(value,mods):
            raise ValueError('Cinnamon cannot assign that combination. Choose another shortcut.')
        return self.Gtk.accelerator_name(value,mods)

    def describe(self,binding):
        key,mods=self.Gtk.accelerator_parse(binding)
        if not key:return None
        supported=sum(int(value) for value in self.modifiers.values())
        if int(mods)&~supported:raise ValueError('This Cinnamon binding uses unsupported modifiers. Review Keyboard Settings.')
        character=self.Gdk.keyval_to_unicode(key)
        return {'symbol':self.Gdk.keyval_name(key),'character':chr(character) if character else None,
            'modifiers':[name for name in MODIFIERS if int(mods)&int(self.modifiers[name])],
            'binding':self.Gtk.accelerator_name(key,mods)}

    def conflicts(self,binding,id,snapshot):
        requested=self.normalize(binding)
        if not requested:raise ValueError('Cinnamon cannot normalize that shortcut combination.')
        for schema in SYSTEM_SCHEMAS:
            settings=self.Gio.Settings.new(schema)
            for key in self.source.lookup(schema,True).list_keys():
                if schema==PARENT and key=='custom-list':continue
                value=settings.get_value(key).unpack()
                candidates=[value] if isinstance(value,str) else value if isinstance(value,list) else []
                if any(self.overlaps(self.normalize(v),requested) for v in candidates if isinstance(v,str)):
                    raise ValueError('That shortcut is already assigned in Cinnamon. Choose another combination.')
        for other in self.parent.get_strv('custom-list'):
            if other not in (id,'__dummy__'):
                if any(self.overlaps(self.normalize(v),requested) for v in self.custom(other).get_strv('binding')):
                    raise ValueError('That shortcut is already assigned to another launcher. Choose another combination.')
        for row in snapshot['bindings']:
            if row['name']!=id and any(self.overlaps(self.normalize(v),requested) for v in row['accelerators']):
                raise ValueError('That shortcut is already assigned to a Cinnamon component. Choose another combination.')

    def read(self,name):
        if self.pending() is not None:
            raise RuntimeError('A shortcut Save was interrupted. Retry Save to recover its owned assignment.')
        name=instance_name(name);self.bridge('Status');row=self.mapping()['instances'].get(name)
        if row is None:return {'schema':1,'configured':False,'key':None,'functionalTested':False}
        entry=self.owned(row);binding=entry.get_strv('binding') if row['id'] in self.parent.get_strv('custom-list') else []
        if len(binding)>1:raise ValueError('This Cinnamon shortcut has multiple bindings. Review Keyboard Settings.')
        key=self.describe(binding[0]) if binding else None
        if binding and key is None:raise ValueError('This Cinnamon binding cannot be represented in the editor.')
        return {'schema':1,'configured':key is not None,'key':key,'functionalTested':False}

    def save(self,name,request):
        name=instance_name(name);binding=self.encode(request);command=self.launcher(name)
        with locked():
            private_directory(self.state.parent)
            self.recover_pending()
            mapping=self.mapping();previous=mapping['instances'].get(name);snapshot=self.snapshot()
            if previous:entry=self.owned(previous);id=previous['id']
            else:
                listed=self.parent.get_strv('custom-list');id=None
                for index in range(10000):
                    candidate='custom'+str(index)
                    if candidate in listed:continue
                    possible=self.custom(candidate)
                    if any(possible.get_user_value(key) is not None for key in FIELDS):continue
                    id=candidate;entry=possible;break
                if id is None:raise RuntimeError('No unused Cinnamon custom shortcut ID is available.')
            self.conflicts(binding,id,snapshot)
            if not self.parent.is_writable('custom-list') or not all(entry.is_writable(key) for key in FIELDS):
                raise RuntimeError('Cinnamon shortcut settings are locked. No assignment was changed.')
            desired={'name':'Augmentor Agent'+(' — Second window' if name=='secondary' else ''),'command':command,'binding':[binding]}
            added=id not in self.parent.get_strv('custom-list')
            after=json.loads(json.dumps(mapping));after['instances'][name]={'id':id,**desired}
            intent={'schema':1,'instance':name,'beforeMapping':mapping,'afterMapping':after,
                'beforeUser':self.user_values(entry),'beforeEffective':self.values(entry),'added':added}
            self.persist(intent,self.pending_path)
            try:
                latest=self.bridge('ShortcutBindings')
                if latest['lock']!=snapshot['lock'] or latest['registryPending']:
                    raise RuntimeError('Cinnamon changed while saving. Try a fresh shortcut check.')
                if previous:self.owned(previous)
                elif any(entry.get_user_value(key) is not None for key in FIELDS):
                    raise RuntimeError('The unused Cinnamon shortcut ID was occupied during Save.')
                self.conflicts(binding,id,latest)
                entry.delay()
                for key,value in desired.items():
                    if not entry.set_value(key,self.GLib.Variant('as' if key=='binding' else 's',value)):
                        raise RuntimeError('Cinnamon refused this shortcut assignment.')
                entry.apply();self.Gio.Settings.sync()
                ids=self.parent.get_strv('custom-list')
                if id not in ids:ids.append(id)
                # Exactly one native parent notification refreshes all grabs.
                ids=[value for value in ids if value!='__dummy__'] if '__dummy__' in ids else ids+['__dummy__']
                if not self.parent.set_strv('custom-list',ids):raise RuntimeError('Cinnamon refused this shortcut registration.')
                self.Gio.Settings.sync()
                observed=self.custom(id)
                if self.values(observed)!=desired or id not in self.parent.get_strv('custom-list'):
                    raise RuntimeError('Cinnamon shortcut settings changed during Save. Reload and try again.')
                deadline=time.monotonic()+1
                while True:
                    settled=self.bridge('ShortcutBindings')
                    if settled['lock']!=snapshot['lock']:
                        raise RuntimeError('Cinnamon lock state changed during Save.')
                    registered=any(row['name']==id and row['accelerators']==[binding] for row in settled['bindings'])
                    if registered and not settled['registryPending']:break
                    if time.monotonic()>=deadline:raise RuntimeError('Cinnamon did not register the shortcut. The previous assignment was kept.')
                    time.sleep(.02)
                self.conflicts(binding,id,settled)
                self.persist(after)
            except OwnershipCommittedError:
                # Atomic replacement already established ownership of desired
                # settings. Keep both consistent even when directory fsync fails.
                raise
            except Exception:
                entry.revert();self.restore_intent(intent);self.clear_pending();raise
            self.clear_pending()
            return self.read(name)


def main():
    raw=sys.stdin.buffer.read(4097)
    if len(raw)>4096:raise ValueError('Cinnamon shortcut request is too large.')
    request=json.loads(raw)
    if not isinstance(request,dict) or type(request.get('schema')) is not int or request['schema']!=1:raise ValueError('Unknown Cinnamon shortcut request.')
    backend=NativeShortcuts();name=instance_name(request.get('instance'));action=request.get('action')
    if action=='read':return backend.read(name)
    if action=='save':return backend.save(name,request)
    raise ValueError('Unknown Cinnamon shortcut action.')


if __name__=='__main__':
    try:print(json.dumps(main()))
    except Exception as error:
        print(json.dumps({'schema':1,'error':str(error),'kind':'invalid' if isinstance(error,ValueError) else 'unavailable'}))
        raise SystemExit(1)
