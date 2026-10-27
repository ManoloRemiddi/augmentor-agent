# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One authenticated endpoint per existing browser native host; no agent process."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import socketserver
import stat
import sys
import threading
import time
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from platform_adapters.paths import private_directory
from platform_adapters.transport import LocalSocket,ThreadingLocalServer,cleanup_endpoint
from platform_support import require_same_user

LIMIT=8*1024*1024

def directory():
    supplied=os.environ.get('AUGMENTOR_BROWSER_EXECUTOR_DIR')
    if supplied:path=Path(supplied)
    elif sys.platform=='win32':
        from platform_adapters.paths import windows_environment
        path=Path(windows_environment()['XDG_RUNTIME_DIR'])/'browsers'
    else:
        base=(Path('/run/user')/str(os.getuid()) if sys.platform=='linux' else Path('/tmp')/('augmentor-'+str(os.getuid()))).resolve()
        scope=Path(os.environ.get('XDG_RUNTIME_DIR',base)).resolve();path=scope/'ab'
        if len(os.fsencode(path))>55:path=base/('ab-'+hashlib.sha256(os.fsencode(scope)).hexdigest()[:12])
    if not path.is_absolute() or path.resolve()!=path:raise PermissionError('Use a canonical private browser executor directory.')
    path=private_directory(path)
    if path.is_symlink() or (sys.platform!='win32' and (path.stat().st_uid!=os.getuid() or path.stat().st_mode&0o077)):
        raise PermissionError('Browser executor directory is not private.')
    return path

def records():
    found=[]
    for file in sorted(directory().glob('*.json')):
        try:
            info=file.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_size>4096 or (sys.platform!='win32' and (info.st_uid!=os.getuid() or info.st_mode&0o077)):continue
            row=json.loads(file.read_text())
            if row.get('id')!=file.stem or len(file.stem)!=32 or any(c not in '0123456789abcdef' for c in file.stem):continue
            if row.get('endpoint')!=str(file.with_suffix('.sock')):continue
            probe=LocalSocket();probe.settimeout(.3)
            try:probe.connect(row['endpoint'])
            except (OSError,ValueError):continue
            finally:probe.close()
            found.append(row)
        except (OSError,ValueError):continue
    return found

def call(row,request):
    connection=LocalSocket();connection.settimeout(24)
    try:
        connection.connect(row['endpoint'])
        connection.sendall((json.dumps(request)+'\n').encode())
        with connection.makefile('rb') as reader:raw=reader.readline(LIMIT+1)
        if len(raw)>LIMIT or not raw.endswith(b'\n'):raise RuntimeError('Browser reply disconnected or exceeded its bound; do not replay an action.')
        value=json.loads(raw)
        if not value.get('ok'):raise RuntimeError(value.get('error','Browser operation failed.'))
        return value['result']
    finally:connection.close()

def request(value):
    rows=records();params=dict(value.get('params',{}));selected=params.pop('executorId',None)
    if selected:
        rows=[row for row in rows if row['id']==selected]
        if not rows:raise RuntimeError('The selected browser disconnected. List browser tabs again; no action was replayed.')
    if params.get('action')=='tabs_list':
        def read(row):
            try:
                result=call(row,{**value,'params':params})
                return [{**tab,'executorId':row['id']} for tab in result.get('tabs',[])]
            except (OSError,RuntimeError,ValueError):return []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as workers:
            tabs=[tab for group in workers.map(read,rows) for tab in group]
        return {'ok':True,'tabs':tabs,'connectedExecutors':len({tab['executorId'] for tab in tabs})}
    if params.get('action')=='capabilities':
        def describe(row):
            try:return {'executorId':row['id'],'capabilities':call(row,{**value,'params':{'action':'capabilities'}}),'tabs':call(row,{**value,'params':{'action':'tabs_list'}}).get('tabs',[])}
            except (OSError,RuntimeError,ValueError) as error:return {'executorId':row['id'],'error':str(error)}
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as workers:descriptions=list(workers.map(describe,rows))
        if len(descriptions)==1 and 'capabilities' in descriptions[0]:
            row=descriptions[0];return {**row['capabilities'],'executorId':row['executorId'],'tabs':row['tabs']}
        if descriptions:return {'ok':True,'executors':descriptions}
    if params.get('action')=='stop':
        for row in rows:
            try:call(row,{**value,'params':params})
            except (OSError,RuntimeError,ValueError):pass
        return {'ok':True,'stopped':True}
    if len(rows)!=1:raise RuntimeError('Choose executorId from browser_tabs_list to identify the intended connected browser.' if rows else 'No connected browser executor. Open the installed Augmentor extension in the intended browser.')
    return call(rows[0],{**value,'params':params})

def serve():
    root=directory();identity=uuid.uuid4().hex;endpoint=root/(identity+'.sock');record=root/(identity+'.json')
    pending={};guard=threading.Lock();output=threading.Lock()
    def emit(value):
        with output:print(json.dumps(value),flush=True)
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.connection.settimeout(25)
            try:
                require_same_user(self.connection)
                raw=self.rfile.readline(LIMIT+1)
                if len(raw)>LIMIT or not raw.endswith(b'\n'):raise ValueError('Invalid browser request.')
                request=json.loads(raw);params=request.get('params')
                if not isinstance(params,dict) or not isinstance(request.get('owner'),str):raise ValueError('A browser operation needs its conversation owner.')
                expires=request.get('expiresAt',0)
                if type(expires) not in (int,float) or expires<time.time()*1000 or expires>time.time()*1000+30000:raise RuntimeError('Browser request expired before dispatch.')
                identity=uuid.uuid4().hex;event=threading.Event();answer={}
                with guard:pending[identity]=(event,answer)
                try:
                    emit({'type':'request','id':identity,'owner':request['owner'],'params':params,'expiresAt':expires})
                    if not event.wait(min(23,max(0,(expires-time.time()*1000)/1000))):raise RuntimeError('Browser request timed out; its outcome may be unknown. Inspect before continuing.')
                    if 'error' in answer:raise RuntimeError(answer['error'])
                    response={'ok':True,'result':answer.get('result')}
                finally:
                    with guard:pending.pop(identity,None)
            except Exception as error:response={'ok':False,'error':str(error)[:500]}
            try:self.wfile.write((json.dumps(response,ensure_ascii=False)+'\n').encode())
            except (BrokenPipeError,ConnectionError,OSError):pass
    server=ThreadingLocalServer(str(endpoint),Handler);server.daemon_threads=True
    if sys.platform!='win32':endpoint.chmod(0o600)
    record.write_text(json.dumps({'id':identity,'endpoint':str(endpoint),'pid':os.getpid()}));record.chmod(0o600)
    threading.Thread(target=server.serve_forever,daemon=True).start();emit({'type':'ready','id':identity})
    try:
        for line in sys.stdin:
            if len(line.encode())>LIMIT:
                try:
                    oversized=json.loads(line)
                    with guard:row=pending.get(oversized.get('id'))
                    if row:row[1]['error']='Browser reply exceeded its transport bound.';row[0].set()
                except ValueError:pass
                continue
            try:
                value=json.loads(line)
                with guard:row=pending.get(value.get('id'))
                if row:
                    event,answer=row
                    if value.get('error'):answer['error']=str(value['error'])[:500]
                    else:answer['result']=value.get('result')
                    event.set()
            except ValueError:break
    finally:
        with guard:
            for event,answer in pending.values():answer['error']='Browser executor disconnected; action outcome may be unknown.';event.set()
        server.shutdown();server.server_close();record.unlink(missing_ok=True);cleanup_endpoint(endpoint)
        # Other native hosts may be about to bind in this shared private directory.

if __name__=='__main__':
    os.umask(0o077)
    if sys.argv[1:] == ['serve']:serve()
    else:
        try:
            raw=sys.stdin.read(LIMIT+1)
            if len(raw)>LIMIT:raise ValueError('Browser input exceeded its bound.')
            print(json.dumps({'ok':True,'result':request(json.loads(raw))},ensure_ascii=False))
        except Exception as error:print(json.dumps({'ok':False,'error':str(error)[:500]}))
