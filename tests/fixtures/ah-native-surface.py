# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual Qt composer -> AH IPC -> SDK reply in an authored temporary profile."""
import json
from pathlib import Path
import sys
import time
from PySide6.QtWidgets import QApplication,QComboBox
sys.path.insert(0,str(Path(sys.argv[1])/'apps/native'))
from augmentor_linux.window import Window
from augmentor_linux.controller import Controller
from augmentor_linux.agent_settings import SettingsDialog

app=QApplication([])
def until(predicate,label):
    end=time.monotonic()+35
    while time.monotonic()<end:
        app.processEvents()
        if predicate():return
        time.sleep(.01)
    raise AssertionError(label)

w=Window(preview=True);w.preferences.values['harness']='ah'
w.controller=Controller(w,harness='ah');w.bind_controller();w.show()
try:
    until(lambda:w.controller.online and bool(w.model_picker.currentData()),'AH connected with its model catalog')
    dialog=SettingsDialog(w);dialog.show_page('connections')
    engine=next(c for c in dialog.findChildren(QComboBox) if c.accessibleName()=='Agent engine')
    assert engine.currentData()=='ah'
    assert {'ah','dsh','pi'}.issubset({engine.itemData(i) for i in range(engine.count())})
    dialog.close()
    w.composer.setPlainText(json.dumps({'kind':'read'}));w.send()
    until(lambda:w.controller.session and not w.controller.running,'actual AH reply finished')
    sid=w.controller.session
    history=w.controller.client.call('session.history',{'sessionId':sid,'maxMessages':100})
    assert 'Synthetic planning reply' in json.dumps(history)
    w.controller.close();w.controller=None
    restored=Controller(harness='ah')
    try:assert restored.session==sid and restored.selection['provider']=='fixture'
    finally:restored.close()
    print(json.dumps({'nativeComposerReply':True,'settingsChoices':['ah','dsh','pi'],'restoredAhConversation':True}))
finally:
    if w.controller:w.controller.close();w.controller=None
    w.close();app.processEvents()
