# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
from types import SimpleNamespace
from augmentor_linux.adapters.dsh_wire import EventStream
from augmentor_linux.controller import Controller

class StatusTests(unittest.TestCase):
    def test_stopped_agent_clears_incomplete_turn_without_replaying_it(self):
        calls=[]
        class Client:
            def call(self,method,payload):
                calls.append(method)
                self.assert_history=method=='session.history'
                if not self.assert_history:raise AssertionError('No mutation permitted')
                return {'events':[{'event':{'seq':1,'type':'turn/start'}},{'event':{'seq':2,'type':'step/end'}}]}
        controller=Controller(client=Client());controller.session='owned';controller.online=True;controller.running=True
        controller.loaded_events=[{'seq':1,'type':'turn/start'}];controller.task=lambda f:f()
        controller.frame({'method':'host/session-status','payload':{'sessionId':'owned','running':False}})
        self.assertFalse(controller.running)
        self.assertEqual(calls,['session.history'])
        self.assertEqual(controller.loaded_events[-1]['type'],'step/end')
        self.assertNotIn('turn/end',[e['type'] for e in controller.loaded_events])
    def test_stop_acknowledgement_does_not_keep_an_idle_runtime_busy(self):
        calls=[]
        client=SimpleNamespace(call=lambda *args:(calls.append(args) or {'accepted':True}),running_state=lambda _:False)
        controller=Controller(client=client);controller.session='owned';controller.running=True;controller.task=lambda f:f()
        controller.stop()
        self.assertFalse(controller.running);self.assertEqual(calls,[('session.cancel',{'sessionId':'owned'})])
    def test_other_session_status_and_errors_do_not_change_this_window(self):
        controller=Controller(client=object());controller.session='owned';controller.running=True
        for method in ('host/session-status','host/session-error'):
            controller.frame({'method':method,'payload':{'sessionId':'other','running':False,'message':'failure'}})
        self.assertTrue(controller.running)
    def test_runtime_error_is_presented_and_clears_busy(self):
        controller=Controller(client=object());controller.session='owned';controller.running=True;errors=[]
        controller.problem.connect(errors.append)
        controller.frame({'method':'host/session-error','payload':{'sessionId':'owned','message':'provider failed'}})
        self.assertFalse(controller.running);self.assertEqual(errors,['provider failed'])
    def test_event_bridge_filters_session_and_delegates_waterfalls(self):
        frames=[];calls=[]
        client=SimpleNamespace(remote=SimpleNamespace(invoke=lambda *args:calls.append(args)))
        stream=EventStream(client,'owned',frames.append,lambda _:None);stream.status_client='client'
        stream.status_frame({'type':'emit','event':'api-session/status','args':['other',False]})
        self.assertEqual(frames,[])
        stream.status_frame({'type':'emit','event':'api-session/status','args':['owned',False]})
        self.assertIs(stream.running,False);self.assertEqual(frames[-1]['method'],'host/session-status')
        stream.status_frame({'type':'emit','event':'api-session/error','args':['owned','provider failed']})
        self.assertEqual(frames[-1]['method'],'host/session-error')
        stream.status_frame({'type':'waterfall','eventId':'approval'})
        self.assertEqual(calls,[('$events/result',{'clientId':'client','eventId':'approval','outcome':{'kind':'next'}})])
