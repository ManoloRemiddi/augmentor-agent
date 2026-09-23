# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise the live-to-saved reply handoff in the real Qt transcript."""
import unittest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from augmentor_linux.controller import Controller
from augmentor_linux.window import Window


TEXT = 'The completed answer must stay visible.\nEvery fact survives completion.'
USER = {'seq': 1, 'type': 'user/message', 'data': {'source': {'kind': 'user'}, 'content': [{'type': 'text', 'text': 'A question'}]}}
CHUNK = {'seq': 2, 'type': 'assistant/chunk', 'data': {'chunk': {'type': 'text-delta', 'text': TEXT}}}
FINAL = {'seq': 3, 'type': 'assistant/message', 'data': {'message': {'content': [{'type': 'text', 'text': TEXT}]}}}
END = {'seq': 4, 'type': 'turn/end', 'data': {'reason': {'kind': 'completed'}}}


class ReplyCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.calls = []
        owner = self
        class Client:
            def call(self, method, payload=None):
                owner.calls.append((method, payload))
                return {'events': [{'event': e} for e in [USER, CHUNK, FINAL, END]], 'hasMore': False}
        self.controller = Controller(client=Client(), harness='dsh')
        self.controller.session = 'reply-test'; self.controller.online = True
        self.jobs = []; self.controller.task = self.jobs.append
        self.window = Window(); self.window.controller = self.controller
        self.controller.event.connect(self.window.on_event)
        self.controller.busy.connect(self.window.set_busy)
        self.controller.recovered.connect(self.window.restore_recovery)
        self.controller.page.connect(self.window.restore_page)
        self.window.show(); self.app.processEvents()

    def tearDown(self):
        self.controller.running = False; self.window.close()

    def frame(self, event):
        self.controller.frame({'method': 'session/event', 'payload': {'sessionId': 'reply-test', 'event': event}})

    def finish_jobs(self):
        while self.jobs: self.jobs.pop(0)()
        QTest.qWait(100)

    def assert_answer(self):
        self.assertEqual(self.window.messages.count(('Augmentor', TEXT)), 1)
        # Markdown soft line breaks become spaces; stored reply remains exact.
        self.assertIn(' '.join(TEXT.split()), ' '.join(self.window.transcript.toPlainText().split()))
        self.assertEqual(self.window.partial, '')

    def test_empty_live_final_recovers_saved_answer_without_resending(self):
        self.frame(USER); self.frame(CHUNK); QTest.qWait(70)
        # Markdown soft line breaks become spaces; stored reply remains exact.
        self.assertIn(' '.join(TEXT.split()), ' '.join(self.window.transcript.toPlainText().split()))
        self.frame({'seq': 3, 'type': 'assistant/message', 'data': {'message': {'content': []}}})
        self.frame(END); self.finish_jobs()
        self.assert_answer()
        self.assertEqual([name for name, _ in self.calls], ['session.history'])

    def test_output_limit_is_visible_without_an_assistant_answer(self):
        event={'seq':4,'type':'turn/end','data':{'reason':{'kind':'max-tokens'}}}
        self.window.on_event(USER)
        self.window.on_event(event)
        QTest.qWait(70)
        self.assertTrue(any(role=='Status' and 'output limit' in text for role,text in self.window.messages))
        self.assertIn('does not establish task completion',self.window.transcript.toPlainText())

    def test_incomplete_harness_notice_survives_completed_end_and_history_reload(self):
        text='Harness: Task incomplete. The model stopped without a public answer or tool action and the recovery limit was reached.'
        notice={'seq':3,'type':'command/done','data':{'kind':'error','text':text}}
        empty={'seq':2,'type':'assistant/message','data':{'message':{'content':[]}}}
        events=[USER,empty,notice,END]
        for event in events:self.window.on_event(event)
        for reopen in (False,True):
            if reopen:self.window.restore_history(events)
            QTest.qWait(70)
            self.assertIn(text,self.window.transcript.toPlainText())
            self.assertEqual(self.window.messages.count(('DSH',text)),1)
            self.assertFalse(any(role=='Augmentor' for role,_ in self.window.messages))

    def test_only_exact_routine_reasoning_notice_is_hidden_live_and_on_reopen(self):
        from copy import deepcopy
        routine='Harness: Saved reasoning: minimal; requested reasoning: xhigh (request policy). Backend enforcement is provider-dependent.'
        notices=[('success',routine), ('success',routine.replace('(request policy)','(bounded recovery)')),
                 ('success',routine.replace('minimal','low')), ('error',routine),
                 ('success','Goal paused'), ('success','Harness: This model step has run for 90 seconds without executing a new action.'),
                 ('success',routine+' Additional diagnostic.')]
        events=[{'seq':index+10,'type':'command/done','data':{'kind':kind,'text':text}}
                for index,(kind,text) in enumerate(notices)]
        original=deepcopy(events)
        for event in events:self.window.on_event(event)
        expected=[('DSH',text) for _,text in notices[1:]]
        for reopen in (False,True):
            if reopen:self.window.restore_history(events)
            QTest.qWait(70)
            self.assertEqual(self.window.messages,expected)
            self.assertEqual(self.window.messages.count(('DSH',routine)),1)  # Error remains visible.
            self.assertFalse(self.window.fold_event(events[0]))  # Duplicate stays hidden.
        self.assertEqual(events,original)  # Presentation only; history is not edited.

    def test_routine_notice_does_not_hide_user_or_assistant_text(self):
        text='Harness: Saved reasoning: minimal; requested reasoning: xhigh (request policy). Backend enforcement is provider-dependent.'
        self.window.on_event({'seq':10,'type':'user/message','data':{'source':{'kind':'user'},'content':[{'type':'text','text':text}]}})
        self.window.on_event({'seq':11,'type':'assistant/message','data':{'message':{'content':[{'type':'text','text':text}]}}})
        self.assertEqual(self.window.messages,[('You',text),('Augmentor',text)])

    def test_missing_live_final_is_committed_and_healthy_final_is_not_duplicated(self):
        for deliver_final in (False, True):
            with self.subTest(deliver_final=deliver_final):
                self.controller.loaded_events = []
                self.window.restore_history([])
                for event in [USER, CHUNK] + ([FINAL] if deliver_final else []) + [END]: self.frame(event)
                self.finish_jobs(); self.assert_answer()

    def test_pending_completion_does_not_restore_a_chat_after_new_chat(self):
        for event in [USER, CHUNK, END]: self.frame(event)
        self.assertTrue(self.jobs, 'Completion must request saved history')
        self.window.new_chat(); self.finish_jobs()
        self.assertEqual(self.window.messages, [])
        self.assertEqual(self.calls, [])

    def test_history_returning_after_new_chat_is_ignored(self):
        call = self.controller.client.call
        def during_read(*args):
            result = call(*args)
            self.window.new_chat()
            return result
        self.controller.client.call = during_read
        for event in [USER, CHUNK, END]: self.frame(event)
        self.finish_jobs()
        self.assertEqual(self.window.messages, [])
        self.assertEqual(self.controller.loaded_events, [])

    def test_completion_keeps_newer_stream_arriving_during_history_read(self):
        call = self.controller.client.call
        def during_read(*args):
            result = call(*args)
            self.frame({'seq': 5, 'type': 'turn/start', 'data': {}})
            self.frame({'seq': 6, 'type': 'assistant/chunk', 'data': {'chunk': {'type': 'text-delta', 'text': 'A newer reply'}}})
            return result
        self.controller.client.call = during_read
        for event in [USER, CHUNK, END]: self.frame(event)
        self.finish_jobs()
        self.assertEqual(self.window.messages.count(('Augmentor', TEXT)), 1)
        self.assertEqual(self.window.partial, 'A newer reply')
        self.assertIn('A newer reply', self.window.transcript.toPlainText())
        self.assertTrue(self.controller.running)

    def test_delayed_older_page_cannot_erase_a_completed_reply(self):
        self.frame(USER)
        bar = self.window.transcript.verticalScrollBar(); bar.setSliderDown(True)
        self.window.restore_page([USER], False, True)
        for event in [CHUNK, FINAL, END]: self.frame(event)
        self.finish_jobs()
        bar.setSliderDown(False); QTest.qWait(150)
        self.assert_answer()

    def test_long_reply_has_visible_layout_after_stream_completion_and_reopen(self):
        paragraph = 'A paragraph of earlier words.\n\n'
        final_text = 'Final answer line.\n' * 70
        context = []
        for seq, (role, text) in enumerate([
            ('assistant', paragraph * 20), ('user', 'A second question'),
            ('assistant', paragraph * 40), ('user', 'A final question'),
        ]):
            data = {'content': [{'type':'text', 'text':text}]}
            context.append({'seq':seq, 'type':role+'/message', 'data':
                {**data, 'source':{'kind':'user'}} if role=='user' else {'message':data}})
        final = {'seq':6, 'type':'assistant/message', 'data':{'message':{'content':[{'type':'text','text':final_text}]}}}
        w = self.window; w.resize(360, 420)
        w.restore_history(context)
        w.on_event({'seq':4, 'type':'assistant/chunk', 'data':{'chunk':{'type':'text-delta','text':'Final answer line.\n'}}})
        QTest.qWait(70)
        w.on_event({'seq':5, 'type':'assistant/chunk', 'data':{'chunk':{'type':'text-delta','text':'Final answer line.\n'*69}}})
        QTest.qWait(70)
        self.assertGreater(w.transcript.document().find('Final answer line.').block().layout().lineCount(), 0)
        w.on_event(final); w.set_busy(False); QTest.qWait(70)
        for reopen in (False, True):
            with self.subTest(reopen=reopen):
                if reopen:w.restore_history(context+[final]); QTest.qWait(70)
                doc = w.transcript.document(); block = doc.find('Final answer line.').block()
                self.assertGreater(block.layout().lineCount(), 0, 'Text exists but Qt gives the answer zero visible lines')
                self.assertGreater(doc.documentLayout().blockBoundingRect(block).height(), 0)
                w.jump_latest()
                # The final answer's copy icon must actually be in the viewport.
                cursor = doc.find('Final answer line.'); cursor.movePosition(cursor.MoveOperation.End)
                self.assertTrue(w.transcript.viewport().rect().intersects(w.transcript.cursorRect(cursor)))
