# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Submission labels must describe observed work, never inferred model internals."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication
from augmentor_linux.controller import Controller
from augmentor_linux.window import Window
from augmentor_linux.adapters.dsh_wire import EventStream


class ResponseProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_submission_labels_precede_the_operations_they_describe(self):
        labels=[]
        class Client:
            def validate_model(inner,selection):self.assertEqual(labels[-1],'Checking selected model…')
            def call(inner,method,payload):
                expected={'session.selectModel':'Applying selected model…','session.prompt':'Sending message to agent…'}
                self.assertEqual(labels[-1],expected[method]);return {'accepted':True}
        c=Controller(client=Client());c.session='fixture';c.save_session=lambda:None;c.task=lambda fn:fn()
        c.submission_progress.connect(lambda generation,text,rank:labels.append(text))
        c.subscribe=lambda sid:self.assertEqual(labels[-1],'Connecting to conversation…')
        c.send('Fixture',{'provider':'test','model':'test'})
        self.assertEqual(labels,['Checking selected model…','Applying selected model…','Connecting to conversation…','Sending message to agent…','Message accepted; waiting for agent…'])
        c.running=False;c.close()

    def test_live_stages_are_replaced_by_thinking_and_late_ack_cannot_restore_them(self):
        w=Window();self.addCleanup(w.close)
        generation=object();w.controller=SimpleNamespace(generation=generation,running=False,close=lambda:None)
        w.messages=[('You','Fixture prompt')];w.begin_response_progress('Submitting message…')
        def deliver(kind,data=None):w.on_event({'type':kind,'data':data or {}});w.render_messages()
        w.submission_progress(generation,'Checking selected model…',1);w.render_messages()
        self.assertIn('Checking selected model…',w.transcript.toPlainText())
        deliver('turn/start');deliver('step/start')
        self.assertIn('Building model request…',w.transcript.toPlainText())
        deliver('assistant/start')
        self.assertIn('Waiting for the model’s first output…',w.transcript.toPlainText())
        w.submission_progress(generation,'Message accepted; waiting for agent…',6)
        self.assertEqual(w.response_progress,'Waiting for the model’s first output…')
        deliver('assistant/chunk',{'chunk':{'type':'reasoning-delta','text':'Live thought'}})
        self.assertIn('Live thought',w.transcript.toPlainText())
        self.assertIsNone(w.response_progress)
        w.submission_progress(generation,'Message accepted; waiting for agent…',6)
        self.assertIsNone(w.response_progress)
        deliver('assistant/chunk',{'chunk':{'type':'text-delta','text':'Answer'}})
        self.assertNotIn('Live thought',w.transcript.toPlainText())
        self.assertIn('Answer',w.transcript.toPlainText())
        self.assertEqual(w.messages,[('You','Fixture prompt'),('Thinking','Live thought')])
        deliver('assistant/start')
        deliver('assistant/chunk',{'chunk':{'type':'tool-call-delta','text':'{}'}})
        self.assertEqual(w.response_progress,'Receiving a tool request from the model…')
        deliver('tool/call',{'name':'fixture'});self.assertIsNone(w.response_progress)

    def test_terminal_events_and_idle_clear_wait_without_leaking_into_history(self):
        for kind in ('turn/end','runtime/error','tool/call','assistant/message'):
            with self.subTest(kind=kind):
                w=Window();self.addCleanup(w.close)
                w.on_event({'type':'assistant/start','data':{}})
                w.on_event({'type':kind,'data':{}});w.render_messages()
                self.assertIsNone(w.response_progress)
                w.restore_history([{'type':'turn/start'},{'type':'step/start'}])
                self.assertNotIn('Building model request',w.transcript.toPlainText())
        w.begin_response_progress('Waiting for the model’s first output…');w.set_busy(False)
        self.assertIsNone(w.response_progress)

    def test_old_submission_generation_cannot_change_new_progress(self):
        w=Window();self.addCleanup(w.close)
        w.controller=SimpleNamespace(generation=object(),close=lambda:None,running=False)
        w.begin_response_progress('Submitting message…')
        w.submission_progress(object(),'Old operation',1)
        self.assertEqual(w.response_progress,'Submitting message…')

    def test_native_transport_delivers_stream_start_before_first_chunk(self):
        frames=[]
        sock=lambda name:SimpleNamespace(name=name,settimeout=lambda _:None,close=lambda:None)
        responses={
            '$events':iter([{'type':'ready','clientId':'fixture'}]),
            'session/control':iter([{'type':'baseline','value':{}}]),
            'session/follow':iter([{'type':'snapshot','cursor':0},
                {'type':'assistant-stream','frame':{'type':'start','time':1}},
                {'type':'assistant-stream','frame':{'type':'chunk','time':2,'chunk':{'type':'reasoning-delta','text':'Thought'}}}])}
        client=SimpleNamespace(remote=SimpleNamespace(stream=lambda name,args:sock(name),item=lambda socket:next(responses[socket.name])),call=lambda *args:{'items':[]})
        def receive(frame):
            frames.append(frame)
            if frame.get('payload',{}).get('event',{}).get('type')=='assistant/chunk':stream.closed.set()
        stream=EventStream(client,'fixture',receive,self.fail)
        with patch('augmentor_linux.adapters.dsh_wire.threading.Thread',return_value=Mock()):stream._run()
        self.assertIsNone(stream.failure)
        events=[f['payload']['event'] for f in frames if f.get('method')=='session/event']
        self.assertEqual([e['type'] for e in events],['assistant/start','assistant/chunk'])
        self.assertTrue(all('seq' not in e for e in events))
