# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
from PySide6.QtWidgets import QApplication
from augmentor_linux.window import Window

class VoiceDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_structured_reply_is_visible_once_and_errors_are_not_replies(self):
        w=Window(preview=True)
        event={'seq':901,'type':'tool/result','data':{'meta':{'resonantVoice':{'version':1,'text':'Hello, Manolo.','speech':{'emotion':'warm'}}},'message':{'content':[{'type':'tool-result','isError':False}]}}}
        self.assertTrue(w.fold_event(event));self.assertFalse(w.fold_event(event))
        self.assertEqual(w.messages[-1],('Augmentor','Hello, Manolo.'))
        event['seq']=902;event['data']['message']['content'][0]['isError']=True
        self.assertFalse(w.fold_event(event));w.close()

    def test_mixed_prose_and_voice_tool_has_one_authoritative_reply(self):
        for tool in ['resonant_voice_reply','resonant_voice_demo']:
            w=Window(preview=True)
            w.fold_event({'type':'assistant/chunk','data':{'chunk':{'type':'text-delta','text':'Good news — it works.'}}})
            w.fold_event({'seq':18,'type':'assistant/message','data':{'message':{'content':[{'type':'text','text':'Good news — it works.'},{'type':'tool-call','name':tool,'id':'call','arguments':'{}'}]}}})
            self.assertEqual(w.partial,'')
            w.fold_event({'seq':20,'type':'tool/result','data':{'meta':{'resonantVoice':{'version':1,'text':'Here are the five samples.'}},'message':{'content':[{'type':'tool-result','isError':False}]}}})
            replies=[text for role,text in w.messages if role=='Augmentor']
            self.assertEqual(replies,['Here are the five samples.']);w.close()
