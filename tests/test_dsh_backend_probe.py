# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Authored executable actors, real namespace lifetime, no DSH/owner source copied."""
import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from test_dsh_preservation_transaction import PreservationTransactionFixture
from dsh import preservation_transaction as tx
from dsh import backend_probe as probes

ACTOR='''import os,time
if os.fork()==0:
 os.setsid()
 with open('/dev/null','wb') as null:null.write(b'AUTHORED_IGNORED_STDERR')
 print('AUTHORED_CHILD_READY',flush=True)
 while True:time.sleep(1)
print('AUTHORED_ACTOR_READY',flush=True)
while True:time.sleep(1)
'''


@unittest.skipUnless(sys.platform=='linux' and shutil.which('bwrap'),'Linux controlled backend requires bubblewrap')
class BackendProbeTests(PreservationTransactionFixture):
    def setUp(self):
        super().setUp()
        self.node=self.incoming/'node/bin/node'
        self.write(self.node,b'#!/usr/bin/python3\nimport os,sys\nos.execv("/usr/bin/python3",["python3",*sys.argv[1:]])\n');self.node.chmod(0o700)
        self.configure_actor(ACTOR)

    def configure_actor(self,code):
        self.write(self.cli/'lib/bin.js',code.encode())
        files=tx.deployment.inventory(self.incoming);self.artifact=tx.preserve.sha(json.dumps(files,sort_keys=True).encode())
        self.write(self.incoming/'desktop-release.json',{'deployment':{'root':str(self.incoming),'version':'0.2.13','node':str(self.node),'python':sys.executable},'files':files,'artifactSha256':self.artifact})
        self.output=self.base/('review-'+str(time.monotonic_ns()));self.stage_sha=self.stage()['planSha256']

    def applied(self,guard):
        digest=self.prepare(guard);tx.commit(self.backup,digest,guard);return digest

    def ready(self,handle):return handle.wait_for(lambda text:'AUTHORED_CHILD_READY' in text and 'AUTHORED_ACTOR_READY' in text,5)

    def test_controlled_namespace_keeps_gate_and_fence_then_reaps_detached_children(self):
        with self.guard() as guard:
            digest=self.applied(guard)
            with probes.backend_probe(self.backup,digest,guard,os.environ,self.base) as (handle,_):
                self.ready(handle);self.assertTrue(handle.alive())
                children=Path('/proc',str(handle.actor_pid),'task',str(handle.actor_pid),'children').read_text().split();self.assertEqual(len(children),1)
                child_fd=os.pidfd_open(int(children[0]))
                try:
                    with self.assertRaisesRegex(ValueError,'managed client'):
                        with tx.shared.launch_lease(self.deployment,exclusive=True):pass
                    with self.assertRaisesRegex(ValueError,'controlled backend'):tx.rollback(self.backup,digest,guard)
                finally:pass
            try:self.assertTrue(select.select([child_fd],[],[],0)[0])
            finally:os.close(child_fd)
            self.assertTrue((self.home/tx.gate.FENCE).exists());tx.rollback(self.backup,digest,guard)
        self.assert_before()

    def test_parent_death_kills_stopped_namespace_actor_and_detached_child(self):
        with self.guard() as guard:digest=self.applied(guard)
        code='''import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]);from dsh import preservation_transaction as tx,backend_probe as probes
home,data,backup=map(Path,sys.argv[2:5]);digest=sys.argv[5];pair=json.loads(sys.argv[6])
with tx.maintenance(home,data,[pair]) as guard:
 with probes.backend_probe(backup,digest,guard,__import__('os').environ,home.parent) as (h,_):
  h.wait_for(lambda t:'AUTHORED_ACTOR_READY' in t and 'AUTHORED_CHILD_READY' in t,5)
  print(json.dumps({'monitor':h.process.pid,'actor':h.actor_pid}),flush=True)
  sys.stdin.read()
'''
        owner=subprocess.Popen([sys.executable,'-I','-B','-c',code,str(tx.ROOT/'services'),str(self.home),str(self.deployment),str(self.backup),digest,json.dumps(self.pair)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        fds=[]
        try:
            self.assertTrue(select.select([owner.stdout],[],[],8)[0]);identity=json.loads(owner.stdout.readline())
            children=Path('/proc',str(identity['actor']),'task',str(identity['actor']),'children').read_text().split();self.assertEqual(len(children),1)
            fds=[os.pidfd_open(pid) for pid in (identity['actor'],int(children[0]))]
            for fd in fds:signal.pidfd_send_signal(fd,signal.SIGSTOP)
            owner.kill();owner.communicate(timeout=5)
            for fd in fds:self.assertTrue(select.select([fd],[],[],5)[0],'Namespace child survived its controller')
            deadline=time.monotonic()+5
            while True:
                try:
                    with self.guard() as guard:tx.rollback(self.backup,digest,guard)
                    break
                except ValueError:
                    if time.monotonic()>deadline:raise
                    time.sleep(.02)
        finally:
            if owner.poll() is None:owner.kill();owner.communicate(timeout=5)
            for fd in fds:os.close(fd)
        self.assert_before()

    def test_missing_namespace_tool_and_changed_cli_refuse_without_config_replacement(self):
        with self.guard() as guard:
            digest=self.applied(guard);snapshot=self.actual()
            with patch.object(probes.shutil,'which',return_value=None):
                with self.assertRaisesRegex(ValueError,'bubblewrap'):
                    with probes.backend_probe(self.backup,digest,guard,os.environ,self.base):pass
            self.assertIsNone(guard.probe);self.assertEqual(self.actual(),snapshot)
            self.write(self.cli/'lib/bin.js',b'AUTHORED CLI CHANGED')
            with self.assertRaisesRegex(ValueError,'supplier input changed'):
                with probes.backend_probe(self.backup,digest,guard,os.environ,self.base):pass
            tx.rollback(self.backup,digest,guard)
        self.assert_before()

    def test_private_output_is_bounded_and_readiness_failure_reaps_its_tree(self):
        self.configure_actor("import time\nprint('x'*1048576,flush=True)\nwhile True:time.sleep(1)\n")
        with self.guard() as guard:
            digest=self.applied(guard)
            with self.assertRaisesRegex(ValueError,'readiness'):
                with probes.backend_probe(self.backup,digest,guard,os.environ,self.base) as (handle,_):
                    handle.wait_for(lambda text:len(text)>1024,5);self.assertLessEqual(len(handle.log_text()),probes.MAX_LOG)
                    handle.wait_for(lambda _:False,.05)
            self.assertIsNone(guard.probe);tx.rollback(self.backup,digest,guard)
        self.assert_before()

    def test_prepared_only_configuration_cannot_start_a_replacement_backend(self):
        with self.guard() as guard:
            digest=self.prepare(guard)
            with self.assertRaisesRegex(ValueError,'Apply the reviewed configuration'):
                with probes.backend_probe(self.backup,digest,guard,os.environ,self.base):pass
            self.assertIsNone(guard.probe);self.assert_before();tx.rollback(self.backup,digest,guard)

    def test_launch_metadata_changes_cannot_switch_the_candidate_interpreter(self):
        with self.guard() as guard:
            digest=self.applied(guard);manifest=self.incoming/'desktop-release.json';raw=manifest.read_bytes()
            value=json.loads(raw);value['deployment']['python']='/usr/bin/false';self.write(manifest,value)
            # File inventory alone still verifies; the reviewed stage must bind
            # the excluded launch record before any selected interpreter runs.
            self.assertEqual(tx.deployment.verify(self.incoming)['artifactSha256'],self.artifact)
            with self.assertRaisesRegex(ValueError,'supplier input changed'):
                with probes.backend_probe(self.backup,digest,guard,os.environ,self.base):pass
            manifest.write_bytes(raw)
            with probes.backend_probe(self.backup,digest,guard,os.environ,self.base) as (handle,_):
                self.ready(handle);self.write(manifest,value)
                with self.assertRaisesRegex(ValueError,'launch metadata changed'):handle.native_adapter_preflight(self.backup)
            tx.rollback(self.backup,digest,guard)
        self.assert_before()

    def test_preflight_rejects_wrong_product_version_without_a_model_request(self):
        self.configure_actor('''import http.server,json,sys
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*_):pass
 def do_GET(self):
  data=json.dumps({'protocol':'augmentor-dsh/1','version':'AUTHORED_WRONG_VERSION','homeId':'wrong'}).encode();self.send_response(200);self.end_headers();self.wfile.write(data)
port=int(sys.argv[sys.argv.index('--port')+1]);server=http.server.HTTPServer(('127.0.0.1',port),Handler)
print('http://127.0.0.1/?token=AUTHORED_PRIVATE_TOKEN',flush=True);server.serve_forever()
''')
        with self.guard() as guard:
            digest=self.applied(guard)
            with probes.backend_probe(self.backup,digest,guard,os.environ,self.base) as (handle,_):
                with self.assertRaisesRegex(ValueError,'version or home identity'):handle.preflight()
            tx.rollback(self.backup,digest,guard)
        self.assert_before()
