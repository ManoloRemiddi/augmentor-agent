#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real Pi/Qwen + Qt acceptance in separate application state."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'apps/native'))
state=Path(tempfile.mkdtemp(prefix='augmentor-pi-live-'))
os.environ['AUGMENTOR_PI_CONFIG']=str(state/'config')
os.environ['AUGMENTOR_PI_STATE']=str(state/'state')
os.environ['AUGMENTOR_PI_WORKSPACE']=str(state/'work')
os.environ['QT_QPA_PLATFORM']='xcb' if os.environ.get('DISPLAY') else 'offscreen'
(state/'config/agent').mkdir(parents=True)
shutil.copy2(root/'config/models.local.example.json',state/'config/agent/models.json')
selection={'provider':'mx-qwen','model':'Qwen3.8-27B-UD-Q6_K_XL'}
(state/'config/settings.json').write_text(json.dumps({'revision':0,'defaultPreset':'workspace-write','pinned':[selection],'hidden':[],'defaultModel':selection}))
from augmentor_linux.runtime_start import ensure_running
ensure_running()
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from augmentor_linux.window import Window
from augmentor_linux.pi_client import PiClient
from augmentor_linux.browser import refresh_accessibility_bus
refresh_accessibility_bus()
app=QApplication([])
app.setQuitOnLastWindowClosed(False)
window=Window(preview=False);window.show()
def wait(predicate,seconds=90):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        app.processEvents();QTest.qWait(20)
        if predicate():return
    raise AssertionError('Timed out; status='+window.status.text()+'; messages='+str(window.messages))
wait(lambda:window.controller.online)
window.set_selection(selection)
window.composer.setPlainText('Use linux_system_profile once to inspect this machine. Reply briefly with the Linux distribution and desktop you actually found.')
window.send()
wait(lambda:window.controller.session is not None)
sid=window.controller.session
wait(lambda:not window.controller.running and any(r=='Augmentor' for r,t in window.messages))
assert any('MX' in t for r,t in window.messages if r=='Augmentor'),window.messages
assert any(e['type']=='tool/result' and e['data']['name']=='linux_system_profile' for e in window.controller.loaded_events)
# Approve only the expected scratch-file write requested by this test.
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox
written=state/'work/pi-proof.txt'
approvals=[]
def approve_scratch():
    dialog=QApplication.activeModalWidget()
    if isinstance(dialog,QMessageBox) and 'write' in dialog.text() and str(written) in dialog.text():
        approvals.append(True);dialog.done(QMessageBox.StandardButton.Yes)
timer=QTimer();timer.timeout.connect(approve_scratch);timer.start(20)
window.composer.setPlainText('Use the write tool to write exactly PI_FILE_OK to '+str(written)+'. Do not use bash. Then reply done.')
window.send();wait(lambda:window.controller.running);wait(lambda:not window.controller.running and written.exists())
timer.stop();assert approvals and written.read_text()=='PI_FILE_OK'
client=PiClient();client.saved_chats('save',sid);client.call('session.rename',{'sessionId':sid,'title':'Pi Linux acceptance'})
client.call('prompts.save',{'name':'acceptance','content':'Summarise the current task.'})
assert client.call('prompts.list')['prompts'][0]['name']=='acceptance'
position=window.geometry();window.hide();app.processEvents();window.bring_forward();app.processEvents();assert window.geometry()==position
window.composer.setPlainText('Preserved draft');window.toggle_compact();app.processEvents();assert window.composer.toPlainText()=='Preserved draft';window.toggle_compact()
(root/'outputs').mkdir(exist_ok=True)
window.grab().save(str(root/'outputs/pi-native-live.png'))
messages=list(window.messages)
window.controller.close();window.controller=None;window.close()
window=Window(preview=False);window.show();wait(lambda:window.controller.online and any(r=='Augmentor' for r,t in window.messages))
assert window.controller.session==sid
assert any('MX' in t for r,t in window.messages if r=='Augmentor')
window.set_selection(selection);window.composer.setPlainText('Write a very long detailed essay about Linux filesystems.');window.send();wait(lambda:window.controller.running);QTest.qWait(900);window.stop();wait(lambda:not window.controller.running)
assert any(e['type']=='turn/end' and e['data'].get('reason',{}).get('kind')=='aborted' for e in window.controller.loaded_events)
result={'state':str(state),'sessionId':sid,'liveProfile':True,'liveWriteWithNativeApproval':True,'sameQtUI':True,'saveRename':True,'prompts':True,'hideRestore':True,'compactDraft':True,'uiRestartResume':True,'stop':True,'messages':messages}
(root/'outputs/live-acceptance.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
window.close();app.processEvents()
client.call('host.shutdown')
