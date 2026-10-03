# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Read-only child owns libatspi's default context; exports no accessible text."""
import argparse
import json
import os
from pathlib import Path
import re
import socket
import struct
import threading
import time
import uuid


def start_time(pid):
    path=Path('/proc')/str(pid)
    if path.stat().st_uid!=os.getuid():raise RuntimeError('Different native user.')
    return (path/'stat').read_text().rsplit(')',1)[1].split()[19]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fd',type=int,required=True);parser.add_argument('--parent-pid',type=int,required=True)
    parser.add_argument('--parent-start',required=True);parser.add_argument('--target-pid',type=int,required=True)
    parser.add_argument('--target-start',required=True);args=parser.parse_args()
    if os.geteuid()==0 or start_time(args.parent_pid)!=args.parent_start or start_time(args.target_pid)!=args.target_start:
        raise RuntimeError('Invalid ordinary-user parent/target.')
    peer=socket.socket(fileno=args.fd)
    if struct.unpack('3i',peer.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))!=(args.parent_pid,os.getuid(),os.getgid()):
        raise RuntimeError('Invalid parent socket credentials.')
    os.environ['ATSPI_NO_CACHE']='1'
    import gi
    gi.require_version('Atspi','2.0')
    from gi.repository import Gio,GLib,Atspi
    context=GLib.MainContext.default();thread=threading.get_ident();epoch=uuid.uuid4().hex
    state={'valid':True,'serial':0,'reason':None,'selectedOwner':None,'lastEvent':None}
    flags=Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT|Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION
    def connection(address):
        bus=Gio.DBusConnection.new_for_address_sync(address,flags,None,None);bus.set_exit_on_close(False);return bus
    def call(bus,name,path,interface,method,signature=None,arguments=()):
        return bus.call_sync(name,path,interface,method,GLib.Variant(signature,arguments) if signature else None,
            None,Gio.DBusCallFlags.NO_AUTO_START,500,None).unpack()[0]
    def daemon(bus,method,value=None):
        return call(bus,'org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus',method,'(s)' if value else None,(value,) if value else ())
    def owner(bus,name):
        value=daemon(bus,'GetNameOwner',name)
        if not isinstance(value,str) or not re.fullmatch(r':\d+\.\d+',value):raise RuntimeError('Invalid native owner.')
        return value
    def invalidate(reason):state['valid']=False;state['reason']=state['reason'] or reason
    session=connection(Gio.dbus_address_get_for_bus_sync(Gio.BusType.SESSION,None))
    launcher=owner(session,'org.a11y.Bus');address=call(session,launcher,'/org/a11y/bus','org.a11y.Bus','GetAddress')
    if not isinstance(address,str) or not address.startswith('unix:') or len(address)>4096:raise RuntimeError('Invalid accessibility bus.')
    os.environ['AT_SPI_BUS_ADDRESS']=address;a11y=connection(address);registry=owner(a11y,'org.a11y.atspi.Registry')
    if daemon(session,'GetConnectionUnixUser',launcher)!=os.getuid() or daemon(a11y,'GetConnectionUnixUser',registry)!=os.getuid():
        raise RuntimeError('Accessibility service has a different user.')
    pins={'sessionBusId':daemon(session,'GetId'),'launcherOwner':launcher,'accessibilityBusId':daemon(a11y,'GetId'),'registryOwner':registry}
    def changed(_bus,_sender,_path,_interface,_method,arguments):
        name,old,next_owner=arguments.unpack()
        if (name=='org.a11y.Bus' and next_owner!=launcher or name=='org.a11y.atspi.Registry' and next_owner!=registry
                or name==state['selectedOwner'] and next_owner!=state['selectedOwner']):invalidate('owner-changed')
    for bus in (session,a11y):
        bus.connect('closed',lambda *_:invalidate('bus-closed'))
        bus.signal_subscribe('org.freedesktop.DBus','org.freedesktop.DBus','NameOwnerChanged','/org/freedesktop/DBus',None,Gio.DBusSignalFlags.NONE,changed)
    if Atspi.init()!=0:raise RuntimeError('Accessibility initialization failed.')
    Atspi.set_timeout(150,500)
    def identity(node):
        name=node.app.bus_name;path=node.path
        if not isinstance(name,str) or not re.fullmatch(r':\d+\.\d+',name) or not isinstance(path,str) or not re.fullmatch(r'/(?:[A-Za-z0-9_]+/?)*',path):
            raise RuntimeError('Invalid accessible identity.')
        return name,path
    def focused_event(event,_data):
        state['serial']+=1
        try:
            if threading.get_ident()!=thread or event.type!='object:state-changed:focused' or event.detail1 not in (0,1):
                raise RuntimeError('Invalid focus event.')
            name,path=identity(event.source);sender,_=identity(event.sender)
            if sender!=name:raise RuntimeError('Different event source owner.')
            state['lastEvent']={'sourceOwner':name,'sourcePath':path,'senderOwner':sender,'focused':bool(event.detail1),'callbackOnOwningThread':True}
        except Exception:invalidate('invalid-focus-event')
    listener=Atspi.EventListener.new(focused_event,None)
    if not listener.register('object:state-changed:focused'):raise RuntimeError('Listener registration refused.')
    def pump():
        for _ in range(64):
            if not context.pending():break
            context.iteration(False)
    def verify():
        if not state['valid']:raise RuntimeError('Invalid accessibility epoch.')
        if start_time(args.target_pid)!=args.target_start or owner(session,'org.a11y.Bus')!=launcher or owner(a11y,'org.a11y.atspi.Registry')!=registry:
            invalidate('identity-changed');raise RuntimeError('Native identity changed.')
    def focus():
        state['queryPhase']='desktop';pump();verify();serial=state['serial'];deadline=time.monotonic()+2;desktop=Atspi.get_desktop(0)
        count=desktop.get_child_count()
        if not 0<=count<=200:raise RuntimeError('Desktop enumeration incomplete.')
        applications=[]
        for index in range(count):
            state['queryPhase']='application-enumeration';state['visitedApplications']=index
            if time.monotonic()>deadline:raise RuntimeError('Focus enumeration deadline.')
            app=desktop.get_child_at_index(index)
            if app is None:raise RuntimeError('Desktop enumeration changed.')
            state['queryPhase']='application-identity'
            name,_=identity(app)
            state['queryPhase']='application-credentials'
            if daemon(a11y,'GetConnectionUnixProcessID',name)==args.target_pid:
                if daemon(a11y,'GetConnectionUnixUser',name)!=os.getuid():raise RuntimeError('Different application user.')
                applications.append((app,name))
        state['queryPhase']='selected-application'
        if len(applications)!=1:raise RuntimeError('Selected application unavailable or ambiguous.')
        app,name=applications[0]
        if state['selectedOwner'] not in (None,name):invalidate('application-owner-changed');raise RuntimeError('Application owner changed.')
        state['selectedOwner']=name;stack=[(app,0,False)];visited=set();focused=[]
        while stack:
            state['queryPhase']='accessible-tree'
            if len(visited)>=1500 or time.monotonic()>deadline:raise RuntimeError('Accessible enumeration incomplete.')
            node,depth,password=stack.pop();node_owner,path=identity(node)
            if node_owner!=name or (node_owner,path) in visited:raise RuntimeError('Accessible identity changed or repeated.')
            visited.add((node_owner,path));states=node.get_state_set();role=int(node.get_role())
            if role<=0 or states.contains(Atspi.StateType.DEFUNCT):raise RuntimeError('Invalid or defunct accessible.')
            password=password or role==int(Atspi.Role.PASSWORD_TEXT)
            showing=states.contains(Atspi.StateType.SHOWING);has_focus=states.contains(Atspi.StateType.FOCUSED)
            if has_focus:
                if not showing:raise RuntimeError('Focused accessible is not showing.')
                focused.append({'owner':name,'path':path,'role':role,'password':password,'focused':True,'showing':True,'defunct':False,
                    'editable':states.contains(Atspi.StateType.EDITABLE),'enabled':states.contains(Atspi.StateType.ENABLED),'sensitive':states.contains(Atspi.StateType.SENSITIVE)})
            if depth<2 or showing:
                children=node.get_child_count()
                if not 0<=children<=100 or depth>=16 and children:raise RuntimeError('Accessible subtree incomplete.')
                for index in range(children):
                    child=node.get_child_at_index(index)
                    if child is None:raise RuntimeError('Accessible subtree changed.')
                    stack.append((child,depth+1,password))
        state['queryPhase']='final-validation';pump();verify()
        if daemon(a11y,'GetConnectionUnixProcessID',name)!=args.target_pid or serial!=state['serial'] or len(focused)!=1:
            raise RuntimeError('Focus changed, unavailable or ambiguous.')
        return {'complete':True,'focus':focused[0],'visitedNodes':len(visited),'observedSerial':serial}
    busy=False;loop=GLib.MainLoop.new(context,False)
    def request(_fd,condition):
        nonlocal busy
        if condition&(GLib.IOCondition.HUP|GLib.IOCondition.ERR):loop.quit();return False
        if busy:invalidate('reentrant-request');return True
        busy=True
        try:
            data,_,flags,_=peer.recvmsg(8192)
            if not data:loop.quit();return False
            if flags&socket.MSG_TRUNC:raise RuntimeError('Oversized request.')
            value=json.loads(data)
            if (set(value)!=set(('operation','nonce','generation')) or value['operation'] not in ('status','focus')
                    or not isinstance(value['nonce'],str) or not re.fullmatch('[a-f0-9]{32}',value['nonce'])
                    or type(value['generation']) is not int or not 0<=value['generation']<2**53):raise RuntimeError('Invalid request.')
            answer={'complete':False,'focus':None}
            try:
                if value['operation']=='focus':answer=focus()
                else:pump();verify()
            except Exception as error:
                answer.update(reason='native-query-incomplete',phase=state.get('queryPhase','native-identity'),kind=type(error).__name__,visitedApplications=state.get('visitedApplications',0))
                if isinstance(error,RuntimeError) and str(error) in ('Focus enumeration deadline.','Selected application unavailable or ambiguous.','Invalid accessible identity.','Invalid or defunct accessible.','Accessible enumeration incomplete.','Focus changed, unavailable or ambiguous.'):
                    answer['refusal']=str(error)
            peer.send(json.dumps({**answer,'nonce':value['nonce'],'generation':value['generation'],'helperPid':os.getpid(),
                'targetPid':args.target_pid,'targetStart':args.target_start,'epoch':epoch,'pins':pins,
                'valid':state['valid'],'serial':state['serial'],'selectedOwner':state['selectedOwner'],'lastEvent':state['lastEvent'],
                'stopReason':state['reason'],'inputQualified':False}).encode())
        except Exception:invalidate('invalid-request');loop.quit();return False
        finally:busy=False
        return True
    GLib.io_add_watch(peer.fileno(),GLib.PRIORITY_DEFAULT,GLib.IOCondition.IN|GLib.IOCondition.HUP|GLib.IOCondition.ERR,request)
    try:loop.run()
    finally:listener.deregister('object:state-changed:focused');Atspi.exit();peer.close()


if __name__=='__main__':main()
