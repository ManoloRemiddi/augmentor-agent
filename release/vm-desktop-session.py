#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Disposable-VM helper for actual compositor, portal and saved-file assertions."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

assert Path('/etc/augmentor-test-vm').read_text().startswith('Isolated Augmentor')
root=Path(sys.argv[1]);action=sys.argv[2]
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
    print(json.dumps(KWin(Gio.bus_get_sync(Gio.BusType.SESSION,None)).read(windows=action=='windows')))
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
    print(json.dumps({'root':str(root),'session':os.environ.get('XDG_SESSION_TYPE'),
        'cpu':subprocess.check_output(['lscpu'],text=True),
        'packages':subprocess.check_output(['dpkg-query','-W','-f=${Package} ${Version}\n','kwin-wayland','xdg-desktop-portal-kde','kate'],text=True)}))
elif action=='scale':
    scale=float(sys.argv[3]);assert scale in (1,1.25,1.5)
    from gi.repository import Gio
    from kwin import KWin
    scene=KWin(Gio.bus_get_sync(Gio.BusType.SESSION,None)).read();assert len(scene['screens'])==1
    subprocess.run(['kscreen-doctor','output.'+scene['screens'][0]['name']+'.scale.'+str(scale)],check=True,stdout=subprocess.DEVNULL)
    print(json.dumps({'scale':scale}))
else:raise RuntimeError('Unknown VM proof operation')
