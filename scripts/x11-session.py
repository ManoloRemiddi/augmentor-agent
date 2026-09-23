#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Run a command on an atomically allocated, authenticated Xvfb display.

Wait for this server to exit before returning. xvfb-run can return while its old
server is still shutting down, letting the next UI check reuse that display.
"""
import os
from pathlib import Path
import secrets
import select
import subprocess
import sys
import tempfile

def run(command):
    with tempfile.TemporaryDirectory(prefix='augmentor-display-') as directory:
        authority=Path(directory)/'Xauthority';authority.touch(mode=0o600)
        cookie=secrets.token_hex(16)
        def authorize(display):
            subprocess.run(['xauth','-f',str(authority)],input=f'add {display} . {cookie}\n',text=True,check=True,stdout=subprocess.DEVNULL)
        # X servers load the cookie records from the authorization file. Add the
        # actual display's client lookup record once -displayfd allocates it.
        authorize(':0')
        reader,writer=os.pipe()
        server=subprocess.Popen(['Xvfb','-displayfd',str(writer),'-screen','0','1280x900x24','-nolisten','tcp','-auth',str(authority)],pass_fds=(writer,))
        os.close(writer)
        try:
            if not select.select([reader],[],[],10)[0]:raise RuntimeError('Xvfb did not announce a display')
            display=os.read(reader,64).decode().strip()
            if not display.isdigit():raise RuntimeError('Xvfb exited before allocating a display')
            authorize(':'+display)
            env={**os.environ,'DISPLAY':':'+display,'XAUTHORITY':str(authority)}
            subprocess.run(['xprop','-root'],env=env,check=True,stdout=subprocess.DEVNULL)
            return subprocess.run(command,env=env).returncode
        finally:
            os.close(reader);server.terminate()
            try:server.wait(timeout=10)
            except subprocess.TimeoutExpired:server.kill();server.wait()

if __name__=='__main__':
    if len(sys.argv)<2:raise SystemExit('Pass the command to run inside X11')
    raise SystemExit(run(sys.argv[1:]))
