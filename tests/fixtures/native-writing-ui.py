# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual Qt writing controls; private authored data, no chat monitor or audio.

The optional root is an operator-selected artifact, never copied into fixtures.
Commands are single-shot test actions; an unknown result is not replayed.
"""
import json
import os
from pathlib import Path
import select
import sys
import time
root=Path(sys.argv[1]).resolve();expected_name=sys.argv[2] if len(sys.argv)>2 else 'shared-author';sys.path.insert(0,str(root))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication,QPushButton
from augmentor_linux.window import Window
from augmentor_linux.panels import PromptLibraryDialog
from augmentor_linux.prompt_client import PromptClient
from augmentor_linux.controller import Controller
import augmentor_linux.panels as panels
assert Path(panels.__file__).resolve()==root/'augmentor_linux/panels.py'
app=QApplication([]);window=Window(preview=True)
assert window.controller is None
# Use the actual controller task dispatcher. Do not start its chat monitor or
# bind the production voice/status timers for this writing-only UI exercise.
window.controller=Controller(window,harness='pi')
assert not window.controller.monitor_started
assert isinstance(window.composer.prompt_menu.catalog.client,PromptClient)
assert Path(window.composer.prompt_menu.catalog.client.base)==Path(os.environ['AUGMENTOR_SHARED_STATE'])/'prompts.sock'
window.composer.setPlainText('KEEP_AUTHORED_COMPOSER_DRAFT');window.show()
dialog=PromptLibraryDialog(window);dialog.show();buffer=b'';pending=None;announced=False
os.set_blocking(0,False)
def emit(value):print(json.dumps(value,ensure_ascii=False),flush=True)
def state():
 return {'rows':[{'id':r['id'],'name':r['name'],'revision':r['revision']} for r in dialog.rows],'name':dialog.name.text(),'content':dialog.content.toPlainText(),'note':dialog.note.text(),'instructions':dialog.improvement.editor.toPlainText(),'instructionNote':dialog.improvement.note.text(),'composer':window.composer.toPlainText(),'saving':dialog.saving,'loading':dialog.loading}
def button(label):
 candidates=[b for b in dialog.findChildren(QPushButton) if b.text()==label and b.isVisible()]
 assert len(candidates)==1,(label,len(candidates));return candidates[0]
def handle(command):
 global pending
 identity=command['id'];op=command['operation'];dialog.tabs.setCurrentIndex(1 if op.startswith('instructions-') else 0)
 if op=='state':emit({'id':identity,'result':state()});return
 if op=='select':
  index=next(i for i,r in enumerate(dialog.rows) if r['name']==command['name']);dialog.list.setCurrentRow(index)
 elif op=='edit':
  if 'name' in command:dialog.name.setText(command['name'])
  dialog.content.setPlainText(command['content'])
 elif op in ('save','refresh','reload'):button({'save':'Save','refresh':'Refresh','reload':'Reload'}[op]).click()
 elif op=='instructions-edit':dialog.improvement.editor.setPlainText(command['content'])
 elif op=='instructions-save':dialog.improvement.save_button.click()
 elif op=='instructions-reload':dialog.improvement.reload_button.click()
 elif op=='snapshot':
  assert str(Path(command['path']).resolve()).startswith(str(Path(os.environ['AUGMENTOR_SHARED_STATE']).parent.resolve())+os.sep)
  assert dialog.grab().save(command['path'])
 elif op=='close':
  dialog.accept();window.composer.clear();window.close();emit({'id':identity,'result':{'closed':True}});QTimer.singleShot(50,app.quit);return
 else:raise ValueError('Unsupported authored UI action')
 pending=(identity,time.monotonic()+10)
def tick():
 global buffer,pending,announced
 try:
  if not announced and not dialog.loading and any(r['name']==expected_name for r in dialog.rows):
   announced=True;emit({'ready':True,'requestedModule':True,'chatMonitorStarted':window.controller.monitor_started,'realTaskDispatcher':True,'state':state()})
  if pending:
   identity,deadline=pending
   if not dialog.loading and not dialog.saving and not dialog.improvement.saving:
    pending=None;emit({'id':identity,'result':state()})
   elif time.monotonic()>deadline:raise TimeoutError('Actual Qt writing action did not settle; not replayed')
  if not pending and select.select([0],[],[],0)[0]:
   chunk=os.read(0,65536)
   if not chunk:dialog.reject();window.composer.clear();window.close();app.quit();return
   buffer+=chunk
   if len(buffer)>65536:raise ValueError('Authored UI command exceeds bound')
  if not pending and b'\n' in buffer:
   line,buffer=buffer.split(b'\n',1);handle(json.loads(line))
 except BaseException as error:
  emit({'fatal':type(error).__name__+': '+str(error)});dialog.reject();window.composer.clear();window.close();app.exit(1)
timer=QTimer();timer.timeout.connect(tick);timer.start(10)
code=app.exec();sys.exit(code)
