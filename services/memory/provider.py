# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Optional Hindsight 0.9.2 adapter behind Augmentor's per-user companion.

Models receive recall only. Retain and configuration belong to explicit UI
actions. Bank identities come from checked user configuration, never tool args.
"""
import hashlib
from contextlib import contextmanager
import ipaddress
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import quote, urlsplit
import uuid

PROTOCOL='augmentor-memory/1'
VERSION='0.9.2'


class MemoryError(ValueError): pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): raise MemoryError('Memory endpoint redirects are disabled.')


def validate(configuration):
    endpoint=configuration.get('endpoint','').strip().rstrip('/')
    url=urlsplit(endpoint)
    try: local=ipaddress.ip_address(url.hostname or '').is_loopback
    except ValueError: local=False
    if not url.hostname or url.username or url.password or url.query or url.fragment or not (url.scheme=='https' or url.scheme=='http' and local):
        raise MemoryError('Use HTTPS for Hindsight, or a numeric loopback HTTP address for a local service.')
    key=configuration.get('apiKey','')
    if not isinstance(key,str) or '\n' in key or '\r' in key or len(key)>8192:
        raise MemoryError('Invalid memory API key.')
    if not local and not key: raise MemoryError('A remote Hindsight connection requires an API key.')
    banks={}
    for scope in ('user','project'):
        bank=configuration.get(scope+'Bank','').strip()
        if bank and not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',bank):
            raise MemoryError('Bank IDs must use 1–64 letters, numbers, - or _.')
        banks[scope]=bank
    if not banks['user']: raise MemoryError('Enter a user bank ID.')
    if banks['project'] and banks['project']==banks['user']:
        raise MemoryError('User and project memory must use different banks.')
    scope=configuration.get('activeScope','user')
    if scope not in banks or not banks[scope]: raise MemoryError('Choose a configured memory scope.')
    return {'endpoint':endpoint,'apiKey':key,'userBank':banks['user'],'projectBank':banks['project'],
            'activeScope':scope,'enabled':True,'provider':'hindsight','version':VERSION}


def http(config,method,path,body=None):
    headers={'accept':'application/json'}
    if config.get('apiKey'): headers['authorization']='Bearer '+config['apiKey']
    data=None
    if body is not None: data=json.dumps(body).encode();headers['content-type']='application/json'
    request=urllib.request.Request(config['endpoint']+path,data=data,headers=headers,method=method)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    try:
        with opener.open(request,timeout=8) as response:
            raw=response.read(4*1024*1024+1)
        if len(raw)>4*1024*1024: raise MemoryError('Hindsight returned more data than this request supports.')
        return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        # Never display provider error bodies: they may contain credentials or
        # unrelated retained contents. Status alone is enough for remediation.
        if exc.code in (401,403): raise MemoryError('Hindsight refused access. Check the API key and bank permissions.') from None
        if exc.code==404: raise MemoryError('That Hindsight record or API endpoint was not found.') from None
        raise MemoryError('Hindsight could not complete this request (HTTP '+str(exc.code)+').') from None
    except (urllib.error.URLError,TimeoutError,ConnectionError,OSError,json.JSONDecodeError):
        raise MemoryError('Hindsight is unavailable. Your chat can continue; no memory write was replayed.') from None


class Memory:
    def __init__(self,path,request=http):
        self.path=Path(path);self.request=request;self.lock=threading.RLock();self.checked={}
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS configuration (singleton INTEGER PRIMARY KEY CHECK(singleton=1), revision INTEGER NOT NULL, value TEXT NOT NULL);
                INSERT OR IGNORE INTO configuration VALUES (1,0,'{"enabled":false,"activeScope":"user"}');
                CREATE TABLE IF NOT EXISTS operations (id TEXT PRIMARY KEY, request_id TEXT UNIQUE NOT NULL, digest TEXT NOT NULL, endpoint TEXT NOT NULL, bank TEXT NOT NULL, scope TEXT NOT NULL, document TEXT NOT NULL, content TEXT NOT NULL, provenance TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL);
            ''')
        os.chmod(self.path,0o600)

    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10);db.row_factory=sqlite3.Row
        db.execute('PRAGMA synchronous=FULL');db.execute('PRAGMA secure_delete=ON')
        try:
            with db:yield db
        finally:db.close()

    def config(self):
        with self.connect() as db:
            row=db.execute('SELECT * FROM configuration').fetchone()
            return {**json.loads(row['value']),'revision':row['revision']}

    def public(self,c=None):
        c=c or self.config()
        return {**{k:v for k,v in c.items() if k!='apiKey'},'apiKeySet':bool(c.get('apiKey')),'protocol':PROTOCOL}

    def bank(self,c,scope):
        if scope not in ('user','project') or not c.get(scope+'Bank'):
            raise MemoryError('That memory scope is not configured.')
        return c[scope+'Bank']

    def route(self,bank,suffix): return '/v1/default/banks/'+quote(bank,safe='')+'/'+suffix

    def operation(self,row):
        return {k:row[k] for k in ('id','scope','document','status','created')}

    def call(self,method,p,request_id):
        if method=='memory.describe': return self.public()
        if method=='memory.check':
            previous=self.config();candidate=dict(p)
            # A blank password field may reuse the stored key only for the
            # identical destination. Changing hosts can never forward that key.
            if not candidate.get('apiKey') and candidate.get('endpoint','').rstrip('/')==previous.get('endpoint'):
                candidate['apiKey']=previous.get('apiKey','')
            c=validate(candidate)
            health=self.request(c,'GET','/health')
            version=self.request(c,'GET','/openapi.json').get('info',{}).get('version')
            if health.get('status')!='healthy': raise MemoryError('Hindsight is not healthy yet.')
            if version!=VERSION: raise MemoryError('This preview supports Hindsight '+VERSION+'. The connection was not saved.')
            token=str(uuid.uuid4())
            with self.lock:
                self.checked={k:v for k,v in self.checked.items() if v[0]>time.monotonic()}
                self.checked[token]=(time.monotonic()+180,c,previous['revision'])
                def expire():
                    with self.lock:self.checked.pop(token,None)
                timer=threading.Timer(180,expire);timer.daemon=True;timer.start()
            return {'token':token,'version':version}
        if method in ('memory.configure','memory.disable'):
            with self.lock,self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                current=db.execute('SELECT * FROM configuration').fetchone();c=json.loads(current['value'])
                if method=='memory.configure':
                    item=self.checked.pop(p.get('token'),None)
                    if not item or item[0]<time.monotonic(): raise MemoryError('Check the memory connection again before saving.')
                    if item[2]!=current['revision']: raise MemoryError('Memory settings changed elsewhere. Reload before saving.')
                    c=item[1]
                else:
                    c['enabled']=False;self.checked.clear()
                db.execute('UPDATE configuration SET revision=revision+1,value=?',(json.dumps(c),))
            return self.public()
        c=self.config();scope=p.get('scope',c.get('activeScope','user'))
        if method=='memory.agentRecall':
            # Only query is accepted from the model-facing tools.
            if set(p)-{'query'}: raise MemoryError('The agent cannot select a bank or memory scope.')
            scope=c.get('activeScope','user')
        if method in ('memory.recall','memory.agentRecall') and not c.get('enabled'):
            return {'enabled':False,'results':[],'scope':scope}
        if not c.get('endpoint'): raise MemoryError('Connect Hindsight in Memory settings first.')
        bank=self.bank(c,scope)
        if method in ('memory.recall','memory.agentRecall'):
            query=p.get('query')
            if not isinstance(query,str) or not query.strip() or len(query)>4096: raise MemoryError('Enter a memory query up to 4,096 characters.')
            try:
                value=self.request(c,'POST',self.route(bank,'memories/recall'),{'query':query,'budget':'low','max_tokens':1024,'trace':False})
                # Keep only useful, attributable text. Treat it as recalled data,
                # never instructions or extra authority for the active task.
                results=[{k:r[k] for k in ('id','text','type','context','document_id') if k in r} for r in value.get('results',[])[:30]]
                return {'enabled':True,'scope':scope,'results':results}
            except MemoryError as exc:
                if method=='memory.agentRecall': return {'enabled':True,'unavailable':True,'results':[],'message':str(exc)}
                raise
        if method=='memory.retain':
            if not c.get('enabled'): raise MemoryError('Memory is disabled. Enable it before retaining a new fact.')
            content=p.get('content');provenance=p.get('provenance',{})
            if not isinstance(content,str) or not content.strip() or len(content)>16000: raise MemoryError('Enter memory text up to 16,000 characters.')
            if not isinstance(provenance,dict) or any(k not in ('surface','harness','sessionId') or not isinstance(v,str) or len(v)>160 for k,v in provenance.items()):
                raise MemoryError('Invalid memory provenance.')
            digest=hashlib.sha256(json.dumps([c['endpoint'],bank,content,provenance],sort_keys=True).encode()).hexdigest()
            with self.lock,self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                old=db.execute('SELECT * FROM operations WHERE request_id=?',(request_id,)).fetchone()
                if old:
                    if old['digest']!=digest: raise MemoryError('That memory request ID belongs to different text.')
                    return self.operation(old)
                pending=db.execute("SELECT * FROM operations WHERE digest=? AND status IN ('unknown','pending','processing')",(digest,)).fetchone()
                if pending:return self.operation(pending)
                # Recheck disable/reconfigure under the same lock before this
                # request becomes an accepted operation.
                if self.config()!=c: raise MemoryError('Memory settings changed. Review the destination before saving.')
                identity=str(uuid.uuid4());document='augmentor-'+identity
                db.execute('INSERT INTO operations VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                    (identity,request_id,digest,c['endpoint'],bank,scope,document,content,json.dumps(provenance),'unknown',time.time()))
            body={'async':True,'operation_id':identity,'items':[{'content':content,'document_id':document,
                  'context':'User explicitly retained this text in Augmentor.',
                  'metadata':{'application':'augmentor',**provenance},'update_mode':'replace'}]}
            status='unknown'
            try:
                result=self.request(c,'POST',self.route(bank,'memories'),body)
                if result.get('success') and result.get('operation_id')==identity: status='pending'
            except MemoryError: pass
            with self.connect() as db:
                db.execute('UPDATE operations SET status=? WHERE id=?',(status,identity))
                return self.operation(db.execute('SELECT * FROM operations WHERE id=?',(identity,)).fetchone())
        if method=='memory.operations':
            with self.connect() as db:
                rows=db.execute('SELECT * FROM operations WHERE endpoint=? AND bank=? ORDER BY created DESC LIMIT 100',(c['endpoint'],bank)).fetchall()
            return {'items':[self.operation(row) for row in rows]}
        if method=='memory.operation':
            with self.connect() as db:
                row=db.execute('SELECT * FROM operations WHERE id=? AND endpoint=? AND bank=?',(p.get('id'),c['endpoint'],bank)).fetchone()
            if not row: raise MemoryError('That operation does not belong to this memory scope.')
            if row['status'] not in ('completed','failed','cancelled','deleted'):
                result=self.request(c,'GET',self.route(bank,'operations/'+quote(row['id'],safe='')))
                status=result.get('status')
                if status=='not_found': status='unknown'
                if status not in ('pending','processing','completed','failed','cancelled','unknown'): raise MemoryError('Unsupported Hindsight operation status.')
                with self.connect() as db: db.execute('UPDATE operations SET status=? WHERE id=?',(status,row['id']))
                row=dict(row,status=status)
            return self.operation(row)
        if method in ('memory.documents','memory.exportPage'):
            offset=p.get('offset',0)
            if type(offset) is not int or not 0<=offset<=1000000: raise MemoryError('Invalid memory page.')
            endpoint='documents' if method=='memory.documents' else 'memories/list'
            value=self.request(c,'GET',self.route(bank,endpoint)+f'?limit=20&offset={offset}')
            return {**value,'scope':scope,'protocol':PROTOCOL}
        if method in ('memory.document','memory.delete'):
            identity=p.get('id')
            if not isinstance(identity,str) or not identity or len(identity)>512: raise MemoryError('Select a memory document.')
            if method=='memory.delete':
                # Accepted retains may still recreate their document. Deletion
                # is available after completion/failure, not while queued.
                with self.connect() as db:
                    active=db.execute("SELECT id FROM operations WHERE document=? AND endpoint=? AND bank=? AND status NOT IN ('completed','failed','cancelled','deleted')",(identity,c['endpoint'],bank)).fetchone()
                if active: raise MemoryError('Refresh this pending operation before deleting its document.')
            result=self.request(c,'DELETE' if method=='memory.delete' else 'GET',self.route(bank,'documents/'+quote(identity,safe='')))
            if method=='memory.delete':
                with self.connect() as db:
                    db.execute("UPDATE operations SET content='',provenance='{}',status='deleted' WHERE document=? AND endpoint=? AND bank=?",(identity,c['endpoint'],bank))
            return result
        raise MemoryError('Unsupported memory operation.')
