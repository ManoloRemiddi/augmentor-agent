# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Offscreen real Qt controls, native adapter and socket; synthetic model only."""
import json, os, time
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton
from augmentor_linux.adapters.codex import CodexAdapter
from augmentor_linux.controller import Controller
from augmentor_linux.pi_client import EventStream
from augmentor_linux.window import Window

app = QApplication([])
client = CodexAdapter()
sid = 'steering-fixture'
controller = Controller(client=client, harness='codex')
controller.session = sid
controller.online = True
controller.running = True
window = Window()
window.controller = controller
controller.queue_changed.connect(window.queue_panel.replace)
controller.queue_result.connect(window.queue_panel.submission_result)
controller.queue_action_result.connect(window.queue_panel.action_result)
controller.event.connect(window.on_event)
controller.busy.connect(window.set_busy)
window.set_models([{'provider':'fixture', 'model':'fixture', 'name':'Fixture'}])
window.show()
window.set_busy(True)
stream = None
completed_turns = []
controller.event.connect(lambda event: completed_turns.append(event) if event['type']=='turn/end' else None)

def until(check):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        app.processEvents()
        if check(): return
        QTest.qWait(10)
    raise AssertionError('Native queue fixture timed out')

def connect():
    value = EventStream(client, sid, controller.frame, lambda message: None)
    value.start()
    return value

def enter(text):
    window.composer.setPlainText(text)
    QTest.keyClick(window.composer, Qt.Key.Key_Return)
    assert window.composer.toPlainText() == ''
    until(lambda: any(row['message']['content'][0]['text'] == text for row in window.queue_panel.items))
    return next(row['id'] for row in window.queue_panel.items if row['message']['content'][0]['text'] == text)

def click(key, label):
    # Locate the real row button by its bound item position.
    index = next(i for i, row in enumerate(window.queue_panel.items) if row['id'] == key)
    widget = window.queue_panel.rows.itemAt(index).widget()
    button = next(b for b in widget.findChildren(QPushButton) if b.text() == label)
    assert button.isEnabled()
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)

try:
    stream = connect()
    until(lambda: getattr(controller, 'queue_turn_id', None))
    correction = enter('SYNTHETIC_STEERING_CORRECTION')
    click(correction, 'Steer')
    until(lambda: any(o['id'] == correction and o.get('steerTurnId') for o in client.call('session.queue', {'sessionId':sid})['operations']))
    removed = enter('SYNTHETIC_REMOVED_PROMPT')
    click(removed, '×')
    until(lambda: not any(row['id'] == removed for row in window.queue_panel.items))
    retained = enter('SYNTHETIC_RECONNECT_PROMPT')
    stream.close()
    window.queue_panel.reset()
    stream = connect()
    until(lambda: any(row['id'] == retained for row in window.queue_panel.items))
    click(retained, '×')
    until(lambda: not any(row['id'] == retained for row in window.queue_panel.items))
    followup = enter('SYNTHETIC_NEXT_TURN')
    print(json.dumps({'ready':True, 'correction':correction, 'followup':followup}), flush=True)
    until(lambda: len(completed_turns)==2 and not controller.running)
    until(lambda: not window.queue_panel.items and not window.queue_panel.pending)
    assert any(text == 'SYNTHETIC_STEERING_CORRECTION' for who, text in window.messages if who == 'You')
    texts = [text for who, text in window.messages if who == 'You']
    assert texts.index('SYNTHETIC_STEERING_CORRECTION') < texts.index('SYNTHETIC_NEXT_TURN')
    print(json.dumps({'nativeQueue':'passed'}), flush=True)
finally:
    if stream: stream.close()
    controller.running = False
    controller.close()
    window.controller = None
    window.close()
