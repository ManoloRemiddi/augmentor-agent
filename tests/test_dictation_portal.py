# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Synthetic portal over a real isolated D-Bus; no compositor permission dialog."""
import os
import threading
import time
import unittest
from services.dictation.portal import Portal,trigger


class ShortcutSyntaxTests(unittest.TestCase):
    def test_xdg_trigger_syntax(self):
        self.assertEqual(trigger('ctrl+space'),'CTRL+space')
        self.assertEqual(trigger('ctrl+alt+F10'),'CTRL+ALT+F10')
        with self.assertRaises(ValueError):trigger('ctrl+space+a')


@unittest.skipUnless(os.environ.get('AUGMENTOR_PORTAL_PROOF')=='1','Requires an isolated dbus-run-session')
class PortalProof(unittest.TestCase):
    def test_real_dbus_response_race_events_and_denied_binding(self):
        from gi.repository import Gio,GLib
        ready=threading.Event();received=[];calls=[];denied=[False];fixture={}
        xml='''<node><interface name="org.freedesktop.host.portal.Registry"><method name="Register"><arg type="s" direction="in"/><arg type="a{sv}" direction="in"/></method></interface><interface name="org.freedesktop.portal.GlobalShortcuts"><method name="CreateSession"><arg type="a{sv}" direction="in"/><arg type="o" direction="out"/></method><method name="BindShortcuts"><arg type="o" direction="in"/><arg type="a(sa{sv})" direction="in"/><arg type="s" direction="in"/><arg type="a{sv}" direction="in"/><arg type="o" direction="out"/></method></interface></node>'''
        session_xml='<node><interface name="org.freedesktop.portal.Session"><method name="Close"/></interface></node>'
        def start():
            context=GLib.MainContext.new();context.push_thread_default();loop=GLib.MainLoop.new(context,False)
            connection=Gio.DBusConnection.new_for_address_sync(Gio.dbus_address_get_for_bus_sync(Gio.BusType.SESSION,None),Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT|Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,None,None)
            result=connection.call_sync('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','RequestName',GLib.Variant('(su)',(Portal.BUS,4)),None,Gio.DBusCallFlags.NONE,1000,None)
            if result.unpack()[0]!=1:raise RuntimeError('Private test bus already has a portal; refuse to replace it.')
            fixture.update(connection=connection,loop=loop,context=context)
            def handle(connection,sender,path,interface,method,params,invocation):
                arguments=params.unpack();calls.append((method,arguments))
                if method in ('Register','Close'):invocation.return_value(None);return
                token=arguments[-1]['handle_token'];request='/org/freedesktop/portal/desktop/request/'+sender[1:].replace('.','_')+'/'+token
                session='/org/freedesktop/portal/desktop/session/test/'+arguments[-1].get('session_handle_token','session')
                if method=='CreateSession':
                    fixture['session']=session
                    connection.register_object(session,Gio.DBusNodeInfo.new_for_xml(session_xml).interfaces[0],handle,None,None)
                    results={'session_handle':GLib.Variant('s',session)}
                else:results={'shortcuts':GLib.Variant('a(sa{sv})',[('dictation',{'trigger_description':GLib.Variant('s','Ctrl+Space')})])}
                # Deliver the Response before the method returns its handle.
                connection.emit_signal(sender,request,'org.freedesktop.portal.Request','Response',GLib.Variant('(ua{sv})',(1 if denied[0] and method=='BindShortcuts' else 0,results)))
                invocation.return_value(GLib.Variant('(o)',(request,)))
            for interface in Gio.DBusNodeInfo.new_for_xml(xml).interfaces:connection.register_object(Portal.PATH,interface,handle,None,None)
            ready.set();loop.run();connection.close_sync(None);context.pop_thread_default()
        thread=threading.Thread(target=start,daemon=True);thread.start();self.assertTrue(ready.wait(3))
        portal=None
        try:
            portal=Portal(lambda session,pressed:received.append((session,pressed)));portal.bind('ctrl+space')
            self.assertEqual(calls[0],('Register',('com.augmentor.Agent',{})))
            self.assertEqual(portal.description,'Ctrl+Space')
            self.assertEqual(next(args for method,args in calls if method=='BindShortcuts')[1][0][1]['preferred_trigger'],'CTRL+space')
            for name in ('Activated','Deactivated'):
                fixture['connection'].emit_signal(None,Portal.PATH,Portal.INTERFACE,name,GLib.Variant('(osta{sv})',(portal.session,'dictation',1,{})))
            deadline=time.monotonic()+2
            while len(received)<2 and time.monotonic()<deadline:time.sleep(.01)
            self.assertEqual(received,[(portal.session,True),(portal.session,False)])
            denied[0]=True
            with self.assertRaisesRegex(RuntimeError,'denied'):portal.bind('ctrl+shift+space')
            self.assertIsNone(portal.session)
        finally:
            if portal:portal.close()
            source=GLib.idle_source_new();source.set_callback(lambda *_:fixture['loop'].quit() or False);source.attach(fixture['context']);thread.join(3)

if __name__=='__main__':unittest.main()
