# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual Unix peers; synthetic protocol only, no product/widget/model actions."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('memory_proof',ROOT/'release/owned-memory-companion-proof.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

SERVER=r'''import json,os,socket;from pathlib import Path
config=json.loads(os.environ['OWNED_MEMORY_TEST']);endpoint=Path(config['endpoint']);audit=Path(config['audit']);token=None
with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
 server.bind(str(endpoint));server.listen()
 try:
  while True:
   peer,_=server.accept()
   with peer:
    with peer.makefile('rb') as stream:raw=stream.readline(65537)
    if not raw:continue
    request=json.loads(raw);action=request['method'].rsplit('.',1)[1]
    if action in ('prepare','commit'):
     assert json.loads(Path(config['journal']).read_text())['pending']==action
    with audit.open('a') as out:out.write(action+'\n')
    if action=='prepare':token=request['params']['token']
    if action=='commit':
     assert request['params']['token']==token
     if config['mode']=='lose-commit':break
    response={'id':request['id'],'result':{'protocol':'augmentor-component-maintenance/1',
     'phase':{'status':'ready','prepare':'prepared','commit':'closing'}[action],
     'active':1 if config['mode']=='busy' else 0,'expiresInSeconds':30 if action=='prepare' else None}}
    peer.sendall((json.dumps(response)+'\n').encode())
    if action=='commit':break
 finally:endpoint.unlink(missing_ok=True)
'''


@unittest.skipUnless(sys.platform.startswith('linux') and hasattr(socket,'SO_PEERCRED'), 'Linux Unix peer credentials required')
class OwnedMemoryCompanionProof(unittest.TestCase):
    def fixture(self, directory):
        home=Path(directory)/'home';home.mkdir(mode=0o700)
        app=Path(directory)/'app';source=app/'services/memory/service.py';source.parent.mkdir(parents=True)
        source.write_text(SERVER);source.chmod(0o600)
        state=home/'state';state.mkdir(mode=0o700)
        journal=home/'proof';journal.mkdir(mode=0o700)
        dsh=home/'dsh';dsh.mkdir(mode=0o700)
        env={**os.environ,'AUGMENTOR_SHARED_STATE':str(state),'DSH_HOME':str(dsh)}
        return home,app,state,journal,dsh,env

    def start(self, fixture, *, mode='normal', foreign=False):
        home,app,state,journal,dsh,env=fixture
        source=app/'services/memory/service.py'
        if foreign:
            source=app/'foreign.py';source.write_text(SERVER)
        config={'endpoint':str(state/'dual-memory.sock'),'audit':str(home/'rpc-audit'),
                'journal':str(journal/'memory-companion-cleanup.json'),'mode':mode}
        child=subprocess.Popen([sys.executable,'-Xutf8','-B',str(source)],env={**env,'OWNED_MEMORY_TEST':json.dumps(config)},
                               stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        self.addCleanup(self.close_child,child)
        deadline=time.monotonic()+5
        while not (state/'dual-memory.sock').exists():
            self.assertIsNone(child.poll());self.assertLess(time.monotonic(),deadline);time.sleep(.01)
        return child

    @staticmethod
    def close_child(child):
        if child.poll() is None:child.terminate()
        child.wait(timeout=5)
        child.stderr.close()

    def tracker(self, fixture):
        home,app,state,journal,dsh,env=fixture
        return module.OwnedMemoryCompanion(app,sys.executable,home,dsh,env,journal)

    def audit(self, fixture):
        path=fixture[0]/'rpc-audit'
        return path.read_text().splitlines() if path.exists() else []

    def test_absent_companion_finishes_without_rpc_and_journal_cannot_be_adopted(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture=self.fixture(directory);tracker=self.tracker(fixture)
            self.assertFalse(tracker.finish()['companionStarted']);self.assertEqual(self.audit(fixture),[])
            with self.assertRaises(FileExistsError):self.tracker(fixture)

    def test_new_native_unix_peer_receives_one_durably_journalled_prepare_commit_and_exits(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture=self.fixture(directory);tracker=self.tracker(fixture);child=self.start(fixture)
            record=tracker.finish();self.assertEqual(record['status'],'pass');self.assertTrue(record['normalExit'])
            self.assertEqual(record['identity']['pid'],child.pid);self.assertFalse(record['signalSent'])
            self.assertEqual(self.audit(fixture),['status','prepare','commit']);child.wait(timeout=5)
            self.assertEqual(child.returncode,0);self.assertIsNone(record['pending'])
            with self.assertRaisesRegex(ValueError,'one-shot'):tracker.finish()

    def test_preexisting_real_daemon_refuses_without_connecting_or_shutdown(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture=self.fixture(directory);child=self.start(fixture)
            with self.assertRaisesRegex(ValueError,'preexisting'):self.tracker(fixture)
            self.assertIsNone(child.poll());self.assertEqual(self.audit(fixture),[])

    def test_active_real_peer_is_terminal_before_prepare_and_is_not_signalled(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture=self.fixture(directory);tracker=self.tracker(fixture);child=self.start(fixture,mode='busy')
            with self.assertRaisesRegex(ValueError,'active'):tracker.finish()
            self.assertEqual(self.audit(fixture),['status']);self.assertIsNone(child.poll())
            self.assertFalse(tracker.record['unknownOutcome']);self.assertIsNone(tracker.record['pending'])
            with self.assertRaisesRegex(ValueError,'one-shot'):tracker.finish()

    def test_lost_commit_reply_keeps_pending_and_unknown_without_retry_even_after_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture=self.fixture(directory);tracker=self.tracker(fixture);child=self.start(fixture,mode='lose-commit')
            with self.assertRaisesRegex(ValueError,'response'):tracker.finish()
            child.wait(timeout=5);self.assertTrue(tracker.record['unknownOutcome'])
            self.assertEqual(tracker.record['pending'],'commit');self.assertEqual(self.audit(fixture),['status','prepare','commit'])
            with self.assertRaisesRegex(ValueError,'one-shot'):tracker.finish()

    def test_foreign_actual_socket_process_refuses_before_any_rpc(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture=self.fixture(directory);tracker=self.tracker(fixture);child=self.start(fixture,foreign=True)
            with self.assertRaisesRegex(ValueError,'does not belong'):tracker.finish()
            self.assertEqual(self.audit(fixture),[]);self.assertIsNone(child.poll())

    def test_actual_owner_and_inode_replacement_between_status_and_prepare_is_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture=self.fixture(directory);tracker=self.tracker(fixture);first=self.start(fixture)
            original=tracker._rpc;replacement=[]
            def exchange(action,token=None):
                result=original(action,token)
                if action=='status':
                    tracker.endpoint.unlink()
                    replacement.append(self.start(fixture))
                return result
            tracker._rpc=exchange
            with self.assertRaisesRegex(ValueError,'owner or socket changed'):tracker.finish()
            self.assertNotEqual(first.pid,replacement[0].pid)
            self.assertEqual(self.audit(fixture),['status'])
            self.assertIsNone(first.poll());self.assertIsNone(replacement[0].poll())
            self.assertIsNone(tracker.record['pending']);self.assertFalse(tracker.record['unknownOutcome'])

    def test_old_process_start_and_changed_source_are_refused_before_rpc(self):
        for changed_source in (False,True):
            with self.subTest(changed_source=changed_source),tempfile.TemporaryDirectory() as directory:
                fixture=self.fixture(directory);tracker=self.tracker(fixture);child=self.start(fixture)
                if changed_source:
                    tracker.source.write_text(SERVER+'\n# changed immutable source\n')
                else:tracker.start_fence+=1000000
                with self.assertRaises(ValueError):tracker.finish()
                self.assertEqual(self.audit(fixture),[]);self.assertIsNone(child.poll())

    def test_linked_or_outside_private_state_refuses_without_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture=self.fixture(directory);home,app,state,journal,dsh,env=fixture
            with self.assertRaisesRegex(ValueError,'inside'):
                module.OwnedMemoryCompanion(app,sys.executable,home,dsh,{**env,'AUGMENTOR_SHARED_STATE':directory},journal)
            link=home/'linked';link.symlink_to(state,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'linked'):
                module.OwnedMemoryCompanion(app,sys.executable,home,dsh,{**env,'AUGMENTOR_SHARED_STATE':str(link)},journal)


if __name__=='__main__':unittest.main()
