# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Private Unix broker observation and bounded maintenance, no ordinary commands."""
import json
import hashlib
import os
from pathlib import Path
import socketserver
import sys
import threading

from platform_adapters import locks
from platform_adapters.paths import private_directory,runtime_directory
from platform_adapters.private_files import descriptor,require_directory
from platform_adapters.transport import ThreadingLocalServer,prepare_endpoint,cleanup_endpoint
from platform_support import require_same_user
from .admission import METHODS
PROTOCOL='augmentor-unix-maintenance/1'


def scope():
    """Current session/state identity only; no directory creation or key reads."""
    base=Path(os.environ.get('AUGMENTOR_DICTATION_STATE',str(Path.home()/'.local/share/augmentor/dictation'))).resolve()
    session='|'.join(os.environ.get(key,'') for key in ('XDG_SESSION_ID','DISPLAY','WAYLAND_DISPLAY'))
    return {'session':hashlib.sha256(session.encode()).hexdigest()[:12],
        'stateSHA256':hashlib.sha256(os.fsencode(base)).hexdigest()}


class DictationControl:
    def __init__(self,root,backend):
        if sys.platform not in ('linux','darwin'):raise RuntimeError('Use the Unix dictation control adapter.')
        self.root=Path(root).resolve();self.backend=backend
        self.runtime=require_directory(private_directory(runtime_directory()))
        self.endpoint=self.runtime/f'augmentor-dictation-{os.getpid()}.sock'
        self.lease=None;self.server=None;self.thread=None;self.ready=False

    def identity(self):
        return {'protocol':PROTOCOL,'component':'dictation','maintenanceAdmission':1,
            'pid':os.getpid(),'buildRoot':str(self.root),'ready':self.ready,**scope()}

    def handle(self,connection):
        committed=False
        try:
            require_same_user(connection);connection.settimeout(5)
            with connection.makefile('rb') as stream:raw=stream.readline(65537)
            if len(raw)>65536 or not raw.endswith(b'\n'):raise ValueError('Incomplete dictation maintenance request.')
            request=json.loads(raw)
            if request=={'protocol':PROTOCOL,'kind':'describe'}:
                response={**self.identity(),'ok':True}
            else:
                if not self.ready:raise ValueError('The dictation broker has not completed startup.')
                if (not isinstance(request,dict) or set(request)!={'protocol','kind','method','params'}
                        or request['protocol']!=PROTOCOL or request['kind']!='maintenance'
                        or request['method'] not in METHODS or not isinstance(request['params'],dict)):
                    raise ValueError('Unsupported dictation maintenance request.')
                result=self.backend.request(request['method'],request['params'])
                committed=request['method']=='host.maintenance.commit' and result['phase']=='closing'
                response={**self.identity(),'ok':True,'result':result}
            connection.sendall(json.dumps(response,separators=(',',':')).encode()+b'\n')
        except Exception:
            try:connection.sendall(json.dumps({**self.identity(),'ok':False,
                'error':'Dictation maintenance could not be confirmed. Its work was preserved.'}).encode()+b'\n')
            except OSError:pass
        finally:
            if committed:
                try:self.backend.normal_stop()
                except Exception:return  # Retain closing/unknown state; never force a child.
                os._exit(0)

    def __enter__(self):
        self.lease=descriptor(self.endpoint.with_suffix('.lock'),writable=True,create=True)
        try:
            locks.flock(self.lease,locks.LOCK_EX|locks.LOCK_NB)
            prepare_endpoint(self.endpoint)
            owner=self
            class Handler(socketserver.BaseRequestHandler):
                def handle(self):owner.handle(self.request)
            self.server=ThreadingLocalServer(str(self.endpoint),Handler);self.server.daemon_threads=True
            self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
            return self
        except BaseException:self.close();raise

    def close(self):
        if self.thread is not None and self.thread.is_alive():self.server.shutdown();self.thread.join(timeout=5)
        if self.server is not None:self.server.server_close();cleanup_endpoint(self.endpoint)
        if self.lease is not None:os.close(self.lease);self.lease=None
        self.thread=None;self.server=None
