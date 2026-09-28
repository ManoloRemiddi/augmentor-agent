# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Private native-browser control, separate from Chromium's binary chat stream.

The launcher must verify that a registering bridge belongs to its owned process
range. A same-user caller can observe identity or send bounded maintenance RPCs;
there is no arbitrary command, process termination or automatic retry interface.
This transport alone grants no permission to replace files or close a browser.
"""
import hmac
import json
import os
from pathlib import Path
import secrets
import socket
import socketserver
import struct
import sys
import threading
import time
import uuid

from platform_adapters import locks
from platform_adapters.private_files import descriptor, require_directory
from platform_adapters.transport import ThreadingLocalServer, prepare_endpoint, cleanup_endpoint
from platform_support import require_same_user

PROTOCOL = 'augmentor-browser-owner/1'
LIMIT = 65536
METHODS = frozenset('host.maintenance.'+action for action in ('status','prepare','renew','cancel','commit'))


def peer_pid(connection):
    require_same_user(connection)
    if sys.platform == 'win32': return connection.verify_peer()
    if sys.platform == 'linux':
        return struct.unpack('3i', connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i')))[0]
    raise RuntimeError('This browser-owner transport requires Windows or the Linux qualification adapter.')


class Records:
    def __init__(self, connection):
        self.connection=connection; self.buffer=bytearray()
        self.write_lock=threading.Lock()
        # Use raw recv, not a buffered socket file: a timeout must not poison a
        # partially read record or lose bytes on an otherwise idle connection.
        self.connection.settimeout(1)

    def read(self, deadline=None):
        while True:
            end=self.buffer.find(b'\n')
            if end>=0:
                raw=bytes(self.buffer[:end]); del self.buffer[:end+1]
                if len(raw)>LIMIT: raise ValueError('Browser control record is too large.')
                value=json.loads(raw)
                if not isinstance(value,dict): raise ValueError('Invalid browser control record.')
                return value
            if len(self.buffer)>LIMIT: raise ValueError('Browser control record is too large.')
            if deadline is not None and time.monotonic()>=deadline: raise TimeoutError('Browser control did not respond; the request was not replayed.')
            try: chunk=self.connection.recv(8192)
            except TimeoutError: continue
            if not chunk: raise ConnectionError('Browser control disconnected; the request was not replayed.')
            self.buffer.extend(chunk)

    def write(self, value):
        raw=json.dumps(value,separators=(',',':')).encode('utf-8')+b'\n'
        if len(raw)>LIMIT: raise ValueError('Browser control record is too large.')
        with self.write_lock: self.connection.sendall(raw)


class BridgeLink:
    def __init__(self, records, timeout):
        self.records=records; self.timeout=timeout
        self.lock=threading.RLock(); self.pending={}; self.closed=False

    def exchange(self, method, params):
        identity=uuid.uuid4().hex; event=threading.Event(); result={}
        with self.lock:
            if self.closed: raise ConnectionError('The observed browser bridge disconnected.')
            self.pending[identity]=(event,result)
        try:
            self.records.write({'protocol':PROTOCOL,'id':identity,'method':method,'params':params})
            if not event.wait(self.timeout): raise TimeoutError('Browser maintenance outcome is unknown. The request was not replayed.')
            if 'error' in result: raise ValueError(result['error'])
            return result['value']
        finally:
            with self.lock: self.pending.pop(identity,None)

    def receive(self, message):
        if message.get('protocol')!=PROTOCOL or not isinstance(message.get('id'),str): raise ValueError('Invalid bridge response.')
        with self.lock:
            pending=self.pending.get(message['id'])
            if pending is None: return  # A late answer is never a new operation.
            event,result=pending
            if event.is_set(): return
            if 'error' in message:
                result['error']='The browser refused maintenance. Its work was preserved.'
            elif isinstance(message.get('result'),dict): result['value']=message['result']
            else: raise ValueError('Invalid browser maintenance response.')
            event.set()

    def close(self):
        with self.lock:
            self.closed=True
            for event,result in self.pending.values():
                if not event.is_set(): result['error']='The observed browser bridge disconnected. The request was not replayed.'; event.set()
        try: self.records.connection.shutdown(socket.SHUT_RDWR)
        except OSError: pass
        self.records.connection.close()


class BrowserControlServer:
    def __init__(self, root, runtime, *, verify_bridge, timeout=10):
        self.root=Path(root).resolve(); self.runtime=require_directory(runtime)
        self.verify_bridge=verify_bridge; self.timeout=timeout
        self.nonce=secrets.token_hex(32)
        self.lock=threading.RLock(); self.bridge=None; self.lease=None; self.server=None; self.thread=None; self.closed=False
        self.lock_path=self.runtime/f'augmentor-browser-{os.getpid()}.lock'
        self.endpoint=self.lock_path.with_suffix('.sock')

    def identity(self):
        return {'protocol':PROTOCOL,'pid':os.getpid(),'buildRoot':str(self.root),'maintenanceAdmission':1}

    def handle(self, connection):
        records=Records(connection)
        observation=None; link=None
        try:
            pid=peer_pid(connection)
            message=records.read(time.monotonic()+5)
            if message.get('protocol')!=PROTOCOL: raise ValueError('Unsupported browser-owner protocol.')
            if message.get('kind')=='bridge':
                if set(message)!={'protocol','kind','nonce'} or not isinstance(message['nonce'],str) or not hmac.compare_digest(message['nonce'],self.nonce):
                    raise PermissionError('The browser bridge registration was refused.')
                # This callback must retain an actual process observation and
                # verify its executable and membership in the launcher's Job.
                observation=self.verify_bridge(pid)
                with self.lock:
                    if self.closed or self.bridge is not None: raise ValueError('A browser bridge is already registered or closing.')
                    link=BridgeLink(records,self.timeout)
                    records.write({**self.identity(),'ok':True})
                    self.bridge=link
                while True: link.receive(records.read())
            if message.get('kind')=='describe' and set(message)=={'protocol','kind'}:
                with self.lock: connected=self.bridge is not None and not self.bridge.closed
                records.write({**self.identity(),'ok':True,'connected':connected}); return
            if message.get('kind')!='maintenance' or set(message)!={'protocol','kind','method','params'} or message.get('method') not in METHODS or not isinstance(message.get('params'),dict):
                raise ValueError('Unsupported browser maintenance request.')
            action=message['method'].removeprefix('host.maintenance.')
            params=message['params']
            if action=='status':
                if params: raise ValueError('Maintenance status does not accept fields.')
            elif set(params)!={'token'} or not isinstance(params['token'],str) or not 32<=len(params['token'])<=64 or any(c not in '0123456789abcdef' for c in params['token']):
                raise ValueError('A valid maintenance reservation is required.')
            with self.lock: current=self.bridge
            if current is None: raise ValueError('The browser bridge is not ready. This request was not started.')
            result=current.exchange(message['method'],params)
            records.write({**self.identity(),'ok':True,'result':result})
        except Exception:
            # Neither form contents nor registration credentials belong in a
            # discovery response. Caller errors do not stop the native bridge.
            try: records.write({**self.identity(),'ok':False,'error':'Browser maintenance could not be confirmed. Its work was preserved; no request was replayed.'})
            except (OSError,ValueError): pass
        finally:
            if link is not None:
                with self.lock:
                    if self.bridge is link: self.bridge=None
                link.close()
            if observation is not None: observation.Close()

    def __enter__(self):
        self.lease=descriptor(self.lock_path,writable=True,create=True)
        try:
            locks.flock(self.lease,locks.LOCK_EX|locks.LOCK_NB)
            prepare_endpoint(self.endpoint)
            owner=self
            class Handler(socketserver.BaseRequestHandler):
                def handle(self): owner.handle(self.request)
            self.server=ThreadingLocalServer(str(self.endpoint),Handler)
            self.server.daemon_threads=True
            self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
            return self
        except BaseException: self.close(); raise

    def close(self):
        with self.lock: self.closed=True; link=self.bridge
        if link is not None: link.close()
        if self.thread is not None and self.thread.is_alive():
            self.server.shutdown();self.thread.join(timeout=5)
        if self.server is not None: self.server.server_close();cleanup_endpoint(self.endpoint)
        if self.lease is not None: os.close(self.lease);self.lease=None
        self.server=None;self.thread=None

    def __exit__(self,*_): self.close()
