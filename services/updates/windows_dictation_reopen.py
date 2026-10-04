# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One fixed broker launch inside the caller's verified, live completion."""
import os
from pathlib import Path
import time

from lifecycle.windows_dictation import discover_dictation
from lifecycle.windows_installer_process import InstallerProcess


def reopen(observer,captured,root,runtime,sha256,immutable,*,qualification=False):
    if not captured.get('hadDictation',False):return False
    if getattr(observer,'dictation_reopening_started',False):raise ValueError('Dictation reopening cannot be replayed.')
    root=Path(root);python=root/'python/python.exe';script=root/'services/dictation/server.py'
    if not python.is_file() or not script.is_file():raise ValueError('The verified target lacks its fixed dictation broker.')
    immutable()
    environment={key:value for key,value in os.environ.items()
        if not key.upper().startswith(('PYTHON','NODE_')) and key.upper() not in
            ('AUGMENTOR_UNIX_STARTUP_FD','AUGMENTOR_WINDOWS_STARTUP_FD')}
    # Use this verified coordinator's runtime, never replay a saved environment.
    environment['XDG_RUNTIME_DIR']=str(runtime)
    observer.dictation_reopening_started=True
    with InstallerProcess(python,sha256,['-I','-Xutf8','-B',str(script)],environment=environment,
            qualification_outer_job=qualification,allow_child_breakaway=True,installed_payload=True) as child:
        deadline=time.monotonic()+30
        while True:
            if child.poll() is not None:raise ValueError('The target dictation broker exited before readiness.')
            try:peers=discover_dictation(root,runtime)
            except FileNotFoundError:peers=[]  # Its held marker can precede pipe publication.
            try:
                if peers:
                    if len(peers)!=1 or peers[0].pid!=child.pid or peers[0].exited():
                        raise ValueError('The target dictation broker differs from its observed new process.')
                    if peers[0].initial['ready']:
                        if peers[0].control('status')['phase']!='ready':
                            raise ValueError('The target dictation broker is not accepting normal work.')
                        immutable()
                        if peers[0].exited():raise ValueError('The target broker exited during immutable verification.')
                        observer.dictation_reopened=True
                        return True
            finally:
                for peer in peers:peer.close()
            if time.monotonic()>=deadline:raise TimeoutError('The target dictation broker did not become ready. Reopen manually.')
            time.sleep(.1)
