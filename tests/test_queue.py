# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import threading,time,unittest
from types import SimpleNamespace
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QPushButton
from augmentor_linux.window import Window
from augmentor_linux.controller import Controller
from augmentor_linux.queue_panel import QueuePanel


def item(key='one',rpc='rpc',placement='queued'):
    return {'id':key,'rpcId':rpc,'placement':placement,'message':{'content':[{'type':'text','text':'Queued prompt'}]}}

class QueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_enter_queues_and_clears_while_stop_remains_available(self):
        w=Window();calls=[]
        w.controller=SimpleNamespace(running=True,session='s',online=True,client=SimpleNamespace(supports_queue=True),queue_prompt=lambda text,key:calls.append((text,key)) or True,stop=lambda:None,close=lambda:None)
        w.set_models([{'provider':'p','model':'m','name':'Model'}]);w.show();w.composer.setPlainText('Next task')
        QTest.keyClick(w.composer,Qt.Key.Key_Return)
        self.assertEqual(w.composer.toPlainText(),'');self.assertEqual(calls[0][0],'Next task')
        self.assertTrue(w.queue_panel.isVisible());self.assertTrue(w.stop_button.isVisible());self.assertTrue(w.send_button.isEnabled())
        self.assertNotIn('Next task',w.transcript.toPlainText())
        w.controller=None;w.close()

    def test_promote_uses_existing_item_and_double_click_is_ignored(self):
        p=QueuePanel();p.running=True;p.submitted('rpc','Queued prompt');p.replace([item()]);calls=[]
        p.action_requested.connect(lambda *args:calls.append(args));p.act('one','steer');p.act('one','steer')
        self.assertEqual(calls,[('one','steer')]);self.assertFalse(p.pending)
        p.replace([item(placement='steering')]);self.assertFalse(next(b for b in p.findChildren(QPushButton) if b.text()=='Steer' and not b.isHidden()).isEnabled())
        p.consumed('rpc');p.replace([item()]);p.submission_result({'id':'rpc','accepted':True})
        self.assertFalse(p.items);self.assertFalse(p.pending);p.close()

    def test_reconnect_baseline_and_unknown_submission_keep_text(self):
        p=QueuePanel();p.replace([item()]);self.assertEqual(len(p.items),1)
        p.submitted('other','Keep this');p.submission_result({'id':'other','accepted':False,'error':'Timeout'})
        self.assertEqual(p.pending['other']['text'],'Keep this');self.assertTrue(p.pending['other']['failed'])
        p.replace([]);self.assertIn('other',p.pending);p.close()

    def test_backend_submissions_are_ordered_and_steer_is_atomic_update(self):
        calls=[];results=[];gate=threading.Event()
        class Client:
            supports_queue=True
            def call(self,method,payload):
                if payload.get('requestId')=='first':gate.wait(2)
                calls.append((method,payload));return {'accepted':True}
        c=Controller(client=Client(),harness='dsh');c.session='s';c.online=True;c.running=True
        c.queue_result.connect(results.append)
        self.assertTrue(c.queue_prompt('First','first'));self.assertTrue(c.queue_prompt('Second','second'))
        gate.set()
        until=time.monotonic()+3
        while len(results)<2 and time.monotonic()<until:QTest.qWait(10)
        self.assertEqual([p['requestId'] for m,p in calls],['first','second'])
        self.assertTrue(all(p['mode']=='queue' for m,p in calls))
        c.task=lambda fn:fn();c.update_queue('item-id','steer')
        self.assertEqual(calls[-1],('session.updateQueue',{'sessionId':'s','itemId':'item-id','action':{'kind':'steer'}}))
        c.running=False;c.close()

    def test_preparing_cancel_does_not_send_queued_prompt(self):
        calls=[]
        c=Controller(client=SimpleNamespace(supports_queue=True,call=lambda *a:calls.append(a)),harness='dsh')
        c.online=True;c.running=True;c.preparing=True;c.generation=object();results=[];c.queue_result.connect(results.append)
        c.queue_prompt('Keep me','id');c.cancel_requested.set();c.preparing=False
        until=time.monotonic()+2
        while not results and time.monotonic()<until:QTest.qWait(10)
        self.assertFalse(calls);self.assertFalse(results[0]['accepted']);c.running=False;c.close()

    def test_completed_command_does_not_remain_in_prompt_queue(self):
        p=QueuePanel();p.submitted('rpc','/goal pause')
        p.submission_result({'id':'rpc','accepted':True,'command':True})
        self.assertFalse(p.pending);self.assertFalse(p.items);p.close()
