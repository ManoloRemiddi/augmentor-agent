#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Live local Qwen + Qt copy, reply branching and edited resubmission in isolated state."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'apps/native'))
state=Path(tempfile.mkdtemp(prefix='augmentor-message-actions-'))
os.environ['AUGMENTOR_PI_CONFIG']=str(state/'config')
os.environ['AUGMENTOR_PI_STATE']=str(state/'state')
os.environ['AUGMENTOR_PI_WORKSPACE']=str(state/'work')
os.environ['QT_QPA_PLATFORM']='offscreen'
(state/'config/agent').mkdir(parents=True)
shutil.copy2(root/'config/models.local.example.json',state/'config/agent/models.json')
selection={'provider':'mx-qwen','model':'Qwen3.8-27B-UD-Q6_K_XL'}
(state/'config/settings.json').write_text(json.dumps({'revision':0,'defaultPreset':'workspace-write','pinned':[selection],'hidden':[],'defaultModel':selection}))
from PySide6.QtCore import QUrl
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from augmentor_linux.pi_client import PiClient
from augmentor_linux.window import Window
app=QApplication([]);app.setQuitOnLastWindowClosed(False)
client=PiClient();client.call('host.describe')
window=Window(preview=False);window.resize(440,680);window.show()
def wait(predicate,seconds=90):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        app.processEvents();QTest.qWait(20)
        if predicate():return
    raise AssertionError('Timed out: '+window.status.text())
def send(text):
    before=sum(role=='Augmentor' for role,_ in window.messages)
    window.composer.setPlainText(text);window.send()
    wait(lambda:not window.controller.running and sum(role=='Augmentor' for role,_ in window.messages)>before and window.send_button.isEnabled())
def action(name,index):window.transcript.anchorClicked.emit(QUrl(f'augmentor-{name}:{index}'))
def last_reply():return next(text for role,text in reversed(window.messages) if role=='Augmentor')
try:
    wait(lambda:window.controller.online);window.set_selection(selection)
    send('Remember the project word ORCHID. Reply with only ORCHID.')
    assert 'ORCHID' in last_reply()
    first_reply=next(i for i,(role,text) in enumerate(window.messages) if role=='Augmentor')
    action('copy',first_reply);assert app.clipboard().text()==window.messages[first_reply][1]
    send('Change the project word to MAGNOLIA. Reply with only MAGNOLIA.')
    assert 'MAGNOLIA' in last_reply()
    original=window.controller.session
    original_history=client.call('session.history',{'sessionId':original})
    action('branch',first_reply)
    wait(lambda:window.controller.session!=original and not window.controller.navigating and len(window.messages)==2)
    branch=window.controller.session
    assert all('MAGNOLIA' not in text for role,text in window.messages)
    question='What project word did I give you? Return only that word.'
    send(question);assert 'ORCHID' in last_reply() and 'MAGNOLIA' not in last_reply()
    branch_history=client.call('session.history',{'sessionId':branch})
    latest=max(i for i,(role,text) in enumerate(window.messages) if role=='You')
    action('copy',latest);assert app.clipboard().text()==question
    action('edit',latest);assert window.composer.toPlainText()==question
    revised='What project word did I give you? Return only that word followed by an exclamation mark.'
    window.composer.setPlainText(revised);window.send()
    wait(lambda:window.controller.session!=branch and not window.controller.running and window.editing is None and 'ORCHID!' in last_reply())
    assert 'ORCHID!' in last_reply(),last_reply()
    assert ('You',question) not in window.messages and ('You',revised) in window.messages
    assert client.call('session.history',{'sessionId':original})==original_history
    assert client.call('session.history',{'sessionId':branch})==branch_history
    (root/'outputs').mkdir(exist_ok=True)
    window.jump_latest();app.processEvents();window.grab().save(str(root/'outputs/message-actions.png'))
    proof={'date':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'model':selection['model'],'copyBothRoles':True,'earlierReplyBranch':True,'contextExcludesLaterTurns':True,'editAndResubmit':True,'originalChatsUnchanged':True,'finalReply':last_reply()}
    (root/'outputs/message-actions-proof.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof),flush=True)
finally:
    if window.controller.running:
        window.stop();wait(lambda:not window.controller.running)
    window.close();app.processEvents();client.call('host.shutdown')
