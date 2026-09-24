#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Harness-independent, per-user prompt service. Single daemon, transactional SQLite."""
import fcntl
import hashlib
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import signal
import socketserver
import sqlite3
import threading
import time
import uuid
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from memory.provider import Memory
from support.report import report as support_report
from dsh.setup import Setup as DshSetup
from platform_support import require_same_user
from home.client import call as home_connection_call

PROTOCOL='augmentor-prompts/1'
LIMIT=1024*1024
DEFAULT_IMPROVEMENT="You are a prompt editor. Rewrite the user's prompt so it clearly communicates their intended goal and is easy to act on.\n\n- Preserve the intent, scope, constraints, and tone.\n- Make the task, relevant context, and expected output explicit where supported by the original.\n- Resolve unclear wording, remove repetition, and organize instructions logically.\n- Do not invent requirements, add unnecessary detail, or carry out the task itself.\n- If an ambiguity would materially change the task, ask only the essential clarifying questions before rewriting. Otherwise, use the most natural interpretation.\n\nUse the fewest words needed for clarity. Return only the improved prompt, without commentary."

def paths():
    home=Path.home()
    state=Path(os.environ.get('AUGMENTOR_SHARED_STATE',Path(os.environ.get('XDG_STATE_HOME',home/'.local/state'))/'augmentor'))
    data=Path(os.environ.get('AUGMENTOR_SHARED_DATA',Path(os.environ.get('XDG_DATA_HOME',home/'.local/share'))/'augmentor'))
    return state,data

class Conflict(ValueError):pass

class Library:
    def __init__(self,path):
        self.path=path;self.changed=threading.Condition()
        self.memory=Memory(Path(path).parent/'memory.sqlite3');self.dsh=DshSetup()
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS improvement (singleton INTEGER PRIMARY KEY CHECK(singleton=1), content TEXT NOT NULL, revision INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS library (singleton INTEGER PRIMARY KEY CHECK(singleton=1), revision INTEGER NOT NULL);
                INSERT OR IGNORE INTO library VALUES (1,0);
                CREATE TABLE IF NOT EXISTS prompts (id TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL, content TEXT NOT NULL, revision INTEGER NOT NULL, updatedAt TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS imports (source TEXT NOT NULL, sourceId TEXT NOT NULL, digest TEXT NOT NULL, promptId TEXT NOT NULL, PRIMARY KEY(source,sourceId,digest));
                CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, digest TEXT NOT NULL, result TEXT NOT NULL);
            ''')
            original=db.execute("SELECT content FROM prompts WHERE lower(name)='prompt'").fetchone()
            seed=original['content'] if original and len(original['content'])<=8000 else DEFAULT_IMPROVEMENT
            seed=re.sub(r'\s*PROMPT:\s*\[clipboard\]\s*$', '', seed, flags=re.IGNORECASE)
            db.execute('INSERT OR IGNORE INTO improvement VALUES (1,?,0)',(seed,))
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10);db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA synchronous=FULL')
        try:
            with db:yield db
        finally:db.close()
    def snapshot(self,db):
        return {'improvement':dict(db.execute('SELECT content,revision FROM improvement').fetchone(),defaultContent=DEFAULT_IMPROVEMENT),
                'revision':db.execute('SELECT revision FROM library').fetchone()[0],
                'prompts':[dict(r) for r in db.execute('SELECT * FROM prompts ORDER BY name COLLATE NOCASE')]}
    def bump(self,db):
        db.execute('UPDATE library SET revision=revision+1');return db.execute('SELECT revision FROM library').fetchone()[0]
    def valid(self,p):
        name=p.get('name');content=p.get('content')
        if not isinstance(name,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}',name):raise ValueError('Use letters, numbers, - or _ for the shortcut name.')
        if not isinstance(content,str) or not content.strip() or len(content)>32000:raise ValueError('Enter prompt text up to 32,000 characters.')
        return name,content
    def save(self,db,p):
        name,content=self.valid(p)
        identity=p.get('promptId') or p.get('id');original=p.get('original') or (name if p.get('expectedRevision') is not None and not identity else None)
        old=db.execute('SELECT * FROM prompts WHERE id=?',(identity,)).fetchone() if identity else db.execute('SELECT * FROM prompts WHERE name=?',(original,)).fetchone() if original else None
        if (identity or original) and not old:raise Conflict('This prompt was deleted or renamed. Your draft is unchanged; reload or save it as a new prompt.')
        if old and old['revision']!=p.get('expectedRevision'):raise Conflict('This prompt changed elsewhere. Your draft is unchanged; reload or save it as a new prompt.')
        if db.execute('SELECT id FROM prompts WHERE name=? AND id<>?',(name,old['id'] if old else '')).fetchone():raise Conflict('That shortcut name already exists. Choose another name.')
        if not old and db.execute('SELECT count(*) FROM prompts').fetchone()[0]>=1000:raise ValueError('The library is limited to 1,000 prompts.')
        if db.execute('SELECT coalesce(sum(length(cast(content AS BLOB))),0) FROM prompts').fetchone()[0]-len((old['content'] if old else '').encode())+len(content.encode())>500000:raise ValueError('The library text limit is 500,000 characters.')
        revision=self.bump(db);identity=old['id'] if old else str(uuid.uuid4())
        db.execute('INSERT INTO prompts VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,content=excluded.content,revision=excluded.revision,updatedAt=excluded.updatedAt',
                   (identity,name,content,revision,time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))
        return identity
    def mutate(self,db,method,p):
        if method=='prompts.improvement.save':
            content=p.get('content')
            if not isinstance(content,str) or not content.strip() or len(content)>8000:raise ValueError('Enter improvement instructions up to 8,000 characters.')
            old=db.execute('SELECT revision FROM improvement').fetchone()[0]
            if old!=p.get('expectedRevision'):raise Conflict('These instructions changed elsewhere. Your draft is kept; reload before saving.')
            revision=self.bump(db)
            db.execute('UPDATE improvement SET content=?,revision=? WHERE singleton=1',(content,revision))
        elif method=='prompts.save':self.save(db,p)
        elif method=='prompts.delete':
            identity=p.get('promptId') or p.get('id')
            old=db.execute('SELECT * FROM prompts WHERE id=?',(identity,)).fetchone() if identity else db.execute('SELECT * FROM prompts WHERE name=?',(p.get('name'),)).fetchone()
            if not old or old['revision']!=p.get('expectedRevision'):raise Conflict('This prompt changed or was deleted elsewhere. Reload before deleting.')
            db.execute('DELETE FROM prompts WHERE id=?',(old['id'],));self.bump(db)
        elif method=='prompts.import':
            source=p.get('source');rows=p.get('prompts')
            if not isinstance(source,str) or len(source)>300 or not isinstance(rows,list) or len(rows)>1000:raise ValueError('Invalid import')
            for row in rows:
                name,content=self.valid(row);source_id=str(row.get('id',name));digest=hashlib.sha256(content.encode()).hexdigest()
                if db.execute('SELECT 1 FROM imports WHERE source=? AND sourceId=? AND digest=?',(source,source_id,digest)).fetchone():continue
                same=db.execute('SELECT id FROM prompts WHERE name=? AND content=?',(name,content)).fetchone()
                if same:identity=same['id']
                else:
                    base=name;number=1
                    while db.execute('SELECT 1 FROM prompts WHERE name=?',(name,)).fetchone():
                        number+=1;name=base[:105]+'-imported-'+str(number)
                    identity=self.save(db,{'name':name,'content':content})
                db.execute('INSERT INTO imports VALUES (?,?,?,?)',(source,source_id,digest,identity))
        else:raise ValueError('Unsupported prompt operation')
        return self.snapshot(db)
    def call(self,method,p,request_id):
        if isinstance(method,str) and method.startswith('home.connection.'):return home_connection_call(method,p)
        if method=='support.report':return support_report()
        if isinstance(method,str) and method.startswith('dsh.'):return self.dsh.call(method,p)
        if isinstance(method,str) and method.startswith('memory.'):
            return self.memory.call(method,p,request_id)
        if method=='prompts.watch':
            with self.changed:
                with self.connect() as db:revision=self.snapshot(db)['revision']
                if revision==p.get('afterRevision'):self.changed.wait(min(15,max(0,float(p.get('timeout',10)))))
            method='prompts.list'
        with self.connect() as db:
            if method in ('prompts.list','host.describe'):
                db.execute('BEGIN')
                result=self.snapshot(db)
                if method=='host.describe':return {'protocol':PROTOCOL,'version':'1.0.0','pid':os.getpid(),'revision':result['revision']}
                return result
            digest=hashlib.sha256(json.dumps([method,p],sort_keys=True).encode()).hexdigest()
            db.execute('BEGIN IMMEDIATE')
            existing=db.execute('SELECT * FROM requests WHERE id=?',(request_id,)).fetchone()
            if existing:
                if existing['digest']!=digest:raise Conflict('Request ID reused with different data.')
                return json.loads(existing['result'])
            result=self.mutate(db,method,p)
            db.execute('INSERT INTO requests VALUES (?,?,?)',(request_id,digest,json.dumps(result)))
            # Keep acknowledgements small: duplicates return the committed result
            # for the latest 256 writes; clients never auto-replay unknown writes.
            db.execute('DELETE FROM requests WHERE rowid NOT IN (SELECT rowid FROM requests ORDER BY rowid DESC LIMIT 256)')
            db.commit()
        with self.changed:self.changed.notify_all()
        return result

class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(20);identity=None
        try:
            require_same_user(self.connection)
            raw=self.rfile.readline(LIMIT+1)
            if len(raw)>LIMIT or not raw.endswith(b'\n'):raise ValueError('Invalid frame')
            request=json.loads(raw);identity=request.get('id')
            if request.get('protocol')!=PROTOCOL:raise ValueError('Incompatible prompt service version')
            if not isinstance(identity,str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,128}',identity):raise ValueError('Invalid request ID')
            params=request.get('params',{})
            if not isinstance(params,dict):raise ValueError('Invalid parameters')
            result=self.server.library.call(request.get('method'),params,identity)
            response={'id':identity,'result':result}
        except Exception as error:
            response={'id':identity,'error':{'code':'conflict' if isinstance(error,Conflict) else 'invalid','message':str(error)}}
        raw=(json.dumps(response,ensure_ascii=False)+'\n').encode()
        if len(raw)>LIMIT:raw=(json.dumps({'id':identity,'error':{'code':'too-large','message':'This record exceeds the supported response size. View it directly in the configured service.'}})+'\n').encode()
        try:self.wfile.write(raw)
        except (BrokenPipeError,ConnectionResetError):pass

class Server(socketserver.ThreadingUnixStreamServer):
    daemon_threads=False  # Graceful shutdown finishes accepted requests.

if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lifecycle'))
    from lease import hold
    hold('runtime')
    os.umask(0o077);state,data=paths()
    for directory in (state,data):directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    lock=(state/'prompts.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise SystemExit(0)
    endpoint=state/'prompts.sock'
    if endpoint.exists():endpoint.unlink()
    server=Server(str(endpoint),Handler);server.library=Library(data/'prompts.sqlite3')
    def stop(*_):threading.Thread(target=server.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:server.serve_forever(poll_interval=.2)
    finally:server.server_close();endpoint.unlink(missing_ok=True)
