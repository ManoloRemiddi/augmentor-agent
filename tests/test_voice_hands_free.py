# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QWidget
from augmentor_linux.voice import VoiceSession
from augmentor_linux.voice_vad import EndpointDetector

FRAME = bytes(1024)


class EndpointTests(unittest.TestCase):
    def test_silence_and_transients_never_open_utterance(self):
        detector=EndpointDetector()
        for _ in range(100):self.assertEqual(detector.feed(FRAME,0),[])
        for _ in range(3):self.assertEqual(detector.feed(FRAME,.99),[])
        self.assertEqual(detector.feed(FRAME,0),[])
        self.assertFalse(detector.active)

    def test_preroll_hysteresis_and_pause_keep_one_utterance(self):
        detector=EndpointDetector(800)
        for i in range(6):detector.feed(bytes([i])*1024,0)
        for i in range(3):detector.feed(bytes([6+i])*1024,.9)
        events=detector.feed(bytes([9])*1024,.9)
        self.assertEqual(events[0],('start',None))
        self.assertEqual(events[1][1],b''.join(bytes([i])*1024 for i in range(10)))
        for _ in range(24):self.assertNotIn('end',[e[0] for e in detector.feed(FRAME,.1)])
        detector.feed(FRAME,.5)  # Uncertain voiced tail resets the silence timer.
        for _ in range(24):self.assertNotIn('end',[e[0] for e in detector.feed(FRAME,.1)])
        self.assertEqual(detector.feed(FRAME,.1)[-1],('end','silence'))
        self.assertFalse(detector.active)

    def test_barge_in_confirmation_longer_than_near_end_and_limit_segments(self):
        detector=EndpointDetector(maximum=.448)
        for _ in range(9):self.assertEqual(detector.feed(FRAME,.9,speaking=True),[])
        self.assertEqual(detector.feed(FRAME,.9,speaking=True)[0],('start',None))
        for _ in range(3):detector.feed(FRAME,.9)
        self.assertEqual(detector.feed(FRAME,.9)[-1],('end','limit'))
        self.assertFalse(detector.active)


class HandsFreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        patcher=patch('augmentor_linux.voice_input.EarlyVoiceInput._open',lambda self:None)
        patcher.start();self.addCleanup(patcher.stop)

    def make_voice(self):
        parent=QWidget();parent.preferences=SimpleNamespace(values={'voice_mode':'hands-free'})
        with patch.object(VoiceSession,'connect_voice',lambda self:None):voice=VoiceSession(parent,{'sessionId':'s'})
        voice.connected=True
        self.addCleanup(lambda parent=parent,voice=voice:voice.close())
        return parent,voice

    def event(self,voice,kind,value=None,epoch=None):
        voice.handle({'type':'vad-'+kind,'epoch':voice.vad_epoch if epoch is None else epoch,'value':value})

    def test_onset_mutes_before_begin_and_endpoint_does_not_close_capture(self):
        parent,voice=self.make_voice()
        calls=[];voice.capture=SimpleNamespace(close=lambda:calls.append('close'))
        voice.pending.extend(FRAME);voice.generation=5
        self.event(voice,'start');self.event(voice,'pcm',FRAME);self.event(voice,'end','silence')
        self.assertEqual(voice.pending,b'')
        self.assertEqual(list(voice.sender_queue.queue),[{'type':'interrupt'},{'type':'begin'},FRAME,{'type':'end'}])
        self.assertTrue(voice.recognizing);self.assertEqual(calls,[])
        self.event(voice,'end','silence')
        self.assertEqual(list(voice.sender_queue.queue).count({'type':'end'}),1)

    def test_ten_minute_byte_cap_finalizes_once_without_closing_continuous_mic(self):
        parent,voice=self.make_voice()
        calls=[];voice.capture=SimpleNamespace(close=lambda:calls.append('closed'))
        self.event(voice,'start')
        voice.max_seconds=600;voice.recorded_bytes=600*32000-512
        voice.microphone(bytes(1024));self.app.processEvents()
        self.assertFalse(voice.accepting_audio);self.assertFalse(voice.utterance_open)
        self.assertTrue(voice.recognizing);self.assertEqual(voice.state,'recognizing')
        self.assertIsNotNone(voice.capture);self.assertEqual(calls,[])
        packets=list(voice.sender_queue.queue)
        self.assertEqual(sum(len(p) for p in packets if isinstance(p,bytes)),512)
        self.assertEqual(packets.count({'type':'end'}),1)
        voice.finish_at_limit()
        voice.handle({'type':'recording-ended','reason':'limit'})
        self.event(voice,'end','limit')
        self.assertEqual(list(voice.sender_queue.queue).count({'type':'end'}),1)
        voice.handle({'type':'transcript','requestId':'capped','sessionId':'s','text':'Long message'})
        self.assertTrue(voice.vad_enabled.is_set());self.assertFalse(voice.closed)

    def test_explicit_main_stop_closes_audio_before_stopping_driver(self):
        from augmentor_linux.window import Window
        calls=[]
        window=SimpleNamespace(voice_dialog=SimpleNamespace(close=lambda:calls.append('voice-close')),
                               controller=SimpleNamespace(stop=lambda:calls.append('driver-stop')))
        Window.stop(window)
        self.assertEqual(calls,['voice-close','driver-stop'])

    def test_old_interrupted_turn_cannot_clear_new_capture_or_reply(self):
        parent,voice=self.make_voice()
        self.event(voice,'start');self.event(voice,'pcm',FRAME)
        voice.generation=4;voice.sender_queue.queue.clear()
        old={'type':'turn/end','data':{'reason':{'kind':'interrupted'}}}
        voice.observe(old)
        self.assertTrue(voice.accepting_audio);self.assertEqual(voice.generation,4)
        self.assertTrue(voice.sender_queue.empty())
        self.event(voice,'end','silence')
        voice.handle({'type':'transcript','requestId':'new','sessionId':'s','text':'New request'})
        voice.generation=5;voice.pending.extend(FRAME);voice.sender_queue.queue.clear()
        voice.observe(old)
        self.assertEqual(voice.generation,5);self.assertEqual(voice.pending,FRAME)
        self.assertTrue(voice.sender_queue.empty())

    def test_asr_completion_rearms_without_replaying_old_microphone_frames(self):
        parent,voice=self.make_voice();voice.recognizing=True
        voice.handle({'type':'transcript','requestId':'one','sessionId':'s','text':'Hello'})
        self.assertTrue(voice.vad_enabled.is_set());self.assertEqual(voice.vad_epoch,1)
        self.event(voice,'start',epoch=0)
        self.assertTrue(voice.sender_queue.empty())
        voice.handle({'type':'transcript','requestId':'one','sessionId':'s','text':'Hello'})
        self.assertEqual(voice.vad_epoch,1)

    def test_terminal_and_audible_drain_are_both_required(self):
        parent,voice=self.make_voice();voice.state='speaking';voice.generation=3;voice.speech_idle=True
        voice.turn_complete=False;voice.update_playback_status()
        self.assertEqual(voice.state,'speaking')
        voice.handle({'type':'turn-complete','generation':2});self.assertFalse(voice.turn_complete)
        voice.handle({'type':'turn-complete','generation':3});voice.audible_until=time.monotonic()+1
        voice.update_playback_status();self.assertEqual(voice.state,'speaking')
        voice.audible_until=0;voice.update_playback_status()
        self.assertEqual(voice.state,'listening')
        self.assertEqual(voice.sender_queue.get_nowait(),{'type':'playback-drained','generation':3})
        voice.update_playback_status();self.assertTrue(voice.sender_queue.empty())

    def test_dac_timestamp_holds_ready_until_device_has_played(self):
        parent,voice=self.make_voice();voice.pending.extend(bytes(960))
        voice.playback_event({'type':'speech-idle','generation':voice.generation})
        voice.playback(bytearray(960),480,SimpleNamespace(outputBufferDacTime=10.2,currentTime=10),None)
        self.assertGreater(voice.audible_until,time.monotonic()+.2)

    def test_playback_markers_preserve_wire_order_and_short_final_audio(self):
        parent,voice=self.make_voice();voice.generation=3
        voice.playback_event({'type':'speaking','generation':3})
        voice.pending.extend(b'\x01\x02'*100)
        out=bytearray(960);voice.playback(out,480,SimpleNamespace(),None)
        self.assertEqual(out,bytes(960));self.assertEqual(len(voice.pending),200)
        voice.playback_event({'type':'speech-idle','generation':2})
        self.assertFalse(voice.playback_buffer.complete)
        voice.playback_event({'type':'speech-idle','generation':3})
        voice.playback(out,480,SimpleNamespace(),None)
        self.assertEqual(out[:200],b'\x01\x02'*100)
        voice.pending.extend(FRAME)
        voice.playback_event({'type':'clear','generation':4})
        self.assertEqual(voice.pending,b'');self.assertEqual(voice.generation,4)
        self.assertFalse(voice.playback_buffer.started)

    def test_diagnostics_keep_first_pcm_timing_and_reset_on_interruption(self):
        parent,voice=self.make_voice();voice.generation=3
        voice.handle({'type':'timing','stage':'asr-final','elapsedMs':650.1})
        voice.handle({'type':'timing','stage':'first-pcm','generation':2,'elapsedMs':900})
        self.assertNotIn('firstPcmMs',voice.timings)
        for value in (1200,2400):voice.handle({'type':'timing','stage':'first-pcm','generation':3,'elapsedMs':value})
        self.assertEqual(voice.timings,{'asrMs':650.1,'firstPcmMs':1200})
        voice.handle({'type':'timing','stage':'asr-final','elapsedMs':float('nan')})
        self.assertEqual(voice.timings['asrMs'],650.1)
        voice.interrupt();self.assertEqual(voice.timings,{})

    def test_fault_and_stop_disable_detection_without_submitting(self):
        parent,voice=self.make_voice();voice.vad_enabled.set()
        self.event(voice,'start')
        voice.handle({'type':'error','message':'device failed'})
        self.assertTrue(voice.closed);self.assertFalse(voice.vad_enabled.is_set())
        self.assertNotIn({'type':'end'},list(voice.sender_queue.queue))

    def test_tap_toggle_and_escape_preserve_manual_mode(self):
        from augmentor_linux.window import Window
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        window=Window(preview=True);window.preferences.values['voice_mode']='hands-free';window.update_controls()
        calls=[];window.open_voice=lambda:calls.append('open');window.show();self.app.processEvents();window.voice_button.setEnabled(True)
        QTest.mouseClick(window.voice_button,Qt.MouseButton.LeftButton)
        self.assertEqual(calls,['open']);self.assertFalse(window.voice_button.hold_elapsed)
        window.voice_opening=True;window.escape();self.assertFalse(window.voice_opening)
        window.close()

    def test_startup_audio_is_retained_before_recognizer_ready(self):
        import threading
        parent,voice=self.make_voice();voice.connected=False
        voice.capture=SimpleNamespace(close=lambda:None)
        voice.vad=SimpleNamespace(reset=lambda:None)
        class Detector:
            def reset(self):pass
            def __call__(self,pcm):return .9 if pcm[0] else 0.
        voice.vad=Detector();voice.vad_enabled.set()
        worker=threading.Thread(target=voice.vad_loop,daemon=True);worker.start()
        # A full spoken opening plus endpoint silence arrives during cold load.
        speech=[bytes([i%120+1])*1024 for i in range(160)]
        for pcm in speech+[FRAME]*25:voice.hands_free_microphone(pcm,512,None,None)
        self.app.processEvents();time.sleep(.02)
        self.assertTrue(voice.recording_available)
        self.assertEqual(voice.sender_queue.qsize(),0,'No begin reaches an unready recognizer')
        voice.connected=True;voice.recognizer_ready.set()
        end=time.monotonic()+2
        while not voice.recognizing and time.monotonic()<end:
            self.app.processEvents();time.sleep(.002)
        self.assertTrue(voice.recognizing)
        messages=list(voice.sender_queue.queue)
        audio=b''.join(m for m in messages if isinstance(m,bytes))
        self.assertEqual(audio,b''.join(speech+[FRAME]*25))
        self.assertEqual(messages.count({'type':'begin'}),1)
        self.assertEqual(messages.count({'type':'end'}),1)
        self.assertTrue(voice.recording_available)
        voice.close();worker.join(timeout=1)

    def test_green_requires_device_frames_and_asr_buffering_stays_available(self):
        parent,voice=self.make_voice();voice.vad_enabled.set()
        self.assertFalse(voice.recording_available)
        voice.hands_free_microphone(FRAME,512,None,None);self.app.processEvents()
        self.assertTrue(voice.recording_available)
        voice.recognizing=True;self.assertTrue(voice.recording_available)
        voice.recognizing=False;voice.vad_enabled.clear();self.assertFalse(voice.recording_available)
        voice.resume_detection();self.assertTrue(voice.recording_available)
        voice.capture=SimpleNamespace(close=lambda:None);voice.last_mic_at=time.monotonic()-1
        voice.update_recording();self.assertFalse(voice.recording_available)
        voice.hands_free_microphone(FRAME,512,None,None);self.assertTrue(voice.recording_available)
        voice.close();self.assertFalse(voice.recording_available);self.assertEqual(voice.vad_queue.qsize(),0)

    def test_startup_buffer_overflow_fails_without_submitting_tail(self):
        parent,voice=self.make_voice();voice.connected=False;voice.vad_enabled.set()
        for _ in range(321):voice.hands_free_microphone(FRAME,512,None,None)
        self.app.processEvents()
        self.assertTrue(voice.closed)
        self.assertEqual(voice.vad_queue.qsize(),0)
        self.assertNotIn({'type':'begin'},list(voice.sender_queue.queue))
        self.assertFalse(voice.recording_available)

    def test_speech_during_asr_is_buffered_and_preserved_on_resume(self):
        import threading
        parent,voice=self.make_voice();voice.recognizing=True;voice.recognizer_ready.set()
        class Detector:
            def reset(self):pass
            def __call__(self,pcm):return .9 if pcm[0] else 0.
        voice.vad=Detector()
        worker=threading.Thread(target=voice.vad_loop,daemon=True);worker.start()
        speech=[bytes([i+1])*1024 for i in range(35)]
        for pcm in speech+[FRAME]*25:voice.hands_free_microphone(pcm,512,None,None)
        time.sleep(.03);self.app.processEvents()
        self.assertEqual(voice.vad_queue.qsize(),60)
        self.assertEqual(voice.sender_queue.qsize(),0)
        voice.recognizing=False;voice.resume_detection()
        end=time.monotonic()+2
        while not voice.recognizing and time.monotonic()<end:
            self.app.processEvents();time.sleep(.002)
        packets=list(voice.sender_queue.queue)
        self.assertEqual(b''.join(p for p in packets if isinstance(p,bytes)),b''.join(speech+[FRAME]*25))
        self.assertEqual(packets.count({'type':'begin'}),1)
        self.assertEqual(packets.count({'type':'end'}),1)
        voice.close();worker.join(timeout=1)

    def test_partial_recognition_is_progress_and_never_submitted(self):
        parent,voice=self.make_voice();voice.accepting_audio=True
        submitted=[];voice.transcript.connect(submitted.append)
        voice.handle({'type':'listening','requestId':'current'})
        voice.handle({'type':'transcript-partial','requestId':'current','sessionId':voice.session_id,'text':'provisional words'})
        self.assertEqual(submitted,[]);self.assertEqual(voice.state,'listening')
        self.assertIn('Transcribing as you speak',voice.status_text)
        voice.handle({'type':'timing','stage':'asr-progress','passes':3,'decodedThroughSeconds':6,'decodeMs':120})
        self.assertEqual(voice.timings['asrPasses'],3)
        self.assertEqual(voice.timings['asrProcessedSeconds'],6)
        voice.end();voice.set_status('Transcribing…','recognizing')
        voice.handle({'type':'transcript-partial','requestId':'stale','sessionId':voice.session_id,'text':'late'})
        self.assertEqual(voice.state,'recognizing');self.assertEqual(submitted,[])
        voice.close()


if __name__=='__main__':unittest.main()
