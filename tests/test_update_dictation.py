# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Broker admission failures and actual isolated Unix process/graph observations."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'services'),str(ROOT/'apps/native')]
spec=importlib.util.spec_from_file_location('dictation_update_broker',ROOT/'services/dictation/server.py')
broker=importlib.util.module_from_spec(spec);spec.loader.exec_module(broker)
from lifecycle.admission import MaintenanceBusy
from lifecycle.posix_components import discover_sockets
from lifecycle.posix_preparation import PosixPreparation
from lifecycle.macos_payload import snapshot
from updates.posix_dictation_reopen import reopen
from updates.posix_reopen import validate_plan
from augmentor_linux import dictation


class BrokerAdmissionTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='agdm-');self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name);self.backend=broker.Backend(self.base)
        self.token={'token':'a'*48}

    def test_disabled_reservation_fences_work_and_cancel_restores_it_without_starting_handy(self):
        with patch.object(self.backend,'start',side_effect=AssertionError('Native capture started')):
            self.assertEqual(self.backend.request('host.maintenance.prepare',self.token)['phase'],'prepared')
            with self.assertRaises(MaintenanceBusy):self.backend.request('enable',{'enabled':True})
            self.backend.request('host.maintenance.cancel',self.token)
            self.assertFalse(self.backend.request('status',{})['enabled'])

    def test_live_voice_owner_refuses_without_releasing_capture(self):
        owner={'token':'b'*32,'pid':os.getpid()}
        self.backend.request('conversation.acquire',owner)
        with self.assertRaises(MaintenanceBusy):self.backend.request('host.maintenance.prepare',self.token)
        self.assertEqual(self.backend.owner,owner)
        self.assertEqual(self.backend.maintenance.gate.control('host.maintenance.status',{})['phase'],'ready')

    def native(self,models=None,phase='ready'):
        self.backend.child=Mock();self.backend.child.poll.return_value=None
        calls=[]
        def call(method,params):
            calls.append((method,params))
            if method=='status':return {'phase':phase}
            if method=='models':return models if models is not None else []
            return {}
        self.backend.call=Mock(side_effect=call)
        return calls

    def test_native_busy_phase_and_download_preserve_work_and_release_only_update_token(self):
        for models,phase in (([],'transcribing'),([{'downloading':True}],'ready')):
            with self.subTest(phase=phase):
                calls=self.native(models,phase)
                with self.assertRaises(MaintenanceBusy):self.backend.request('host.maintenance.prepare',self.token)
                self.assertEqual(calls[0][0],'conversation.acquire')
                self.assertEqual(calls[0][1]['token'],self.token['token'])
                self.assertGreater(calls[0][1]['expires_at'],0)
                self.assertEqual(calls[-1],('conversation.release',self.token))
                self.assertNotIn('cancel',[method for method,_ in calls])
                self.assertEqual(self.backend.maintenance.gate.control('host.maintenance.status',{})['phase'],'ready')

    def test_unknown_release_retains_closed_admission_and_native_reference(self):
        self.native();self.backend.request('host.maintenance.prepare',self.token)
        self.backend.call.side_effect=TimeoutError('Lost matching release acknowledgement.')
        with self.assertRaises(TimeoutError):self.backend.request('host.maintenance.cancel',self.token)
        self.assertEqual(self.backend.maintenance.native_token,self.token['token'])
        with self.assertRaises(MaintenanceBusy):self.backend.request('status',{})

    def test_unknown_native_acquire_never_replays_release_or_reopens_admission(self):
        self.native();self.backend.call.side_effect=TimeoutError('Acquire outcome unknown.')
        with self.assertRaises(TimeoutError):self.backend.request('host.maintenance.prepare',self.token)
        self.assertEqual(self.backend.call.call_count,1)
        self.assertEqual(self.backend.maintenance.native_token,self.token['token'])
        self.assertTrue(self.backend.maintenance.uncertain)
        with self.assertRaises(MaintenanceBusy):self.backend.request('host.maintenance.cancel',self.token)

    def test_expired_reservation_releases_native_before_normal_work(self):
        calls=self.native();now=[0];self.backend.maintenance.gate.clock=lambda:now[0]
        self.backend.request('host.maintenance.prepare',self.token);now[0]=31
        self.backend.maintenance.expire()
        self.assertEqual(calls[-1],('conversation.release',self.token))
        self.assertEqual(self.backend.request('host.maintenance.status',{})['phase'],'ready')

    def test_download_reply_gap_remains_busy_until_confirmed_completion(self):
        rows=[{'id':'synthetic','installed':False,'downloading':False}]
        self.native(rows);self.backend.maintenance.download_started('synthetic')
        with self.assertRaises(MaintenanceBusy):self.backend.request('host.maintenance.prepare',self.token)
        rows[0]['installed']=True
        self.assertEqual(self.backend.request('host.maintenance.prepare',self.token)['phase'],'prepared')

    def test_commit_is_one_shot_and_shutdown_never_escalates_a_stalled_child(self):
        self.native();self.backend.request('host.maintenance.prepare',self.token)
        self.backend.request('host.maintenance.commit',self.token)
        with self.assertRaises(MaintenanceBusy):self.backend.request('host.maintenance.commit',self.token)
        child=self.backend.child;child.stdin.closed=False;child.wait.side_effect=subprocess.TimeoutExpired('fixture',10)
        with self.assertRaises(subprocess.TimeoutExpired):self.backend.normal_stop()
        child.terminate.assert_not_called();child.kill.assert_not_called();self.assertIs(self.backend.child,child)
        self.assertFalse(getattr(self.backend,'shutting_down',False))

    def test_only_boolean_captured_dictation_marker_is_accepted(self):
        valid={'instances':[],'hadBrowser':False,'hadDictation':True}
        self.assertEqual(validate_plan(valid),valid)
        for value in (1,'true',[],None):
            with self.assertRaises(ValueError):validate_plan({**valid,'hadDictation':value})


@unittest.skipUnless(sys.platform=='linux','Actual Linux socket pidfd and copied system interpreter.')
class NativeBrokerTests(unittest.TestCase):
    def test_actual_graph_preserves_voice_then_drains_and_reopens_original_session_once(self):
        with tempfile.TemporaryDirectory(prefix='agdb-') as folder:
            base=Path(folder);runtime=base/'run';runtime.mkdir(mode=0o700)
            project=base/'project';project.mkdir(mode=0o700)
            for path in (ROOT/'services').rglob('*.py'):
                target=project/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
            path=project/'apps/native/augmentor_linux/dictation.py';path.parent.mkdir(parents=True)
            shutil.copy2(ROOT/'apps/native/augmentor_linux/dictation.py',path)
            python=project/'python/bin/python3';python.parent.mkdir(parents=True);shutil.copy2(Path(sys.executable).resolve(),python)
            env={**os.environ,'AUGMENTOR_DICTATION_STATE':str(base/'dictation'),
                'XDG_RUNTIME_DIR':str(runtime),'XDG_STATE_HOME':str(base/'state')}
            steps=[];peers=[]
            with patch.dict(os.environ,env):
                child=subprocess.Popen([str(python),'-I','-B',str(project/'services/dictation/server.py')],
                    env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                def observe():return discover_sockets(runtime,r'augmentor-dictation-[1-9][0-9]{0,19}\.sock',project,python,kind='dictation')
                def stop_live():
                    current=observe()
                    try:
                        for peer in current:
                            with __import__('lifecycle.reservations',fromlist=['Reservations']).Reservations(keepalive=False) as group:
                                group.prepare(peer);group.commit(peer,checkpoint=lambda *_:None)
                    finally:
                        for peer in current:peer.close()
                try:
                    deadline=time.monotonic()+10
                    while not peers:
                        if child.poll() is not None:self.fail(child.stderr.read().decode())
                        if time.monotonic()>deadline:self.fail('The private broker did not register.')
                        peers=observe();time.sleep(.02)
                    for peer in peers:peer.close()
                    with patch.dict(os.environ,{'XDG_SESSION_ID':'different-fixture-session'}):
                        with self.assertRaisesRegex(ValueError,'another session'):observe()
                    dictation.request('conversation.acquire',{'token':'b'*32,'pid':os.getpid()},start=False)
                    graph=PosixPreparation(project,runtime,runtime/'shared')
                    with self.assertRaises(ValueError):graph.__enter__()
                    self.assertTrue(graph.preparation_released);self.assertIsNone(child.poll())
                    dictation.request('conversation.release',{'token':'b'*32},start=False)
                    with PosixPreparation(project,runtime,runtime/'shared') as graph:
                        captured=graph.reopen_plan();self.assertTrue(captured['hadDictation'])
                        self.assertEqual([peer.pid for peer in graph.dictation],[child.pid])
                        with self.assertRaises(RuntimeError):dictation.request('enable',{'enabled':True},start=False)
                        blocked=subprocess.run([str(python),'-I','-B',str(project/'services/dictation/server.py')],
                            env={**env,'AUGMENTOR_DICTATION_STATE':str(base/'blocked-state')},
                            capture_output=True,timeout=10)
                        self.assertNotEqual(blocked.returncode,0)
                        self.assertIn(b'BlockingIOError',blocked.stderr)
                        graph.drain(checkpoint=lambda stage,peer:steps.append((stage,peer.pid)))
                    self.assertEqual(child.wait(timeout=10),0)
                    self.assertEqual(steps,[(stage,child.pid) for stage in ('commit-intent','commit-acknowledged','exited')])
                    witness=Mock();witness.dictation_reopening_started=False
                    payload=snapshot(project);checks=[]
                    def immutable():checks.append(True);self.assertEqual(snapshot(project),payload)
                    self.assertTrue(reopen(witness,captured,project,runtime,immutable))
                    self.assertTrue(witness.dictation_reopened);self.assertGreaterEqual(len(checks),2)
                    with self.assertRaisesRegex(ValueError,'replayed'):reopen(witness,captured,project,runtime,immutable)
                    self.assertFalse(dictation.request('status',start=False)['enabled'])
                finally:
                    try:dictation.request('conversation.release',{'token':'b'*32},start=False)
                    except (RuntimeError,OSError,TimeoutError):pass
                    stop_live()
                    if child.poll() is None:child.terminate()
                    child.communicate(timeout=10)
