# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""DSH wire adapter. All host-specific request envelopes live here."""
import ipaddress
import json
import os
import sys
from pathlib import Path
import re
import threading
import urllib.request
from urllib.parse import urlsplit
import uuid

import websocket
import yaml


from ..pi_client import ContractError
from .dsh_interactions import NativeInteractions
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'services'))
from dsh.setup import current as dsh_configuration
from dsh.remote import client as remote_client


def loopback_url(value):
    parsed = urlsplit(value)
    try:
        local = ipaddress.ip_address(parsed.hostname or '').is_loopback
    except ValueError:
        local = False
    if parsed.scheme != 'http' or not local or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ContractError('A numeric loopback HTTP endpoint is required.')
    return value.rstrip('/')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ContractError('DSH endpoint redirects are disabled.')


class DshClient:
    supports_queue = True
    def __init__(self, base=None, home=None):
        configured=dsh_configuration()
        self.base = loopback_url(base or os.environ.get('DSH_AUGMENTOR_URL') or configured.get('endpoint','http://127.0.0.1:3080'))
        self.home = Path(home or os.environ.get('DSH_HOME') or configured.get('home',Path.home()/'.dsh'))
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.remote = remote_client(self.base,self.home)
        self.interactions = None

    def _post(self, path, body):
        req = urllib.request.Request(self.base + '/api/' + path, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
        limit = (128 if path == 'session.list' else 16) * 1024 * 1024
        with self.opener.open(req, timeout=20) as response:
            data = response.read(limit + 1)
        if len(data) > limit:
            raise ContractError('DSH response exceeded the adapter size limit.')
        return json.loads(data)

    def call(self, method, payload=None):
        if not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9]*(?:\.[a-zA-Z][a-zA-Z0-9]*)+', method):
            raise ContractError('Invalid DSH method')
        try:return self.remote.call(method,payload)
        except ValueError as error:raise ContractError(str(error)) from error

    def respond(self, rpc_id, value):
        interactions=self.interactions
        if interactions is None:
            raise ContractError('No native DSH interaction connection is active.')
        return interactions.respond(rpc_id,value)

    def local_models(self):
        # This validates DSH's configured endpoint, not the forwarding behavior
        # of an arbitrary local proxy. It reads no credential file.
        config = yaml.safe_load((self.home / 'settings.yaml').read_text()) or {}
        providers = config.get('llm-pi-ai', {}).get('providers', {})
        allowed = set()
        for provider, settings in providers.items():
            try:
                loopback_url(settings.get('baseURL', ''))
                allowed.add(provider)
            except (ContractError, ValueError):
                pass
        catalog = self.call('llm.models')
        rows = []
        for group in catalog.get('groups', []):
            if group.get('id') in allowed:
                rows.extend({'provider': group['id'], 'model': model['id'], 'name': model.get('name', model['id'])} for model in group.get('models', []))
        if not rows:
            raise ContractError('No DSH model with a verified localhost endpoint is configured.')
        return rows

    def validate_model(self, selection):
        if not isinstance(selection, dict) or not all(isinstance(selection.get(k), str) and selection[k] for k in ('provider', 'model')):
            raise ContractError('Choose a DSH model before sending a message.')
        catalog = self.call('llm.models')
        if not any(group['id'] == selection['provider'] and any(m['id'] == selection['model'] for m in group.get('models', [])) for group in catalog.get('groups', [])):
            raise ContractError('The selected model is no longer in the DSH catalog. Refresh the model picker.')

    def model_catalog(self):
        catalog = self.call('llm.models')
        settings = self.call('settings.describe')
        namespaces = {n['ns']: n for n in settings.get('namespaces', [])}
        curation = namespaces.get('model-picker-augmented', {}).get('value', {})
        endpoints = namespaces.get('llm-pi-ai', {}).get('value', {}).get('providers', {})
        groups = []
        for group in catalog.get('groups', []):
            provider = group['id']
            try:
                loopback_url(endpoints.get(provider, {}).get('baseURL', ''))
                location = 'Local'
            except (ContractError, ValueError):
                location = 'Network'
            groups.append({'provider': provider, 'name': group.get('name', provider), 'models': [
                {'provider': provider, 'model': m['id'], 'name': m.get('name', m['id']), 'location': location}
                for m in group.get('models', [])]})
        default = namespaces.get('agent-default-model', {}).get('value', {})
        hidden = curation.get('hidden', {})
        return {'groups': groups, 'pinned': curation.get('pinned', []),
                'hidden': [k for k, v in hidden.items() if v] if isinstance(hidden, dict) else [],
                'default': {k: default.get(k) for k in ('provider', 'model')}, 'failures': catalog.get('failures', [])}

    def session_rows(self):
        sessions = self.call('session.list').get('items', [])
        workspaces = self.call('workspace.list')
        saved = {s for w in workspaces.get('items', []) for s in w.get('sessionIds', [])}
        archived = set(workspaces.get('archivedSessionIds', []))
        return [dict({k:row.get(k) for k in ('sessionId','cwd','agentPreset','updatedAt','running','blank')},
                     title=row.get('projections', {}).get('values', {}).get('title') or row['sessionId'],
                     saved=row['sessionId'] in saved, archived=row['sessionId'] in archived)
                for row in sorted(sessions, key=lambda r: r.get('updatedAt', 0), reverse=True)]

    def setting(self, namespace):
        settings = self.call('settings.describe')
        return next((n for n in settings.get('namespaces', []) if n['ns'] == namespace), None)

    def saved_chats(self, action='state', session=None):
        try:
            token = (self.home / 'augmentor-linux-token').read_text().strip()
        except OSError as exc:
            raise ContractError('The updated Linux chat plugin has not loaded in DSH yet.') from exc
        body = {'action':action, 'sessionId':session}
        req = urllib.request.Request(self.base + '/api/augmentor-linux/chats', data=json.dumps(body).encode(), headers={'Content-Type':'application/json','x-augmentor-linux-token':token})
        try:
            with self.opener.open(req, timeout=12) as response:
                value=json.loads(response.read(1024*1024))
        except urllib.error.HTTPError as exc:
            try: message=json.loads(exc.read(8192)).get('error','Chat operation failed')
            except Exception: message='Chat operation failed; verify the Linux plugin version.'
            raise ContractError(message) from exc
        if not value.get('ok'):raise ContractError(value.get('error','Chat operation failed'))
        return value.get('saved',[])


class EventStream:
    """Only this UI's session is delivered. Other mux frames are discarded."""
    def __init__(self, client, session, on_frame, on_disconnect):
        self.client, self.session = client, session
        self.on_frame, self.on_disconnect = on_frame, on_disconnect
        self.socket = None
        self.control_socket = None
        self.status_socket = None
        self.running = None
        self.closed = threading.Event()
        self.ready = threading.Event()
        self.failure = None
        self.interactions = None

    def start(self):
        threading.Thread(target=self._run, daemon=True, name='augmentor-events').start()
        if not self.ready.wait(6):
            self.close()
            raise ContractError('DSH event connection timed out.')
        if self.failure:
            raise ContractError(self.failure)

    def _run(self):
        try:
            if self.session is None:
                self.client.remote.authorize();self.ready.set();self.closed.wait();return
            self.status_socket = self.client.remote.stream('$events',{})
            status_ready=self.client.remote.item(self.status_socket)
            if status_ready.get('type')!='ready':raise ContractError('DSH status stream did not open.')
            self.status_client=status_ready['clientId']
            self.status_socket.settimeout(1)
            rows=self.client.call('session.list')['items']
            row=next((r for r in rows if r['sessionId']==self.session),None)
            if row is not None:self.status_frame({'type':'emit','event':'api-session/status','args':[self.session,bool(row.get('running'))]})
            threading.Thread(target=self.status_loop,daemon=True,name='augmentor-status').start()
            self.socket = self.client.remote.stream('session/follow',{'request':{'address':{'kind':'session','sessionId':self.session},'maxMessages':1,'assistantStream':True}})
            opening=self.client.remote.item(self.socket)
            if opening.get('type')!='snapshot':raise ContractError('DSH session stream did not open.')
            cursor=opening['cursor'];self.socket.settimeout(1)
            self.control_socket=self.client.remote.stream('session/control',{})
            baseline=self.client.remote.item(self.control_socket)
            if baseline.get('type')!='baseline':raise ContractError('DSH queue stream did not open.')
            self.queue_frame(baseline.get('value',{}).get('queues',{}).get(self.session,[]))
            self.control_socket.settimeout(1)
            if getattr(self.client,'native_interactions',False):
                self.interactions=NativeInteractions(self.client.interaction_operation,self.session,self.on_frame)
                self.interactions.claim()
                if self.closed.is_set():return
                self.client.interactions=self.interactions
                threading.Thread(target=self.interaction_loop,daemon=True,name='augmentor-interactions').start()
            threading.Thread(target=self.control_loop,daemon=True,name='augmentor-queue').start()
            self.ready.set()
            while not self.closed.is_set():
                try:frame=self.client.remote.item(self.socket)
                except websocket.WebSocketTimeoutException:continue
                event=None
                if frame.get('type')=='event' and frame['event']['seq']>cursor:
                    event=frame['event'];cursor=event['seq']
                elif frame.get('type')=='assistant-stream' and frame['frame']['type']=='chunk':
                    event={'type':'assistant/chunk','time':frame['frame']['time'],'data':{'chunk':frame['frame']['chunk']}}
                if event:
                    self.on_frame({'type':'server-request','method':'session/event','payload':{'sessionId':self.session,'event':event}})
                    if event['type'] in ('turn/start','turn/end'):
                        self.on_frame({'type':'server-request','method':'host/session-status','payload':{'sessionId':self.session,'running':event['type']=='turn/start'}})
        except Exception as exc:
            self.failure = str(exc)
            self.ready.set()
            if not self.closed.is_set():
                self.on_disconnect(self.failure)
        finally:
            self.close()
            if self.control_socket:self.control_socket.close()
            if self.socket:
                self.socket.close()

    def status_frame(self, frame):
        if frame.get('type')=='waterfall':
            self.client.remote.invoke('$events/result',{'clientId':self.status_client,'eventId':frame['eventId'],'outcome':{'kind':'next'}})
            return
        args=frame.get('args',[])
        if frame.get('type')!='emit' or len(args)!=2 or args[0]!=self.session:return
        if frame.get('event')=='api-session/status' and type(args[1]) is bool:
            self.running=args[1]
            self.on_frame({'method':'host/session-status','payload':{'sessionId':self.session,'running':args[1]}})
        elif frame.get('event')=='api-session/error' and isinstance(args[1],str):
            self.on_frame({'method':'host/session-error','payload':{'sessionId':self.session,'message':args[1]}})

    def status_loop(self):
        try:
            while not self.closed.is_set():
                try:frame=self.client.remote.item(self.status_socket)
                except websocket.WebSocketTimeoutException:continue
                self.status_frame(frame)
        except Exception as exc:
            if not self.closed.is_set():self.on_disconnect(str(exc));self.close()

    def queue_frame(self, items):
        self.on_frame({'method':'session/queue','payload':{'sessionId':self.session,'items':items}})

    def interaction_loop(self):
        try:
            while not self.closed.is_set():
                self.interactions.poll()
                if self.closed.wait(0.5):return
        except Exception as exc:
            if not self.closed.is_set():self.on_disconnect(str(exc));self.close()

    def control_loop(self):
        try:
            while not self.closed.is_set():
                try:frame=self.client.remote.item(self.control_socket)
                except websocket.WebSocketTimeoutException:continue
                if frame.get('type')=='queue' and frame.get('sessionId')==self.session:self.queue_frame(frame['items'])
        except Exception as exc:
            if not self.closed.is_set():self.on_disconnect(str(exc));self.close()

    def close(self):
        self.closed.set()
        interactions=self.interactions
        if interactions:
            if self.client.interactions is interactions:self.client.interactions=None
            try:interactions.close()
            except Exception:pass  # The host lease expires even when release cannot arrive.
        if self.control_socket:self.control_socket.close()
        if self.status_socket:self.status_socket.close()
        if self.socket:
            self.socket.close()
