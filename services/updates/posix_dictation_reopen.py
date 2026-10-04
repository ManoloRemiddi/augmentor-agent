# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One-shot fixed target broker start within the caller's verified completion."""
import os
from pathlib import Path
import subprocess
import time

from lifecycle.posix_components import discover_sockets


def reopen(backend,captured,root,runtime,immutable):
    if not captured.get('hadDictation',False):return False
    if getattr(backend,'dictation_reopening_started',False):raise ValueError('Dictation reopening cannot be replayed.')
    root=Path(root);python=root/'python/bin/python3';script=root/'services/dictation/server.py'
    if not python.is_file() or not script.is_file():raise ValueError('The verified target lacks its fixed dictation broker.')
    immutable()
    environment={key:value for key,value in os.environ.items()
        if not key.startswith(('PYTHON','NODE_')) and key!='AUGMENTOR_UNIX_STARTUP_FD'}
    backend.dictation_reopening_started=True
    child=subprocess.Popen([str(python),'-I','-B',str(script)],stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=environment,close_fds=True,start_new_session=True)
    deadline=time.monotonic()+30
    while True:
        if child.poll() is not None:raise ValueError('The target dictation broker exited before readiness.')
        peers=discover_sockets(runtime,r'augmentor-dictation-[1-9][0-9]{0,19}\.sock',root,python,kind='dictation')
        try:
            if peers:
                if len(peers)!=1 or peers[0].process.pid!=child.pid or peers[0].process.exited():
                    raise ValueError('The target dictation broker differs from its observed new process.')
                if peers[0].initial.get('ready') is True:
                    state=peers[0].control('status')
                    if state['phase']!='ready':raise ValueError('The target dictation broker is not accepting normal work.')
                    immutable()
                    if peers[0].process.exited():raise ValueError('The target broker exited during immutable verification.')
                    backend.dictation_reopened=True
                    # Reap the supervised child later without affecting its lifetime.
                    import threading
                    threading.Thread(target=child.wait,daemon=True).start()
                    return True
        finally:
            for peer in peers:peer.close()
        if time.monotonic()>=deadline:raise TimeoutError('The target dictation broker did not become ready. Reopen manually.')
        time.sleep(.1)
