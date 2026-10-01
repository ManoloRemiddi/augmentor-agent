# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real Qt controls, native adapter and speech socket with synthetic audio devices."""
import fake_audio  # noqa: F401
import json
import os
from pathlib import Path
import time
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from augmentor_linux.controller import Controller
from augmentor_linux.window import Window

app = QApplication([])
controller = Controller(harness='codex')
controller.online = True
window = Window()
window.controller = controller
window.preferences.values['resonant_voice'] = True
window.preferences.values['voice_mode'] = 'manual'
for name, slot in [('session_info', window.session_changed), ('event', window.on_event), ('busy', window.set_busy),
                   ('sent', window.message_sent), ('connection', window.connection_changed), ('problem', window.on_problem)]:
    getattr(controller, name).connect(slot)
problems = []
controller.problem.connect(problems.append)
window.set_models([{'provider': 'local', 'model': 'fixture', 'name': 'Fixture'}])
window.show()
window.update_controls()

def until(check):
    deadline = time.monotonic()+10
    while time.monotonic()<deadline:
        app.processEvents()
        if check(): return
        QTest.qWait(10)
    raise AssertionError('Native voice timed out: '+str(problems)+' '+str(window.status.text()))

try:
    assert window.voice_button.isEnabled()
    QTest.mouseClick(window.voice_button, Qt.MouseButton.LeftButton)
    until(lambda: window.voice_dialog and window.voice_dialog.can_record)
    assert controller.session.startswith('augmentor-linux-codex-')
    QTest.mousePress(window.voice_button, Qt.MouseButton.LeftButton)
    until(lambda: window.voice_dialog.accepting_audio and window.voice_dialog.recorded_bytes>0)
    QTest.mouseRelease(window.voice_button, Qt.MouseButton.LeftButton)
    until(lambda: window.voice_dialog.waiting_request and window.voice_dialog.waiting_request.startswith('resonant-voice:'))
    until(lambda: window.voice_dialog.turn_complete and Path(os.environ['AUGMENTOR_VOICE_TEST_AUDIO_LOG']).exists())
    assert not problems, problems
    assert len(window.voice_dialog.submitted) == 1
    print(json.dumps({'nativeVoice': 'passed', 'sessionId': controller.session}), flush=True)
finally:
    window.close_voice_panel()
    controller.running = False
    controller.close()
    window.controller = None
    window.close()
