# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bounded, compositor-authenticated access to GNOME 46/48/50 read-only observers."""
import json
import math
import re

PATH='/com/augmentor/GnomeObserver'
INTERFACE='com.augmentor.GnomeObserver'


def parsed(value):
    def invalid(_):raise ValueError('Non-finite JSON number')
    try:
        if not isinstance(value,str) or len(value)>131072:raise ValueError()
        result=json.loads(value,parse_constant=invalid)
        if not isinstance(result,dict):raise ValueError()
        return result
    except (ValueError,TypeError):raise RuntimeError('GNOME returned an invalid observation.') from None


def valid_status(value):
    if (value.get('schema')!=1 or value.get('backend')!='gnome-shell-observer'
            or value.get('inputQualified') is not False
            or not re.fullmatch(r'(?:46|48|50)\.\d+(?:\.\d+)?',str(value.get('shellVersion','')))
            or not re.fullmatch(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}',str(value.get('epoch','')))
            or type(value.get('serial')) is not int or not 0<=value['serial']<2**53):
        raise RuntimeError('GNOME returned an invalid observer status.')
    return value


def geometry(value):
    if not isinstance(value,dict) or set(value)!=set(('x','y','width','height')):
        raise RuntimeError('GNOME returned invalid window geometry.')
    if any(type(n) not in (int,float) or not math.isfinite(n) or abs(n)>100000 for n in value.values()) or value['width']<=0 or value['height']<=0:
        raise RuntimeError('GNOME returned invalid window geometry.')


def valid_scene(value):
    valid_status(value)
    epoch=value['epoch']
    def window(record):
        if not isinstance(record,dict) or not re.fullmatch(re.escape(epoch)+r':\d{1,16}',str(record.get('id',''))):
            raise RuntimeError('GNOME returned an invalid window identity.')
        if type(record.get('pid')) is not int or record['pid']<0:
            raise RuntimeError('GNOME returned invalid window metadata.')
        for key in ('application','title'):
            if not isinstance(record.get(key),str) or len(record[key])>1024:
                raise RuntimeError('GNOME returned invalid window metadata.')
        if any(type(record.get(key)) is not bool for key in ('overrideRedirect','unmanaging')):
            raise RuntimeError('GNOME returned invalid window lifecycle.')
        geometry(record.get('geometry'))
    records=value.get('windows')
    above=value.get('above')
    if not isinstance(records,list) or len(records)>200 or not isinstance(above,list) or len(above)>200:
        raise RuntimeError('GNOME returned an incomplete window list.')
    for record in records:window(record)
    ids=[record['id'] for record in records]
    if len(ids)!=len(set(ids)):raise RuntimeError('GNOME returned duplicate window identities.')
    if value.get('window') is not None:
        window(value['window'])
        if value['window'] not in records:raise RuntimeError('GNOME focus is absent from its scene.')
    for record in above:
        window(record)
        if record not in records or record==value.get('window'):
            raise RuntimeError('GNOME returned invalid covering windows.')
    if len({record['id'] for record in above})!=len(above):raise RuntimeError('GNOME returned duplicate covering windows.')
    screens=value.get('screens')
    if not isinstance(screens,list) or not 1<=len(screens)<=16:raise RuntimeError('GNOME returned invalid monitors.')
    for screen in screens:
        if not isinstance(screen,dict) or not isinstance(screen.get('name'),str) or len(screen['name'])>100:
            raise RuntimeError('GNOME returned invalid monitors.')
        geometry(screen.get('geometry'))
        if type(screen.get('scale')) not in (int,float) or not math.isfinite(screen['scale']) or not 0<screen['scale']<=8:
            raise RuntimeError('GNOME returned invalid monitor scale.')
    workspace=value.get('workspace')
    if not isinstance(workspace,dict) or any(type(workspace.get(k)) is not int or workspace[k]<0 for k in ('id','index')):
        raise RuntimeError('GNOME returned invalid workspace identity.')
    guards=value.get('guards');reasons=value.get('blockedReasons')
    if not isinstance(guards,dict) or not isinstance(reasons,list) or len(reasons)>20 or any(not isinstance(s,str) or len(s)>100 for s in reasons):
        raise RuntimeError('GNOME returned invalid input guards.')
    if not isinstance(guards.get('sessionMode'),str) or not 1<=len(guards['sessionMode'])<=100:
        raise RuntimeError('GNOME returned an invalid session mode.')
    if 'parentSessionMode' in guards and guards['parentSessionMode'] is not None and (
            not isinstance(guards['parentSessionMode'],str) or not 1<=len(guards['parentSessionMode'])<=100):
        raise RuntimeError('GNOME returned an invalid parent session mode.')
    if value['shellVersion'].startswith('46.') and 'parentSessionMode' not in guards:
        raise RuntimeError('GNOME 46 returned an incomplete session mode profile.')
    for key in ('locked','greeter','overview','overviewTarget','overviewAnimation','stageGrabbed','windowDragging','screenShieldAvailable'):
        if type(guards.get(key)) is not bool:raise RuntimeError('GNOME returned incomplete input guards.')
    for key in ('screenShieldActive','screenShieldLocked'):
        if key not in guards or (type(guards[key]) is not bool if guards['screenShieldAvailable'] else guards[key] is not None):
            raise RuntimeError('GNOME returned incomplete lock guards.')
    for key in ('actionMode','modalCount'):
        if type(guards.get(key)) is not int or guards[key]<0:raise RuntimeError('GNOME returned incomplete input guards.')
    for key in ('stageGrabActor','stageKeyFocus'):
        if key not in guards or (guards[key] is not None and (type(guards[key]) is not int or guards[key]<1)):
            raise RuntimeError('GNOME returned invalid stage identity.')
    return value


class GnomeObserver:
    def __init__(self,bus):
        from gi.repository import Gio,GLib
        self.bus=bus;self.Gio=Gio;self.GLib=GLib
        self.owner=self.current_owner();self.epoch=None
        status=valid_status(self.call('Status'))
        if status.get('readOnly') is not True:raise RuntimeError('GNOME observer is not read-only.')
        self.epoch=status['epoch']

    def current_owner(self):
        return self.bus.call_sync('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus',
            'GetNameOwner',self.GLib.Variant('(s)',('org.gnome.Shell',)),None,
            self.Gio.DBusCallFlags.NO_AUTO_START,500,None).unpack()[0]

    def call(self,method,args=None):
        if self.current_owner()!=self.owner:raise RuntimeError('GNOME Shell changed; discard the old observation.')
        value=self.bus.call_sync(self.owner,PATH,INTERFACE,method,args,None,
            self.Gio.DBusCallFlags.NO_AUTO_START,1000,None).unpack()[0]
        if self.current_owner()!=self.owner:raise RuntimeError('GNOME Shell changed; discard the old observation.')
        result=parsed(value)
        if self.epoch is not None and result.get('epoch')!=self.epoch:
            raise RuntimeError('GNOME observer restarted; discard the old observation.')
        return result

    def read(self,cancel=None,windows=False):
        if cancel and cancel.is_set():raise RuntimeError('Desktop control stopped.')
        value=valid_scene(self.call('Read'))
        if cancel and cancel.is_set():raise RuntimeError('Desktop control stopped.')
        return {**value,'compositorOwner':self.owner}

    def inspect_point(self,expected,x,y):
        if not isinstance(expected,str) or len(expected)>100 or any(type(n) not in (int,float) or not math.isfinite(n) for n in (x,y)):
            raise ValueError('Invalid point inspection.')
        value=self.call('InspectPoint',self.GLib.Variant('(sdd)',(expected,float(x),float(y))))
        if (value.get('schema')!=1 or value.get('inputQualified') is not False or value.get('expected')!=expected
                or type(value.get('serial')) is not int or not 0<=value['serial']<2**53
                or any(type(value.get(key)) is not bool for key in ('blocked','windowMatches','reactiveWindowMatches','paintedWindowMatches'))
                or value['windowMatches']!=(value['reactiveWindowMatches'] and value['paintedWindowMatches'])
                or (not value['windowMatches'] and not value['blocked'])):
            raise RuntimeError('GNOME returned an invalid point inspection.')
        return value
