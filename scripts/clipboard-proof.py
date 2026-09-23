#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise prompt editing, persistence and clipboard insertion with an isolated Pi host."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import threading
from types import SimpleNamespace
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'apps/native'))
state=Path(tempfile.mkdtemp(prefix='augmentor-clipboard-proof-'))
os.environ['AUGMENTOR_PI_CONFIG']=str(state/'config')
os.environ['AUGMENTOR_PI_STATE']=str(state/'state')
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from augmentor_linux.window import Window
from augmentor_linux.panels import PromptLibraryDialog
from augmentor_linux.pi_client import PiClient
app=QApplication([]);app.setQuitOnLastWindowClosed(False)
client=PiClient();client.call('host.describe')
window=Window();window.controller=SimpleNamespace(client=client,close=lambda:None,closed=False,running=False,task=lambda work:threading.Thread(target=work,daemon=True).start())
window.composer.prompt_menu.catalog.client=client
window.show();window.activateWindow()
def wait(predicate):
    end=time.monotonic()+10
    while time.monotonic()<end:
        app.processEvents();QTest.qWait(20)
        if predicate():return
    raise AssertionError('UI operation timed out')
try:
    dialog=PromptLibraryDialog(window);dialog.show()
    wait(lambda:window.composer.prompt_menu.catalog.loaded)
    dialog.name.setText('rewrite')
    prefix='Rewrite the quoted sentence. Keep the intent and every fact. Use plain, human-sounding English: short sentences, everyday words, no jargon. Fix all errors, cut wordiness, never use em dashes (—), keep the original tone. If the meaning is unclear, ask first. Return only the improved sentence.\n\n"'
    dialog.content.setPlainText(prefix)
    cursor=dialog.content.textCursor();cursor.movePosition(cursor.MoveOperation.End);dialog.content.setTextCursor(cursor)
    QTest.mouseClick(dialog.clipboard_button,Qt.MouseButton.LeftButton)
    dialog.content.insertPlainText('"')
    template=prefix+'[clipboard]"'
    assert dialog.content.toPlainText()==template
    dialog.save();wait(lambda:bool(dialog.rows))
    path=state/'config/agent/prompts/rewrite.md'
    assert path.read_text()==template
    dialog.close();dialog=PromptLibraryDialog(window);dialog.show();wait(lambda:bool(dialog.rows))
    dialog.list.setCurrentRow(0)
    assert dialog.content.toPlainText()==template
    (root/'outputs').mkdir(exist_ok=True)
    app.processEvents();dialog.grab().save(str(root/'outputs/prompt-library-clipboard.png'))
    dialog.close();window.activateWindow();window.composer.setFocus();app.processEvents()
    copied='This sentence need a few small fixes.\nPlease keep café and 😀.'
    app.clipboard().setText(copied)
    sent=[];window.composer.submit_requested.connect(lambda:sent.append(True))
    QTest.keyClicks(window.composer,'/rewrite')
    wait(lambda:bool(window.composer.prompt_menu.items))
    QTest.keyClick(window.composer,Qt.Key.Key_Return)
    assert window.composer.toPlainText()==template.replace('[clipboard]',copied)
    assert not sent
    assert path.read_text()==template
    proof={'date':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'realPiStore':True,'editorButton':True,'reopenedLiteralTemplate':True,'multilineUnicodeExpansion':True,'insertDoesNotSend':True}
    (root/'outputs/clipboard-proof.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof))
finally:
    window.close();client.call('host.shutdown')
