#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Desktop transport; only a never-submitted connection may be started/retried."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time


def call(request,start=True):
    path=Path(os.environ.get('XDG_RUNTIME_DIR',f'/tmp/augmentor-{os.getuid()}' if sys.platform=='darwin' else f'/run/user/{os.getuid()}'))/'augmentor-desktop.sock'
    client=socket.socket(socket.AF_UNIX);client.settimeout(115)
    try:
        try:client.connect(str(path))
        except (FileNotFoundError,ConnectionRefusedError):
            if not start or os.environ.get('AUGMENTOR_DESKTOP_NO_AUTOSTART')=='1' or request.get('method')!='connect':
                if request.get('method')=='stop':return {'ok':True,'result':{'stopped':True}}
                raise RuntimeError('Desktop control is not connected. Use linux_desktop_connect first.')
            # Retrieve only graphical session variables from the user's own manager.
            env=dict(os.environ)
            allowed={'DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','XDG_CURRENT_DESKTOP','XDG_SESSION_TYPE'}
            try:
                for line in subprocess.check_output(['systemctl','--user','show-environment'],text=True,timeout=3).splitlines():
                    key,_,value=line.partition('=')
                    if key in allowed:env[key]=value
            except (OSError,subprocess.SubprocessError):pass
            if sys.platform=='linux':env['QT_QPA_PLATFORM']='xcb'
            child=subprocess.Popen([sys.executable,str(Path(__file__).with_name('service.py'))],env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            import threading
            threading.Thread(target=child.wait,daemon=True).start()
            end=time.monotonic()+8
            while True:
                try:client.connect(str(path));break
                except (FileNotFoundError,ConnectionRefusedError):
                    if time.monotonic()>end:raise RuntimeError('Desktop executor could not start. Check the desktop package and logged-in graphical session.')
                    time.sleep(.05)
        client.sendall((json.dumps({'protocol':'augmentor-desktop/1',**request})+'\n').encode())
        with client.makefile('rb') as reader:raw=reader.readline(2*1024*1024+1)
        if len(raw)>2*1024*1024 or not raw.endswith(b'\n'):raise RuntimeError('Invalid desktop response. An action may already have run; inspect before retrying.')
        return json.loads(raw)
    finally:client.close()


if __name__=='__main__':
    try:
        raw=sys.stdin.read(32769)
        if len(raw)>32768:raise RuntimeError('Desktop request exceeds size limit.')
        response=call(json.loads(raw))
    except Exception as exc:response={'ok':False,'error':str(exc)[:600]}
    print(json.dumps(response))
