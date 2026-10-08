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
from .. import agent_entries

class DshAdapter(DshClient):
    harness='dsh';preset='augmentor-linux';label='DSH'
    capabilities={'branch':True,'edit':True}
    stream_type=EventStream
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.native_interactions=False
        saved=current();self.product=saved.get('endpoint')==self.base and saved.get('home')==str(self.home)
        if self.product:self.preset='augmentor-linux-product'
        self.entry=agent_entries.get()
        self.custom=bool(self.entry and self.entry.get('preset'))
        if self.custom:self.preset=self.entry['preset']
        self.supports_prompt_improvement=not self.custom
        self.supports_voice=not self.custom
        self.initial_selection=(self.entry or {}).get('model')
    def owns_preset(self, preset):
        if self.custom:return preset==self.preset
        return preset in ('augmentor-linux-product','augmentor-browser-product') if self.product else preset==self.preset
    def owns_session(self,row):
        return self.owns_preset(row.get('agentPreset')) and (not self.custom or Path(row.get('cwd','')).resolve()==self.workspace().resolve())
    def agent_catalog(self):return super().call('agentPresets.list').get('presets',[])
    def setting(self,namespace):
        if self.custom and namespace=='permission':return None
        return super().setting(namespace)
    def check_entry(self):
        if agent_entries.binding(self.entry)!=agent_entries.binding(agent_entries.get()):
            raise ContractError('This desktop agent changed. Reopen its window to use the new selection.')
    def check_preset(self):
        row=next((r for r in self.agent_catalog() if r.get('id')==self.preset),None)
        if row is None or row.get('broken'):
            if not self.custom:raise ContractError('The Augmentor agent preset is unavailable. Open Settings → Connect DSH, check the connection, then Save and use DSH.')
            raise ContractError('Selected DSH agent preset is unavailable: '+self.preset+'. Refresh Agents in Settings or repair it in DSH.')
    def running_state(self, session):
        row=next((row for row in self.call('session.list')['items'] if row['sessionId']==session),None)
        return bool(row.get('running')) if row is not None else None
    def voice_ticket(self, session):
        if self.custom:raise ContractError('The Augmentor voice bridge is unavailable for independent DSH agents. Use typed chat or dictation.')
        if not self.product:raise ContractError('Connect the Augmentor DSH integration first.')
        token=(self.home/'augmentor-product-token').read_text().strip()
        row=next((row for row in self.call('session.list')['items'] if row['sessionId']==session),{})
        if not self.owns_preset(row.get('agentPreset')):raise ContractError('This conversation belongs to another role.')
        surface='browser' if row.get('agentPreset')=='augmentor-browser-product' else 'linux'
        result=http(self.base,'/api/resonant-voice',{'surface':surface,'sessionId':session},
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
        if self.custom and method=='settings.mutate' and p.get('ns')=='permission':raise ContractError('DSH owns this independent agent’s permissions.')
        if method=='host.describe' and self.product:
            status=http(self.base,'/api/augmentor-product');token=(self.home/'augmentor-product-token').read_text().strip()
            if status.get('version')!=VERSION or status.get('homeId')!=hashlib.sha256(token.encode()).hexdigest():raise ContractError('Reconnect the matching DSH integration from Settings.')
            self.native_interactions=status.get('nativeInteractions')==1 and (not self.custom or status.get('desktopAgents')==1)
        if method=='host.describe':
            self.check_entry();self.check_preset()
        if method in ('session.create','session.prompt','session.selectModel','session.branch','session.updateQueue'):
            self.check_entry()
            if self.custom:
                self.check_preset()
                if method=='session.create' and (p.get('agentPreset')!=self.preset or Path(p.get('cwd','')).resolve()!=self.workspace().resolve()):
                    raise ContractError('This conversation belongs to another DSH agent or working folder.')
                if method!='session.create':
                    sid=p.get('sessionId');row=next((r for r in super().call('session.list')['items'] if r['sessionId']==sid),None)
                    if row is None or not self.owns_session(row):raise ContractError('This conversation belongs to another DSH agent or working folder.')
        if method=='session.branch':return branch(super().call,p,surface='linux',endpoint=self.base,exact_fork=product_exact_fork(self.base,self.home) if self.product else None,allowed_presets=(self.preset,) if self.custom else None,required_cwd=str(self.workspace()) if self.custom else None)
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
        if self.custom:raise ContractError('Prompt improvement is unavailable for independent DSH agents.')
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
        key=(self.entry or {}).get('stateKey')
        return Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'augmentor-linux'/('session.'+key+'.json' if key else 'session.json')
    def workspace(self):return Path((self.entry or {}).get('cwd') or os.environ.get('AUGMENTOR_DSH_WORKSPACE',Path.home()/'Augmentor Linux'))
