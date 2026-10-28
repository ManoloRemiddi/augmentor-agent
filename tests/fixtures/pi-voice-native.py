# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual Pi Qt voice and Send controls; synthetic audio devices, no owner profile."""
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

app=QApplication([])
controller=Controller(harness='pi')
controller.client.call('host.describe')
controller.online=True
window=Window();window.controller=controller
window.preferences.values['resonant_voice']=True
window.preferences.values['voice_mode']='manual'
for name,slot in [('session_info',window.session_changed),('event',window.on_event),('busy',window.set_busy),('sent',window.message_sent),('connection',window.connection_changed),('problem',window.on_problem)]:
    getattr(controller,name).connect(slot)
problems=[];controller.problem.connect(problems.append)
window.set_models([{'provider':'fixture','model':'plan-fixture','name':'Independent public Pi fixture'}])
window.show();window.update_controls()
def until(check):
    end=time.monotonic()+10
    while time.monotonic()<end:
        app.processEvents()
        if check():return
        QTest.qWait(10)
    raise AssertionError('Pi Qt voice control timed out: '+str(problems)+' '+window.status.text())
try:
    assert window.voice_button.isEnabled()
    QTest.mouseClick(window.voice_button,Qt.MouseButton.LeftButton)
    until(lambda:window.voice_dialog and window.voice_dialog.can_record)
    assert controller.session.startswith('augmentor-linux-pi-')
    QTest.mousePress(window.voice_button,Qt.MouseButton.LeftButton)
    until(lambda:window.voice_dialog.accepting_audio and window.voice_dialog.recorded_bytes>0)
    QTest.mouseRelease(window.voice_button,Qt.MouseButton.LeftButton)
    until(lambda:window.voice_dialog.turn_complete and not controller.running and Path(os.environ['AUGMENTOR_VOICE_TEST_AUDIO_LOG']).exists())
    assert len(window.voice_dialog.submitted)==1
    sid=controller.session;window.close_voice_panel()
    until(lambda:not controller.voice_closing and controller.admission.control('host.maintenance.status',{})['active']==0)
    window.composer.setPlainText('A typed follow-up using the original Send button.')
    window.update_controls();assert window.send_button.isEnabled()
    QTest.mouseClick(window.send_button,Qt.MouseButton.LeftButton)
    until(lambda:not controller.running and controller.session==sid and window.composer.toPlainText()=='')
    assert not problems,problems
    print(json.dumps({'nativePiVoice':'passed','sessionId':sid,'typedFollowup':True}),flush=True)
finally:
    window.close_voice_panel();controller.close();window.controller=None;window.close()
