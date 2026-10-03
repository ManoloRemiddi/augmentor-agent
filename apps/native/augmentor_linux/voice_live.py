# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""GPT-Live audio adapter for the existing native/browser conversation controller."""
import base64
import json
import math
import queue
import sys
import threading
import time
from array import array
from PySide6.QtCore import QTimer
from .voice import VoiceSession
from .voice_provider import LIVE_URL, cloud_key, load_config
from .live_dialogue import LiveDialogue, INSTRUCTIONS


class LiveVoiceSession(VoiceSession):
    @property
    def recording_available(self):
        return not self.closed and self.microphone_receiving and self.accepting_audio

    def __init__(self, parent, ticket, hands_free=None, early_input=None):
        self.audio_frames = queue.Queue(maxsize=64)
        self.finalized = threading.Event()
        self.transport_finished = threading.Event()
        self.write_lock = threading.Lock()
        self.last_activity = time.monotonic()
        self.started_at = self.last_activity
        self.last_audio = 0.
        self.last_voice = 0.
        self.usage_seconds = None
        self.live_started = False
        self.dialogue = None
        super().__init__(parent, ticket, hands_free=hands_free, early_input=None)
        self.sender_queue = queue.Queue(maxsize=1024)
        self.dialogue = LiveDialogue(self.submit_transcript, self.control, self.clear_playback,
                                    self.pause_ms, self.hands_free)
        self.live_timer = QTimer(self)
        self.live_timer.setInterval(100)
        self.live_timer.timeout.connect(self.tick_live)
        self.live_timer.start()

    def send_live(self, value):
        if not self.write_lock.acquire(timeout=1):raise RuntimeError('Voice transport is backpressured')
        try:self.ws.send(json.dumps(value))
        finally:self.write_lock.release()

    def control(self, value):
        if self.closed:return
        try:self.sender_queue.put_nowait(value)
        except queue.Full:
            # Device callbacks never close Qt timers or audio streams directly.
            self.received.emit({'type':'error','message':'Voice input fell behind. Reopen Voice.'})

    def set_status(self, text, state='error'):
        if state not in ('error','disconnected'):
            seconds = self.dialogue.seconds if self.dialogue and self.dialogue.seconds is not None else max(0,time.monotonic()-self.started_at)
            text += f' · Voice ≈ ${seconds / 60 * .05:.2f}'
        super().set_status(text,state)

    def connect_voice(self):
        try:
            import sounddevice as sd
            import websocket
            self.sd = sd
            config = load_config()
            self.ws = websocket.create_connection(LIVE_URL, timeout=10,
                header={'Authorization': 'Bearer ' + cloud_key()}, suppress_origin=True, redirect_limit=0)
            if self.closed: self.ws.close(); return
            self.send_live({'type': 'session.start', 'session': {'model': 'gpt-live-1',
                'instructions': INSTRUCTIONS, 'delegation': {'type': 'client'}, 'store': False,
                'audio': {'format': {'type': 'audio/pcm', 'rate': 24000},
                          'output': {'voice': config['cloudVoice']}}}})
            # A finite startup deadline prevents an opened socket with no session
            # acknowledgment from remaining billable indefinitely.
            startup_deadline=time.monotonic()+10
            while not self.closed:
                if time.monotonic()>startup_deadline:raise RuntimeError('Live startup timed out')
                value = json.loads(self.ws.recv())
                if value.get('type') == 'error': raise RuntimeError('Live startup rejected')
                if value.get('type') == 'session.started': break
            if self.closed: return
            self.live_started = True
            self.ws.settimeout(2)
            if self.hands_free and sys.platform.startswith('linux'):
                from .voice_echo import EchoRoute
                self.echo_route = EchoRoute.create()
            output = self.echo_route.open_output if self.echo_route else lambda device, **options: device.RawOutputStream(**options)
            self.output = output(sd, samplerate=24000, channels=1, dtype='int16', blocksize=480, callback=self.playback)
            if self.closed: self.output.close(); return
            self.output.start()
            threading.Thread(target=self.send_loop, daemon=True).start()
            self.received.emit({'type': 'live-ready'})
            while True:
                try:raw = self.ws.recv()
                except websocket.WebSocketTimeoutException:continue
                if not raw: break
                if not isinstance(raw, str) or len(raw) > 1024 * 1024: raise ValueError('Invalid Live frame')
                event = json.loads(raw)
                if event.get('type') == 'session.closed':
                    seconds = event.get('usage', {}).get('seconds')
                    if type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0: self.usage_seconds = seconds
                    self.finalized.set()
                    break
                if event.get('type') == 'session.output_audio.delta':
                    if not self.closed:
                        pcm=base64.b64decode(event.get('delta',''),validate=True)
                        if len(pcm)%2 or len(pcm)>96000:raise ValueError('Invalid PCM')
                        self.audio_frames.put_nowait(pcm)
                        # Process acknowledgements and audio on the same Qt queue.
                        # Otherwise the first PCM can race its commentary ack.
                        self.received.emit({'type':'live-audio'})
                elif not self.closed:
                    self.received.emit({'type': 'live-event', 'event': event})
        except Exception:
            if not self.closed:
                self.received.emit({'type': 'error', 'message': 'OpenAI Voice disconnected. Check API access, audio devices and network. No request will be replayed.'})
        finally:
            if self.ws:
                try: self.ws.close()
                except Exception: pass
            self.transport_finished.set()
            if not self.closed: self.received.emit({'type': 'disconnected'})

    def send_loop(self):
        try:
            while not self.closed:
                try: value = self.sender_queue.get(timeout=.2)
                except queue.Empty: continue
                if isinstance(value, bytes):
                    self.send_live({'type': 'session.input_audio.append', 'audio': base64.b64encode(value).decode('ascii')})
                else: self.send_live(value)
        except Exception:
            if not self.closed: self.received.emit({'type': 'error', 'message': 'OpenAI Voice connection lost. No audio or request will be replayed.'})

    def handle(self, event):
        if self.closed: return
        kind = event.get('type')
        try:
            if kind == 'live-ready':
                self.connected = True
                if self.hands_free: self.start_hands_free()
                else: self.set_status('Ready · Hold to talk', 'ready')
            elif kind == 'live-event':
                value = event['event']
                if value.get('type') == 'error': raise ValueError('OpenAI Voice rejected a command. Reopen Voice; no request will be replayed.')
                self.dialogue.receive(value)
                if value.get('type') == 'session.input_transcript.delta':
                    self.last_activity = time.monotonic()
            elif kind == 'live-audio':
                pcm=self.audio_frames.get_nowait()
                if self.dialogue.output_allowed and time.monotonic()-self.last_voice>self.pause_ms/1000:
                    with self.audio_lock:
                        if len(self.pending)+len(pcm)>384000:raise ValueError('Playback queue limit')
                        self.pending.extend(pcm);self.playback_buffer.complete=False
                    self.last_audio=self.last_activity=time.monotonic()
                    self.set_status('Speaking · Interrupt to reply','speaking')
            elif kind == 'live-barge': self.interrupt()
            elif kind in ('error', 'disconnected'):
                self.set_status(event.get('message', 'OpenAI Voice disconnected. Reopen to continue.'), 'error')
                self.shutdown()
            elif kind == 'microphone-ready': self.changed.emit()
        except Exception as error:
            self.set_status(str(error), 'error')
            self.shutdown()

    def clear_playback(self):
        with self.audio_lock:
            self.playback_buffer.reset()
            self.audible_until = 0.
        self.speech_idle = True

    def interrupt(self):
        if self.dialogue: self.dialogue.interrupt()
        else: self.clear_playback()
        if self.live_started and not self.closed:
            self.control({'type': 'session.instructions.append', 'delegation_id': None,
                          'content': 'Stop speaking. Remain silent until a new verified application result arrives.'})

    def begin(self):
        if self.hands_free or not self.can_record: return
        try:
            self.dictation_lease.acquire()
            self.interrupt()
            self.dialogue.begin()
            self.control({'type': 'session.input_audio.unmute'})
            self.capture = self.sd.RawInputStream(samplerate=24000, channels=1, dtype='int16', blocksize=480, callback=self.microphone)
            self.accepting_audio = True
            self.recorded_bytes = 0
            self.recording_started = time.monotonic()
            self.capture.start(); self.capture_timer.start()
            self.set_status('Release to send · Slide left to lock', 'listening')
        except Exception:
            self.set_status('Microphone unavailable. Check your audio device and permissions.')
            self.shutdown()

    def start_hands_free(self):
        try:
            self.dictation_lease.acquire()
            capture = self.echo_route.open_input if self.echo_route else lambda device, **options: device.RawInputStream(**options)
            self.capture = capture(self.sd, samplerate=24000, channels=1, dtype='int16', blocksize=480, callback=self.microphone)
            self.accepting_audio = True
            self.capture.start(); self.capture_timer.start()
            note = 'Listening · Tap or Esc to stop'
            if self.echo_route is None: note += ' · Use headphones'
            self.set_status(note, 'listening')
        except Exception:
            self.set_status('Hands-free audio is unavailable. Check audio permissions or use hold-to-talk.')
            self.shutdown()

    def microphone(self, data, _frames=None, _time=None, status=None):
        if self.closed or not self.accepting_audio: return
        if status:
            self.received.emit({'type': 'error', 'message': 'Microphone lost audio. Reopen Voice.'}); return
        pcm = bytes(data)
        samples = array('h', pcm)
        if not samples: return
        rms = math.sqrt(sum(x * x for x in samples) / len(samples)) / 32768
        now = time.monotonic()
        if rms > .015:
            if now - self.last_voice > .3 and self.dialogue and self.dialogue.output_allowed:
                self.received.emit({'type': 'live-barge'})
            self.last_voice = self.last_activity = now
            if self.dialogue: self.dialogue.last_speech = now
        self.note_microphone_frame()
        self.meter_levels = [min(1., rms * 8)] * 11
        self.recorded_bytes += len(pcm)
        self.control(pcm)
        if not self.hands_free and self.recorded_bytes >= self.max_seconds * 48000: self.limit_reached.emit()

    def end(self, send=True, automatic=False):
        if self.hands_free or not self.capture: return
        self.accepting_audio = False
        self.capture_timer.stop(); self.capture.stop(); self.capture.close(); self.capture = None
        self.dictation_lease.release()
        self.control({'type':'session.input_audio.mute'})
        self.timings['recordedSeconds'] = round(self.recorded_bytes / 48000, 3)
        self.input_ended_at = time.monotonic()
        if send:
            self.dialogue.end()
            self.recognizing = True
            self.set_status('Preparing your request…', 'recognizing')
        else: self.shutdown()

    def submit_transcript(self, event):
        self.last_activity = time.monotonic()
        self.recognizing = False
        self.submitted.add(event['requestId'])
        self.set_status('Your selected model is working…', 'thinking')
        self.transcript.emit({'sessionId': self.session_id, **event})

    def submission_result(self, result):
        try: self.dialogue.submission(result)
        except (ValueError, TypeError, AttributeError) as error:
            self.set_status(str(error)); self.shutdown()

    def observe(self, event):
        if self.closed: return
        try: self.dialogue.observe(event)
        except (ValueError, TypeError, AttributeError) as error:
            self.set_status(str(error)); self.shutdown()

    def update_playback_status(self):
        pass  # Live has no output-audio-done event; tick_live tracks local drain.

    def tick_live(self):
        if self.closed or not self.dialogue: return
        try:
            self.dialogue.tick()
            now = time.monotonic()
            with self.audio_lock:
                if self.last_audio and now - self.last_audio > .5: self.playback_buffer.complete = True
                empty = not self.pending
            if empty and not self.dialogue.working and not self.recognizing and now - self.last_audio > 1 and self.state in ('speaking','thinking'):
                self.speech_idle = True
                self.set_status('Listening · Tap or Esc to stop' if self.hands_free else 'Ready · Hold to talk', 'listening' if self.hands_free else 'ready')
            if not self.dialogue.working and not self.dialogue.fragments and empty and now - self.last_activity > 60:
                self.set_status('Voice paused to limit charges · Tap to resume', 'disconnected'); self.shutdown()
            elif now - self.started_at > 1800:
                self.set_status('Voice session limit reached · Tap to resume', 'disconnected'); self.shutdown()
        except (ValueError, TypeError, AttributeError) as error:
            self.set_status(str(error)); self.shutdown()

    def shutdown(self):
        if self.closed: return
        self.closed = True
        self.connected = False
        self.accepting_audio = False
        self.capture_timer.stop(); self.playback_timer.stop()
        if hasattr(self, 'live_timer'): self.live_timer.stop()
        for name in ('capture','output','echo_route'):
            resource=getattr(self,name)
            setattr(self,name,None)
            if resource:
                try:resource.close()
                except Exception:pass
        self.dictation_lease.release()
        self.clear_playback()
        while not self.audio_frames.empty():
            try:self.audio_frames.get_nowait()
            except queue.Empty:break
        if self.ws and self.live_started and not self.transport_finished.is_set():
            try:
                self.send_live({'type': 'session.close'})
                self.finalized.wait(3)
            except Exception: pass
        if self.ws:
            try: self.ws.close()
            except Exception: pass
        if self.live_started:
            from .voice_provider import record_usage
            seconds = self.usage_seconds if self.finalized.is_set() else self.dialogue.seconds if self.dialogue else None
            try: record_usage(seconds, self.finalized.is_set() and self.usage_seconds is not None)
            except OSError: pass  # Receipt storage must never retain audio resources.
            if not self.finalized.is_set():self.status_text='Voice closed · Final API usage is unconfirmed'
        self.changed.emit()

    def close(self):
        self.shutdown()


def voice_session(parent, ticket, **options):
    implementation = LiveVoiceSession if ticket.get('protocol') == 'augmentor-live/1' else VoiceSession
    return implementation(parent, ticket, **options)
