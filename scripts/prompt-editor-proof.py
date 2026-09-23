#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real Qt prompt editor and shared service, with isolated user data."""
import json
import os
from pathlib import Path
import signal
import socket
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
APP=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT
work=Path(tempfile.mkdtemp(prefix='augmentor-prompt-editor-'))
for key,leaf in {'XDG_CONFIG_HOME':'config','XDG_DATA_HOME':'data','XDG_STATE_HOME':'state','AUGMENTOR_SHARED_CONFIG':'shared-config','AUGMENTOR_SHARED_DATA':'shared-data','AUGMENTOR_SHARED_STATE':'shared-state','AUGMENTOR_PI_CONFIG':'pi-config','AUGMENTOR_PI_STATE':'pi-state'}.items():os.environ[key]=str(work/leaf)
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(APP/'apps/native'))
from PySide6.QtCore import Qt,QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QPushButton,QMessageBox
from augmentor_linux.window import Window
from augmentor_linux.panels import PromptLibraryDialog
from augmentor_linux.prompt_client import PromptClient
# Reserve an unused loopback port: the DSH controller exercises its ordinary
# offline path while prompt operations use the real isolated shared service.
reserved=socket.socket();reserved.bind(('127.0.0.1',0))
os.environ['DSH_AUGMENTOR_URL']='http://127.0.0.1:'+str(reserved.getsockname()[1])
app=QApplication([]);window=Window(preview=False,harness='dsh');window.setup_offered=True
client=PromptClient();pid=None;dialog=None

def until(check):
    end=time.monotonic()+10
    while time.monotonic()<end:
        app.processEvents()
        if check():return
        QTest.qWait(20)
    raise AssertionError('Prompt editor timed out: '+(dialog.note.text() if dialog else 'startup'))

def click(text):
    button=next(b for b in dialog.tabs.widget(0).findChildren(QPushButton) if b.text()==text)
    assert button.isEnabled()
    QTest.mouseClick(button,Qt.MouseButton.LeftButton)

def confirm(answer):
    def respond():
        box=app.activeModalWidget()
        assert isinstance(box,QMessageBox)
        QTest.mouseClick(box.button(answer),Qt.MouseButton.LeftButton)
    QTimer.singleShot(50,respond)
    click('Delete')

try:
    pid=client.call('host.describe')['pid']
    window.composer.prompt_menu.catalog.client=client
    window.show();dialog=PromptLibraryDialog(window);dialog.show()
    until(lambda:not dialog.loading)
    dialog.name.setText('fixture');dialog.content.setPlainText('Original café 🌞 [clipboard]')
    click('Save');until(lambda:not dialog.saving and dialog.note.text()=='Prompt saved.')
    row=client.call('prompts.list')['prompts'][0]
    dialog.list.setCurrentRow(0);dialog.content.setPlainText('Unsaved local draft')
    external=PromptClient()
    external.call('prompts.save',{'id':row['id'],'name':row['name'],'content':'External café change','expectedRevision':row['revision']})
    dialog.refresh();until(lambda:not dialog.loading and 'changed elsewhere' in dialog.note.text())
    assert dialog.content.toPlainText()=='Unsaved local draft'
    click('Save');until(lambda:not dialog.saving)
    assert 'changed' in dialog.note.text().lower()
    assert dialog.content.toPlainText()=='Unsaved local draft'
    assert client.call('prompts.list')['prompts'][0]['content']=='External café change'
    click('Reload');assert dialog.content.toPlainText()=='External café change'
    dialog.name.setText('renamed');dialog.content.setPlainText('Resolved café 🌞 [clipboard] / [clipboard]')
    click('Save');until(lambda:not dialog.saving and dialog.note.text()=='Prompt saved.')
    saved=client.call('prompts.list')['prompts'][0]
    assert saved['id']==row['id'] and saved['name']=='renamed' and saved['content']=='Resolved café 🌞 [clipboard] / [clipboard]'
    dialog.hide();window.activateWindow();window.composer.setFocus();app.processEvents()
    sent=[];window.composer.submit_requested.connect(lambda:sent.append(True))
    app.clipboard().setText('Clipboard A [clipboard]')
    QTest.keyClicks(window.composer,'/renamed')
    until(lambda:window.composer.prompt_menu.isVisible() and bool(window.composer.prompt_menu.items))
    QTest.keyClick(window.composer,Qt.Key.Key_Tab)
    expanded='Resolved café 🌞 Clipboard A [clipboard] / Clipboard A [clipboard]'
    assert window.composer.toPlainText()==expanded and not sent
    app.clipboard().setText('Clipboard B');app.processEvents()
    assert window.composer.toPlainText()==expanded and not sent
    dialog.show();app.processEvents()
    dialog.list.setCurrentRow(0);confirm(QMessageBox.StandardButton.No)
    assert client.call('prompts.list')['prompts']==[saved]
    confirm(QMessageBox.StandardButton.Yes);until(lambda:not dialog.saving and dialog.note.text()=='Prompt deleted.')
    assert client.call('prompts.list')['prompts']==[]
    result={'appRoot':str(APP),'fixture':str(work),'realSharedService':True,'qtPlatform':'offscreen','saveAndRename':True,'externalConflictKeepsDraft':True,'staleSaveRefused':True,'reloadThenSave':True,'deleteCancelAndConfirm':True,'clipboardSubstitution':True,'clipboardChangesDoNotAlterDraft':True,'promptSelectionDoesNotSubmit':True}
    output=ROOT/'outputs/cross-platform/prompt-editor-proof.json';output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
finally:
    if dialog:dialog.close()
    window.close();app.processEvents();reserved.close()
    if pid:
        try:os.kill(pid,signal.SIGTERM)
        except ProcessLookupError:pass
