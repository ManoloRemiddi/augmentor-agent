# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Gesture-owned microphone buffer, independent of DSH conversation preparation."""
import threading
import time
from collections import deque
from PySide6.QtCore import QObject, Signal, QTimer


class EarlyVoiceInput(QObject):
    changed = Signal()
    failed = Signal(str)
    MAX_FRAMES = 320  # 10.24 seconds, never silently keep only the tail.

    def __init__(self, parent=None):
        super().__init__(parent)
        self.closed=False;self.receiving=False;self.error=None;self.last_frame=0.
        self.stream=None;self.route=None;self.sd=None;self.consumer=None
        self.frames=deque();self.lock=threading.RLock();self.opened=threading.Event()
        self.watchdog=QTimer(self);self.watchdog.setInterval(100)
        self.watchdog.timeout.connect(self._check_receiving);self.watchdog.start()
        threading.Thread(target=self._open,daemon=True).start()

    def _check_receiving(self):
        if self.closed:self.watchdog.stop();return
        if self.receiving and time.monotonic()-self.last_frame>.5:
            self.receiving=False;self.changed.emit()

    def _open(self):
        try:
            import sounddevice as sd
            from .voice_echo import EchoRoute
            self.sd=sd
            route=EchoRoute.create()
            with self.lock:
                if self.closed:route.close();return
                self.route=route
            stream=route.open_input(sd,samplerate=16000,channels=1,dtype='int16',blocksize=512,
                                    callback=self._frame,latency='low')
            with self.lock:
                if self.closed:stream.close();return
                self.stream=stream
            stream.start()
        except Exception as error:
            if not self.closed:
                self.error=str(error);self.failed.emit('Microphone unavailable: '+str(error));self.close()
        finally:self.opened.set()

    def _frame(self,data,frames,timing,status):
        with self.lock:
            if self.closed:return
            if status:
                self.receiving=False;self.error='Microphone lost audio. Please restart voice.'
                self.failed.emit(self.error);return
            self.last_frame=time.monotonic()
            pcm=bytes(data)
            if self.consumer:self.consumer(pcm,frames,timing,status)
            elif len(self.frames)<self.MAX_FRAMES:self.frames.append(pcm)
            else:
                self.receiving=False;self.frames.clear()
                self.error='Voice preparation exceeded the recording buffer. Please restart voice.'
                self.failed.emit(self.error);return
            if not self.receiving and not self.error:
                self.receiving=True;self.changed.emit()

    def wait_ready(self):
        if not self.opened.wait(10) or self.closed or self.error or self.stream is None:
            raise RuntimeError(self.error or 'Microphone preparation did not complete.')

    def attach(self,consumer):
        with self.lock:
            if self.closed or self.error:raise RuntimeError(self.error or 'Microphone was closed.')
            # Serialize the handoff with the callback: no second input stream,
            # no gap between old buffered samples and the next device frame.
            for pcm in self.frames:consumer(pcm,512,None,None)
            self.frames.clear();self.consumer=consumer

    def close(self):
        with self.lock:
            if self.closed:return
            self.closed=True;self.receiving=False;self.frames.clear();self.consumer=None
            stream,self.stream=self.stream,None;route,self.route=self.route,None
        if stream:stream.close()
        if route:route.close()
        self.opened.set()
