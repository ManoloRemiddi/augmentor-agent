# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Supervise an isolated X display, original Qt app, loopback VNC and authenticated web bridge."""
import argparse
import atexit
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import subprocess
import time

ROOT=Path(__file__).resolve().parents[2]

def desktop_config(explicit=None):
    descriptor=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'augmentor/desktop.json'
    if descriptor.exists():
        selected=json.loads(descriptor.read_text())
        if explicit is None or Path(explicit).resolve()==Path(selected['root']):
            if not (Path(selected['root'])/'apps/native/augmentor_linux/window.py').is_file():
                raise RuntimeError('The selected desktop release is missing; repair its deployment.')
            return selected
    return {'root':str(Path(explicit or ROOT).resolve()),'python':str(ROOT/'.venv/bin/python')}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--origin',action='append',default=[])
    parser.add_argument('--desktop-root',type=Path,default=None,help='Development override; normally use the shared desktop deployment.')
    parser.add_argument('--preview',action='store_true',help='Native UI fixture only; no agent connection.')
    args=parser.parse_args()
    selected=desktop_config(args.desktop_root or (ROOT if args.preview else None))
    os.umask(0o077)
    state=Path.home()/'.local/state/augmentor-mobile';state.mkdir(parents=True,exist_ok=True,mode=0o700)
    import fcntl
    lock=(state/'desktop.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    (state/'supervisor.pid').write_text(str(os.getpid()))
    runtime=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'augmentor-mobile-runtime/root'
    binary=shutil.which('x11vnc') or str(runtime/'usr/bin/x11vnc')
    if not Path(binary).exists():raise SystemExit('Install the rootless runtime with apps/mobile/setup-runtime.sh first.')
    compositor=shutil.which('xcompmgr') or str(runtime/'usr/bin/xcompmgr')
    if not Path(compositor).exists():raise SystemExit('Update the rootless runtime with apps/mobile/setup-runtime.sh; the Desktop activity halo requires xcompmgr.')
    display=next((f':{i}' for i in range(95,195) if not Path(f'/tmp/.X{i}-lock').exists() and not Path(f'/tmp/.X11-unix/X{i}').exists()),None)
    if display is None:raise SystemExit('No free isolated X display.')
    env={**os.environ,'DISPLAY':display,'XAUTHORITY':str(state/'Xauthority'),'QT_QPA_PLATFORM':'xcb',
         'AUGMENTOR_TOUCH_VIEWPORT':str(state/'viewport.json'),'AUGMENTOR_REMOTE_STATE':str(state),
         'AUGMENTOR_X11VNC':binary,'LD_LIBRARY_PATH':str(runtime/'usr/lib/x86_64-linux-gnu')+(':'+os.environ['LD_LIBRARY_PATH'] if os.environ.get('LD_LIBRARY_PATH') else '')}
    env.pop('WAYLAND_DISPLAY',None)
    env['XDG_SESSION_TYPE']='x11'
    # Separate X display and cookie. Never shadow or attach to the user's desktop.
    Path(env['XAUTHORITY']).touch(mode=0o600)
    subprocess.run(['xauth','-f',env['XAUTHORITY']],input=f'add {display} . {secrets.token_hex(16)}\n'.encode(),check=True,stdout=subprocess.DEVNULL,env=env)
    (state/'viewport.json').write_text(json.dumps({'width':412,'height':820,'show':'initial'}))
    password=secrets.token_urlsafe(6);(state/'vnc-secret').write_text(password)
    subprocess.run([binary,'-storepasswd',password,str(state/'vnc-auth')],env=env,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    with socket.socket() as probe:probe.bind(('127.0.0.1',0));vnc_port=probe.getsockname()[1]
    env['AUGMENTOR_VNC_PORT']=str(vnc_port)
    env['AUGMENTOR_REMOTE_ORIGINS']=json.dumps(['http://127.0.0.1:8765',*args.origin])
    children=[];logs=[]
    def spawn(name,command):
        log=(state/(name+'.log')).open('w');logs.append(log)
        process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=log);process.component=name;children.append(process);return process
    def cleanup():
        for child in reversed(children):
            if child.poll() is None:child.terminate()
        for child in children:
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:child.kill();child.wait()
        for log in logs:log.close()
    atexit.register(cleanup)
    signal.signal(signal.SIGTERM,lambda *_:raise_exit());signal.signal(signal.SIGINT,lambda *_:raise_exit())
    spawn('display',['Xvfb',display,'-screen','0','1600x1400x24','-auth',env['XAUTHORITY'],'-nolisten','tcp','-noreset'])
    for _ in range(50):
        if Path('/tmp/.X11-unix/X'+display[1:]).exists():break
        time.sleep(.1)
    if shutil.which('xsetroot'):
        subprocess.run(['xsetroot','-solid','#101819'],env=env,check=True)
    # Composite the original transparent halo instead of displaying an opaque
    # black overlay while the agent works. Own only this isolated display.
    spawn('compositor',[compositor,'-n'])
    source=Path(selected['root'])
    env['AUGMENTOR_REMOTE_DESKTOP_ROOT']=str(source)
    python=Path(selected['python'])
    if selected.get('node'):env['AUGMENTOR_PI_NODE']=selected['node']
    if selected.get('dshService'):env['AUGMENTOR_DSH_SERVICE']=selected['dshService']
    print('Desktop source: '+str(source),flush=True)
    spawn('desktop',[str(python),str(ROOT/'apps/mobile/native_runner.py'),*(['--preview'] if args.preview else [])])
    spawn('vnc',[binary,'-norc','-display',display,'-auth',env['XAUTHORITY'],'-rfbauth',str(state/'vnc-auth'),'-rfbport',str(vnc_port),'-listen','127.0.0.1','-noipv6','-rfbportv6','0','-forever','-shared','-clip','412x820+0+0','-noxdamage','-repeat'])
    for _ in range(50):
        try:
            with socket.create_connection(('127.0.0.1',vnc_port),timeout=.2):break
        except OSError:time.sleep(.1)
    spawn('bridge',['node',str(ROOT/'apps/mobile/server.mjs')])
    print('Original Desktop preview: http://127.0.0.1:8765\nPairing key: '+str(state/'pairing-key'),flush=True)
    while all(child.poll() is None for child in children):time.sleep(.5)
    raise SystemExit('Remote component stopped: '+str([(p.component,p.poll()) for p in children])+'; logs: '+str(state))

def raise_exit():raise SystemExit(0)
if __name__=='__main__':main()
