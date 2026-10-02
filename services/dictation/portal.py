# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Consent-based Wayland global shortcuts through the desktop portal.

Signals arrive on a private GLib context. The broker serializes key events with
settings and microphone ownership; this module never opens a microphone.
"""
import os
import secrets
import threading


def required():
    return os.environ.get('XDG_SESSION_TYPE')=='wayland' and 'KDE' not in os.environ.get('XDG_CURRENT_DESKTOP','').upper()


def trigger(binding):
    parts=binding.lower().split('+');modifiers={'ctrl':'CTRL','control':'CTRL','shift':'SHIFT','alt':'ALT','super':'LOGO','meta':'LOGO'}
    keys=[part for part in parts if part not in modifiers]
    if len(keys)!=1:raise ValueError('Use modifiers and one key for the dictation shortcut.')
    key={'space':'space','escape':'Escape','enter':'Return'}.get(keys[0],keys[0].upper() if keys[0].startswith('f') and keys[0][1:].isdigit() else keys[0])
    return '+'.join([modifiers[part] for part in parts if part in modifiers]+[key])


class Portal:
    BUS='org.freedesktop.portal.Desktop'
    PATH='/org/freedesktop/portal/desktop'
    INTERFACE='org.freedesktop.portal.GlobalShortcuts'

    def __init__(self,callback):
        self.callback=callback;self.session=None;self.description=None;self.error=None;self.ready=threading.Event();self.closed=False
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
        if not self.ready.wait(5):raise RuntimeError('Desktop shortcut service did not start.')
        if self.error:raise RuntimeError(self.error)

    def run(self):
        try:
            import gi
            gi.require_version('Gio','2.0')
            from gi.repository import Gio,GLib
            self.Gio=Gio;self.GLib=GLib;self.context=GLib.MainContext.new();self.context.push_thread_default()
            self.loop=GLib.MainLoop.new(self.context,False)
            address=Gio.dbus_address_get_for_bus_sync(Gio.BusType.SESSION,None)
            self.connection=Gio.DBusConnection.new_for_address_sync(address,Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT|Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,None,None)
            self.connection.call_sync(self.BUS,self.PATH,'org.freedesktop.host.portal.Registry','Register',GLib.Variant('(sa{sv})',('com.augmentor.Agent',{})),None,Gio.DBusCallFlags.NONE,5000,None)
            for name in ('Activated','Deactivated','ShortcutsChanged'):
                self.connection.signal_subscribe(self.BUS,self.INTERFACE,name,self.PATH,None,Gio.DBusSignalFlags.NONE,self.signal,name)
            self.ready.set();self.loop.run()
            self.connection.close_sync(None);self.context.pop_thread_default()
        except Exception as error:self.error='Wayland global shortcuts are unavailable: '+str(error);self.ready.set()

    def schedule(self,callback):
        source=self.GLib.idle_source_new()
        def once(*_):callback();return False
        source.set_callback(once);source.attach(self.context)

    def signal(self,connection,sender,path,interface,name,parameters,*_):
        values=parameters.unpack()
        if not self.session or values[0]!=self.session:return
        if name=='ShortcutsChanged':
            for key,options in values[1]:
                if key=='dictation':self.description=options.get('trigger_description')
        elif values[1]=='dictation':self.callback(self.session,name=='Activated')

    def request(self,method,signature,values):
        done=threading.Event();response=[];token='augmentor_'+secrets.token_hex(8)
        options={'handle_token':self.GLib.Variant('s',token)}
        if method=='CreateSession':options['session_handle_token']=self.GLib.Variant('s',token+'_session')
        request_path='/org/freedesktop/portal/desktop/request/'+self.connection.get_unique_name()[1:].replace('.','_')+'/'+token
        def invoke():
            def received(connection,sender,path,interface,signal,parameters,*_):
                code,result=parameters.unpack();response.append(result if code==0 else RuntimeError('Desktop shortcut permission was cancelled or denied.'));done.set()
            self.subscription=self.connection.signal_subscribe(self.BUS,'org.freedesktop.portal.Request','Response',request_path,None,self.Gio.DBusSignalFlags.NONE,received,None)
            try:self.connection.call_sync(self.BUS,self.PATH,self.INTERFACE,method,self.GLib.Variant(signature,(*values,options)),None,self.Gio.DBusCallFlags.NONE,5000,None)
            except Exception as error:response.append(RuntimeError('This desktop does not provide global shortcuts: '+str(error)));done.set()
        self.schedule(invoke)
        completed=done.wait(45)
        def cleanup():
            self.connection.signal_unsubscribe(self.subscription)
            if not completed:
                try:self.connection.call_sync(self.BUS,request_path,'org.freedesktop.portal.Request','Close',None,None,self.Gio.DBusCallFlags.NONE,1000,None)
                except Exception:pass
        self.schedule(cleanup)
        if not completed:raise TimeoutError('Desktop shortcut setup timed out. Dictation has not started.')
        if isinstance(response[0],Exception):raise response[0]
        return response[0]

    def bind(self,binding):
        self.unbind()
        response=self.request('CreateSession','(a{sv})',())
        self.session=response['session_handle']
        try:
            shortcuts=[('dictation',{'description':self.GLib.Variant('s','Augmentor system dictation'),'preferred_trigger':self.GLib.Variant('s',trigger(binding))})]
            response=self.request('BindShortcuts','(oa(sa{sv})sa{sv})',(self.session,shortcuts,''))
            accepted=dict(response.get('shortcuts',[]))
            if 'dictation' not in accepted:raise RuntimeError('Desktop did not bind the dictation shortcut.')
            self.description=accepted['dictation'].get('trigger_description',binding)
        except Exception:self.unbind();raise

    def unbind(self):
        session,self.session=self.session,None
        if session:
            try:self.connection.call_sync(self.BUS,session,'org.freedesktop.portal.Session','Close',None,None,self.Gio.DBusCallFlags.NONE,2000,None)
            except Exception:pass

    def close(self):
        if self.closed:return
        self.closed=True;self.unbind();self.schedule(self.loop.quit)
