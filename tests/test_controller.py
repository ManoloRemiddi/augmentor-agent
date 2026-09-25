# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import threading
import time
import unittest
import tempfile
import os
from unittest.mock import patch

from augmentor_linux.controller import Controller


class ControllerTests(unittest.TestCase):
    def test_retired_harness_is_rejected_before_a_client_can_start(self):
        with self.assertRaisesRegex(ValueError,'retired'):
            Controller(harness='opencode')

    def test_last_session_is_restored_from_private_metadata_only(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {'XDG_STATE_HOME': root}):
            first = Controller()
            first.session = 'augmentor-linux-pi-' + 'a' * 32
            first.save_session()
            second = Controller()
            self.assertEqual(second.session, first.session)
            self.assertEqual(first.state_file.stat().st_mode & 0o777, 0o600)
            self.assertNotIn('messages', first.state_file.read_text())

    def test_stop_during_preparation_prevents_prompt(self):
        started, release = threading.Event(), threading.Event()
        class Client:
            calls = []
            def validate_model(self, selection):
                started.set()
                release.wait(2)
            def call(self, method, payload):
                self.calls.append(method)
                return {}
        client = Client()
        controller = Controller(client=client)
        controller.send('do something', {})
        self.assertTrue(started.wait(1))
        controller.stop()
        self.assertTrue(controller.running)
        release.set()
        deadline = time.monotonic() + 2
        while controller.running and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertFalse(controller.running)
        self.assertNotIn('session.prompt', client.calls)

    def test_submission_result_is_explicit_for_rejection_and_pre_send_cancel(self):
        for outcome in ('reject','cancel','accept'):
            class Client:
                def validate_model(self, selection):
                    if outcome=='cancel':controller.cancel_requested.set()
                def call(self, method, payload):return {'accepted':outcome=='accept'}
            controller=Controller(client=Client());controller.session='fixture'
            controller.connected=True;controller.stream=type('Stream',(),{'session':'fixture'})()
            controller.save_session=lambda:None;controller.task=lambda fn:fn()
            failed=[];sent=[]
            controller.submission_failed.connect(failed.append);controller.sent.connect(sent.append)
            if outcome=='reject':
                with self.assertRaisesRegex(Exception,'did not accept'):controller.send('Fixture prompt',{'provider':'test','model':'test'})
            else:controller.send('Fixture prompt',{'provider':'test','model':'test'})
            self.assertEqual(failed,[] if outcome=='accept' else ['Fixture prompt'])
            self.assertEqual(sent,['Fixture prompt'] if outcome=='accept' else [])

    def test_idle_subscription_baseline_cannot_release_a_preparing_send(self):
        class Client:
            def validate_model(self,_):pass
            def call(self,method,payload):return {'accepted':True}
        controller=Controller(client=Client());controller.session='fixture'
        controller.save_session=lambda:None;controller.task=lambda fn:fn()
        def subscribe(sid):
            controller.frame({'method':'host/session-status','payload':{'sessionId':sid,'running':False}})
            self.assertTrue(controller.running)
            self.assertFalse(controller.send('Duplicate',{}))
        controller.subscribe=subscribe
        controller.send('First',{'provider':'test','model':'test'})
        self.assertTrue(controller.running)
        controller.frame({'method':'host/session-status','payload':{'sessionId':'fixture','running':False}})
        self.assertFalse(controller.running)

    def test_reconnect_recovers_history_without_cancel_or_prompt_replay(self):
        class Client:
            calls=[]
            def session_rows(self):return [{'sessionId':'owned','cwd':'/tmp/owned','agentPreset':'augmentor-linux-pi','running':True}]
            def call(self,method,payload=None):
                self.calls.append(method)
                if method=='session.history':return {'events':[{'event':{'seq':1,'type':'turn/start'}},{'event':{'seq':2,'type':'assistant/chunk'}}]}
                return {}
            def model_catalog(self):return {'groups':[]}
            def saved_chats(self):return []
        class Stream:
            failure=None
            def __init__(self,client,sid,frame,disconnected):self.session=sid;self.frame=frame
            def start(self):self.frame({'method':'session/event','payload':{'event':{'seq':3,'type':'turn/end'}}})
            def close(self):pass
        client=Client();controller=Controller(client=client);controller.session='owned'
        controller.loaded_events=[{'seq':1,'type':'turn/start'}]
        with patch('augmentor_linux.controller.EventStream',Stream):controller.recover_connection()
        self.assertIn('session.create',client.calls)
        self.assertNotIn('session.cancel',client.calls)
        self.assertNotIn('session.prompt',client.calls)
        self.assertEqual([e['seq'] for e in controller.loaded_events],[1,2,3])
        self.assertFalse(controller.running)
        self.assertTrue(controller.online)

    def test_disconnect_keeps_running_turn_and_requests_no_mutation(self):
        client=type('Client',(),{'call':lambda *_:self.fail('Disconnect must not call Pi mutations')})()
        controller=Controller(client=client);controller.running=True;controller.session='owned'
        controller.disconnected('temporary outage')
        self.assertTrue(controller.running)
        self.assertFalse(controller.online)
        self.assertFalse(controller.cancel_requested.is_set())

    def test_read_only_history_never_cancels_its_agent(self):
        class Client:
            calls=[]
            def call(self,method,payload=None):self.calls.append(method);return {}
        client=Client();controller=Controller(client=client);controller.session='foreign';controller.read_only=True
        controller.task=lambda fn:fn();controller.close()
        self.assertNotIn('session.cancel',client.calls)

    def test_edit_branches_before_prompt_and_preserves_explicit_model(self):
        calls=[]
        model={'provider':'test','model':'chosen'}
        class Client:
            def validate_model(self,selection):calls.append(('validate',selection))
            def call(self,method,payload=None):
                calls.append((method,payload))
                if method=='session.branch':return {'sessionId':'edited','selection':{'provider':'test','model':'old'},'cwd':'/tmp','title':'Edit','agentPreset':'augmentor-linux-pi'}
                if method=='session.history':return {'events':[]}
                if method=='session.prompt':return {'accepted':True}
                return {}
        controller=Controller(client=Client());controller.session='source';controller.online=True;controller.task=lambda fn:fn()
        controller.subscribe=lambda sid:setattr(controller,'connected',True)
        controller.send('Revised',model,edit_from={'sessionId':'source','seq':7})
        methods=[m for m,_ in calls]
        self.assertLess(methods.index('session.branch'),methods.index('session.prompt'))
        payload=next(p for m,p in calls if m=='session.prompt')
        self.assertEqual(payload['sessionId'],'edited');self.assertEqual(payload['content'][0]['text'],'Revised')
        self.assertEqual(controller.selection,model)

    def test_edit_rejects_a_changed_chat_before_branching_or_sending(self):
        class Client:
            def validate_model(self,_):pass
            def call(self,*_):raise AssertionError('No session mutation expected')
        controller=Controller(client=Client());controller.session='new-chat';controller.task=lambda fn:fn()
        from augmentor_linux.pi_client import ContractError
        with self.assertRaisesRegex(ContractError,'conversation changed'):
            controller.send('Revised',{},edit_from={'sessionId':'old-chat','seq':1})
        self.assertFalse(controller.running)


class RecoveryRaceTests(unittest.TestCase):
    def test_history_terminal_event_wins_over_stale_running_list(self):
        controller=Controller(client=object())
        controller.loaded_events=[{'seq':1,'type':'turn/start'},{'seq':2,'type':'turn/end'}]
        self.assertFalse(controller.history_running(True))
        controller.loaded_events.append({'seq':3,'type':'turn/start'})
        self.assertTrue(controller.history_running(False))
