# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Start one detached socket harness host. Only safe health probes trigger recovery."""
import fcntl
import os
import shutil
import socket
import subprocess
import time
import sys
from pathlib import Path


def ensure_running(harness='pi'):
    if harness != 'pi':raise ValueError('Only Pi uses the managed socket runtime.')
    prefix='AUGMENTOR_'+harness.upper()
    project=Path(__file__).resolve().parents[3]
    state=Path(os.environ.get(prefix+'_STATE',Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/('augmentor-'+harness)))
    state.mkdir(mode=0o700,parents=True,exist_ok=True)
    endpoint=os.environ.get(prefix+'_SOCKET',str(state/'runtime.sock'))
    def alive():
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as probe:
            probe.settimeout(1)
            try:probe.connect(endpoint);return True
            except (FileNotFoundError,ConnectionRefusedError):return False
    if alive():return
    with (state/'startup.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if alive():return
        node=os.environ.get('AUGMENTOR_PI_NODE') or shutil.which('node')
        script=project/'dist/runtime/src/main.js'
        if not node or not script.exists():raise RuntimeError(harness+' runtime is not built. Run npm ci --ignore-scripts and npm run build in the app installation.')
        log=os.open(state/'runtime.log',os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
        try:child=subprocess.Popen([sys.executable,str(project/'scripts/run-component.py'),'runtime',node,str(script)],cwd=project,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,env={**os.environ,'PI_TELEMETRY':'0','PI_SKIP_VERSION_CHECK':'1'})
        finally:os.close(log)
        until=time.monotonic()+60
        while time.monotonic()<until:
            if alive():return
            if child.poll() is not None:raise RuntimeError(harness+' runtime failed to start. See '+str(state/'runtime.log'))
            time.sleep(.1)
        raise RuntimeError(harness+' runtime startup timed out. See '+str(state/'runtime.log'))
