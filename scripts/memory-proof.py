#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real Hindsight + actual Qt form + independent shared-service client.

HINDSIGHT_TEST_ENDPOINT must name an expendable local 0.9.2 service. The fixture
creates two dedicated banks and deletes its own documents after verification.
No developer model credentials or Augmentor profile are copied.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
APP_ROOT=Path(os.environ.get('AUGMENTOR_PROOF_APP_ROOT',ROOT)).resolve()
sys.path.insert(0,str(APP_ROOT/'apps/native'))
endpoint=os.environ.get('HINDSIGHT_TEST_ENDPOINT','http://127.0.0.1:8887')
assert endpoint.startswith('http://127.0.0.1:'),'Use a disposable local Hindsight instance'
work=Path(tempfile.mkdtemp(prefix='augmentor-memory-proof-',dir='/tmp' if sys.platform=='darwin' else None));suffix=uuid.uuid4().hex[:12]
os.environ.update(QT_QPA_PLATFORM=os.environ.get('QT_QPA_PLATFORM','offscreen'),XDG_CONFIG_HOME=str(work/'config'),
    XDG_DATA_HOME=str(work/'data'),XDG_STATE_HOME=str(work/'state'),AUGMENTOR_SHARED_STATE=str(work/'shared-state'),AUGMENTOR_SHARED_DATA=str(work/'shared-data'))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from augmentor_linux.window import Window
from augmentor_linux.memory import MemoryDialog
from augmentor_linux.prompt_client import PromptClient

app=QApplication([]);window=Window(preview=True);window.show();dialog=MemoryDialog(window);dialog.show();dialog.tabs.setCurrentIndex(1);client=PromptClient()
def until(check,seconds=90):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        app.processEvents();QTest.qWait(20)
        if check():return
    raise AssertionError('Memory UI timed out: '+dialog.note.text())
def rpc(method,params=None):return client.call('memory.'+method,params or {})
records=[]
try:
    until(lambda:not dialog.busy)
    assert not rpc('describe')['enabled']
    dialog.endpoint.setText(endpoint);dialog.user.setText('augmentor-ui-user-'+suffix);dialog.project.setText('augmentor-ui-project-'+suffix)
    QTest.mouseClick(dialog.check,Qt.MouseButton.LeftButton);until(lambda:dialog.save.isEnabled())
    assert not rpc('describe')['enabled'],'Check saved the connection'
    QTest.mouseClick(dialog.save,Qt.MouseButton.LeftButton);until(lambda:dialog.config.get('enabled') and not dialog.busy)
    assert (work/'shared-data/memory.sqlite3').stat().st_mode&0o777==0o600
    dialog.tabs.setCurrentIndex(2)
    fact='The acceptance user has the nickname Amber Comet '+suffix+'. They prefer concise paragraphs.'
    dialog.text.setPlainText(fact);QTest.mouseClick(dialog.retain,Qt.MouseButton.LeftButton)
    until(lambda:bool(rpc('operations')['items']))
    record=rpc('operations')['items'][0];records.append(('user',record))
    until(lambda:rpc('operation',{'id':record['id']})['status']=='completed')
    until(lambda:not dialog.busy);dialog.refresh();until(lambda:not dialog.busy and len(dialog.documents)==1)
    dialog.list.setCurrentRow(0);until(lambda:fact in dialog.contents.toPlainText())
    dialog.grab().save(str(ROOT/'outputs/memory-native.png'))
    # A separate Node process uses the same boundary as both engine plugins.
    command="import {recall} from './dist/memory/src/index.js';console.log(JSON.stringify(await recall('What is the acceptance user nickname?')));"
    found=json.loads(subprocess.check_output(['node','--input-type=module','-e',command],cwd=APP_ROOT,text=True,env=os.environ))
    assert any(suffix in row['text'] for row in found['results']),found
    engines=None
    if os.environ.get('DSH_TEST_MODULES'):
        from proof_memory_engines import prove
        engines=prove(APP_ROOT,work,suffix)
    # Separate banks prove a project fact cannot leak into user-scope recall.
    project=rpc('retain',{'scope':'project','content':'The private project codename is Violet Harbor '+suffix+'.','provenance':{'surface':'browser','harness':'dsh'}})
    records.append(('project',project))
    until(lambda:rpc('operation',{'scope':'project','id':project['id']})['status']=='completed')
    user=rpc('agentRecall',{'query':'What is the project codename?'})
    assert not any('Violet Harbor' in row['text'] for row in user['results'])
    project_result=rpc('recall',{'scope':'project','query':'What is the project codename?'})
    assert any('Violet Harbor' in row['text'] for row in project_result['results'])
    exported=rpc('exportPage',{'scope':'user','offset':0})
    assert exported['total']>=1 and any(suffix in row['text'] for row in exported['items'])
    until(lambda:not dialog.busy);dialog.tabs.setCurrentIndex(1);QTest.mouseClick(dialog.disable,Qt.MouseButton.LeftButton);until(lambda:not dialog.config.get('enabled') and not dialog.busy)
    assert rpc('agentRecall',{'query':'nickname'})=={'enabled':False,'results':[],'scope':'user'}
    assert rpc('document',{'id':record['document']})['original_text']==fact
    for scope,row in records:rpc('delete',{'scope':scope,'id':row['document']})
    assert rpc('documents',{'scope':'user'})['total']==0;assert rpc('documents',{'scope':'project'})['total']==0
    with __import__('sqlite3').connect(work/'shared-data/memory.sqlite3') as db:
        assert db.execute("SELECT count(*) FROM operations WHERE content<>''").fetchone()[0]==0
    result={'hindsight':'0.9.2','qtCheckSaveRetainViewDisable':True,'independentNodeRecall':True,'userProjectIsolation':True,
        'asyncCompletionObserved':True,'factExportVerified':True,'remoteAndLocalDeleteVerified':True,'engineTools':engines,'testState':str(work),'appRoot':str(APP_ROOT)}
    (ROOT/'outputs/memory-proof.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
finally:
    dialog.reject();window.close();app.processEvents()
    try:os.kill(client.call('host.describe')['pid'],15)
    except (ProcessLookupError,RuntimeError):pass
