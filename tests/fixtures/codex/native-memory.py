# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual Qt composer and existing memory controls against an isolated shared host."""
import json, time, threading
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from augmentor_linux.controller import Controller
from augmentor_linux.window import Window
from augmentor_linux.memory import MemoryDialog
from augmentor_linux.prompt_client import PromptClient

app = QApplication([])
controller = Controller(harness='codex')
controller.session = 'one'
controller.online = True
controller.selection = {'provider':'local', 'model':'fixture'}
window = Window(); window.controller = controller
for name, slot in [('session_info',window.session_changed), ('event',window.on_event), ('busy',window.set_busy),
                   ('page',window.restore_page), ('sent',window.message_sent), ('submission_failed',window.message_not_sent),
                   ('connection',window.connection_changed), ('problem',window.on_problem)]:
    getattr(controller,name).connect(slot)
problems = []; controller.problem.connect(problems.append)
window.set_models([{'provider':'local','model':'fixture','name':'Fixture'}]); window.show()
panel = None; dialog = None
calls = {};calls_lock = threading.Lock();original_call = PromptClient.call
def traced_call(client, method, *args, **kwargs):
    identity = threading.get_ident()
    with calls_lock:calls[identity] = (method,time.monotonic())
    try:return original_call(client,method,*args,**kwargs)
    finally:
        with calls_lock:calls.pop(identity,None)
PromptClient.call = traced_call

def until(check,label='composer or memory readiness'):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        app.processEvents()
        if check(): return
        QTest.qWait(10)
    with calls_lock:pending=[{'method':method,'seconds':round(time.monotonic()-started,2)} for method,started in calls.values()]
    raise AssertionError('Native memory timeout: ' + json.dumps({'phase':label,'problems':problems,'pendingCompanionCalls':pending,
        'panelBusy':panel.busy if panel else None,'panelStatus':panel.status.text() if panel else None,'controllerRunning':controller.running}))

def prompt(text, answer, enter=True):
    until(lambda: window.send_button.isEnabled())
    window.composer.setPlainText(text)
    if enter: QTest.keyClick(window.composer,Qt.Key.Key_Return)
    else: QTest.mouseClick(window.send_button,Qt.MouseButton.LeftButton)
    until(lambda: any(who=='Augmentor' and value==answer for who,value in window.messages) and not controller.running)

try:
    controller.client.call('host.describe')
    assert controller.capabilities['memory'] is True
    controller.client.call('session.create', {'sessionId':'one', 'cwd':str(controller.client.workspace()), 'selection':controller.selection})
    controller.subscribe('one')
    until(lambda:controller.connected)
    prompt('MODEL_STEP_1 NATIVE_BOUNDARY_FIXTURE_TEXT', 'PUBLIC_REPLY_1')
    until(lambda: PromptClient().call('memory.dual.describe')['events']==2)
    dialog = MemoryDialog(window); dialog.show(); panel = dialog.tabs.widget(0)
    until(lambda:not panel.busy and '2 transcript records' in panel.status.text())
    QTest.mouseClick(panel.toggle,Qt.MouseButton.LeftButton)
    until(lambda:not panel.busy and not panel.enabled)
    prompt('MODEL_STEP_3 NATIVE_CAPTURE_PAUSED_TEXT', 'PUBLIC_REPLY_3', False)
    QTest.mouseClick(panel.refresh,Qt.MouseButton.LeftButton)
    until(lambda:not panel.busy,'refresh after capture-paused Send')
    assert '2 transcript records' in panel.status.text()
    assert 'Recall and new capture are paused.' in panel.contents.toPlainText()
    QTest.mouseClick(panel.toggle,Qt.MouseButton.LeftButton)
    until(lambda:not panel.busy and panel.enabled)
    prompt('MODEL_STEP_4 NATIVE_CONTINUATION_TEXT', 'PUBLIC_REPLY_4')
    until(lambda: panel.client.call('memory.dual.describe')['events']==4)
    QTest.mouseClick(panel.refresh,Qt.MouseButton.LeftButton)
    until(lambda:not panel.busy and '4 transcript records' in panel.status.text(),'refresh after resumed Enter')
    assert all('augmentor_memory_manifest' not in text and 'external_augmentor_memory_data' not in text for _,text in window.messages)
    print(json.dumps({'nativeMemory':'passed'}),flush=True)
finally:
    if dialog: dialog.close()
    controller.running=False; controller.close(); window.controller=None; window.close()
