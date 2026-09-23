# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
from pathlib import Path
import os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'services'))
from dsh.branch import branch,product_exact_fork
from dsh.setup import current,http,VERSION
import hashlib
import json
import urllib.request
import urllib.error
from .dsh_wire import DshClient,EventStream
from ..pi_client import ContractError

class DshAdapter(DshClient):
    harness='dsh';preset='augmentor-linux';label='DSH'
    capabilities={'branch':True,'edit':True}
    stream_type=EventStream
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.native_interactions=False
        saved=current();self.product=saved.get('endpoint')==self.base and saved.get('home')==str(self.home)
        if self.product:self.preset='augmentor-linux-product'
    def voice_ticket(self, session):
        if not self.product:raise ContractError('Connect the Augmentor DSH integration first.')
        token=(self.home/'augmentor-product-token').read_text().strip()
        result=http(self.base,'/api/resonant-voice',{'surface':'linux','sessionId':session},
                    {'x-augmentor-product-token':token})
        if not result.get('ok'):raise ContractError(result.get('error','Resonant Voice is unavailable.'))
        if result.get('protocol')!='resonant-voice/1':raise ContractError('Incompatible voice service.')
        return result

    def saved_chats(self,action='state',session=None):
        if not self.product:return super().saved_chats(action,session)
        token=(self.home/'augmentor-product-token').read_text().strip()
        result=http(self.base,'/api/augmentor-product',{'surface':'linux','action':action,'sessionId':session},{'x-augmentor-product-token':token})
        if not result.get('ok'):raise ContractError('DSH could not complete this saved-chat operation.')
        return result['saved']
    def interaction_operation(self, **values):
        if not self.product:
            raise ContractError('Reconnect the Augmentor DSH integration for native interactions.')
        token=(self.home/'augmentor-product-token').read_text().strip()
        result=http(self.base,'/api/augmentor-product',
                    {'surface':'linux','action':'interaction',**values},
                    {'x-augmentor-product-token':token})
        if not result.get('ok'):
            raise ContractError('DSH could not complete this interaction operation.')
        return result
    def call(self,method,payload=None):
        p=payload or {}
        if method=='host.describe' and self.product:
            status=http(self.base,'/api/augmentor-product');token=(self.home/'augmentor-product-token').read_text().strip()
            if status.get('version')!=VERSION or status.get('homeId')!=hashlib.sha256(token.encode()).hexdigest():raise ContractError('Reconnect the matching DSH integration from Settings.')
            self.native_interactions=status.get('nativeInteractions')==1
        if method=='session.branch':return branch(super().call,p,surface='linux',endpoint=self.base,exact_fork=product_exact_fork(self.base,self.home) if self.product else None)
        if method=='session.create':p={k:v for k,v in p.items() if k!='selection'}
        if method=='models.pin':
            section=self.setting('model-picker-augmented')
            if not section:raise ContractError('Enable the DSH model picker plugin to pin models.')
            key=p['provider']+'/'+p['model'];pins=[v for v in section['value'].get('pinned',[]) if v!=key]
            if p.get('pinned'):pins.append(key)
            super().call('settings.mutate',{'ns':'model-picker-augmented','expectedRevision':section['revision'],'ops':[{'op':'set','path':['pinned'],'value':pins}]})
            return self.model_catalog()
        return super().call(method,p)
    supports_prompt_improvement=True

    def improve_prompt(self, text, instructions, selection):
        if not self.product:raise ContractError('Connect the Augmentor DSH integration before improving prompts.')
        token=(self.home/'augmentor-product-token').read_text().strip()
        # Inline editing must return an editable draft, including feedback and fragments.
        instructions += ('\n\nInline editor override: Always rewrite the supplied text, even if it is feedback, '
                         'a reaction, a fragment, or a conversational message rather than a task. '
                         'Do not ask clarifying questions. Preserve unresolved ambiguity instead of inventing details. '
                         'For text that is already clear, return it unchanged. Return kind rewrite, never clarify.')
        payload={'surface':'linux','action':'improvePrompt','text':text,'instructions':instructions,'provider':selection['provider'],'model':selection['model']}
        body=json.dumps(payload).encode()
        if len(body)>16384:raise ContractError('This draft is too long for the prompt editor.')
        request=urllib.request.Request(self.base+'/api/augmentor-product',data=body,headers={'Content-Type':'application/json','x-augmentor-product-token':token})
        try:
            with self.opener.open(request,timeout=65) as response:raw=response.read(128*1024+1)
        except urllib.error.HTTPError as exc:
            try:message=json.loads(exc.read(8192)).get('error','Could not improve this prompt.')
            except ValueError:message='Could not improve this prompt.'
            raise ContractError(message) from exc
        if len(raw)>128*1024:raise ContractError('The rewrite exceeded the response limit.')
        result=json.loads(raw)
        if not result.get('ok'):raise ContractError(result.get('error','Could not improve this prompt.'))
        return result

    def state_path(self):
        return Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'augmentor-linux/session.json'
    def workspace(self):return Path(os.environ.get('AUGMENTOR_DSH_WORKSPACE',Path.home()/'Augmentor Linux'))
