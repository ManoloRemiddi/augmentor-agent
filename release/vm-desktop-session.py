#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Disposable-VM helper for actual compositor, portal and saved-file assertions."""
import json
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import time


def require_editor_absent(pids):
    if pids:raise ValueError('A prior Kate remains; no editor was closed or replaced.')


def editor_process(pid,path):
    path=Path(path)
    if path!=Path.home()/'augmentor-desktop-acceptance.txt' or path.is_symlink():
        raise ValueError('Editor requires the existing owned fixture path.')
    proc=Path('/proc')/str(pid)
    identity={'pid':pid,'uid':proc.stat().st_uid,
              'startTicks':(proc/'stat').read_text().split(') ',1)[1].split()[19],
              'exe':os.readlink(proc/'exe'),
              'argv':(proc/'cmdline').read_bytes().rstrip(b'\0').decode().split('\0')}
    if (identity['uid']!=os.getuid() or identity['exe']!='/usr/bin/kate' or
            identity['argv']!=['kate','--startanon',str(path)]):
        raise ValueError('The fresh owned Kate process identity differs.')
    return identity


def editor_process_birth(pid):
    proc=Path('/proc')/str(pid)
    return proc.stat().st_uid,(proc/'stat').read_text().split(') ',1)[1].split()[19]


def wait_editor_process(pid,path):
    """Wait only for this new child to exec; never adopt a replacement PID."""
    birth=editor_process_birth(pid)
    if birth[0]!=os.getuid():raise ValueError('The fresh editor child owner differs.')
    end=time.monotonic()+5
    while True:
        if editor_process_birth(pid)!=birth:raise ValueError('The fresh editor child owner or start changed.')
        try:identity=editor_process(pid,path)
        except ValueError as error:
            if time.monotonic()>=end:raise ValueError('The fresh editor did not reach its exact Kate identity within five seconds.') from error
            time.sleep(.05);continue
        if (editor_process_birth(pid)!=birth or (identity['uid'],identity['startTicks'])!=birth):
            raise ValueError('The fresh editor child owner or start changed.')
        if time.monotonic()>=end:raise ValueError('The fresh editor identity deadline expired.')
        return identity


def admit_editor_focus(editor,process,window,focused,complete):
    """Admit the original editor window and one actual editable text control."""
    if process!=editor['process']:
        raise ValueError('The fresh owned editor process changed.')
    if (not window or window.get('pid')!=process['pid'] or window.get('id')!=editor['windowId'] or
            window.get('application')!='org.kde.kate' or Path(editor['path']).name not in window.get('title','')):
        raise ValueError('The original owned Kate window is not foreground.')
    if not complete or len(focused)!=1:
        raise ValueError('Editor focus is incomplete or ambiguous.')
    focus=focused[0]
    if (focus.get('focused') is not True or focus.get('showing') is not True or
            focus.get('editable') is not True or focus.get('password') is not False or
            focus.get('textInterface') is not True or focus.get('defunct') is not False):
        raise ValueError('Editor input requires one showing editable nonpassword text control.')
    if editor.get('focusPath') is not None and focus.get('path')!=editor['focusPath']:
        raise ValueError('The owned editor text focus changed.')
    return {'process':process,'window':window,'focus':focus,'complete':True}


def read_editor_focus(editor):
    """Bounded read-only inspection; never selects, closes or types into a widget."""
    import gi
    gi.require_version('Atspi','2.0')
    from gi.repository import Atspi,Gio
    from kwin import KWin
    process=editor_process(editor['process']['pid'],editor['path'])
    kwin=KWin(Gio.bus_get_sync(Gio.BusType.SESSION,None));before=kwin.read()
    # Refuse a foreign foreground before reading any accessible text.
    window=before['window']
    if (process!=editor['process'] or not window or window.get('id')!=editor['windowId'] or
            window.get('pid')!=process['pid'] or window.get('application')!='org.kde.kate'):
        raise ValueError('The original owned Kate window is not foreground.')
    end=time.monotonic()+6
    Atspi.set_timeout(500,1000);desktop=Atspi.get_desktop(0);apps=[]
    if desktop.get_child_count()>200:raise ValueError('Accessibility application bound exceeded.')
    for index in range(desktop.get_child_count()):
        if time.monotonic()>=end:raise ValueError('Editor accessibility traversal time bound exceeded.')
        app=desktop.get_child_at_index(index)
        if app is not None and app.get_process_id()==process['pid']:apps.append(app)
    if len(apps)!=1:raise ValueError('The owned editor accessibility application is ambiguous.')
    stack=[(apps[0],[])];focused=[];focus_nodes=[];count=0
    while stack and count<1500 and time.monotonic()<end:
        node,path=stack.pop();count+=1
        if node is None:raise ValueError('Editor accessibility traversal is incomplete.')
        state=node.get_state_set()
        if state.contains(Atspi.StateType.FOCUSED) and state.contains(Atspi.StateType.SHOWING):
            password=node.get_role()==Atspi.Role.PASSWORD_TEXT
            editable=state.contains(Atspi.StateType.EDITABLE);text=node.get_text_iface() if not password else None
            focus={'path':path,'role':node.get_role_name(),'password':password,'editable':editable,'focused':True,'showing':True,
                   'defunct':state.contains(Atspi.StateType.DEFUNCT),'textInterface':text is not None}
            if text is not None and editable and not password:
                size=Atspi.Text.get_character_count(node)
                if not 0<=size<=4096:raise ValueError('Owned editor text exceeds its diagnostic bound.')
                focus['text']=Atspi.Text.get_text(node,0,-1)
            focused.append(focus)
            focus_nodes.append(node)
        if len(path)<2 or state.contains(Atspi.StateType.SHOWING):
            children=node.get_child_count()
            if children>100 or (len(path)>=16 and children):raise ValueError('Editor accessibility traversal bound exceeded.')
            stack.extend((node.get_child_at_index(index),path+[index]) for index in range(children))
    result=admit_editor_focus(editor,process,window,focused,not stack and time.monotonic()<end)
    state=focus_nodes[0].get_state_set()
    if (not all(state.contains(flag) for flag in (Atspi.StateType.FOCUSED,Atspi.StateType.SHOWING,Atspi.StateType.EDITABLE)) or
            state.contains(Atspi.StateType.DEFUNCT) or focus_nodes[0].get_role()==Atspi.Role.PASSWORD_TEXT):
        raise ValueError('The owned editor text focus changed during inspection.')
    if editor_process(process['pid'],editor['path'])!=process or kwin.read()!=before:
        raise ValueError('Owned editor process or scene changed during focus inspection.')
    if time.monotonic()>=end:raise ValueError('Editor accessibility traversal time bound exceeded.')
    return result


def package_query(target):
    """Native names for the maintained RPM/dpkg proof; no desktop pass implied."""
    if target in ('fedora43-x86_64','fedora44-x86_64'):
        return ['rpm','-q','--qf','%{NAME} %{VERSION}-%{RELEASE} %{ARCH}\n',
                'augmentor-agent','kwin','plasma-workspace','xdg-desktop-portal-kde','kate']
    if target in ('debian13-amd64','debian13-arm64','ubuntu24.04-amd64','ubuntu26.04-amd64','linuxmint22.3-amd64'):
        return ['dpkg-query','-W','-f=${Package} ${Version}\n',
                'augmentor-runtime','augmentor-desktop','kwin-wayland','plasma-workspace','xdg-desktop-portal-kde','kate']
    raise ValueError('No qualified KDE package-query adapter for target: '+str(target))


def selected_identity(root, selected, release, installed, deployment, source, target, store):
    """Bind a proof to the selected clean build and its native package payload."""
    root=Path(root);store=Path(store)
    if not root.is_absolute() or '..' in root.parts or not root.is_relative_to(store) or root==store:
        raise ValueError('The proof requires a selected managed release.')
    if not isinstance(source,str) or len(source)!=40 or any(c not in '0123456789abcdef' for c in source):
        raise ValueError('Use an exact clean source commit.')
    if selected.get('root')!=str(root) or selected.get('sourceRef')!=source:
        raise ValueError('The selected root/source differs from the requested proof.')
    expected={'commit':source,'dirty':False}
    if any(v.get('source')!=expected or v.get('target')!=target for v in (release,installed)):
        raise ValueError('Selected/native clean source or target differs.')
    if selected.get('version')!=release.get('version') or installed.get('version')!=release.get('version'):
        raise ValueError('Selected/native product version differs.')
    if deployment.get('deployment')!=selected or deployment.get('artifactSha256')!=selected.get('artifactSha256'):
        raise ValueError('The selected deployment receipt differs.')
    if (not isinstance(selected.get('artifactSha256'),str) or len(selected['artifactSha256'])!=64 or
            any(c not in '0123456789abcdef' for c in selected['artifactSha256'])):
        raise ValueError('The selected artifact identity is absent.')
    return {'root':str(root),'source':source,'target':target,'artifactSha256':selected['artifactSha256']}


def window_observation_source():
    """Complete compositor identities for the proof's native portal owner guard."""
    return '''function rect(r){return {x:r.x,y:r.y,width:r.width,height:r.height}};
function identity(w){return {id:String(w.internalId),pid:w.pid,application:w.resourceClass,title:w.caption,geometry:rect(w.frameGeometry)}};
var w=workspace.activeWindow;var order=workspace.stackingOrder;
callDBus(SERVICE,'/com/augmentor/Desktop','com.augmentor.Desktop','Report',TOKEN,JSON.stringify({window:w?identity(w):null,windows:order.map(identity),screens:workspace.screens.map(s=>({name:s.name,geometry:rect(s.geometry)}))}));
'''


def kscreen_environment(environment):
    """The display-settings client needs the actual Wayland backend."""
    display=environment.get('WAYLAND_DISPLAY')
    if environment.get('XDG_SESSION_TYPE')!='wayland' or not isinstance(display,str) or not display:
        raise ValueError('Display configuration requires a normal Wayland session/display.')
    return {**environment,'QT_QPA_PLATFORM':'wayland'}


def configure_scale(name,scale,environment):
    # Bound the owned child too: an outer SSH timeout cannot reap that child.
    subprocess.run(['kscreen-doctor','output.'+name+'.scale.'+str(scale)],
                   env=kscreen_environment(environment),check=True,timeout=20,stdout=subprocess.DEVNULL)


def admit_session_state(sessions,uid,session_id,screensaver):
    """Admit one actual local user session, with both lock authorities clear."""
    candidates=[row for row in sessions if row.get('User')==str(uid) and
                row.get('Type')=='wayland' and row.get('Class')=='user' and
                row.get('Seat')=='seat0' and row.get('Remote')=='no' and
                row.get('Active')=='yes' and row.get('State')=='active']
    if len(candidates)!=1 or candidates[0].get('Id')!=session_id:
        raise ValueError('The ordinary active seat0 Wayland session is absent, changed, or ambiguous.')
    session=candidates[0]
    if session.get('LockedHint')!='no':
        raise ValueError('The actual Wayland session is locked or its lock state is unknown.')
    if (screensaver.get('active') is not False or screensaver.get('uid')!=uid or
            not isinstance(screensaver.get('owner'),str) or not screensaver['owner'].startswith(':') or
            type(screensaver.get('pid')) is not int or screensaver['pid']<=0):
        raise ValueError('The actual session ScreenSaver is active or its owner/state is unverified.')
    return {'admitted':True,'session':session,'screensaver':screensaver}


def session_state(uid,environment):
    """Read lock/session state without executing a payload or changing settings."""
    from gi.repository import Gio,GLib
    started=time.monotonic()
    if (os.getuid()!=uid or environment.get('XDG_SESSION_TYPE')!='wayland' or
            not environment.get('WAYLAND_DISPLAY') or not environment.get('DISPLAY')):
        raise ValueError('The actual ordinary Wayland session environment is absent.')
    def properties(command):
        text=subprocess.check_output(command,text=True,timeout=5)
        return dict(line.split('=',1) for line in text.splitlines() if '=' in line)
    ids=properties(['loginctl','show-user',str(uid),'-p','Sessions']).get('Sessions','').split()
    if not ids or len(ids)>32:
        raise ValueError('The owned user session list is absent or exceeds its bound.')
    sessions=[properties(['loginctl','show-session',name,'-p','Id','-p','User','-p','Type',
                          '-p','Class','-p','Seat','-p','Remote','-p','Active','-p','State','-p','LockedHint'])
              for name in ids]
    bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
    def call(destination,path,interface,method,parameters=None):
        return bus.call_sync(destination,path,interface,method,parameters,None,0,3000,None).unpack()[0]
    def bus_identity(method,value):
        return call('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus',
                    method,GLib.Variant('(s)',(value,)))
    owner=bus_identity('GetNameOwner','org.freedesktop.ScreenSaver')
    pid=bus_identity('GetConnectionUnixProcessID',owner)
    owner_uid=bus_identity('GetConnectionUnixUser',owner)
    process=Path('/proc')/str(pid)
    start=(process/'stat').read_text().split(') ',1)[1].split()[19]
    active=call(owner,'/org/freedesktop/ScreenSaver','org.freedesktop.ScreenSaver','GetActive')
    if (bus_identity('GetNameOwner','org.freedesktop.ScreenSaver')!=owner or
            (process/'stat').read_text().split(') ',1)[1].split()[19]!=start or process.stat().st_uid!=uid):
        raise ValueError('The session ScreenSaver owner changed during its lock check.')
    screensaver={'owner':owner,'pid':pid,'uid':owner_uid,'startTicks':start,'active':active}
    latest_sessions=sessions
    try:
        result=admit_session_state(sessions,uid,environment.get('XDG_SESSION_ID'),screensaver)
        # Check login1 again after the session-bus request; no stale unlocked hint.
        current=properties(['loginctl','show-session',result['session']['Id'],'-p','Id','-p','User','-p','Type',
                            '-p','Class','-p','Seat','-p','Remote','-p','Active','-p','State','-p','LockedHint'])
        latest_sessions=[current]
        screensaver['active']=call(owner,'/org/freedesktop/ScreenSaver','org.freedesktop.ScreenSaver','GetActive')
        if (bus_identity('GetNameOwner','org.freedesktop.ScreenSaver')!=owner or
                (process/'stat').read_text().split(') ',1)[1].split()[19]!=start):
            raise ValueError('The session ScreenSaver owner changed during its final lock check.')
        result=admit_session_state([current],uid,environment.get('XDG_SESSION_ID'),screensaver)
    except ValueError as error:
        result={'admitted':False,'sessions':latest_sessions,'screensaver':screensaver,'error':str(error)}
    return {**result,'checkedAt':time.time(),'elapsedSeconds':round(time.monotonic()-started,6)}


assert Path('/etc/augmentor-test-vm').read_text().startswith('Isolated Augmentor')
if os.environ.get('AUGMENTOR_PROOF_UID') or os.environ.get('AUGMENTOR_PROOF_USER'):
    assert os.getuid()==int(os.environ['AUGMENTOR_PROOF_UID']) and os.environ.get('USER')==os.environ['AUGMENTOR_PROOF_USER']
root=Path(sys.argv[1]);action=sys.argv[2]
identity=None
expected_source=os.environ.get('AUGMENTOR_PROOF_SOURCE')
expected_target=os.environ.get('AUGMENTOR_PROOF_TARGET')
if expected_source or expected_target:
    assert expected_source and expected_target and len(expected_source)==40
    assert os.getuid()!=0 and not root.is_symlink()
    selected=json.loads((Path.home()/'.local/share/augmentor/desktop.json').read_text())
    release=json.loads((root/'release.json').read_text())
    installed=json.loads(Path('/usr/lib/augmentor/release.json').read_text())
    deployment=json.loads((root/'desktop-release.json').read_text())
    identity=selected_identity(root,selected,release,installed,deployment,expected_source,expected_target,
                               Path.home()/'.local/share/augmentor/releases')
for line in subprocess.check_output(['systemctl','--user','show-environment'],text=True).splitlines():
    key,_,value=line.partition('=');os.environ[key]=value
os.environ['QT_QPA_PLATFORM']='xcb'
sys.path.insert(0,str(root/'services/desktop'))
if action=='session-state':
    print(json.dumps(session_state(int(os.environ['AUGMENTOR_PROOF_UID']),os.environ)))
elif action=='serve':
    if os.environ.get('AUGMENTOR_VM_FOCUS_DEBUG')=='1':
        from portal import Portal
        original_focus=Portal.focus_info
        def traced_focus(self,pid):
            previous=sys.gettrace();summary={};started=time.monotonic()
            def trace(frame,event,arg):
                if frame.f_code is not original_focus.__code__:return None
                if event=='return':
                    values=frame.f_locals
                    summary.update(nodes=values.get('count',0),pendingNodes=len(values.get('stack',[])),
                                   focused=len(values.get('focused',[])),returned=len(arg) if isinstance(arg,list) else None)
                elif event=='exception':summary['exceptionType']=arg[0].__name__
                return trace
            sys.settrace(trace)
            try:return original_focus(self,pid)
            finally:
                sys.settrace(previous)
                print(json.dumps({'focusDiagnostic':summary,'elapsedSeconds':round(time.monotonic()-started,3)}),file=sys.stderr,flush=True)
        Portal.focus_info=traced_focus
    from service import main
    main()
elif action=='rpc':
    from client import call
    try:result=call(json.load(sys.stdin),False)
    except Exception as exc:result={'ok':False,'error':str(exc)}
    print(json.dumps(result))
elif action in ('scene','windows'):
    from gi.repository import Gio
    from kwin import KWin
    kwin=KWin(Gio.bus_get_sync(Gio.BusType.SESSION,None))
    print(json.dumps(kwin.execute(window_observation_source()) if action=='windows' else kwin.read()))
elif action=='portal-owner':
    from gi.repository import Gio,GLib
    bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
    pid=bus.call_sync('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus',
                      'GetConnectionUnixProcessID',GLib.Variant('(s)',('org.freedesktop.impl.portal.desktop.kde',)),None,0,5000,None).unpack()[0]
    print(json.dumps({'pid':pid,'exe':os.readlink('/proc/'+str(pid)+'/exe')}))
elif action=='editor':
    os.environ['QT_QPA_PLATFORM']='wayland';os.environ['QT_LINUX_ACCESSIBILITY_ALWAYS_ON']='1'
    output=Path.home()/'augmentor-desktop-acceptance.txt'
    # Prior windows and buffers belong to their original run. Refuse them;
    # never force cleanup or silently adopt a replacement editor.
    owned=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:
            if proc.stat().st_uid!=os.getuid():continue
            if (proc/'comm').read_text().strip()=='kate':owned.append(int(proc.name))
        except (FileNotFoundError,ProcessLookupError):pass
    require_editor_absent(owned)
    if output.is_symlink():raise ValueError('Owned editor fixture must not be a symlink.')
    output.write_text('Fixture ready\n')
    editor=subprocess.Popen(['kate','--startanon',str(output)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    print(json.dumps({'path':str(output),'launcherPid':editor.pid,'previousPids':[],
                      'process':wait_editor_process(editor.pid,output)}))
elif action in ('editor-focus','editor-text'):
    result=read_editor_focus(json.loads(sys.argv[3]))
    print(json.dumps(result if action=='editor-focus' else {'texts':[result['focus']['text']]}))
elif action=='file':
    name=sys.argv[3]
    assert name in ('augmentor-desktop-acceptance.txt','augmentor-desktop-acceptance-saved.txt')
    path=Path.home()/name
    print(json.dumps({'exists':path.exists(),'text':path.read_text() if path.exists() else None}))
elif action=='remove-output':
    (Path.home()/'augmentor-desktop-acceptance-saved.txt').unlink(missing_ok=True)
elif action=='versions':
    target=expected_target or os.environ.get('AUGMENTOR_PROOF_PACKAGE_TARGET') or json.loads((root/'release.json').read_text()).get('target')
    if identity:
        spec=importlib.util.spec_from_file_location('verified_selected_deployment',root/'scripts/desktop-deployment.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.verify(root)
        audit=['rpm','-V','augmentor-agent'] if target.startswith('fedora') else ['dpkg','--verify','augmentor-runtime','augmentor-desktop']
        result=subprocess.run(audit,capture_output=True,text=True,timeout=90)
        if result.returncode or result.stdout.strip() or result.stderr.strip():
            raise ValueError('Native package file audit failed: '+result.stdout+result.stderr)
    packages=subprocess.check_output(package_query(target),text=True)
    portal=[line for line in packages.splitlines() if line.startswith('xdg-desktop-portal-kde ')]
    assert len(portal)==1
    print(json.dumps({'root':str(root),'session':os.environ.get('XDG_SESSION_TYPE'),
        'selectedIdentity':identity,
        'portalPackage':portal[0],
        'cpu':subprocess.check_output(['lscpu'],text=True),
        'packages':packages}))
elif action=='scale':
    scale=float(sys.argv[3]);assert scale in (1,1.25,1.5)
    from gi.repository import Gio
    from kwin import KWin
    scene=KWin(Gio.bus_get_sync(Gio.BusType.SESSION,None)).read();assert len(scene['screens'])==1
    configure_scale(scene['screens'][0]['name'],scale,os.environ)
    print(json.dumps({'scale':scale}))
else:raise RuntimeError('Unknown VM proof operation')
