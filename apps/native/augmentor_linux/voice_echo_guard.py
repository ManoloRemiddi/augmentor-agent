# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Acoustic playback-reference guard in addition to PipeWire AEC.

Compares waveform correlation, never transcript text. The audio callback only
queues bounded reference PCM; resampling/correlation run on the VAD worker.
"""
import queue
import time
from collections import deque


class PlaybackEchoGuard:
    def __init__(self):
        self.incoming=queue.Queue(maxsize=64)
        self.history=deque()
        self.last_playback=0.

    def played(self,pcm,at=None):
        at=time.monotonic() if at is None else at
        try:self.incoming.put_nowait((at,bytes(pcm)))
        except queue.Full:
            # Lose an old reference, never block the audio output callback.
            try:self.incoming.get_nowait()
            except queue.Empty:pass
            try:self.incoming.put_nowait((at,bytes(pcm)))
            except queue.Full:pass

    def is_echo(self,pcm,now=None):
        import numpy as np
        now=time.monotonic() if now is None else now
        while True:
            try:at,chunk=self.incoming.get_nowait()
            except queue.Empty:break
            x=np.frombuffer(chunk,dtype='<i2').astype(np.float32)/32768
            if len(x) and np.any(x):
                self.history.append((at,np.interp(np.arange(0,len(x),1.5),np.arange(len(x)),x).astype(np.float32)))
                self.last_playback=at
        while self.history and self.history[0][0]<now-1.2:self.history.popleft()
        if not self.history or now-self.last_playback>.3:return False
        mic=np.frombuffer(pcm,dtype='<i2').astype(np.float32)/32768
        rms=float(np.sqrt(np.mean(mic*mic)))
        # Residual near-silence must not become a short hallucinated interrupt.
        if rms<.002:return True
        reference=np.concatenate([x for _,x in self.history]);n=len(mic)
        if len(reference)<n:return False
        mic=mic-mic.mean();energy=float(np.dot(mic,mic))
        if energy<1e-10:return True
        sums=np.concatenate(([0.],np.cumsum(reference,dtype=np.float64)))
        squares=np.concatenate(([0.],np.cumsum(reference*reference,dtype=np.float64)))
        local_energy=squares[n:]-squares[:-n]-(sums[n:]-sums[:-n])**2/n
        correlation=np.abs(np.correlate(reference,mic,'valid'))/np.sqrt(np.maximum(local_energy*energy,1e-12))
        return bool(np.max(correlation)>=.6)
