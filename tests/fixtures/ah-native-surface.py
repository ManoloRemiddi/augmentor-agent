# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual Qt composer -> AH IPC -> SDK reply in an authored temporary profile."""
import json
from pathlib import Path
import sys
import time
from PySide6.QtWidgets import QApplication,QComboBox,QPushButton
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from unittest.mock import patch
from types import SimpleNamespace
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

w=Window(preview=True)
# An authored initial DSH client isolates the real selection UI from owner DSH.
initial=SimpleNamespace(harness='dsh',base='fixture-dsh',setting=lambda ns:None)
w.controller=Controller(w,client=initial,harness='dsh');w.show()
try:
    w.open_settings();until(lambda:w.settings_panel is not None,'actual settings panel opens');dialog=w.settings_panel;dialog.show_page('connections')
    engine=next(c for c in dialog.findChildren(QComboBox) if c.accessibleName()=='Agent engine')
    assert engine.currentData()=='dsh'
    assert {'ah','dsh','pi'}.issubset({engine.itemData(i) for i in range(engine.count())})
    engine.setCurrentIndex(engine.findData('ah'));engine.activated.emit(engine.currentIndex())
    until(lambda:w.controller.harness=='ah' and w.controller.online and bool(w.model_picker.currentData()),'selection connects AH with its model catalog')
    # Reproduce the exact Home settings trap, including real Back/More buttons.
    from augmentor_linux.home_settings import HomeDialog
    with patch('augmentor_linux.prompt_client.PromptClient.call',return_value={'connected':False}):
        dialog.open_editor('Home',lambda:HomeDialog(w))
    QTest.mouseClick(dialog.nav['all'],Qt.MouseButton.LeftButton);app.processEvents()
    assert dialog.editor is None and dialog.stack.currentWidget() is dialog.pages['all']
    button=next(b for b in dialog.findChildren(QPushButton) if 'Open harness in browser' in b.text())
    with patch('augmentor_linux.window.QDesktopServices.openUrl',return_value=True) as opened:
        QTest.mouseClick(button,Qt.MouseButton.LeftButton)
        until(lambda:opened.called,'selected AH browser URL opened')
        url=opened.call_args.args[0]
        assert url.host()=='127.0.0.1' and url.fragment().startswith('token=')
    with patch('augmentor_linux.prompt_client.PromptClient.call',return_value={'connected':False}):
        dialog.open_editor('Home',lambda:HomeDialog(w))
    QTest.mouseClick(dialog.findChild(QPushButton,'settings-back'),Qt.MouseButton.LeftButton);app.processEvents()
    assert w.settings_panel is None and w.stack.currentWidget() is w.expanded
    w.open_settings();app.processEvents();dialog=w.settings_panel
    QTest.mouseClick(dialog.findChild(QPushButton,'settings-back'),Qt.MouseButton.LeftButton);app.processEvents()
    assert w.settings_panel is None
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
