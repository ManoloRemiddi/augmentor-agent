# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Prompt transport independent of either harness, with bounded startup."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import threading
import uuid
from .pi_client import ContractError

PROTOCOL='augmentor-prompts/1'

class PromptClient:
    def __init__(self):
        state=Path(os.environ.get('AUGMENTOR_SHARED_STATE',Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'augmentor'))
        self.base=str(state/'prompts.sock')
    def call(self,method,payload=None,request_id=None):
        automatic=method.startswith('memory.dual.')
        endpoint=str(Path(self.base).with_name('dual-memory.sock')) if automatic else self.base
        connection=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);connection.settimeout(20)
        try:
            try:connection.connect(endpoint)
            except (FileNotFoundError,ConnectionRefusedError):
                service=Path(__file__).resolve().parents[3]/('services/memory/service.py' if automatic else 'services/prompt-library/service.py')
                if not service.is_file():raise ContractError('Shared prompt service is not installed.')
                # This client is also used outside the app launcher. Never rely
                # on inherited environment flags to preserve a sealed bundle.
                child=subprocess.Popen([sys.executable,'-B',str(service)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
                threading.Thread(target=child.wait,daemon=True).start()
                deadline=time.monotonic()+5
                while True:
                    try:connection.connect(endpoint);break
                    except (FileNotFoundError,ConnectionRefusedError):
                        if time.monotonic()>deadline:raise ContractError('Shared prompt service could not start.')
                        time.sleep(.05)
            identity=request_id or uuid.uuid4().hex
            raw=(json.dumps({'protocol':PROTOCOL,'id':identity,'method':method,'params':payload or {}})+'\n').encode()
            if len(raw)>1024*1024:raise ContractError('Prompt request exceeds size limit.')
            connection.sendall(raw)
            with connection.makefile('rb') as reader:response=reader.readline(1024*1024+1)
            if len(response)>1024*1024 or not response.endswith(b'\n'):raise ContractError('Invalid prompt response')
            result=json.loads(response)
            if result.get('id')!=identity:raise ContractError('Invalid prompt response ID')
            if 'error' in result:raise ContractError(result['error']['message'])
            return result['result']
        except (OSError,ValueError) as error:raise ContractError('Shared prompt library is unavailable: '+str(error)) from error
        finally:connection.close()
    def setting(self,namespace):
        if namespace!='prompt-library':return None
        result=self.call('prompts.list')
        return {'ns':namespace,'revision':result['revision'],'value':result}
