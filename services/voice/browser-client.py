# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Private stdio transport for the same VoiceSession used by the floating UI."""
import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'apps/native'))
from PySide6.QtCore import QCoreApplication, QObject, QTimer, Signal
from augmentor_linux.voice import VoiceSession
from augmentor_linux.voice_input import EarlyVoiceInput
from augmentor_linux.preferences import Preferences


class Client(QObject):
    command = Signal(dict)

    def __init__(self, emit, session_type=VoiceSession, input_type=EarlyVoiceInput, preferences=None):
        super().__init__()
        self.publish, self.session_type, self.input_type = emit, session_type, input_type
        self.preferences = preferences or Preferences()
        self.voice = self.early = None
        self.intent = False
        self.prepared = False
        self.hands_free = False
        self.last_heartbeat = time.monotonic()
        self.command.connect(self.receive)
        self.watchdog = QTimer(self)
        self.watchdog.setInterval(1000)
        self.watchdog.timeout.connect(self.check_lease)
        self.watchdog.start()

    def check_lease(self):
        if time.monotonic() - self.last_heartbeat > 6:
            self.finish()

    def state(self):
        v = self.voice
        if v and self.intent and v.can_record:
            self.intent = False
            v.begin()
        self.publish({'type': 'state', 'state': v.state if v else 'connecting',
                   'status': v.status_text if v else 'Preparing speech models…',
                   'handsFree': self.hands_free, 'canRecord': bool(v and v.can_record),
                   'recording': bool(v and v.accepting_audio),
                   'recordingAvailable': bool(v.recording_available if v else self.early and self.early.receiving),
                   'closed': bool(v and v.closed)})

    def finish(self):
        self.intent = False
        if self.voice:
            self.voice.close()
            self.voice = None
        if self.early:
            self.early.close()
            self.early = None
        self.publish({'type': 'state', 'state': 'closed', 'closed': True, 'status': 'Voice off'})
        app = QCoreApplication.instance()
        if app: app.quit()

    def fail(self, message):
        self.publish({'type': 'error', 'message': str(message)})
        self.finish()

    def receive(self, value):
        try:
            action = value.get('action')
            if action == 'heartbeat':
                self.last_heartbeat = time.monotonic()
            elif action == 'prepare' and not self.prepared:
                if not self.preferences.values['resonant_voice']:raise ValueError('Enable Voice in Settings first.')
                self.prepared = True
                self.hands_free = value.get('handsFree') is True
                if self.hands_free:
                    self.early = self.input_type(self)
                    self.early.changed.connect(self.state)
                    self.early.failed.connect(self.fail)
                self.state()
            elif action == 'start' and self.prepared and not self.voice:
                ticket = value['ticket']
                self.voice = self.session_type(self, ticket, hands_free=self.hands_free, early_input=self.early)
                self.voice.changed.connect(self.state)
                self.voice.transcript.connect(lambda event: self.publish({'type': 'transcript', **event}))
                self.voice.recording_progress.connect(lambda elapsed, maximum, levels: self.publish(
                    {'type': 'progress', 'elapsed': elapsed, 'maximum': maximum, 'levels': levels}))
                self.state()
            elif action == 'begin' and not self.hands_free:
                self.intent = True
                self.state()
            elif action == 'end':
                self.intent = False
                if self.voice: self.voice.end()
            elif action == 'interrupt':
                self.intent = False
                if self.voice: self.voice.interrupt()
            elif action == 'submission' and self.voice:
                self.voice.submission_result(value['result'])
            elif action == 'observe' and self.voice:
                self.voice.observe(value['event'])
            elif action == 'close':
                self.finish()
        except Exception as error:
            self.fail(error)


def main():
    app = QCoreApplication(sys.argv)
    def emit(value):
        print(json.dumps(value, separators=(',', ':')), flush=True)
    client = Client(emit)
    def read():
        try:
            while True:
                line = sys.stdin.buffer.readline(65537)
                if not line or len(line) > 65536: break
                value = json.loads(line)
                if not isinstance(value, dict): break
                client.command.emit(value)
        except (ValueError, OSError): pass
        finally: client.command.emit({'action': 'close'})
    threading.Thread(target=read, daemon=True).start()
    app.aboutToQuit.connect(lambda: client.voice.shutdown() if client.voice else None)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
