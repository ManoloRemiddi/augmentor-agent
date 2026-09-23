# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fresh compositor-owned window identity through KWin's public scripting API."""
import json
import os
from pathlib import Path
import re
import tempfile
import uuid
from gi.repository import Gio,GLib


class KWin:
    def __init__(self,bus):
        self.bus=bus;self.pending={}
        xml=Gio.DBusNodeInfo.new_for_xml('<node><interface name="com.augmentor.Desktop"><method name="Report"><arg type="s" direction="in"/><arg type="s" direction="in"/></method></interface></node>')
        self.registration=bus.register_object('/com/augmentor/Desktop',xml.interfaces[0],self.receive,None,None)
    def call(self,path,interface,method,signature=None,args=()):
        return self.bus.call_sync('org.kde.KWin',path,interface,method,GLib.Variant(signature,args) if signature else None,None,0,3000,None).unpack()
    def receive(self,connection,sender,path,interface,method,args,invocation):
        # Only the compositor may answer a pending observation.
        owner=self.bus.call_sync('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetNameOwner',GLib.Variant('(s)',('org.kde.KWin',)),None,0,2000,None).unpack()[0]
        token,value=args.unpack()
        if sender!=owner or token not in self.pending:invocation.return_dbus_error('com.augmentor.Invalid','Unknown observation');return
        self.pending[token].append(json.loads(value));invocation.return_value(None)
    def read(self,cancel=None,windows=False):
        token=uuid.uuid4().hex;result=[];self.pending[token]=result;leases=[]
        source='''function rect(r){return {x:r.x,y:r.y,width:r.width,height:r.height}};
var w=workspace.activeWindow; var order=workspace.stackingOrder; var above=w?order.slice(order.indexOf(w)+1).filter(a=>!a.minimized&&!a.hidden&&!a.deleted&&(!a.desktops.length||a.desktops.indexOf(workspace.currentDesktop)>=0)&&(!a.activities.length||a.activities.indexOf(workspace.currentActivity)>=0)):[];
callDBus(SERVICE,'/com/augmentor/Desktop','com.augmentor.Desktop','Report',TOKEN,JSON.stringify({window:w?{id:String(w.internalId),pid:w.pid,application:w.resourceClass,title:w.caption,geometry:rect(w.frameGeometry)}:null,above:above.map(a=>({id:String(a.internalId),pid:a.pid,geometry:rect(a.frameGeometry)})),screens:workspace.screens.map(s=>({name:s.name,geometry:rect(s.geometry)}))}));
'''.replace('SERVICE',json.dumps(self.bus.get_unique_name())).replace('TOKEN',json.dumps(token))
        if windows:source=source.replace('JSON.stringify({window:', 'JSON.stringify({windows:order.map(a=>({id:String(a.internalId),title:a.caption,geometry:rect(a.frameGeometry)})),window:')
        try:
            for _ in range(32):
                xml=self.call('/Scripting','org.freedesktop.DBus.Introspectable','Introspect')[0]
                occupied={int(n) for n in re.findall(r'<node name="Script(\d+)"',xml)}
                name='augmentor-desktop-'+uuid.uuid4().hex
                with tempfile.NamedTemporaryFile(mode='w',prefix='augmentor-window-',suffix='.js',delete=False) as file:file.write(source);path=file.name
                sid=self.call('/Scripting','org.kde.kwin.Scripting','loadScript','(ss)',(path,name))[0];leases.append((name,path))
                if type(sid) is not int or sid<0:raise RuntimeError('KWin could not inspect the active window.')
                if sid in occupied:Path(path).write_text('// Inert reservation for KWin script-ID collision.\n');continue
                self.call('/Scripting/Script'+str(sid),'org.kde.kwin.Script','run')
                import time
                end=time.monotonic()+3
                while not result and time.monotonic()<end:
                    if cancel and cancel.is_set():raise RuntimeError('Desktop control stopped.')
                    while GLib.MainContext.default().pending():GLib.MainContext.default().iteration(False)
                    time.sleep(.005)
                if not result:raise RuntimeError('KWin did not return a fresh window observation.')
                return result[0]
            raise RuntimeError('KWin has no free script slot for observation.')
        finally:
            self.pending.pop(token,None)
            for name,path in reversed(leases):
                try:self.call('/Scripting','org.kde.kwin.Scripting','unloadScript','(s)',(name,))
                finally:Path(path).unlink(missing_ok=True)
