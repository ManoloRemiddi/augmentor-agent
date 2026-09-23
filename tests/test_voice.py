# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import tempfile
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QWidget
from augmentor_linux.controller import Controller
from augmentor_linux.voice import VoiceDialog


class VoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        patcher=patch('augmentor_linux.voice_input.EarlyVoiceInput._open',lambda self:None)
        patcher.start();self.addCleanup(patcher.stop)

    def test_prepare_preserves_model_and_creates_before_ticket_without_prompt(self):
        calls = []
        with tempfile.TemporaryDirectory() as directory:
            client = SimpleNamespace(harness='dsh', preset='augmentor-linux-product',
                workspace=lambda: Path(directory), validate_model=lambda selection: None,
                call=lambda method, payload: calls.append((method, payload)) or {},
                voice_ticket=lambda sid: calls.append(('ticket', sid)) or {'sessionId': sid})
            controller = Controller(client=client, harness='dsh')
            controller.online = True
            controller.subscribe = lambda sid: calls.append(('subscribe', sid))
            result = controller.prepare_voice({'provider': 'local', 'model': 'selected'})
            self.assertEqual([c[0] for c in calls], ['session.create', 'session.selectModel', 'subscribe', 'ticket'])
            self.assertEqual(calls[1][1]['model'], 'selected')
            self.assertEqual(result['sessionId'], controller.session)
            self.assertFalse(controller.navigating)

    def test_unknown_creation_failure_never_submits_or_requests_ticket(self):
        calls = []
        with tempfile.TemporaryDirectory() as directory:
            def unknown(method, payload):
                calls.append(method)
                raise RuntimeError('outcome unknown')
            client = SimpleNamespace(harness='dsh', workspace=lambda: Path(directory),
                validate_model=lambda _: None, call=unknown, voice_ticket=lambda _: self.fail('ticket requested'))
            c = Controller(client=client, harness='dsh');c.online = True
            with self.assertRaisesRegex(RuntimeError, 'unknown'):
                c.prepare_voice({'provider': 'p', 'model': 'm'})
            self.assertEqual(calls, ['session.create'])
            self.assertFalse(c.navigating)

    def test_local_interrupt_discards_pending_pcm_immediately(self):
        with patch.object(VoiceDialog, 'connect_voice', lambda self: None):
            parent=QWidget();parent.stop=lambda:None
            dialog = VoiceDialog(parent, {'sessionId': 's'})
            dialog.pending.extend(bytes(960));dialog.generation = 5
            dialog.interrupt()
            self.assertEqual(dialog.pending, b'')
            self.assertEqual(dialog.generation, -1)
            self.assertEqual(dialog.sender_queue.get_nowait(), {'type': 'interrupt'})
            dialog.close()

    def test_inline_panel_never_duplicates_committed_speech(self):
        from PySide6.QtWidgets import QDialog
        with patch.object(VoiceDialog,'connect_voice',lambda self:None):
            parent=QWidget();parent.stop=lambda:None
            panel=VoiceDialog(parent,{'sessionId':'s'})
            self.assertNotIsInstance(panel,QWidget);self.assertNotIsInstance(panel,QDialog)
            panel.observe({'type':'assistant/message','seq':7,'data':{'message':{'content':[{'type':'text','text':'Already streamed'}]}}})
            self.assertTrue(panel.sender_queue.empty())
            panel.handle({'type':'ready'});panel.handle({'type':'speaking'})
            self.assertEqual(panel.status_text,'Speaking…')
            panel.close()

    def test_settings_disable_disconnects_hides_and_persists(self):
        from augmentor_linux.window import Window
        calls=[]
        fake=SimpleNamespace(preferences=SimpleNamespace(values={},save=lambda:calls.append('saved')),
            voice_dialog=None,close_voice_panel=lambda:calls.append('closed'),update_controls=lambda:calls.append('controls'))
        Window.set_voice_enabled(fake,False)
        self.assertFalse(fake.preferences.values['resonant_voice'])
        self.assertEqual(calls,['saved','closed','controls'])
        fake.set_status=lambda message:calls.append(message)
        Window.open_voice(fake)
        self.assertIn('Enable Resonant Voice',calls[-1])

    def test_voice_toggle_controls_robot_visibility(self):
        from augmentor_linux.window import Window
        window=Window(preview=True)
        window.set_voice_enabled(False)
        self.assertTrue(window.voice_button.isHidden())
        window.set_voice_enabled(True)
        self.assertFalse(window.voice_button.isHidden())
        window.close()

    def test_exterior_halo_tracks_window_without_clipping(self):
        from augmentor_linux.activity import ActivityHalo
        from PySide6.QtCore import QPoint, QRect
        window=QWidget();window.resize(500,400)
        halo=ActivityHalo(window)
        self.assertTrue(halo.canvas.isWindow())
        for x,y in [(100,200),(500,600)]:
            window.move(x,y);halo.position_canvas()
            extra=halo.extent-halo.margin
            expected=QRect(window.mapToGlobal(QPoint(0,0)),window.size()).adjusted(-extra,-extra,extra,extra)
            self.assertEqual(halo.canvas.geometry(),expected)
            self.assertGreater(halo.canvas.width(),window.width())
        halo.canvas.close();window.close()

    def test_recoverable_error_leaves_microphone_usable(self):
        with patch.object(VoiceDialog,'connect_voice',lambda self:None):
            parent=QWidget();parent.stop=lambda:None
            panel=VoiceDialog(parent,{'sessionId':'s'})
            panel.handle({'type':'ready'})
            panel.handle({'type':'error','message':'Speech unavailable','recoverable':True})
            self.assertTrue(panel.can_record);panel.close()

    def make_voice_window(self):
        from augmentor_linux.window import Window
        window=Window(preview=True)
        window.controller=Controller(client=SimpleNamespace(harness='dsh'),harness='dsh')
        window.controller.online=True
        window.show();self.app.processEvents()
        voice=VoiceDialog(window,{'sessionId':'s'})
        voice.sd=SimpleNamespace(RawInputStream=lambda **kwargs:SimpleNamespace(start=lambda:None,stop=lambda:None,close=lambda:None))
        window.voice_dialog=voice
        voice.panel_closed.connect(window.close_voice_panel)
        voice.changed.connect(window.voice_state_changed)
        voice.recording_progress.connect(window.voice_button.set_recording_progress)
        voice.handle({'type':'ready'})
        return window,voice

    def test_first_hold_in_new_chat_survives_session_creation(self):
        from augmentor_linux.window import Window
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        with tempfile.TemporaryDirectory() as directory, patch.object(VoiceDialog,'connect_voice',lambda self:None):
            window=Window(preview=True);window.show();self.app.processEvents()
            client=SimpleNamespace(harness='dsh',preset='voice-test',workspace=lambda:Path(directory),
                validate_model=lambda selection:None,call=lambda *args:{},voice_ticket=lambda sid:{'sessionId':sid})
            controller=Controller(client=client,harness='dsh');controller.online=True
            controller.subscribe=lambda sid:None
            controller.session_info.connect(window.session_changed)
            window.controller=controller
            window.model_picker.currentData=lambda:{'provider':'test','model':'chosen'}
            pending=[];window.call_in_background=lambda work,ready:pending.append((work,ready))
            window.update_controls()
            try:
                QTest.mousePress(window.voice_button,Qt.MouseButton.LeftButton);QTest.qWait(300)
                work,ready=pending.pop();result=work();ready(result)
                self.assertFalse(controller.navigating)
                self.assertTrue(window.voice_button.isEnabled(),'Voice stayed disabled after creating the first session')
                self.assertTrue(window.send_button.isEnabled(),'Send stayed disabled after voice preparation')
                self.assertTrue(window.model_picker.isEnabled())
                self.assertTrue(window.voice_button.holding,'Session creation cancelled the original hold')
                voice=window.voice_dialog
                voice.sd=SimpleNamespace(RawInputStream=lambda **kw:SimpleNamespace(start=lambda:None,stop=lambda:None,close=lambda:None))
                voice.handle({'type':'ready'});self.app.processEvents()
                self.assertIsNotNone(voice.capture)
                QTest.mouseRelease(window.voice_button,Qt.MouseButton.LeftButton)
                self.assertTrue(voice.recognizing)
            finally:
                window.controller=None;window.close()

    def test_tap_silences_without_recording_or_resizing(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        with patch.object(VoiceDialog,'connect_voice',lambda self:None):
            window,voice=self.make_voice_window();size=window.size()
            voice.pending.extend(bytes(960))
            QTest.mouseClick(window.voice_button,Qt.MouseButton.LeftButton)
            self.assertEqual(voice.pending,b'');self.assertIsNone(voice.capture)
            self.assertEqual(window.size(),size)
            self.assertEqual(voice.sender_queue.get_nowait(),{'type':'interrupt'})
            self.assertTrue(voice.sender_queue.empty());window.close()

    def test_hold_records_release_sends_once(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        with patch.object(VoiceDialog,'connect_voice',lambda self:None):
            window,voice=self.make_voice_window()
            QTest.mousePress(window.voice_button,Qt.MouseButton.LeftButton)
            QTest.qWait(300)
            self.assertIsNotNone(voice.capture)
            self.assertEqual(window.voice_button.state,'listening')
            QTest.mouseRelease(window.voice_button,Qt.MouseButton.LeftButton)
            self.assertIsNone(voice.capture);self.assertTrue(voice.recognizing)
            packets=list(voice.sender_queue.queue)
            self.assertEqual(sum(p['type']=='begin' for p in packets),1)
            self.assertEqual(sum(p['type']=='end' for p in packets),1)
            window.close()

    def test_escape_discards_recording_without_stopping_task(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        with patch.object(VoiceDialog,'connect_voice',lambda self:None):
            window,voice=self.make_voice_window()
            QTest.mousePress(window.voice_button,Qt.MouseButton.LeftButton);QTest.qWait(300)
            window.escape()
            QTest.mouseRelease(window.voice_button,Qt.MouseButton.LeftButton)
            self.assertTrue(voice.closed);self.assertIsNone(window.voice_dialog)
            self.assertNotIn({'type':'end'},list(voice.sender_queue.queue));window.close()

    def test_readiness_after_release_never_opens_microphone(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        with patch.object(VoiceDialog,'connect_voice',lambda self:None):
            window,voice=self.make_voice_window()
            voice.connected=False;voice.set_status('Preparing','connecting')
            QTest.mousePress(window.voice_button,Qt.MouseButton.LeftButton);QTest.qWait(300)
            self.assertIsNone(voice.capture)
            QTest.mouseRelease(window.voice_button,Qt.MouseButton.LeftButton)
            voice.handle({'type':'ready'});self.app.processEvents()
            self.assertIsNone(voice.capture);window.close()

    def test_keyboard_hold_and_drag_out_cancellation(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt,QPoint
        with patch.object(VoiceDialog,'connect_voice',lambda self:None):
            window,voice=self.make_voice_window()
            window.voice_button.setFocus()
            QTest.keyPress(window.voice_button,Qt.Key.Key_Space);QTest.qWait(300)
            self.assertIsNotNone(voice.capture)
            QTest.keyRelease(window.voice_button,Qt.Key.Key_Space)
            self.assertTrue(voice.recognizing);window.close()
            window,voice=self.make_voice_window()
            QTest.mousePress(window.voice_button,Qt.MouseButton.LeftButton);QTest.qWait(300)
            QTest.mouseRelease(window.voice_button,Qt.MouseButton.LeftButton,pos=QPoint(-20,-20))
            self.assertTrue(voice.closed)
            self.assertNotIn({'type':'end'},list(voice.sender_queue.queue));window.close()

    def test_readiness_during_hold_starts_recording(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        with patch.object(VoiceDialog,'connect_voice',lambda self:None):
            window,voice=self.make_voice_window()
            voice.connected=False;voice.set_status('Preparing','connecting')
            QTest.mousePress(window.voice_button,Qt.MouseButton.LeftButton);QTest.qWait(300)
            voice.handle({'type':'ready'});self.app.processEvents()
            self.assertIsNotNone(voice.capture)
            QTest.mouseRelease(window.voice_button,Qt.MouseButton.LeftButton);window.close()

    def test_drag_away_discards_before_release(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt,QPointF,QEvent
        from PySide6.QtGui import QMouseEvent
        with patch.object(VoiceDialog,'connect_voice',lambda self:None):
            window,voice=self.make_voice_window()
            QTest.mousePress(window.voice_button,Qt.MouseButton.LeftButton);QTest.qWait(300)
            event=QMouseEvent(QEvent.Type.MouseMove,QPointF(-20,-20),QPointF(-20,-20),Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
            self.app.sendEvent(window.voice_button,event)
            self.assertTrue(voice.closed)
            self.assertNotIn({'type':'end'},list(voice.sender_queue.queue));window.close()

    def test_hide_cancels_capture_and_disconnect_errors_remain_visible(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        with patch.object(VoiceDialog,'connect_voice',lambda self:None):
            window,voice=self.make_voice_window()
            QTest.mousePress(window.voice_button,Qt.MouseButton.LeftButton);QTest.qWait(300)
            window.hide()
            self.assertTrue(voice.closed);self.assertIsNone(window.voice_dialog)
            self.assertNotIn({'type':'end'},list(voice.sender_queue.queue))
            voice.handle({'type':'error','message':'Voice connection lost'})
            self.assertEqual(voice.state,'error');self.assertFalse(voice.can_record)
            voice.handle({'type':'ready'});self.assertEqual(voice.state,'error');window.close()

    def test_slide_left_locks_release_keeps_recording_click_sends_once(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt,QPointF,QPoint,QEvent
        from PySide6.QtGui import QMouseEvent
        with patch.object(VoiceDialog,'connect_voice',lambda self:None):
            window,voice=self.make_voice_window();button=window.voice_button
            QTest.mousePress(button,Qt.MouseButton.LeftButton);QTest.qWait(300)
            event=QMouseEvent(QEvent.Type.MouseMove,QPointF(-25,14),QPointF(-25,14),Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
            self.app.sendEvent(button,event)
            self.assertTrue(button.locked)
            QTest.mouseRelease(button,Qt.MouseButton.LeftButton,pos=QPoint(-25,14))
            self.assertIsNotNone(voice.capture)
            self.assertNotIn({'type':'end'},list(voice.sender_queue.queue))
            QTest.mouseClick(button,Qt.MouseButton.LeftButton)
            self.assertIsNone(voice.capture);self.assertFalse(button.locked)
            self.assertEqual(list(voice.sender_queue.queue).count({'type':'end'}),1)
            window.close()

    def test_locked_recording_escape_cancels_without_submit(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        with patch.object(VoiceDialog,'connect_voice',lambda self:None):
            window,voice=self.make_voice_window()
            QTest.mousePress(window.voice_button,Qt.MouseButton.LeftButton);QTest.qWait(300)
            window.voice_button.lock_recording()
            QTest.mouseRelease(window.voice_button,Qt.MouseButton.LeftButton)
            window.escape()
            self.assertTrue(voice.closed);self.assertFalse(window.voice_button.locked)
            self.assertNotIn({'type':'end'},list(voice.sender_queue.queue));window.close()

    def test_microphone_waveform_is_audio_driven_and_time_warnings(self):
        from array import array
        with patch.object(VoiceDialog,'connect_voice',lambda self:None):
            window,voice=self.make_voice_window();voice.max_seconds=600;voice.begin()
            voice.microphone(bytes(640));voice.update_recording()
            self.assertEqual(window.voice_button.levels,[0.]*11)
            voice.microphone(array('h',[6000,-6000]*160).tobytes());voice.update_recording()
            self.assertGreater(max(window.voice_button.levels),0)
            voice.microphone(bytes(640));voice.update_recording()
            self.assertEqual(window.voice_button.levels,[0.]*11)
            button=window.voice_button
            button.set_recording_progress(479,600,[0.]*11);self.assertEqual(button.recording_colour().name(),'#52d68a')
            button.set_recording_progress(480,600,[0.]*11);self.assertEqual(button.recording_colour().name(),'#ffae42')
            button.set_recording_progress(540,600,[0.]*11);self.assertEqual(button.recording_colour().name(),'#ff5964')
            window.close()

    def test_limit_finishes_once_and_keeps_received_audio(self):
        with patch.object(VoiceDialog,'connect_voice',lambda self:None):
            window,voice=self.make_voice_window();voice.max_seconds=600;voice.begin()
            voice.recorded_bytes=600*32000-640
            voice.microphone(bytes(1280));self.app.processEvents()
            packets=list(voice.sender_queue.queue)
            self.assertEqual(sum(len(p) for p in packets if isinstance(p,bytes)),640)
            self.assertEqual(packets.count({'type':'end'}),1)
            self.assertTrue(voice.recognizing);self.assertIsNone(voice.capture)
            voice.handle({'type':'recording-ended','reason':'limit'})
            self.assertEqual(list(voice.sender_queue.queue).count({'type':'end'}),1)
            self.assertFalse(window.voice_button.locked);window.close()

    def test_server_limit_stops_mic_without_duplicate_end(self):
        with patch.object(VoiceDialog,'connect_voice',lambda self:None):
            window,voice=self.make_voice_window();voice.begin()
            voice.handle({'type':'recording-ended','reason':'limit'})
            self.assertTrue(voice.recognizing);self.assertIsNone(voice.capture)
            self.assertNotIn({'type':'end'},list(voice.sender_queue.queue));window.close()

    def test_theme_and_reduced_motion(self):
        from augmentor_linux.window import Window
        from PySide6.QtCore import QEvent
        window=Window(preview=True);window.show();self.app.processEvents()
        window.apply_appearance({'accent_hue':32,'animation':True})
        self.assertEqual(window.voice_button.accent,window.accent)
        window.voice_button.hovered=True;window.voice_button.sync_motion()
        self.assertTrue(window.voice_button.motion.isActive())
        window.apply_appearance({'animation':False})
        self.assertFalse(window.voice_button.motion.isActive());window.close()

    def test_empty_chat_retains_explicit_model_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'session.json'
            selection={'provider':'local','model':'chosen'}
            path.write_text(json.dumps({'endpoint':'http://127.0.0.1:3080','session':None,'selection':selection}))
            client=SimpleNamespace(harness='dsh',base='http://127.0.0.1:3080',state_path=lambda:path)
            with patch('augmentor_linux.adapters.dsh.DshAdapter',return_value=client):
                controller=Controller(harness='dsh')
                self.assertEqual(controller.selection,selection)
                self.assertIsNone(controller.session)


    def test_right_drag_latches_hands_free_before_or_after_hold_and_release_does_not_send(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt,QPointF,QPoint,QEvent
        from PySide6.QtGui import QMouseEvent
        for wait in (0,300):
            with self.subTest(wait=wait),patch.object(VoiceDialog,'connect_voice',lambda self:None):
                window,voice=self.make_voice_window();button=window.voice_button
                starts=[]
                def open_hands_free():
                    starts.append(window.voice_is_hands_free());window.voice_opening=True
                    button.set_state('connecting')
                window.open_voice=open_hands_free
                QTest.mousePress(button,Qt.MouseButton.LeftButton);QTest.qWait(wait)
                event=QMouseEvent(QEvent.Type.MouseMove,QPointF(42,14),QPointF(42,14),Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
                self.app.sendEvent(button,event)
                self.assertEqual(starts,[True]);self.assertTrue(voice.closed)
                self.assertTrue(button.hands_free);self.assertTrue(window.voice_opening)
                QTest.mouseRelease(button,Qt.MouseButton.LeftButton,pos=QPoint(42,14))
                self.assertTrue(window.voice_opening)
                self.assertNotIn({'type':'end'},list(voice.sender_queue.queue))
                self.assertEqual(window.preferences.values['voice_mode'],'manual')
                QTest.mouseClick(button,Qt.MouseButton.LeftButton)
                self.assertFalse(window.voice_opening);self.assertFalse(button.hands_free)
                self.assertFalse(window.voice_is_hands_free());window.close()

    def test_right_drag_reuses_pending_voice_preparation(self):
        from augmentor_linux.window import Window
        window=Window(preview=True)
        window.controller=Controller(client=SimpleNamespace(harness='dsh'),harness='dsh')
        window.controller.online=True
        window.voice_opening=True;epoch=window.voice_epoch
        window.start_gesture_hands_free()
        self.assertEqual(window.voice_epoch,epoch)
        self.assertTrue(window.voice_is_hands_free())
        window.escape();self.assertFalse(window.voice_opening);self.assertFalse(window.voice_is_hands_free())
        window.close()

    def test_hands_free_colour_tracks_theme_and_preserves_recording_warnings(self):
        from augmentor_linux.voice_button import VoiceButton
        from PySide6.QtGui import QColor
        button=VoiceButton();button.hands_free=True
        for accent in ['#45bc80','#b79de5','#4f87e6']:
            button.configure(accent);button.set_state('listening')
            self.assertEqual(button.recording_colour().name(),'#ffae42')
            button.recording_available=True
            colour=button.recording_colour()
            self.assertNotEqual(colour,QColor(accent))
            self.assertEqual(colour.name(),'#52d68a')
            button.set_state('thinking');self.assertEqual(button.recording_colour(),colour)
            button.set_state('off');self.assertEqual(button.recording_colour(),QColor(accent));button.recording_available=False
        button.set_state('listening');button.set_recording_progress(480,600,[0.]*11)
        self.assertEqual(button.recording_colour().name(),'#ffae42')
        button.set_recording_progress(540,600,[0.]*11)
        self.assertEqual(button.recording_colour().name(),'#ff5964');button.close()

    def test_icon_tracks_drag_then_snaps_back_without_moving_layout(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt,QPointF,QEvent
        from PySide6.QtGui import QMouseEvent
        with patch.object(VoiceDialog,'connect_voice',lambda self:None):
            window,voice=self.make_voice_window();button=window.voice_button;origin=button.pos();window_size=window.size()
            QTest.mousePress(button,Qt.MouseButton.LeftButton);QTest.qWait(260)
            event=QMouseEvent(QEvent.Type.MouseMove,QPointF(2,14),QPointF(2,14),Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
            self.app.sendEvent(button,event)
            self.assertLess(button.x(),origin.x());self.assertFalse(button.locked)
            button.lock_recording();QTest.qWait(200)
            self.assertEqual(button.pos(),origin);self.assertEqual(window.size(),window_size)
            self.assertTrue(button.locked);window.close()

    def test_saved_hands_free_mode_buffers_before_pending_ticket_finishes(self):
        from augmentor_linux.window import Window
        window=Window(preview=True)
        window.controller=Controller(client=SimpleNamespace(harness='dsh'),harness='dsh')
        window.controller.online=True
        window.preferences.values['voice_mode']='hands-free'
        pending=[];window.call_in_background=lambda work,ready:pending.append((work,ready))
        window.open_voice();source=window.voice_input
        self.assertTrue(window.voice_opening);self.assertEqual(len(pending),1)
        source._frame(bytes(1024),512,None,None);self.app.processEvents()
        self.assertTrue(window.voice_button.recording_available);self.assertEqual(len(source.frames),1)
        window.escape();self.assertTrue(source.closed);self.assertFalse(source.frames)
        window.close()

    def test_early_capture_is_cancelled_if_window_closes_before_ticket(self):
        from augmentor_linux.window import Window
        window=Window(preview=True);window.voice_opening=True;window.prepare_voice_input();capture=window.voice_input
        capture._frame(bytes(1024),512,None,None)
        window.close();self.app.processEvents()
        self.assertTrue(capture.closed);self.assertFalse(capture.frames);self.assertIsNone(window.voice_input)


if __name__ == '__main__':
    unittest.main()
