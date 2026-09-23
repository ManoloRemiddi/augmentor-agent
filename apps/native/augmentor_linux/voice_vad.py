# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""CPU speech endpointing; no microphone, network, or GUI operations here.

Silero v6.2.1's documented ONNX recurrent-state/context contract is used with
numpy (upstream model © Silero Team, MIT; installed beside its LICENSE).
"""
from collections import deque
from pathlib import Path
import hashlib
import math
from array import array

MODEL_SHA256 = '1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3'


class SileroVad:
    def __init__(self, path=None):
        import numpy as np
        import onnxruntime as ort
        path = Path(path or Path.home()/'.local/share/resonant-voice/vad/silero-v6.2.1.onnx')
        if hashlib.sha256(path.read_bytes()).hexdigest() != MODEL_SHA256:
            raise RuntimeError('Hands-free speech detector is missing or has changed. Reinstall its pinned model.')
        options = ort.SessionOptions()
        options.inter_op_num_threads = 1
        options.intra_op_num_threads = 1
        self.session = ort.InferenceSession(str(path), sess_options=options, providers=['CPUExecutionProvider'])
        self.np = np
        self.reset()

    def reset(self):
        self.state = self.np.zeros((2, 1, 128), dtype=self.np.float32)
        self.context = self.np.zeros((1, 64), dtype=self.np.float32)

    def __call__(self, pcm):
        np = self.np
        samples = np.frombuffer(pcm, dtype='<i2').astype(np.float32).reshape(1, 512)/32768.
        joined = np.concatenate((self.context, samples), axis=1)
        result, self.state = self.session.run(None, {'input': joined, 'state': self.state, 'sr': np.array(16000, dtype=np.int64)})
        self.context = samples[:, -64:]
        return float(result[0][0])


class EndpointDetector:
    """32 ms frames, 320 ms pre-roll; hysteresis rejects brief transients.

    Events are emitted in order: start, pcm*, end. Ending resets the detector;
    the owner must disable processing during ASR so it cannot overlap requests.
    """
    FRAME_BYTES = 1024
    FRAME_SECONDS = .032

    def __init__(self, pause_ms=800, maximum=600):
        self.pause_frames = max(13, min(63, math.ceil(pause_ms/32)))
        self.maximum_frames = max(1, int(maximum/.032))
        self.reset()

    def reset(self):
        self.pre = deque(maxlen=10)
        self.active = False
        self.onset = self.silence = self.frames = 0

    def feed(self, pcm, probability, speaking=False):
        if len(pcm) != self.FRAME_BYTES:
            raise ValueError('VAD expects one 32 ms frame')
        if not self.active:
            self.pre.append(pcm)
            self.onset = self.onset+1 if probability >= (.65 if speaking else .55) else 0
            if self.onset < (10 if speaking else 4):
                return []
            self.active = True
            self.frames = len(self.pre)
            events = [('start', None), ('pcm', b''.join(self.pre))]
            self.pre.clear()
            return events
        self.frames += 1
        self.silence = self.silence+1 if probability < .35 else 0
        events = [('pcm', pcm)]
        if self.silence >= self.pause_frames or self.frames >= self.maximum_frames:
            events.append(('end', 'limit' if self.frames >= self.maximum_frames else 'silence'))
            self.reset()
        return events


def levels(pcm):
    samples = array('h', pcm)
    rms = math.sqrt(sum(x*x for x in samples)/max(1, len(samples)))/32768
    return ([0.]*11 if rms < .004 else [min(1., math.sqrt(sum((x/32768)**2 for x in samples[i::11])/max(1,len(samples[i::11])))*8) for i in range(11)])
