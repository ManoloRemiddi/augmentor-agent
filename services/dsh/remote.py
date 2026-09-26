# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Authenticated DSH 0.1.5 Typert transport shared by setup, desktop and branching.

Only an explicit authentication refusal can retry a request. Network failures
and server errors are never replayed. Session cookies remain in this process.
"""
import ipaddress
import json
import os
from pathlib import Path
import re
import threading
import urllib.error
import urllib.request
from urllib.parse import urlsplit, parse_qs, quote
import uuid
import websocket

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None

class Remote:
    def __init__(self, base, home, token=None):
        u=urlsplit(base)
        if u.scheme!='http' or not ipaddress.ip_address(u.hostname or '').is_loopback or u.username or u.password or u.path not in ('','/') or u.query or u.fragment:
            raise ValueError('DSH requires a numeric loopback HTTP origin.')
        self.base=base.rstrip('/');self.home=Path(home);self.cookie='';self.token=token
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        self.lock=threading.RLock()
    def request(self, path, body=None, headers=None):
        data=None if body is None else json.dumps(body).encode()
        request=urllib.request.Request(self.base+path,data=data,headers={'Content-Type':'application/json',**(headers or {})})
        try:return self.opener.open(request,timeout=20)
        except urllib.error.HTTPError as e:return e
    def browser_url(self):
        """A fresh native-to-browser login handoff, never a cached launch token.

        The browser exchanges DSH's process token for its own HttpOnly cookie.
        Callers must not persist, log or display this credential-bearing URL.
        """
        try:secret=(self.home/'augmentor-ws-token').read_text().strip()
        except OSError:secret=''
        with self.request('/api/augmentor/auth',{}, {'x-augmentor-token':secret}) as r:
            if r.status!=200:raise ValueError('DSH could not open its browser session. Check the Augmentor connection in Agent setup.')
            token=json.loads(r.read(8192)).get('token')
        if not isinstance(token,str) or not re.fullmatch('[A-Za-z0-9_-]+',token):raise ValueError('Invalid DSH launch token.')
        return self.base+'/?token='+quote(token,safe='')
    def configured_providers(self):
        """Use DSH's Models page contract, not catalog presence, for setup status.

        Credential describe returns availability only, never a stored key. This
        checks configuration, not whether a provider accepts an inference call.
        """
        active={row['id'] for row in self.invoke('llm/listProviders')}
        directory=self.invoke('llm/listConfigurableProviders')
        namespaces={row['ns']:row['value'] for row in self.invoke('settings/describe').get('namespaces',[])}
        references={}
        for row in directory:
            if row['provider'] not in active:continue
            value=namespaces.get(row['settingsNs'],{})
            for key in row.get('settingsPath',[]):
                value=value.get(key,{}) if isinstance(value,dict) else {}
            ref=value.get('apiKeyEnv') if isinstance(value,dict) else None
            if ref:references[row['provider']]=ref
        credentials=self.invoke('credentials/describe',{'refs':list(set(references.values()))}) if references else {}
        return sorted(provider for provider in active if provider not in references or credentials.get(references[provider],{}).get('configured') is True)
    def authorize(self):
        with self.lock:
            with self.request('/',headers={'Cookie':self.cookie}) as r:
                if r.status==200:return
                if r.status!=401:raise ValueError('DSH local authentication failed.')
            self.cookie=''
            token=self.token or os.environ.get('AUGMENTOR_DSH_AUTH_TOKEN')
            if not token:
                try:secret=(self.home/'augmentor-ws-token').read_text().strip()
                except OSError:secret=''
                with self.request('/api/augmentor/auth',{}, {'x-augmentor-token':secret}) as r:
                    if r.status!=200:raise ValueError('Paste the complete local URL printed by dsh web into Connect DSH, then check again. No DeepSeek account is needed.')
                    token=json.loads(r.read(8192)).get('token')
            if not isinstance(token,str) or not re.fullmatch('[A-Za-z0-9_-]+',token):raise ValueError('Invalid DSH launch token.')
            with self.request('/?token='+quote(token,safe='')) as r:
                cookies=r.headers.get_all('Set-Cookie',[])
                self.cookie=next((c.split(';')[0] for c in cookies if c.startswith('dsh-auth-')),'')
                if r.status!=303 or not self.cookie:raise ValueError('DSH rejected the local launch URL. Reopen the URL printed by the running dsh web process.')
            self.token=None
    def invoke(self, method, args=None):
        identity=uuid.uuid4().hex
        body={'type':'client-request','rpcId':identity,'method':method,'payload':{'args':args or {}}}
        for attempt in range(2):
            with self.request('/api/'+method,body,{'Cookie':self.cookie}) as response:
                if response.status==401 and attempt==0:
                    self.authorize();continue
                limit=(128 if method=='session/list' else 16)*1024*1024
                raw=response.read(limit+1)
                if len(raw)>limit:raise ValueError('DSH response exceeds the adapter size limit.')
                if response.status!=200:raise ValueError(f'DSH {method} failed (HTTP {response.status}); the request was not replayed.')
                value=json.loads(raw)
                if value.get('type')!='server-response' or value.get('rpcId')!=identity:raise ValueError('Unexpected DSH response envelope.')
                if not value.get('result',{}).get('ok'):raise ValueError(value.get('result',{}).get('error',{}).get('message','DSH request failed.'))
                return value['result'].get('value')  # Void RPCs omit value on the wire.
    def stream(self, endpoint, args=None):
        self.authorize()
        sock=websocket.create_connection(self.base.replace('http://','ws://',1)+'/api/remote.mux',timeout=8,suppress_origin=True,header={'Cookie':self.cookie},http_no_proxy=['127.0.0.1','::1'])
        sock.send(json.dumps({'type':'open','streamId':'augmentor','endpoint':endpoint,'payload':{'args':args or {}}}))
        return sock
    @staticmethod
    def item(sock):
        while True:
            raw=sock.recv()
            if not raw:raise ValueError('DSH stream closed.')
            if len(raw)>16*1024*1024:raise ValueError('DSH event exceeds size limit.')
            frame=json.loads(raw)
            if frame.get('type')=='item':return frame['value']
            if frame.get('type') in ('error','end'):raise ValueError(frame.get('error',{}).get('message','DSH stream ended.'))
    def snapshot(self, session):
        sock=self.stream('session/follow',{'request':{'address':{'kind':'session','sessionId':session},'maxMessages':1}})
        try:
            value=self.item(sock)
            if value.get('type')!='snapshot':raise ValueError('DSH did not return a history opening.')
            return value
        finally:sock.close()
    def call(self, method, payload=None):
        p=payload or {}
        if method=='host.describe':
            catalog=self.invoke('session/modelCatalog')
            return {'version':'0.1.5-rc.1','home':str(self.home),**(catalog.get('default') or {})}
        if method=='llm.models':return self.invoke('session/modelCatalog')
        if method in ('settings.describe','agentPresets.list'):return self.invoke(method.replace('.','/'))
        if method=='settings.mutate':return self.invoke('settings/mutate',p)
        if method=='session.list':
            value=self.invoke('session/list',{'_request':p})
            return {**value,'items':[{**row,'agentPreset':row.get('projections',{}).get('values',{}).get('agentPreset',row.get('agentPreset'))} for row in value['items']]}
        if method=='workspace.list':
            sock=self.stream('workspace/follow')
            try:return self.item(sock)['value']
            finally:sock.close()
        if method in ('session.history','session.models'):
            opening=self.snapshot(p['sessionId'])
            if method=='session.models':
                catalog=self.invoke('session/modelCatalog');selection=opening.get('projections',{}).get('values',{}).get('modelSelection',{})
                return {**catalog,'current':selection.get('next') or selection.get('pending') or selection.get('lastUsed') or catalog.get('default')}
            request={'address':{'kind':'session','sessionId':p['sessionId']},'throughSeq':opening['cursor'],'maxMessages':min(p.get('maxMessages',200),200)}
            if 'beforeSeq' in p:request['beforeSeq']=p['beforeSeq']
            page=self.invoke('session/page',{'request':request})
            return {'sessionId':p['sessionId'],'header':opening['header'],'events':page['records'],'hasMore':page['hasMore']}
        if method=='session.prompt':
            content=p.get('content',[])
            line=content[0].get('text','') if len(content)==1 and content[0].get('type')=='text' else ''
            if re.match(r'^/[a-z][a-z0-9_-]*(?=$|[\t\n\r ])',line):
                result=self.invoke('commands/execute',{'agentId':p['sessionId'],'line':line,'submittedAttachments':[]})
                if result is None:raise ValueError('Unknown DSH command. To insert a saved prompt, select it with Tab or click it first.')
                if result['result']['kind']=='error':raise ValueError(result['result']['text'])
                return {'accepted':True,'command':result}
        if method in ('session.create','session.selectModel','session.cancel','session.rename','session.fork','session.prompt','session.updateQueue'):
            request=dict(p)
            if method=='session.prompt':request.setdefault('requestId',uuid.uuid4().hex)
            return self.invoke(method.replace('.','/'),{'request':request})
        raise ValueError('Unsupported DSH method: '+method)

_clients={}
_lock=threading.RLock()
def client(base,home=None,token=None):
    home=Path(home or os.environ.get('DSH_HOME',Path.home()/'.dsh'))
    key=(base,str(home))
    with _lock:
        if key not in _clients:_clients[key]=Remote(base,home,token)
        elif token:_clients[key].token=token;_clients[key].cookie=''
        return _clients[key]
