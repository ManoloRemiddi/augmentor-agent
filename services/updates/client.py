# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bounded fixed-helper transport shared by the service and install coordinator."""
import json
from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time

from platform_adapters.paths import private_directory
from platform_adapters.private_files import require_directory, descriptor
from platform_adapters import locks
from .policy import MAX_ARTIFACT


def node_executable(root, *, development=False, require_bundled=False):
    root=Path(root)
    if not require_bundled:
        selected=os.environ.get('AUGMENTOR_PI_NODE')
        if selected:
            candidate=Path(selected)
            if not candidate.is_absolute() or not candidate.is_file():
                raise ValueError('The selected update runtime is unavailable.')
            return candidate
    for candidate in (root/'node/bin/node',root/'node/node.exe'):
        if candidate.is_file():return candidate
    if development and not require_bundled:
        selected=shutil.which('node')
        if selected:return Path(selected).resolve()
    raise ValueError('The bundled update runtime is unavailable. Repair the installed application.')


def repository_request(root, cache, request, *, node=None, timeout=None, cancelled=None,
                       progress=lambda _bytes:None, observed=lambda _process:None):
    if not isinstance(request,dict) or request.get('operation') not in ('discover','download') or 'cache' in request:
        raise ValueError('Use a fixed update-helper operation without an external cache path.')
    cache=require_directory(private_directory(Path(cache)))
    body=json.dumps({**request,'cache':str(cache)}).encode()
    if len(body)>65536:raise ValueError('Update request exceeds its supported size.')
    timeout=timeout if timeout is not None else (1800 if request['operation']=='download' else 120)
    if type(timeout) not in (int,float) or not 0<timeout<=1800:raise ValueError('Use a bounded update-helper deadline.')
    cancelled=cancelled or threading.Event()
    deadline=time.monotonic()+timeout
    # Independent service/coordinator helpers share the rollback floor. Atomic
    # individual files alone cannot prevent concurrent refreshes from writing
    # older trusted metadata after a newer helper has advanced that floor.
    with cache_writer(cache,deadline,cancelled):
        return invoke(root,body,node,deadline,cancelled,progress,observed)


@contextmanager
def cache_writer(cache, deadline, cancelled):
    fd=descriptor(cache/'client.lock',writable=True,create=True)
    try:
        while True:
            if cancelled.is_set():raise InterruptedError('Update operation cancelled.')
            if time.monotonic()>=deadline:raise TimeoutError('The update cache is busy. Try again later.')
            try:locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB);break
            except BlockingIOError:cancelled.wait(.05)
        yield
    finally:os.close(fd)


def invoke(root, body, node, deadline, cancelled, progress, observed):
    environment={key:value for key,value in os.environ.items() if not key.upper().startswith('NODE_')}
    flags={'creationflags':subprocess.CREATE_NO_WINDOW} if sys.platform=='win32' else {}
    process=subprocess.Popen([str(node or node_executable(root,require_bundled=True)),str(Path(root)/'services/updates/repository.mjs')],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=environment,**flags)
    reply=bytearray();oversized=threading.Event();write_errors=[]
    def write_request():
        try:
            process.stdin.write(body);process.stdin.close()
        except (OSError, ValueError) as error:write_errors.append(error)
    def read_progress():
        while line:=process.stderr.readline(257):
            if len(line)>256:oversized.set();process.terminate();return
            try:data=json.loads(line)
            except ValueError:continue
            if isinstance(data,dict) and type(data.get('bytes')) is int and 0<=data['bytes']<=MAX_ARTIFACT:progress(data['bytes'])
    def read_reply():
        while chunk:=process.stdout.read(8192):
            if len(reply)+len(chunk)>2*1024**2:oversized.set();process.terminate();return
            reply.extend(chunk)
    observer=threading.Thread(target=read_progress,name='augmentor-update-progress',daemon=True)
    reader=threading.Thread(target=read_reply,name='augmentor-update-reply',daemon=True)
    writer=threading.Thread(target=write_request,name='augmentor-update-request',daemon=True)
    observer.start();reader.start();writer.start()
    try:
        observed(process)
        while process.poll() is None:
            if cancelled.wait(.05):raise InterruptedError('Update operation cancelled.')
            if time.monotonic()>=deadline:raise TimeoutError('The update server did not respond in time.')
        reader.join(timeout=3);observer.join(timeout=3);writer.join(timeout=3)
        if reader.is_alive() or observer.is_alive() or oversized.is_set():raise ValueError('Update reply exceeds its supported size.')
        if writer.is_alive() or write_errors:raise ValueError('The update helper did not accept its request.')
        result=json.loads(reply)
        if not isinstance(result,dict):raise ValueError('The update helper returned an invalid reply.')
        if process.returncode or result.get('error'):raise ValueError(result.get('error','The update helper failed.'))
        return result
    finally:
        if process.poll() is None:process.terminate()
        try:process.wait(timeout=3)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
        observer.join(timeout=3);reader.join(timeout=3);writer.join(timeout=3)
        for stream in (process.stdin,process.stdout,process.stderr):stream.close()
        observed(None)
