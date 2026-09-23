# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Private Unix-socket client for Augmentor's Pi host. No harness HTTP API."""
import json
import os
import socket
import threading
import uuid
from pathlib import Path

PROTOCOL = 'augmentor-pi/1'
MAX_FRAME = 1024 * 1024

class ContractError(RuntimeError):
    pass


def socket_path():
    state = Path(os.environ.get('AUGMENTOR_PI_STATE', Path(os.environ.get('XDG_STATE_HOME', Path.home()/'.local/state'))/'augmentor-pi'))
    return os.environ.get('AUGMENTOR_PI_SOCKET', str(state/'runtime.sock'))


class Connection:
    def __init__(self, path, protocol=PROTOCOL):
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.settimeout(20)
        try:
            self.socket.connect(path)
            self.file = self.socket.makefile('rb')
            value = self.call('host.hello', {'protocol': protocol})
            if value.get('protocol') != protocol:
                raise ContractError('Incompatible Augmentor runtime')
        except Exception:
            self.socket.close()
            raise

    def read(self):
        raw = self.file.readline(MAX_FRAME+1)
        if not raw:
            raise ContractError('Pi runtime connection closed')
        if len(raw)>MAX_FRAME or not raw.endswith(b'\n'):
            raise ContractError('Pi runtime frame exceeded limit')
        return json.loads(raw)

    def call(self, method, params=None):
        identity = uuid.uuid4().hex
        raw = (json.dumps({'id':identity,'method':method,'params':params or {}})+'\n').encode()
        if len(raw)>MAX_FRAME: raise ContractError('Request exceeded size limit')
        self.socket.sendall(raw)
        result=self.read()
        if result.get('id')!=identity: raise ContractError('Invalid Pi response correlation')
        if 'error' in result: raise ContractError(result['error'].get('message','Pi request failed'))
        return result.get('result')

    def close(self):
        try:self.socket.shutdown(socket.SHUT_RDWR)
        except OSError:pass
        self.file.close()
        self.socket.close()


class PiClient:
    def __init__(self, base=None):
        self.base = base or socket_path()

    def call(self, method, payload=None):
        connection=None
        try:
            try:connection=Connection(self.base)
            except (FileNotFoundError,ConnectionRefusedError):
                if method != 'host.describe' or os.environ.get('AUGMENTOR_PI_NO_AUTOSTART') == '1':raise
                from .runtime_start import ensure_running
                ensure_running()
                connection=Connection(self.base)
            return connection.call(method,payload)
        except (OSError,ValueError) as exc:
            raise ContractError('Cannot reach the Pi runtime: '+str(exc)) from exc
        finally:
            if connection:connection.close()

    def respond(self, rpc_id, value):
        return self.call('interaction.respond',{'rpcId':rpc_id,'sessionId':value['sessionId'],'value':value})

    def validate_model(self, selection):return self.call('models.validate',selection)
    def model_catalog(self):return self.call('models.list')
    def session_rows(self):return self.call('session.list')['items']
    def saved_chats(self,action='state',session=None):return self.call('chats.saved',{'action':action,'sessionId':session})['saved']
    def setting(self,namespace):return next((s for s in self.call('settings.describe')['namespaces'] if s['ns']==namespace),None)


class EventStream:
    def __init__(self,client,session,on_frame,on_disconnect):
        self.client,self.session=client,session
        self.on_frame,self.on_disconnect=on_frame,on_disconnect
        self.connection=None;self.closed=threading.Event();self.ready=threading.Event();self.failure=None

    def start(self):
        threading.Thread(target=self._run,daemon=True,name='augmentor-pi-events').start()
        if not self.ready.wait(6):
            self.close();raise ContractError('Pi event connection timed out')
        if self.failure:raise ContractError(self.failure)

    def _run(self):
        try:
            self.connection=self.client.connection() if hasattr(self.client,'connection') else Connection(self.client.base)
            self.connection.call('events.subscribe',{'sessionId':self.session})
            self.connection.socket.settimeout(None)
            self.ready.set()
            while not self.closed.is_set():
                value=self.connection.read()
                if 'event' in value:self.on_frame(value['event'])
        except Exception as exc:
            self.failure=str(exc);self.ready.set()
            if not self.closed.is_set():self.on_disconnect(self.failure)
        finally:
            if self.connection:self.connection.close()

    def close(self):
        self.closed.set()
        if self.connection:
            try:self.connection.socket.shutdown(socket.SHUT_RDWR)
            except OSError:pass
