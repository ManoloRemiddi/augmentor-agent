#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Disposable-VM helper for actual compositor, portal and saved-file assertions."""
import json
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


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
if action=='serve':
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
    # Every editor this fixture opens is owned by the disposable test. Avoid
    # accumulating windows and stale file-reload dialogs across proof runs.
    owned=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:
            args=(proc/'cmdline').read_bytes().split(b'\0')
            if (proc/'comm').read_text().strip()=='kate' and str(output).encode() in args:
                os.kill(int(proc.name),signal.SIGTERM);owned.append(proc)
        except (OSError,ProcessLookupError):pass
    end=time.monotonic()+5
    while any(p.exists() for p in owned) and time.monotonic()<end:time.sleep(.1)
    for proc in owned:
        if proc.exists():
            try:os.kill(int(proc.name),signal.SIGKILL)
            except ProcessLookupError:pass
    output.write_text('Fixture ready\n')
    editor=subprocess.Popen(['kate','--startanon',str(output)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    print(json.dumps({'path':str(output),'launcherPid':editor.pid,'previousPids':[int(p.name) for p in owned]}))
elif action=='editor-text':
    # Read the actual focused widget independently of the executor/model. Used
    # to press Stop only after at least one character was visibly inserted.
    import gi
    gi.require_version('Atspi','2.0')
    from gi.repository import Atspi,Gio
    from kwin import KWin
    window=KWin(Gio.bus_get_sync(Gio.BusType.SESSION,None)).read()['window']
    assert window and 'augmentor-desktop-acceptance' in window['title']
    Atspi.set_timeout(500,1000);desktop=Atspi.get_desktop(0);texts=[]
    for i in range(desktop.get_child_count()):
        app=desktop.get_child_at_index(i)
        if app is None or app.get_process_id()!=window['pid']:continue
        stack=[app];count=0
        while stack and count<1500:
            node=stack.pop();count+=1
            try:
                state=node.get_state_set()
                if state.contains(Atspi.StateType.FOCUSED) and node.get_text_iface():texts.append(Atspi.Text.get_text(node,0,-1))
                if node is app or state.contains(Atspi.StateType.SHOWING):
                    stack.extend(node.get_child_at_index(j) for j in range(min(node.get_child_count(),100)))
            except Exception:pass
    print(json.dumps({'texts':texts}))
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
