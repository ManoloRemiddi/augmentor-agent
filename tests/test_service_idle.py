# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))
from lifecycle.idle import Lifetime
from lifecycle.admission import Admission


class LifetimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'owner.lock'
        self.file = self.path.open('a')
        self.addCleanup(self.file.close)
        self.now = 0
        self.life = Lifetime(self.file, timeout=5, clock=lambda: self.now)

    def test_default_is_five_minutes(self):
        self.assertEqual(Lifetime(self.file).timeout, 300)

    def test_active_request_finishes_then_receives_full_idle_interval(self):
        self.assertTrue(self.life.enter())
        self.now = 10
        self.assertFalse(self.life.retire())
        self.life.leave()
        self.assertFalse(self.life.retire())
        self.now = 15
        self.assertTrue(self.life.retire())
        self.assertFalse(self.life.enter())

    def test_background_work_and_maintenance_hold_block_retirement(self):
        admission = Admission(clock=lambda: self.now)
        self.now = 6
        with admission.work():
            self.assertFalse(self.life.retire(admission.retire_idle))
        admission.control('host.maintenance.prepare', {'token':'a'*32})
        self.assertFalse(self.life.retire(admission.retire_idle))
        admission.control('host.maintenance.cancel', {'token':'a'*32})
        self.assertTrue(self.life.retire(admission.retire_idle))

    def test_deleted_lock_retires_without_waiting_for_idle_timeout(self):
        self.path.unlink()
        self.assertTrue(self.life.retire())

    @unittest.skipIf(os.name == 'nt', 'Windows pipes have no filesystem endpoint')
    def test_startup_never_adopts_a_replacement_regular_file_as_its_socket(self):
        endpoint=self.path.with_suffix('.sock');endpoint.write_text('replacement fixture')
        life=Lifetime(self.file,endpoint)
        self.assertTrue(life.retire())
        life.cleanup(endpoint)
        self.assertEqual(endpoint.read_text(),'replacement fixture')

    @unittest.skipIf(os.name == 'nt', 'Windows prevents replacing open locks')
    def test_recreated_tree_cannot_keep_old_service_or_remove_new_socket(self):
        endpoint = self.path.with_suffix('.sock')
        endpoint.touch()
        life = Lifetime(self.file, endpoint)
        endpoint.rename(endpoint.with_suffix('.old'))
        endpoint.touch()
        self.assertTrue(life.retire())
        life.cleanup(endpoint)
        self.assertTrue(endpoint.exists())


@unittest.skipIf(os.name == 'nt', 'Unix socket integration; shared lifetime logic is OS independent')
class CompanionProcessTests(unittest.TestCase):
    def start(self, name, root):
        # Exercise real service entrypoints with a shorter in-process test clock
        # policy. Production has no environment switch to disable its bound.
        runner = """
import runpy,sys
sys.path.insert(0,sys.argv[1]);sys.path.insert(0,sys.argv[1]+'/services')
from lifecycle import idle
from services.lifecycle import idle as dictation_idle
for module in (idle,dictation_idle):
    original=module.Lifetime.__init__
    def init(self,*args,_original=original,**kwargs):
        kwargs['timeout']=2
        _original(self,*args,**kwargs)
    module.Lifetime.__init__=init
runpy.run_path(sys.argv[2],run_name='__main__')
"""
        env={**os.environ,'AUGMENTOR_SHARED_STATE':str(root/'state'),
             'AUGMENTOR_SHARED_DATA':str(root/'data'), 'AUGMENTOR_DICTATION_STATE':str(root/'dictation'),
             'HOME':str(root), 'DSH_HOME':str(root/'no-dsh')}
        script=ROOT/'services'/name/('server.py' if name=='dictation' else 'service.py')
        process=subprocess.Popen([sys.executable,'-B','-c',runner,str(ROOT),str(script)],env=env,
                                 stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        def cleanup():
            if process.poll() is None:
                process.terminate();process.wait(timeout=10)
            process.stderr.close()
        self.addCleanup(cleanup)
        endpoint=root/'state'/('dual-memory.sock' if name=='memory' else 'prompts.sock')
        deadline=time.monotonic()+10
        while True:
            if name=='dictation':
                endpoints=list((root/'dictation').glob('*.sock'))
                if endpoints: endpoint=endpoints[0]
            if endpoint.exists(): break
            self.assertIsNone(process.poll(),process.stderr.read().decode() if process.poll() is not None else '')
            self.assertLess(time.monotonic(),deadline)
            time.sleep(.02)
        return process,endpoint

    def call(self, endpoint, method, params=None):
        with socket.socket(socket.AF_UNIX) as connection:
            connection.settimeout(8);connection.connect(str(endpoint))
            connection.sendall((json.dumps({'protocol':'augmentor-prompts/1','id':'fixture',
                                           'method':method,'params':params or {}})+'\n').encode())
            with connection.makefile('rb') as stream:reply=json.loads(stream.readline())
            self.assertNotIn('error',reply)
            return reply['result']

    def test_legacy_watchdog_reads_real_process_and_preserves_clients_and_configuration(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('live_watchdog',ROOT/'scripts/retire-test-companions.py')
        watchdog=importlib.util.module_from_spec(spec);spec.loader.exec_module(watchdog)
        with tempfile.TemporaryDirectory(prefix='augmentor-pi-contract-') as directory:
            root=Path(directory);process,endpoint=self.start('memory',root)
            rows=watchdog.snapshot();row=next(r for r in rows if r['pid']==process.pid)
            self.assertTrue(watchdog.eligible(row,rows))
            client={'pid':99999999,'ppid':0,'start':'0','service':None,'env':{'AUGMENTOR_SHARED_STATE':str(root/'state')}}
            self.assertFalse(watchdog.eligible(row,rows+[client]))
            child={**client,'ppid':process.pid,'env':{}}
            self.assertFalse(watchdog.eligible(row,rows+[child]))
            (root/'data/hindsight.json').write_text('{}')
            self.assertFalse(watchdog.eligible(row,rows))
            process.terminate();self.assertEqual(process.wait(timeout=8),0)

    def test_unused_services_exit_and_keep_databases(self):
        for name in ('memory','prompt-library','dictation'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                process,endpoint=self.start(name,root)
                self.assertEqual(process.wait(timeout=8),0,process.stderr.read().decode())
                self.assertFalse(endpoint.exists())
                if name!='dictation':self.assertTrue(list((root/'data').glob('*.sqlite3')))

    def test_long_watch_is_not_cut_off_and_service_restarts_with_saved_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);process,endpoint=self.start('prompt-library',root)
            self.call(endpoint,'prompts.save',{'name':'retained','content':'Synthetic fixture'})
            revision=self.call(endpoint,'prompts.list')['revision']
            self.call(endpoint,'prompts.watch',{'afterRevision':revision,'timeout':3})
            self.assertIsNone(process.poll())
            self.assertEqual(process.wait(timeout=8),0)
            restarted,endpoint=self.start('prompt-library',root)
            self.assertEqual(self.call(endpoint,'prompts.list')['prompts'][0]['content'],'Synthetic fixture')
            restarted.terminate();self.assertEqual(restarted.wait(timeout=8),0)

    def test_deleted_and_replaced_endpoints_retire_all_brokers(self):
        for name in ('memory','prompt-library','dictation'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root=Path(directory);process,endpoint=self.start(name,root)
                endpoint.rename(endpoint.with_suffix('.retired'))
                endpoint.write_text('replacement fixture')
                self.assertEqual(process.wait(timeout=8),0,process.stderr.read().decode())
                self.assertEqual(endpoint.read_text(),'replacement fixture')

    def test_live_disabled_dictation_owner_prevents_retirement(self):
        from multiprocessing.connection import Client
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);process,endpoint=self.start('dictation',root)
            key=(root/'dictation/auth.key').read_bytes()
            def call(method,params):
                with Client(str(endpoint),family='AF_UNIX',authkey=key) as connection:
                    connection.send_bytes(json.dumps({'method':method,'params':params}).encode())
                    self.assertTrue(connection.poll(5))
                    self.assertNotIn('error',json.loads(connection.recv_bytes()))
            owner={'token':'b'*32,'pid':os.getpid()}
            call('conversation.acquire',owner)
            time.sleep(4)
            self.assertIsNone(process.poll())
            call('conversation.release',owner)
            self.assertEqual(process.wait(timeout=8),0)


class LegacyWatchdogTests(unittest.TestCase):
    def test_observations_reset_on_activity_and_pid_reuse(self):
        import importlib.util
        from unittest.mock import patch
        spec=importlib.util.spec_from_file_location('test_watchdog',ROOT/'scripts/retire-test-companions.py')
        watchdog=importlib.util.module_from_spec(spec);spec.loader.exec_module(watchdog)
        row={'pid':123,'start':'1'}
        with patch.object(watchdog,'eligible',return_value=True):
            seen,ready=watchdog.advance([row],{},10)
            self.assertFalse(ready)
            seen,ready=watchdog.advance([row],seen,610)
            self.assertEqual(ready,[row])
            seen,ready=watchdog.advance([{**row,'start':'2'}],seen,611)
            self.assertFalse(ready)
        with patch.object(watchdog,'eligible',return_value=False):
            self.assertEqual(watchdog.advance([row],seen,612),({},[]))

    def test_only_known_temporary_test_namespaces_are_in_scope(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('test_watchdog_scope',ROOT/'scripts/retire-test-companions.py')
        watchdog=importlib.util.module_from_spec(spec);spec.loader.exec_module(watchdog)
        for path in ('/tmp/augmentor-pi-contract-synthetic/shared-state','/tmp/augmentor-offscreen-dictation-synthetic'):
            self.assertTrue(watchdog.isolated(path))
        for path in ('/home/owner/.local/state/augmentor','/tmp/unrelated','/tmp/augmentor-real-install','relative'):
            self.assertFalse(watchdog.isolated(path))
