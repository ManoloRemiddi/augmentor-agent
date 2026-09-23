# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Optional Resonant Voice session. The existing controller submits every prompt."""
from .instances import current_name
import json
import queue
import threading
import time
import math
from array import array
from PySide6.QtCore import QObject, Signal, QTimer


class VoiceSession(QObject):
    panel_closed = Signal()
    changed = Signal()
    received = Signal(dict)
    transcript = Signal(dict)
    recording_progress = Signal(float, float, object)
    limit_reached = Signal()

    def __init__(self, parent, ticket, hands_free=None, early_input=None):
        super().__init__(parent)
        self.hands_free = (getattr(parent, 'preferences', None) is not None and parent.preferences.values.get('voice_mode') == 'hands-free') if hands_free is None else bool(hands_free)
        self.pause_ms = getattr(getattr(parent, 'preferences', None), 'values', {}).get('voice_pause_ms', 800)
        self.early_input=early_input
        from .voice_echo_guard import PlaybackEchoGuard
        self.echo_guard=PlaybackEchoGuard()
        self.echo_frames_rejected=0
        self.echo_route = None
        # Up to 10.24 seconds of PCM while the recognizer loads or finalizes.
        # ASR-gap frames belong to the next utterance; close discards everything.
        self.vad_queue = queue.Queue(maxsize=320)
        self.recognizer_ready = threading.Event()
        self.microphone_receiving = False
        self.vad_enabled = threading.Event()
        self.vad_epoch = 0
        self.turn_complete = True
        self.audible_until = 0.
        self.drained_generation = None
        self.session_id = ticket['sessionId']
        self.ticket = ticket
        self.submitted = set()
        self.speak_turn = False
        self.waiting_request = None
        self.ws = None
        self.capture = None
        self.closed = False
        self.generation = 0
        from .voice_playback import PlaybackBuffer
        self.playback_buffer = PlaybackBuffer()
        self.pending = self.playback_buffer.data
        self.timings = {}
        self.input_ended_at = None
        self.input_request_id = None
        self.output_underflows = 0
        self.audio_lock = threading.Lock()
        self.sender_queue = queue.Queue(maxsize=512 if self.hands_free else 128)
        self.output = None
        self.recognizing = False
        self.connected = False
        self.speech_idle = True
        self.max_seconds = 600
        self.recorded_bytes = 0
        self.recording_started = None
        self.accepting_audio = False
        self.utterance_open = False
        self.meter_levels = [0.] * 11
        self.last_mic_at = 0.
        self.limit_reached.connect(self.finish_at_limit)
        self.capture_timer = QTimer(self)
        self.capture_timer.setInterval(50)
        self.capture_timer.timeout.connect(self.update_recording)
        self.state = 'connecting'
        self.status_text = 'Connecting to speech models…'
        self.playback_timer=QTimer(self);self.playback_timer.setInterval(100);self.playback_timer.timeout.connect(self.update_playback_status);self.playback_timer.start()
        self.received.connect(self.handle)
        threading.Thread(target=self.connect_voice, daemon=True).start()

    def set_status(self, text, state='error'):
        self.status_text = text
        self.state = state
        self.changed.emit()

    @property
    def can_record(self):
        return self.connected and not self.closed and not self.recognizing and self.capture is None

    @property
    def recording_available(self):
        if (not self.closed and self.early_input and self.early_input.consumer is None
                and self.early_input.receiving and not self.early_input.error):return True
        return (not self.closed and self.microphone_receiving
                and ((self.vad_enabled.is_set() or self.recognizing) if self.hands_free else self.accepting_audio))

    def note_microphone_frame(self):
        self.last_mic_at=time.monotonic()
        if not self.microphone_receiving:
            self.microphone_receiving=True
            self.received.emit({'type':'microphone-ready'})

    def control(self, message):
        if self.closed:
            return
        try:
            self.sender_queue.put_nowait(message)
        except queue.Full:
            self.received.emit({'type': 'error', 'message': 'Audio input fell behind. Reopen Voice.'})
            self.shutdown()

    def connect_voice(self):
        try:
            import sounddevice as sd
            import websocket
            self.sd = sd
            self.ws = websocket.create_connection(self.ticket['url'], timeout=10, suppress_origin=True,
                                                  http_proxy_host=None)
            self.ws.send(json.dumps({'type': 'auth', 'ticket': self.ticket['ticket'], 'textSource': 'plugin', 'profile': current_name()}))
            self.ws.settimeout(None)
            if self.hands_free:
                from .voice_echo import EchoRoute
                from .voice_vad import SileroVad
                self.vad = SileroVad()
                if self.early_input:
                    self.early_input.wait_ready();self.echo_route=self.early_input.route
                else:self.echo_route = EchoRoute.create()
            output_stream = self.echo_route.open_output if self.echo_route else lambda sd, **kw: sd.RawOutputStream(**kw)
            self.output = output_stream(sd, samplerate=24000, channels=1, dtype='int16', blocksize=480,
                                             callback=self.playback, **({'latency':'low'} if self.hands_free else {}))
            if self.closed:
                self.ws.close()
                self.output.close()
                return
            self.output.start()
            threading.Thread(target=self.send_loop, daemon=True).start()
            if self.hands_free:self.received.emit({'type':'capture-preparing'})
            while not self.closed:
                frame = self.ws.recv()
                if not frame:
                    break
                if isinstance(frame, bytes):
                    if len(frame) < 8 or len(frame) % 2:
                        raise ValueError('Invalid audio packet')
                    generation = int.from_bytes(frame[:4], 'little')
                    with self.audio_lock:
                        if generation == self.generation:
                            if len(self.pending) + len(frame)-8 > 384000:
                                raise ValueError('Playback fell behind. Reopen Voice.')
                            self.pending.extend(frame[8:])
                else:
                    value = json.loads(frame)
                    # Invalidate in the receive thread before subsequent binary frames.
                    self.playback_event(value)
                    self.received.emit(value)
        except ImportError as error:
            self.received.emit({'type': 'error', 'message': 'A voice dependency is missing: '+str(error)})
        except Exception as error:
            if not self.closed:
                self.received.emit({'type': 'error', 'message': str(error)})
        finally:
            if not self.closed:
                self.received.emit({'type': 'disconnected'})
            self.shutdown()

    def send_loop(self):
        try:
            while not self.closed:
                try:
                    value = self.sender_queue.get(timeout=.2)
                except queue.Empty:
                    continue
                if isinstance(value, bytes):
                    self.ws.send_binary(value)
                else:
                    self.ws.send(json.dumps(value))
        except Exception:
            if not self.closed:
                self.received.emit({'type': 'error', 'message': 'Voice connection lost; no audio will be replayed.'})
            self.shutdown()

    def playback_event(self, event):
        # Process completion/reset markers in wire order, not after a GUI delay.
        with self.audio_lock:
            kind = event.get('type')
            if kind == 'clear':
                self.generation = event['generation']
                self.playback_buffer.reset()
            elif event.get('generation') == self.generation:
                if kind == 'speaking':self.playback_buffer.start()
                elif kind == 'speech-idle':self.playback_buffer.complete = True

    def playback(self, outdata, frames, _time, _status):
        with self.audio_lock:
            now = time.monotonic()
            pcm = self.playback_buffer.read(len(outdata), now)
            size = len(pcm)
            outdata[:] = pcm + bytes(len(outdata)-size)
            if getattr(_status, 'output_underflow', False):self.output_underflows += 1
            if size and self.input_ended_at is not None:
                self.timings.setdefault('firstPlaybackMs', round((now-self.input_ended_at)*1000, 1))
            if size:
                self.echo_guard.played(bytes(outdata))
                # PortAudio's DAC timestamp includes queued device latency. Fall back
                # to its reported latency when the host provides no timestamps.
                try: delay = max(0., _time.outputBufferDacTime - _time.currentTime)
                except (AttributeError, TypeError): delay = float(getattr(self.output, 'latency', .04))
                self.audible_until = time.monotonic() + delay + size/48000 + .03
                self.drained_generation = None

    def begin(self):
        if self.hands_free:return
        self.speak_turn = False
        self.waiting_request = "recording"
        if not self.can_record:
            return
        self.interrupt()
        try:
            self.control({'type': 'begin'})
            self.recorded_bytes = 0
            self.recording_started = time.monotonic()
            self.accepting_audio = True
            self.meter_levels = [0.] * 11
            self.capture = self.sd.RawInputStream(samplerate=16000, channels=1, dtype='int16', blocksize=320,
                                                  callback=self.microphone)
            self.capture.start()
            self.capture_timer.start()
            self.set_status('Release to send · Slide left to lock', 'listening')
        except Exception as error:
            self.set_status(str(error))
            self.shutdown()

    def start_hands_free(self):
        if self.closed or self.capture:return
        try:
            self.capture = self.early_input.stream if self.early_input else self.echo_route.open_input(self.sd, samplerate=16000, channels=1,
                dtype='int16', blocksize=512, callback=self.hands_free_microphone, latency='low')
            self.vad_enabled.set()
            threading.Thread(target=self.vad_loop, daemon=True).start()
            if self.early_input:self.early_input.attach(self.hands_free_microphone)
            else:self.capture.start()
            self.capture_timer.start()
            self.set_status('Starting microphone…', 'connecting')
        except Exception as error:
            self.set_status('Hands-free unavailable: '+str(error))
            self.shutdown()

    def hands_free_microphone(self, data, _frames, _time, status):
        if self.closed:return
        if status:
            self.microphone_receiving=False
            self.received.emit({'type':'error', 'message':'Microphone lost audio. Restart hands-free to continue.'})
            return
        try:
            self.vad_queue.put_nowait((self.vad_epoch if self.vad_enabled.is_set() else None, bytes(data)))
            self.note_microphone_frame()
        except queue.Full:
            self.received.emit({'type':'error', 'message':'Microphone buffer filled while speech recognition was unavailable. Restart hands-free to continue.'})

    def vad_loop(self):
        from .voice_vad import EndpointDetector, levels
        detector = EndpointDetector(self.pause_ms, self.max_seconds)
        epoch = self.vad_epoch
        try:
            while not self.closed:
                if not self.recognizer_ready.wait(.1) or not self.vad_enabled.wait(.1):continue
                if self.closed:break
                try:frame_epoch, pcm = self.vad_queue.get(timeout=.2)
                except queue.Empty:continue
                if frame_epoch is None:frame_epoch=self.vad_epoch
                if frame_epoch != self.vad_epoch:
                    detector.reset();self.vad.reset();continue
                if epoch != frame_epoch:
                    detector.reset();self.vad.reset();epoch = frame_epoch
                self.meter_levels = levels(pcm)
                if not detector.active and self.echo_guard.is_echo(pcm):
                    self.echo_frames_rejected+=1;detector.reset();self.vad.reset();continue
                probability = self.vad(pcm)
                for kind, value in detector.feed(pcm, probability, speaking=not self.speech_idle or time.monotonic()<self.audible_until):
                    if kind == 'end':self.vad_enabled.clear()
                    self.received.emit({'type':'vad-'+kind, 'value':value, 'epoch':epoch})
        except Exception as error:
            self.received.emit({'type':'error', 'message':'Speech detector stopped: '+str(error)})

    def resume_detection(self):
        if not self.hands_free or self.closed:return
        self.vad_epoch += 1
        self.vad_enabled.set()
        self.changed.emit()

    def handle_vad(self, event):
        if not self.hands_free or self.closed or event.get('epoch') != self.vad_epoch:return
        kind=event['type']
        if kind=='vad-start':
            self.interrupt()
            self.speak_turn=False;self.waiting_request='recording'
            self.turn_complete=False
            self.control({'type':'begin'})
            self.recorded_bytes=0;self.recording_started=time.monotonic()
            self.accepting_audio=True;self.utterance_open=True
            self.set_status('Listening · Pause to send · Tap to stop', 'listening')
        elif kind=='vad-pcm' and self.accepting_audio:
            self.microphone(event['value'])
        elif kind=='vad-end' and self.accepting_audio:
            self.end(automatic=event.get('value')=='limit')

    def microphone(self, data, *_):
        if not self.accepting_audio or self.closed:return
        if not self.hands_free:self.note_microphone_frame()
        remaining=max(0,int(self.max_seconds*32000)-self.recorded_bytes)
        pcm=bytes(data)[:remaining]
        if pcm:
            self.recorded_bytes+=len(pcm)
            samples=array('h',pcm)
            rms=math.sqrt(sum(x*x for x in samples)/len(samples))/32768
            self.meter_levels=[0.] * 11 if rms<.004 else [
                min(1.,math.sqrt(sum((x/32768)**2 for x in samples[i::11])/len(samples[i::11]))*8)
                if samples[i::11] else 0. for i in range(11)]
            self.last_mic_at=time.monotonic()
            self.control(pcm)
        if self.recorded_bytes>=self.max_seconds*32000:
            self.accepting_audio=False
            self.limit_reached.emit()

    def update_recording(self):
        if not self.capture:return
        if self.microphone_receiving and time.monotonic()-self.last_mic_at>.5:
            self.microphone_receiving=False;self.changed.emit()
        if self.hands_free and self.recording_started is None:
            levels=self.meter_levels if time.monotonic()-self.last_mic_at<.15 else [0.]*11
            self.recording_progress.emit(0.,self.max_seconds,levels)
            return
        if self.recording_started is None:return
        elapsed=min(self.max_seconds,time.monotonic()-self.recording_started)
        levels=self.meter_levels if time.monotonic()-self.last_mic_at<.15 else [0.] * 11
        self.recording_progress.emit(elapsed,self.max_seconds,levels)
        if elapsed>=self.max_seconds:self.finish_at_limit()

    def finish_at_limit(self):
        self.end(automatic=True)

    def end(self, send=True, automatic=False):
        if (self.hands_free and self.utterance_open) or (not self.hands_free and self.capture is not None):
            self.input_ended_at = time.monotonic()
            self.timings['recordedSeconds'] = round(self.recorded_bytes/32000, 3)
        if self.hands_free:
            if not self.utterance_open:return
            self.utterance_open=False
            self.accepting_audio=False;self.recognizing=True;self.vad_enabled.clear()
            self.recording_started=None
            if send:self.control({'type':'end'})
            self.set_status('Transcribing…', 'recognizing')
            return
        if self.capture:
            self.accepting_audio=False
            self.capture_timer.stop()
            self.capture.stop()
            self.capture.close()
            self.capture = None
            self.recognizing=True
            if send:self.control({'type': 'end'})
            self.set_status('Recording limit reached · transcribing…' if automatic else 'Transcribing…', 'recognizing')

    def interrupt(self):
        with self.audio_lock:
            self.playback_buffer.reset()
            self.timings = {}
            self.input_ended_at = None
            self.output_underflows = 0
            self.generation = -1
            self.audible_until = 0.
            self.drained_generation = None
        self.control({'type': 'interrupt'})
        self.speech_idle = True
        if self.connected and not self.closed and not self.recognizing and not self.capture:
            self.set_status('Ready · previous speech stopped', 'ready')

    def observe(self, event):
        if self.closed:return
        # This UI event has no voice request/generation identity. An old driver's
        # interrupted end can arrive after barge-in has started a newer utterance.
        # Hands-free cancellation therefore uses the service's ordered clear
        # packets and explicit local Stop, not this unscoped observer event.
        if self.hands_free:return
        if event.get('type')=='turn/end' and event.get('data',{}).get('reason',{}).get('kind') in ('aborted','error','interrupted'):
            self.interrupt()

    def update_playback_status(self):
        if self.closed or not self.speech_idle or self.recognizing or self.accepting_audio:return
        if self.hands_free and not self.turn_complete:return
        if time.monotonic() < self.audible_until:return
        with self.audio_lock:empty=not self.pending
        if empty:
            if self.hands_free:
                if self.drained_generation != self.generation:
                    self.drained_generation = self.generation
                    self.control({'type':'playback-drained','generation':self.generation})
                if self.state in ('speaking','thinking'):
                    self.set_status('Listening · Tap to stop', 'listening')
            elif self.state=='speaking':self.set_status('Ready', 'ready')

    def submission_result(self, result):
        request=result.get('id','')
        if self.closed or not request.startswith('resonant-voice:') or request.split(':',1)[1] not in self.submitted:return
        if not result.get('accepted'):
            self.set_status('Follow-up was not confirmed. '+result.get('error','Check the conversation before retrying.'))
            if self.hands_free:self.shutdown()

    def handle(self, event):
        if self.closed and event['type'] not in ('error','disconnected'):return
        if event['type']=='timing':
            if event.get('stage') in ('asr-progress', 'asr-final'):
                for source, target in (('passes', 'asrPasses'), ('decodedThroughSeconds', 'asrProcessedSeconds'), ('decodeMs', 'asrLastDecodeMs')):
                    metric = event.get(source)
                    if isinstance(metric, (int, float)) and math.isfinite(metric) and metric >= 0:
                        self.timings[target] = round(metric, 3)
            value = event.get('elapsedMs')
            if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
                if event.get('stage') == 'asr-final':self.timings['asrMs'] = round(value, 1)
                elif event.get('stage') == 'first-pcm' and event.get('generation') == self.generation:
                    self.timings.setdefault('firstPcmMs', round(value, 1))
            return
        if event['type']=='capture-preparing':
            self.start_hands_free();return
        if event['type']=='microphone-ready':
            if self.hands_free and self.state in ('connecting','ready'):
                self.set_status('Listening · Tap to stop' if self.connected else 'Listening · Speech recognition is warming up', 'listening')
            else:self.changed.emit()
            return
        if event['type'].startswith('vad-'):
            self.handle_vad(event);return
        if event['type'] == 'ready':
            self.max_seconds=max(1,min(600,int(event.get('maxUtteranceSeconds',60))))
            self.connected=True
            self.recognizer_ready.set()
            if self.hands_free:
                self.start_hands_free()
                if self.microphone_receiving:self.set_status('Listening · Tap to stop', 'listening')
            else:self.set_status('Ready', 'ready')
        elif event['type'] == 'listening':
            self.input_request_id = event.get('requestId')
        elif event['type'] == 'transcript-partial':
            # Provisional recognition never goes to the controller or composer.
            if (event.get('requestId') == self.input_request_id and event.get('sessionId') == self.session_id
                    and self.accepting_audio and event.get('text')):
                self.set_status('Listening · Transcribing as you speak', 'listening')
        elif event['type'] == 'recording-ended':
            self.end(send=False,automatic=True)
        elif event['type'] == 'transcript':
            if self.closed or event['requestId'] in self.submitted:return
            self.recognizing=False
            self.submitted.add(event['requestId'])
            self.set_status('Thinking…', 'thinking')
            self.waiting_request='resonant-voice:'+event['requestId']
            self.turn_complete=False
            self.transcript.emit(event)
            self.resume_detection()
        elif event['type']=='speaking':
            self.speech_idle=False
            if not self.accepting_audio and not self.recognizing:self.set_status('Speaking… · Speak to interrupt' if self.hands_free else 'Speaking…', 'speaking')
        elif event['type']=='speech-idle':
            if event.get('generation',self.generation)==self.generation:self.speech_idle=True
        elif event['type']=='turn-complete':
            if event.get('generation',self.generation)==self.generation and event.get('requestId',self.waiting_request)==self.waiting_request:self.turn_complete=True
        elif event['type'] == 'empty-transcript':
            self.recognizing=False
            self.turn_complete=True
            self.set_status('Listening · Tap to stop' if self.hands_free else 'No speech recognized · hold to retry', 'listening' if self.hands_free else 'ready')
            self.resume_detection()
        elif event['type'] == 'error':
            if not event.get('recoverable'):self.connected=False
            self.set_status(event['message'])
            if self.hands_free:self.shutdown()
        elif event['type'] == 'disconnected':
            self.connected=False
            if self.state!='error':self.set_status('Voice disconnected · click to reconnect', 'disconnected')

    def shutdown(self):
        self.accepting_audio = False
        self.utterance_open = False
        self.closed = True
        self.microphone_receiving = False
        self.vad_enabled.clear()
        self.recognizer_ready.set()
        while True:
            try:self.vad_queue.get_nowait()
            except queue.Empty:break
        if self.early_input:
            self.early_input.close();self.early_input=None;self.capture=None;self.echo_route=None
        if self.capture:
            self.capture.close()
            self.capture = None
        if self.output:
            self.output.close()
            self.output = None
        if self.ws:
            self.ws.close()
        if self.echo_route:
            self.echo_route.close()
            self.echo_route=None

    def close(self):
        self.capture_timer.stop()
        self.playback_timer.stop()
        self.shutdown()
        self.panel_closed.emit()

# Compatibility name for callers; the session has no visual surface.
VoiceDialog = VoiceSession
