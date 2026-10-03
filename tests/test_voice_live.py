# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Synthetic Live transport/audio proofs. These do not contact OpenAI."""
import base64
import json
import os
import queue
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication
from augmentor_linux.voice_live import LiveVoiceSession
from augmentor_linux.voice_settings import VoiceSettingsDialog, CloudVoiceSettingsDialog
from augmentor_linux.window import Window


class Socket:
    def __init__(self):
        self.events=queue.Queue();self.sent=[];self.closed=False
        self.events.put(json.dumps({'type':'session.started','session':{'id':'synthetic'}}))
    def recv(self):return self.events.get(timeout=5)
    def send(self,raw):
        value=json.loads(raw);self.sent.append(value)
        if value['type']=='session.close':self.events.put(json.dumps({'type':'session.closed','usage':{'seconds':12}}))
        if value['type']=='session.commentary.append':self.events.put(json.dumps({'type':'session.commentary.appended','client_event_id':value['event_id']}))
    def settimeout(self,_):pass
    def close(self):self.closed=True;self.events.put('')


class Stream:
    def __init__(self,**options):self.options=options;self.closed=False;self.started=False
    def start(self):self.started=True
    def stop(self):self.started=False
    def close(self):self.closed=True


class LiveAudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.env=patch.dict(os.environ,{'AUGMENTOR_PI_CONFIG':self.directory.name,'AUGMENTOR_WINDOW_ID':'main'})
        self.env.start();self.addCleanup(self.env.stop)
        self.socket=Socket();self.inputs=[];self.outputs=[]
        def stream(rows,**options):
            value=Stream(**options);rows.append(value);return value
        audio=SimpleNamespace(RawInputStream=lambda **kw:stream(self.inputs,**kw),RawOutputStream=lambda **kw:stream(self.outputs,**kw))
        for patcher in [patch.dict('sys.modules',{'sounddevice':audio}),
                        patch('augmentor_linux.voice_live.cloud_key',return_value='synthetic-key'),
                        patch('augmentor_linux.voice_live.load_config',return_value={'cloudVoice':'marin'}),
                        patch('websocket.create_connection',return_value=self.socket)]:
            patcher.start();self.addCleanup(patcher.stop)
        self.parent=QObject();self.parent.preferences=SimpleNamespace(values={'voice_pause_ms':400})
        self.voice=LiveVoiceSession(self.parent,{'protocol':'augmentor-live/1','sessionId':'existing'})
        self.addCleanup(self.voice.close)
        self.until(lambda:self.voice.connected)

    def until(self,condition):
        deadline=time.monotonic()+3
        while not condition() and time.monotonic()<deadline:
            self.app.processEvents();time.sleep(.01)
        self.assertTrue(condition())

    def test_connection_uses_existing_session_and_no_local_speech_models(self):
        self.assertEqual(self.voice.session_id,'existing')
        config=self.socket.sent[0]['session']
        self.assertEqual(config['delegation'],{'type':'client'});self.assertEqual(config['audio']['format']['rate'],24000)
        self.assertFalse(hasattr(self.voice,'vad'));self.assertEqual(self.inputs,[])
        self.voice.begin();self.assertEqual(self.inputs[0].options['samplerate'],24000)
        pcm=b'\x00\x00'*480;self.voice.microphone(pcm)
        self.until(lambda:any(e['type']=='session.input_audio.append' for e in self.socket.sent))
        event=next(e for e in self.socket.sent if e['type']=='session.input_audio.append')
        self.assertEqual(base64.b64decode(event['audio']),pcm)

    def test_unverified_audio_is_silent_then_matching_model_result_opens_playback(self):
        self.socket.events.put(json.dumps({'type':'session.output_audio.delta','delta':base64.b64encode(b'\x01\x00'*480).decode()}))
        self.app.processEvents();time.sleep(.02);self.assertEqual(self.voice.pending,bytearray())
        submissions=[];self.voice.transcript.connect(submissions.append)
        self.voice.begin();self.voice.end()
        self.socket.events.put(json.dumps({'type':'session.input_transcript.delta','event_id':'input','delta':'Check order','end_ms':100}))
        self.until(lambda:len(submissions)==1)
        identifier=submissions[0]['requestId']
        self.voice.submission_result({'id':'augmentor-voice:'+identifier,'accepted':True,'turnId':'turn-1'})
        self.voice.observe({'type':'assistant/message','turnId':'turn-1','data':{'message':{'content':[{'type':'text','text':'The order shipped.'}]}}})
        self.voice.observe({'type':'turn/end','turnId':'turn-1','data':{'reason':{'kind':'completed'}}})
        self.until(lambda:self.voice.dialogue.output_allowed)
        pcm=b'\x01\x00'*480
        self.socket.events.put(json.dumps({'type':'session.output_audio.delta','delta':base64.b64encode(pcm).decode()}))
        self.until(lambda:bool(self.voice.pending))
        self.assertEqual(bytes(self.voice.pending),pcm)
        self.voice.interrupt();self.assertEqual(self.voice.pending,bytearray())

    def test_back_to_back_commentary_ack_and_audio_keep_the_first_pcm(self):
        pcm=b'\x01\x00'*480
        self.voice.dialogue.awaiting_output.add('confirmed-result')
        self.socket.events.put(json.dumps({'type':'session.commentary.appended','client_event_id':'confirmed-result'}))
        self.socket.events.put(json.dumps({'type':'session.output_audio.delta','delta':base64.b64encode(pcm).decode()}))
        time.sleep(.03)  # Receiver can queue both before Qt processes either.
        self.until(lambda:bool(self.voice.pending))
        self.assertEqual(bytes(self.voice.pending),pcm)

    def test_close_releases_audio_and_confirms_final_duration(self):
        self.voice.begin();self.voice.close()
        self.assertTrue(self.inputs[0].closed);self.assertTrue(self.outputs[0].closed)
        self.assertTrue(self.socket.closed);self.assertTrue(self.voice.finalized.is_set())
        self.assertEqual(self.voice.usage_seconds,12)
        from augmentor_linux.voice_provider import config_path
        receipt=config_path().with_name('voice-usage.json')
        self.assertEqual(json.loads(receipt.read_text()),{'seconds':12,'confirmed':True})

    def test_missing_final_receipt_is_preserved_as_unconfirmed_without_replay(self):
        self.voice.dialogue.seconds=7
        self.socket.send=lambda raw:self.socket.sent.append(json.loads(raw))
        with patch.object(self.voice.finalized,'wait',return_value=False):self.voice.close()
        from augmentor_linux.voice_provider import usage_receipt
        self.assertEqual(usage_receipt(),{'seconds':7,'confirmed':False})
        self.assertIn('unconfirmed',self.voice.status_text)
        self.assertTrue(self.outputs[0].closed)
        self.assertEqual(sum(event['type']=='session.close' for event in self.socket.sent),1)

    def test_audio_close_failure_cannot_strand_the_billed_session(self):
        with patch.object(self.outputs[0],'close',side_effect=OSError('Device lost')):self.voice.close()
        self.assertTrue(self.voice.closed);self.assertTrue(self.socket.closed)
        self.assertTrue(self.voice.finalized.is_set());self.assertIsNone(self.voice.output)

    def test_idle_session_closes_while_backend_execution_is_independent(self):
        self.voice.last_activity-=61;self.voice.tick_live()
        self.assertTrue(self.voice.closed);self.assertTrue(self.voice.finalized.is_set())
        self.assertFalse(any(e['type'].startswith('response.') for e in self.socket.sent))


class ProviderUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_hub_and_red_actionable_icon_without_local_models(self):
        window=Window(preview=True)
        status={'provider':'local','configured':False}
        with patch.object(VoiceSettingsDialog,'work',lambda self,work,callback:callback((status,None))):
            dialog=VoiceSettingsDialog(window)
            self.assertEqual(dialog.provider.count(),2)
            self.assertIn('needs setup',dialog.note.text())
            dialog.enabled.setChecked(False);self.assertTrue(dialog.local.isHidden());self.assertTrue(dialog.cloud.isHidden())
            dialog.enabled.setChecked(True);self.assertFalse(dialog.local.isHidden());self.assertFalse(dialog.cloud.isHidden())
            window.preferences.persistent=True;window.update_controls()
            self.assertEqual(window.voice_button.state,'needs-setup');self.assertTrue(window.voice_button.isEnabled())
            self.assertEqual(window.voice_button.recording_colour().name(),'#ff5964')
            self.assertIn('needs setup',window.voice_button.accessibleName())
            window.preferences.persistent=False;dialog.close();window.close()

    def test_cloud_setup_masks_key_and_clears_it_when_closed(self):
        from PySide6.QtWidgets import QLineEdit
        window=Window(preview=True);dialog=CloudVoiceSettingsDialog(window)
        self.assertEqual(dialog.key.echoMode(),QLineEdit.EchoMode.Password)
        dialog.key.setText('synthetic-key');dialog.close();self.assertEqual(dialog.key.text(),'')
        window.close()


if __name__=='__main__':unittest.main()
