# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Independent, owner-pinned GNOME consent session; this component sends no input.

Create on the dedicated worker context. Cancellation may be requested from Qt;
cleanup and every portal call stay on the owning worker. No cached consent reuse.
"""
import os
import re
import threading
import time
import uuid
import xml.etree.ElementTree as ET
from gi.repository import Gio,GLib

NAME='org.freedesktop.portal.Desktop';PATH='/org/freedesktop/portal/desktop'
RD='org.freedesktop.portal.RemoteDesktop';SC='org.freedesktop.portal.ScreenCast'
REGISTRY='org.freedesktop.host.portal.Registry'
OWNERS=(NAME,'org.freedesktop.impl.portal.desktop.gnome','org.gnome.Shell')


class ConsentSession:
    def __init__(self,context,request_timeout=80):
        if type(request_timeout) is not int or not 1<=request_timeout<=180:
            raise RuntimeError('Invalid desktop consent timeout.')
        self.request_timeout=request_timeout
        if GLib.MainContext.get_thread_default()!=context:
            raise RuntimeError('Portal consent requires its own worker context.')
        self.context=context;self.thread=threading.get_ident();self.cancel=threading.Event();self.mutex=threading.Lock()
        self.generation=0;self.rpc_cancel=Gio.Cancellable();self.session=None;self.request_path=None;self.fd=None
        self.owners={};self.subscriptions=[];self.closed=False;self.stream=None;self.interfaces=None;self.on_stopped=None;self.on_request=None;self.stop_reason=None
        address=Gio.dbus_address_get_for_bus_sync(Gio.BusType.SESSION,None)
        self.bus=Gio.DBusConnection.new_for_address_sync(address,
            Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT|Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,None,None)
        self.bus.set_exit_on_close(False)
        self.closed_signal=self.bus.connect('closed',lambda *_:self.request_stop('bus-closed'))
        for name in OWNERS:
            self.subscriptions.append(self.bus.signal_subscribe('org.freedesktop.DBus','org.freedesktop.DBus',
                'NameOwnerChanged','/org/freedesktop/DBus',name,Gio.DBusSignalFlags.NONE,self.owner_changed))

    def owning_thread(self):
        if threading.get_ident()!=self.thread:raise RuntimeError('Portal operation ran outside its owning worker.')

    def owner(self,name):
        value=self.bus.call_sync('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetNameOwner',
            GLib.Variant('(s)',(name,)),GLib.VariantType.new('(s)'),Gio.DBusCallFlags.NO_AUTO_START,1000,self.rpc_cancel).unpack()[0]
        if not isinstance(value,str) or not re.fullmatch(r':\d+\.\d+',value):raise RuntimeError('Portal returned an invalid native owner.')
        return value

    def owner_changed(self,_bus,_sender,_path,_interface,_method,args):
        name,_old,next_owner=args.unpack()
        if name in self.owners and next_owner!=self.owners[name]:self.request_stop('owner-changed');self.close()

    def request_stop(self,reason='requested'):
        if reason not in ('requested','bus-closed','owner-changed','owner-check-changed','native-session-closed'):reason='requested'
        with self.mutex:
            first=not self.cancel.is_set();self.generation+=1;self.cancel.set();self.rpc_cancel.cancel()
            if first:self.stop_reason=reason
        if first and self.on_stopped:self.on_stopped()

    def verify(self,generation):
        self.owning_thread()
        if self.cancel.is_set() or generation!=self.generation or self.closed:
            raise RuntimeError('Desktop sharing stopped. No action is replayed.')
        if any(self.owner(name)!=owner for name,owner in self.owners.items()):
            self.request_stop('owner-check-changed');raise RuntimeError('Desktop service changed. Fresh consent is required.')

    def call(self,interface,method,signature,args,generation):
        self.verify(generation)
        reply=self.bus.call_sync(self.owners[NAME],PATH,interface,method,GLib.Variant(signature,args) if signature else None,
            None,Gio.DBusCallFlags.NO_AUTO_START,5000,self.rpc_cancel).unpack()
        self.verify(generation);return reply

    def request(self,interface,method,signature,args,generation):
        if self.on_request:self.on_request(method)
        results=[];token='request'+uuid.uuid4().hex;unique=self.bus.get_unique_name()[1:].replace('.','_')
        expected='/org/freedesktop/portal/desktop/request/'+unique+'/'+token
        args=list(args);args[-1]={**args[-1],'handle_token':GLib.Variant('s',token)}
        def response(_c,sender,path,_i,_m,value):
            if sender==self.owners[NAME] and path==expected and generation==self.generation and not self.cancel.is_set():results.append(value.unpack())
        subscription=self.bus.signal_subscribe(self.owners[NAME],'org.freedesktop.portal.Request','Response',expected,None,Gio.DBusSignalFlags.NONE,response)
        # Known path is retained before dispatch so cancellation during a lost
        # method reply can close the request without guessing another path.
        self.request_path=expected
        try:
            path=self.call(interface,method,signature,tuple(args),generation)[0]
            if path!=expected:raise RuntimeError('Portal returned a different request identity.')
            deadline=time.monotonic()+self.request_timeout
            while not results and time.monotonic()<deadline:
                self.verify(generation)
                while self.context.pending():self.context.iteration(False)
                time.sleep(.01)
            self.verify(generation)
            if not results:raise RuntimeError('Desktop sharing request timed out. No input was sent.')
            code,reply=results[0]
            if type(code) is not int or code!=0:raise RuntimeError('Desktop sharing was declined or cancelled. No input was sent.')
            if not isinstance(reply,dict):raise RuntimeError('Portal returned an invalid consent response.')
            return reply
        finally:
            if not results:self.close_path(expected,'org.freedesktop.portal.Request')
            self.bus.signal_unsubscribe(subscription);self.request_path=None

    def negotiate(self):
        self.owning_thread();generation=self.generation;self.verify(generation)
        if os.environ.get('XDG_SESSION_TYPE')!='wayland' or 'GNOME' not in os.environ.get('XDG_CURRENT_DESKTOP','').upper().split(':'):
            raise RuntimeError('This consent candidate requires a GNOME Wayland session.')
        self.owners={name:self.owner(name) for name in OWNERS};interfaces={}
        for interface in (RD,SC):
            values=self.call('org.freedesktop.DBus.Properties','GetAll','(s)',(interface,),generation)[0]
            interfaces[interface]={key:value for key,value in values.items() if key in ('version','AvailableDeviceTypes','AvailableSourceTypes','AvailableCursorModes') and type(value) is int}
        if (interfaces[RD].get('version',0)<2 or interfaces[RD].get('AvailableDeviceTypes',0)&3!=3 or
                interfaces[SC].get('version',0)<5 or interfaces[SC].get('AvailableSourceTypes',0)&1!=1 or
                interfaces[SC].get('AvailableCursorModes',0)&1!=1):raise RuntimeError('GNOME portal capabilities are incomplete.')
        xml=self.call('org.freedesktop.DBus.Introspectable','Introspect',None,(),generation)[0]
        if not isinstance(xml,str) or len(xml.encode())>131072:raise RuntimeError('Portal introspection is invalid or oversized.')
        root=ET.fromstring(xml);advertised=any(node.get('name')==REGISTRY for node in root.findall('interface'))
        if advertised:self.call(REGISTRY,'Register','(sa{sv})',('com.augmentor.Agent',{}),generation)
        self.interfaces=interfaces;return {'interfaces':interfaces,'registryRegistered':advertised,'inputSent':False}

    def connect(self):
        self.owning_thread();generation=self.generation
        try:
            negotiation=self.negotiate()
            token='session'+uuid.uuid4().hex;unique=self.bus.get_unique_name()[1:].replace('.','_')
            expected='/org/freedesktop/portal/desktop/session/'+unique+'/'+token
            # Retain only our precomputed identity before CreateSession. A late
            # grant or lost response must still be closed after cancellation.
            self.session=expected
            result=self.request(RD,'CreateSession','(a{sv})',({'session_handle_token':GLib.Variant('s',token)},),generation)
            if result.get('session_handle')!=expected:raise RuntimeError('Portal returned a different session identity.')
            self.verify(generation);self.session=expected
            self.subscriptions.append(self.bus.signal_subscribe(self.owners[NAME],'org.freedesktop.portal.Session','Closed',expected,None,Gio.DBusSignalFlags.NONE,self.revoked))
            self.request(RD,'SelectDevices','(oa{sv})',(expected,{'types':GLib.Variant('u',3),'persist_mode':GLib.Variant('u',0)}),generation)
            self.request(SC,'SelectSources','(oa{sv})',(expected,{'types':GLib.Variant('u',1),'multiple':GLib.Variant('b',False),'cursor_mode':GLib.Variant('u',1)}),generation)
            result=self.request(RD,'Start','(osa{sv})',(expected,'',{}),generation)
            devices=result.get('devices');streams=result.get('streams')
            if type(devices) is not int or devices&3!=3 or not isinstance(streams,list) or len(streams)!=1:
                raise RuntimeError('Keyboard, pointer and one monitor must be shared together.')
            node,metadata=streams[0]
            if type(node) is not int or not 0<node<2**32 or not isinstance(metadata,dict):raise RuntimeError('Portal stream identity is invalid.')
            answer,fds=self.bus.call_with_unix_fd_list_sync(self.owners[NAME],PATH,SC,'OpenPipeWireRemote',
                GLib.Variant('(oa{sv})',(expected,{})),GLib.VariantType.new('(h)'),Gio.DBusCallFlags.NO_AUTO_START,5000,None,self.rpc_cancel)
            # Own the returned FD before the final generation check, so late
            # cancellation also closes it during the exception cleanup.
            self.fd=fds.get(answer.unpack()[0]);self.verify(generation);self.stream=(node,metadata)
            return {**negotiation,'devices':devices,'streamNode':node,'streamMetadata':metadata,'inputSent':False}
        except Exception:self.close();raise

    def revoked(self,_bus,_sender,path,_i,_m,_args):
        if path==self.session:self.request_stop('native-session-closed');self.close()

    def close_path(self,path,interface):
        if not path or not self.owners.get(NAME):return
        try:self.bus.call_sync(self.owners[NAME],path,interface,'Close',None,None,Gio.DBusCallFlags.NO_AUTO_START,1000,None)
        except GLib.Error:pass

    def close(self):
        self.owning_thread();self.request_stop()
        request,self.request_path=self.request_path,None;session,self.session=self.session,None;fd,self.fd=self.fd,None
        self.stream=None;self.close_path(request,'org.freedesktop.portal.Request');self.close_path(session,'org.freedesktop.portal.Session')
        if fd is not None:os.close(fd)

    def dispose(self):
        self.owning_thread()
        if self.closed:return
        self.close();self.closed=True
        for subscription in self.subscriptions:self.bus.signal_unsubscribe(subscription)
        self.subscriptions=[];self.bus.disconnect(self.closed_signal)
        self.bus.close_sync(None)
