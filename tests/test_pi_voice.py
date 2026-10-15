# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Native public Pi client admission, close ownership and typed/spoken routing."""
import threading
import time
from types import SimpleNamespace
import unittest
from PySide6.QtWidgets import QApplication
from augmentor_linux.controller import Controller
from augmentor_linux.pi_client import ContractError

class PiVoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def controller(self,ticket=None,close=None):
        calls=[]
        def call(method,payload):
            calls.append((method,payload));return {'accepted':True}
        client=SimpleNamespace(harness='pi',capabilities={'voice':True},supports_queue=True,validate_model=lambda _:None,call=call,
            voice_ticket=ticket or (lambda sid,opening:{'sessionId':sid}),voice_close=close or (lambda *_:None))
        c=Controller(client=client);c.online=c.connected=True;c.session='owned'
        c.stream=SimpleNamespace(session='owned',close=lambda:None);self.addCleanup(c.close)
        return c,calls

    def until(self,check):
        end=time.monotonic()+5
        while time.monotonic()<end:
            self.app.processEvents()
            if check():return
            time.sleep(.005)
        self.fail('Native Pi lifecycle did not settle.')

    def test_close_joins_preparation_and_retirement_with_the_same_opening_identity(self):
        entered=threading.Event();ticket_gate=threading.Event();close_gate=threading.Event();closings=[];errors=[]
        def ticket(sid,opening):
            entered.set();ticket_gate.wait();return {'sessionId':sid}
        def close(sid,opening):
            closings.append((sid,opening));close_gate.wait()
        c,_=self.controller(ticket,close)
        def prepare():
            try:c.prepare_voice({'provider':'fixture','model':'fixture'})
            except Exception as error:errors.append(str(error))
        worker=threading.Thread(target=prepare);worker.start()
        try:
            self.assertTrue(entered.wait(2));c.close_voice();self.until(lambda:bool(closings))
            self.assertEqual(c.voice_closing,1)
            self.assertGreater(c.admission.control('host.maintenance.status',{})['active'],0)
            with self.assertRaises(ContractError):c.prepare_voice({'provider':'fixture','model':'fixture'})
            ticket_gate.set();self.until(lambda:len(closings)>=2)
            self.assertEqual(c.voice_closing,1,'local ticket settlement cannot clear an unsettled remote close')
        finally:ticket_gate.set();close_gate.set();worker.join(3)
        self.until(lambda:c.voice_closing==0)
        self.assertEqual(errors,['Voice is closing.']);self.assertIsNone(c.voice_pending);self.assertIsNone(c.voice_session)
        self.assertEqual(len(set(closings)),1,'all phases close only their own opening')

    def test_cancelled_before_preparation_does_not_open_a_ticket(self):
        tickets=[];c,_=self.controller(lambda *args:tickets.append(args))
        cancelled=threading.Event();cancelled.set()
        with self.assertRaisesRegex(ContractError,'closing'):c.prepare_voice({},cancelled=cancelled)
        self.assertFalse(tickets);self.assertIsNone(c.voice_pending);self.assertFalse(c.navigating)

    def test_spoken_send_is_explicit_and_a_speech_looking_typed_identity_remains_typed(self):
        c,calls=self.controller();c.task=lambda fn,**_:fn()
        self.assertTrue(c.send('Spoken',{'provider':'fixture','model':'fixture'},request_id='resonant-voice:first',input_mode='voice'))
        self.assertEqual([p for m,p in calls if m=='session.prompt'][-1]['inputMode'],'voice')
        c.running=False
        self.assertTrue(c.send('Typed',{'provider':'fixture','model':'fixture'},request_id='resonant-voice:typed'))
        self.assertNotIn('inputMode',[p for m,p in calls if m=='session.prompt'][-1]);c.running=False

    def test_spoken_steering_keeps_the_observed_turn_and_explicit_mode(self):
        c,calls=self.controller();c.task=lambda fn,**_:fn();c.running=True;c.generation=object();c.queue_turn_id='observed-turn'
        self.assertTrue(c.queue_prompt('Correction','resonant-voice:correction',mode='steer',input_mode='voice'))
        prompt=[p for m,p in calls if m=='session.prompt'][-1]
        self.assertEqual(prompt['inputMode'],'voice');self.assertEqual(prompt['expectedTurnId'],'observed-turn');c.running=False

    def test_invalid_mode_does_not_start_controller_work(self):
        c,calls=self.controller()
        with self.assertRaisesRegex(ContractError,'input mode'):c.send('bad',{},input_mode='unknown')
        with self.assertRaisesRegex(ContractError,'input mode'):c.queue_prompt('bad','id',input_mode='unknown')
        self.assertFalse(calls);self.assertFalse(c.running)

    def test_a_retired_voice_object_cannot_submit_into_a_new_same_chat_connection(self):
        from augmentor_linux.window import Window
        calls=[]
        controller=SimpleNamespace(harness='pi',session='same-chat',read_only=False,running=False,
            send=lambda text,selection,**kwargs:calls.append((text,kwargs)) or True)
        window=SimpleNamespace(controller=controller,voice_dialog=SimpleNamespace(closed=False,submitted={'current-utterance'}),model_picker=SimpleNamespace(currentData=lambda:{}))
        Window.voice_transcript(window,{'sessionId':'same-chat','requestId':'retired-utterance','text':'Late old transcript'})
        self.assertFalse(calls)
        Window.voice_transcript(window,{'sessionId':'same-chat','requestId':'current-utterance','text':'Current transcript'})
        self.assertEqual(calls,[('Current transcript',{'request_id':'resonant-voice:current-utterance','input_mode':'voice'})])

if __name__=='__main__':unittest.main()
