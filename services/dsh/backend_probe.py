# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Temporary, managed-gate-blocking backend preflight; never finalizes activation.

The PID namespace owns the whole temporary tree, including detached children.
This is lifetime isolation, not a filesystem/network permission boundary. Owner
use still requires the outer cold backups and reviewed entrypoint/profile graph.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time

from . import preservation_transaction as tx
from .remote import Remote

MAX_LOG=512*1024


def namespace_command(command,cwd,launch_fd,info_fd=None):
    binary=shutil.which('bwrap')
    if binary is None:raise ValueError('Install the qualified Linux bubblewrap dependency before backend preflight.')
    args=[binary,'--bind','/','/','--unshare-user','--unshare-pid','--as-pid-1','--die-with-parent',
          '--proc','/proc','--dev','/dev','--sync-fd',str(launch_fd),'--chdir',str(cwd)]
    if info_fd is not None:args+=['--info-fd',str(info_fd)]
    return [*args,'--',*command]


class BackendProbe:
    def __init__(self,command,environment,cwd,launch_fd,home,version,endpoint):
        self.launch_fd=launch_fd
        self.home=home;self.version=version;self.endpoint=endpoint;self.closed=False
        self.buffer=b'';self.buffer_lock=threading.Lock();self.process=None;self.monitor_fd=None;self.actor_fd=None;self.thread=None
        reader,writer=os.pipe2(os.O_CLOEXEC)
        try:
            args=namespace_command(command,cwd,launch_fd,writer)
            self.process=subprocess.Popen(args,env=environment,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                          pass_fds=(launch_fd,writer),start_new_session=True)
            self.monitor_fd=os.pidfd_open(self.process.pid)
            self.thread=threading.Thread(target=self._drain,daemon=True);self.thread.start()
            os.close(writer);writer=None
            data=b'';deadline=time.monotonic()+5;identity=None
            while identity is None:
                remaining=deadline-time.monotonic()
                if remaining<=0 or not select.select([reader],[],[],remaining)[0]:raise ValueError('Temporary backend namespace did not start.')
                chunk=os.read(reader,4096)
                if not chunk:raise ValueError('Temporary backend namespace was refused.')
                data+=chunk
                if len(data)>8192:raise ValueError('Temporary backend namespace status exceeded its bound.')
                try:identity=json.JSONDecoder().raw_decode(data.decode().lstrip())[0]
                except ValueError:pass
            pid=identity.get('child-pid')
            if type(pid) is not int or pid<=0 or os.readlink('/proc/'+str(pid)+'/ns/pid')==os.readlink('/proc/self/ns/pid'):
                raise ValueError('Temporary backend has no distinct PID namespace identity.')
            path=Path('/proc')/str(pid)/'stat';before=path.read_text().rsplit(')',1)[1].split()
            self.actor_fd=os.pidfd_open(pid);after=path.read_text().rsplit(')',1)[1].split()
            if before[1]!=str(self.process.pid) or after[1]!=before[1] or after[19]!=before[19] or self.process.poll() is not None:
                raise ValueError('Temporary backend process ownership changed.')
            self.actor_pid=pid
        except BaseException:
            self.close();raise
        finally:
            os.close(reader)
            if writer is not None:os.close(writer)

    def _drain(self):
        try:
            while data:=os.read(self.process.stdout.fileno(),65536):
                with self.buffer_lock:self.buffer=(self.buffer+data)[-MAX_LOG:]
        except (OSError,ValueError):pass

    def log_text(self):
        with self.buffer_lock:return self.buffer.decode('utf-8',errors='replace')

    def alive(self):
        return not self.closed and self.process.poll() is None and self.actor_fd is not None and not select.select([self.actor_fd],[],[],0)[0]

    def wait_for(self,predicate,seconds=30):
        if type(seconds) not in (int,float) or not 0<seconds<=30:raise ValueError('Backend readiness has a thirty-second maximum.')
        deadline=time.monotonic()+seconds
        while self.alive():
            result=predicate(self.log_text())
            if result:return result
            if time.monotonic()>=deadline:break
            time.sleep(.02)
        raise ValueError('Temporary backend did not satisfy readiness; its private log stays bounded in memory.')

    def preflight(self):
        token=self.wait_for(lambda text:re.search(r'[?&]token=([A-Za-z0-9_-]+)',text)).group(1)
        remote=Remote(self.endpoint,self.home,token)
        with remote.request('/api/augmentor-product') as response:
            raw=response.read(8193)
            if response.status!=200 or len(raw)>8192:raise ValueError('Replacement product identity was unavailable.')
        product=tx.preserve.document(raw)
        secret=tx.preserve.read(self.home/'augmentor-product-token').decode().strip()
        if product.get('protocol')!='augmentor-dsh/1' or product.get('version')!=self.version or product.get('homeId')!=hashlib.sha256(secret.encode()).hexdigest():
            raise ValueError('Replacement product version or home identity differs; matching guards remain enforced.')
        catalog=remote.invoke('session/modelCatalog');presets=remote.invoke('agentPresets/list')
        registered={row['id'] for row in presets['presets'] if not row.get('broken')}
        if not isinstance(catalog.get('groups'),list) or not isinstance(catalog.get('default'),dict) or not tx.preserve.ROLES<=registered:
            raise ValueError('Replacement catalogue or required personal presets are unavailable.')
        if not self.alive():raise ValueError('Replacement backend exited during preflight.')
        return {'productVersion':self.version,'homeIdentityMatches':True,'personalPresetsRegistered':True,'catalogGroups':len(catalog['groups']),'modelRequests':0}

    def native_adapter_preflight(self,transaction):
        """Actual candidate adapter/import path, on a temporary connection registry."""
        if not self.alive():raise ValueError('Start the controlled backend before checking the candidate adapter.')
        root=Path(self.client_deployment['root']);python=self.client_deployment['python']
        if tx.preserve.sha(tx.preserve.read(root/'desktop-release.json',private=True))!=self.manifest_sha:
            raise ValueError('Incoming launch metadata changed before candidate adapter preflight.')
        tx.incoming_seal(root,self.artifact_sha)
        with tempfile.TemporaryDirectory(prefix='.native-preflight-',dir=transaction) as temporary:
            path=Path(temporary);tx.atomic(path/'harnesses.json',tx.encoded({'dsh':{'home':str(self.home),'endpoint':self.endpoint,'version':self.version}}))
            env={**self.environment,'AUGMENTOR_SHARED_CONFIG':str(path),'DSH_AUGMENTOR_URL':self.endpoint,
                 'PYTHONPATH':str(root/'apps/native'),'QT_QPA_PLATFORM':'offscreen'}
            code=('import os\nfrom augmentor_linux.adapters.dsh import DshAdapter\n'
                  'if os.getpid()!=1:raise RuntimeError("Adapter preflight requires its owned PID namespace.")\n'
                  'a=DshAdapter()\n'
                  'if not a.product:raise RuntimeError("Candidate adapter is not connected to the product.")\n'
                  'a.call("host.describe")\n')
            command=namespace_command([python,'-B','-c',code],root,self.launch_fd)
            result=subprocess.run(command,cwd=root,env=env,capture_output=True,timeout=30,pass_fds=(self.launch_fd,))
            if result.returncode or not self.alive():raise ValueError('The actual candidate Native adapter refused this backend.')
        return {'candidateNativeAdapterMatched':True,'candidateClientPidNamespace':True,'physicalGuiAcceptance':False,'modelRequests':0}

    def close(self):
        if self.closed:return
        terminal=self.process is None
        try:
            if self.process is not None:
                if self.actor_fd is not None and not select.select([self.actor_fd],[],[],0)[0]:
                    try:signal.pidfd_send_signal(self.actor_fd,signal.SIGTERM)
                    except ProcessLookupError:pass
                try:self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    if self.monitor_fd is None:self.process.kill()
                    else:signal.pidfd_send_signal(self.monitor_fd,signal.SIGKILL)
                    self.process.wait(timeout=5)
                if self.actor_fd is not None and not select.select([self.actor_fd],[],[],5)[0]:
                    raise ValueError('Temporary backend teardown is unfinished; keep the update fenced.')
                terminal=True
                if self.thread is not None:self.thread.join(timeout=2)
                if self.process.stdout is not None:self.process.stdout.close()
        finally:
            if terminal:
                for name in ('actor_fd','monitor_fd'):
                    fd=getattr(self,name)
                    if fd is not None:os.close(fd);setattr(self,name,None)
                self.closed=True


@contextmanager
def backend_probe(output,digest,guard,environment,cwd):
    """Check one applied configuration while normal managed clients stay fenced."""
    output=Path(output);value,status=tx.inspect(output,digest,guard)
    if status['phase']!='applied' or tx.targets(value)!=[row['afterSha256'] for row in value['files']]:
        raise ValueError('Apply the reviewed configuration before replacement-backend preflight.')
    plan,release=tx.validate_suppliers(output,value,guard);root=Path(value['incoming'])
    manifest_sha=plan['ownerInputs'].get(str(root/'desktop-release.json'))
    if not isinstance(manifest_sha,str):raise ValueError('Prepare a fresh stage binding the exact incoming launch metadata.')
    node=root/'node/bin/node';entry=Path(plan.get('cliEntry',''))
    if release['deployment'].get('node')!=str(node) or not node.is_file() or not os.access(node,os.X_OK):
        raise ValueError('Use the verified incoming bundled Node interpreter.')
    if str(entry) not in plan['ownerInputs'] or tx.preserve.sha(tx.preserve.read(entry))!=plan['ownerInputs'][str(entry)]:
        raise ValueError('Prepare a fresh stage binding the exact CLI entry before preflight.')
    cwd=Path(cwd)
    if not cwd.is_absolute() or cwd.resolve()!=cwd or not cwd.is_dir():raise ValueError('Use the recorded canonical backend working directory.')
    pair=guard.pairs[0]
    env={**environment,'DSH_HOME':str(guard.home),'AUGMENTOR_SHARED_STATE':pair['state'],'AUGMENTOR_SHARED_DATA':pair['data'],
         'AUGMENTOR_PYTHON':release['deployment']['python'],'AUGMENTOR_PI_NODE':str(node),'PYTHONDONTWRITEBYTECODE':'1',
         'DSH_TELEMETRY_MODE':'DISABLED','PI_TELEMETRY':'0','PI_SKIP_VERSION_CHECK':'1'}
    with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    endpoint='http://127.0.0.1:'+str(port)
    command=[str(node),str(entry),'web','--host','127.0.0.1','--port',str(port),'--no-open']
    handle=BackendProbe(command,env,cwd,guard.launch_fd,guard.home,plan['candidateVersion'],endpoint);handle.environment=env
    handle.client_deployment=dict(release['deployment']);handle.manifest_sha=manifest_sha;handle.artifact_sha=value['artifactSha256']
    guard.probe=handle
    try:yield handle,release
    finally:
        handle.close();guard.probe=None
