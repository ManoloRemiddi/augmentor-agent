#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Kernel-authenticated Windows listener; private stdio multiplexes Node clients.

No TCP port, reusable PID, agent loop or supplier internals. EOF closes every
owned pipe; untrusted client bytes are base64 data, never relay control frames.
"""
import base64
import json
import os
from pathlib import Path
import queue
import socketserver
import sys
import threading

VERSION='augmentor-pipe-server/1'
MAX_FRAME=128*1024


def main(endpoint):
    from platform_adapters.windows_pipe import ThreadingPipeServer
    import msvcrt
    msvcrt.setmode(sys.stdin.fileno(),os.O_BINARY);msvcrt.setmode(sys.stdout.fileno(),os.O_BINARY)
    stopped=threading.Event();lock=threading.Lock();output_lock=threading.Lock();clients={};next_id=0
    def emit(kind,**fields):
        raw=(json.dumps({'version':VERSION,'type':kind,**fields},ensure_ascii=True)+'\n').encode('ascii')
        with output_lock:
            try:
                offset=0
                while offset<len(raw):offset+=os.write(sys.stdout.fileno(),raw[offset:])
            except OSError:stopped.set()
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            nonlocal next_id
            with lock:
                if stopped.is_set() or len(clients)>=32:return
                next_id+=1;identity=next_id;outgoing=queue.Queue(maxsize=32);clients[identity]=(self.request,outgoing)
            emit('connect',id=identity)
            def send():
                try:
                    while True:
                        raw=outgoing.get()
                        if raw is None:return
                        self.request.sendall(raw)
                except (OSError,ValueError):self.request.close()
            threading.Thread(target=send,daemon=True).start()
            try:
                while not stopped.is_set():
                    raw=self.request.recv(65536)
                    if not raw:break
                    emit('data',id=identity,data=base64.b64encode(raw).decode('ascii'))
            except (OSError,ValueError):pass
            finally:
                with lock:clients.pop(identity,None)
                self.request.close()
                try:outgoing.put_nowait(None)
                except queue.Full:pass
                emit('close',id=identity)
    server=ThreadingPipeServer(endpoint,Handler)
    emit('ready')
    threading.Thread(target=server.serve_forever,daemon=True).start()
    stream=os.fdopen(sys.stdin.fileno(),'rb',buffering=0,closefd=False)
    try:
        while not stopped.is_set():
            raw=stream.readline(MAX_FRAME+1)
            if not raw:break
            if len(raw)>MAX_FRAME or not raw.endswith(b'\n'):raise ValueError('Invalid relay frame.')
            value=json.loads(raw.decode('ascii'))
            if not isinstance(value,dict) or value.get('version')!=VERSION:raise ValueError('Invalid relay version.')
            kind=value.get('type')
            if kind=='shutdown' and set(value)=={'version','type'}:break
            if type(value.get('id')) is not int or value['id']<=0:raise ValueError('Invalid relay identity.')
            with lock:client=clients.get(value['id'])
            if kind=='close' and set(value)=={'version','type','id'}:
                if client:client[0].close()
            elif kind=='data' and set(value)=={'version','type','id','data'}:
                if not isinstance(value['data'],str):raise ValueError('Invalid relay data.')
                data=base64.b64decode(value['data'],validate=True)
                if len(data)>65536 or base64.b64encode(data).decode('ascii')!=value['data']:raise ValueError('Invalid relay bytes.')
                if client:
                    try:client[1].put_nowait(data)
                    except queue.Full:client[0].close()
            else:raise ValueError('Invalid relay operation.')
    finally:
        stopped.set();server.shutdown();server.server_close()
        with lock:remaining=list(clients.values())
        for connection,outgoing in remaining:
            connection.close()
            try:outgoing.put_nowait(None)
            except queue.Full:pass
    return 0


if __name__=='__main__':
    if sys.platform!='win32' or len(sys.argv)!=2:raise SystemExit('Windows private listener endpoint required.')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    try:raise SystemExit(main(sys.argv[1]))
    except Exception:
        print('Private Windows listener was refused or disconnected.',file=sys.stderr)
        raise SystemExit(1)
