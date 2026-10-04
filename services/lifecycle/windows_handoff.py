# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One-shot installer gate transfer over a private, kernel-authenticated pipe.

Only a live member of the already verified installer's Job receives a duplicate.
Preparation alone never permits file replacement: APPLY is a separate decision.
The caller must qualify global drain and durable recovery before authorizing it.
"""
import os
import math
from pathlib import Path
import secrets
import socketserver
import struct
import sys
import threading

HELLO=b'AUGI\x01\0\0\0'
READY=b'READY\0\0\0'
APPLY=b'APPLY\0\0\0'
ABORT=b'ABORT\0\0\0'
ACCEPTED=b'ACCEPTED'


def read_exact(connection,length):
    result=bytearray()
    while len(result)<length:
        chunk=connection.recv(length-len(result))
        if not chunk:raise ConnectionError('The installer handoff disconnected. No request was replayed.')
        result.extend(chunk)
    return bytes(result)


class InstallerHandoff:
    def __init__(self,startup):
        if sys.platform!='win32':raise RuntimeError('Installer handoff requires Windows.')
        if not startup.maintenance or startup.fd is None:raise ValueError('Retain the startup writer before handing off.')
        self.startup=startup
        self.endpoint=Path(startup.path).parent/('installer-'+secrets.token_hex(24)+'.sock')
        self.installer=None;self.process=None;self.pid=None
        self.server=None;self.thread=None;self.connection=None
        self.bound=threading.Event();self.ready=threading.Event();self.decision=threading.Event();self.finished=threading.Event()
        self.lock=threading.RLock();self.claimed=False;self.closed=False;self.apply=False;self.accepted=False;self.error=None

    def arguments(self):
        from platform_adapters.windows_pipe import pipe_name
        if self.server is None or self.closed:raise ValueError('Start the private handoff before launching its installer.')
        return ['/augmentorpipe='+pipe_name(self.endpoint),'/augmentorcoordinator='+str(os.getpid())]

    def bind(self,installer):
        with self.lock:
            if self.installer is not None or self.closed:raise ValueError('The handoff is already bound or closed.')
            self.installer=installer;self.bound.set()

    def handle(self,connection):
        import msvcrt,win32api,win32con
        observation=None;claimed=False
        try:
            connection.settimeout(5)
            pid=connection.verify_peer()
            if not self.bound.wait(5):raise TimeoutError('The installer launch did not bind to its handoff.')
            if self.installer is None:raise ValueError('No verified installer is bound.')
            observation=self.installer.observe(pid,transfer=True)
            if read_exact(connection,len(HELLO))!=HELLO:raise ValueError('Unsupported installer handoff.')
            with self.lock:
                if self.claimed or self.closed:raise ValueError('The installer handoff is already consumed or closed.')
                self.claimed=claimed=True;self.connection=connection
                self.process,observation=observation,None;self.pid=pid
                if self.startup.fd is None:raise ValueError('Startup exclusion was released before transfer.')
                remote=win32api.DuplicateHandle(win32api.GetCurrentProcess(),msvcrt.get_osfhandle(self.startup.fd),
                    self.process,0,False,win32con.DUPLICATE_SAME_ACCESS)
                # This handle belongs to the OTHER process: never CloseHandle
                # its numeric value in this coordinator's handle table.
                value=remote.Detach()
            connection.sendall(b'GATE'+struct.pack('<Q',value))
            if read_exact(connection,len(READY))!=READY:raise ValueError('The installer did not confirm the startup gate.')
            self.ready.set()
            if not self.decision.wait(60):raise TimeoutError('Installer authorization expired before application.')
            connection.sendall(APPLY if self.apply else ABORT)
            if self.apply:
                if read_exact(connection,len(ACCEPTED))!=ACCEPTED:raise ValueError('The installer application acknowledgment was lost.')
                self.accepted=True
        except Exception as error:
            if claimed:self.error=error
        finally:
            if observation is not None:observation.Close()
            if claimed:self.finished.set()

    def wait_ready(self,timeout=10):
        import time
        if not math.isfinite(timeout) or not 0<timeout<=30:raise ValueError('Use a bounded installer readiness wait.')
        deadline=time.monotonic()+timeout
        while not self.ready.wait(.02):
            if self.finished.is_set():raise RuntimeError('The installer could not retain startup exclusion.') from self.error
            if time.monotonic()>=deadline:raise TimeoutError('The installer did not acknowledge readiness; application was not authorized.')
        if self.finished.is_set():raise RuntimeError('The prepared installer disconnected.') from self.error

    def authorize(self):
        with self.lock:
            if self.closed or not self.ready.is_set() or self.finished.is_set() or self.decision.is_set():
                raise ValueError('The prepared installer cannot accept authorization.')
            self.apply=True;self.decision.set()
        if not self.finished.wait(10) or not self.accepted:
            raise RuntimeError('The installer application outcome is unknown. Do not repeat authorization; inspect transaction recovery.') from self.error

    def __enter__(self):
        from platform_adapters.transport import ThreadingLocalServer
        owner=self
        class Handler(socketserver.BaseRequestHandler):
            def handle(self):owner.handle(self.request)
        self.server=ThreadingLocalServer(str(self.endpoint),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,name='augmentor-installer-handoff',daemon=True)
        self.thread.start()
        return self

    def close(self):
        with self.lock:
            if self.closed:return
            self.closed=True
            # Once sent, APPLY can never be retried or retracted by cleanup.
            self.decision.set();self.bound.set()
        if self.connection is not None:
            self.finished.wait(10)
            self.connection.close()
        if self.server is not None:
            self.server.shutdown();self.thread.join(timeout=5);self.server.server_close()
        if self.process is not None:self.process.Close();self.process=None

    def __exit__(self,*_):self.close()
