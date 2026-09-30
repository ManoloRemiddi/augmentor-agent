# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Synthetic device callbacks; use the real speech transport and playback buffer."""
import os
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace

class Stream:
    def __init__(self, output=False, **options):
        self.output = output
        self.callback = options['callback']
        self.running = False
        self.latency = .01

    def start(self):
        self.running = True
        def run():
            while self.running:
                data = bytearray(960) if self.output else bytes(640)
                self.callback(data, len(data)//2, None, None)
                if self.output and any(data):
                    Path(os.environ['AUGMENTOR_VOICE_TEST_AUDIO_LOG']).write_text('synthetic PCM played')
                time.sleep(.02)
        threading.Thread(target=run, daemon=True).start()

    def close(self): self.running = False
    def stop(self): self.close()

sys.modules['sounddevice'] = SimpleNamespace(RawOutputStream=lambda **kw: Stream(True, **kw), RawInputStream=lambda **kw: Stream(False, **kw))
