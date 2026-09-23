# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Small bounded jitter buffer for streaming 24 kHz mono PCM.

Breeze/tempo processing emits uneven chunks. Playing the first tiny packet
immediately can exhaust it in the middle of the opening word. Keep device
callbacks running with silence while collecting a short initial reserve.
"""
class PlaybackBuffer:
    TARGET_BYTES = 9600  # 200 ms, below the service's 500 ms pacing reserve.
    MAX_WAIT = .250

    def __init__(self):
        self.data = bytearray()
        self.reset()

    def reset(self):
        self.data.clear()
        self.started = False
        self.waiting_since = None
        self.complete = False
        self.starvations = 0

    def start(self):
        self.complete = False
        if not self.data:
            self.started = False
            self.waiting_since = None

    def read(self, size, now):
        if not self.data:
            if self.started and not self.complete:
                self.starvations += 1
                self.started = False
            self.waiting_since = None
            return b''
        if not self.started:
            if self.waiting_since is None:
                self.waiting_since = now
            if (len(self.data) < self.TARGET_BYTES and not self.complete
                    and now-self.waiting_since < self.MAX_WAIT):
                return b''
            self.started = True
            self.waiting_since = None
        pcm = bytes(self.data[:size])
        del self.data[:len(pcm)]
        if len(pcm) < size and not self.complete:
            self.starvations += 1
            self.started = False
        return pcm
