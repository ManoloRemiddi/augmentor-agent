# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Rendered production Qt settings against the isolated real Pi host."""
import json,os,time
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt,QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QPushButton
from augmentor_linux.pi_client import PiClient
from augmentor_linux.window import Window
from augmentor_linux.panels import SettingsDialog
from augmentor_linux.reasoning_settings import ReasoningDialog
app=QApplication([]);client=PiClient();sid='reasoning';errors=[]
pointer=Path(os.environ['AUGMENTOR_PI_STATE'])/'session.json'
pointer.write_text(json.dumps({'endpoint':client.base,'session':sid,'selection':{'provider':'test','model':'reasoning'}}));pointer.chmod(0o600)
def until(check,label):
 end=time.monotonic()+10
 while time.monotonic()<end:
  app.processEvents()
  if check():return
  QTest.qWait(10)
 raise AssertionError('Native reasoning timeout: '+label)
window=Window(preview=False,harness='pi');window.show()
initial=client.call('reasoning.describe');original=client.call('session.reasoning',{'sessionId':sid})
try:
 until(lambda:window.controller.online and window.controller.connected and window.send_button.isEnabled(),'connected')
 shortcuts_patch=patch('augmentor_linux.shortcut_settings.current_keys',return_value=[]);shortcuts_patch.start()
 settings=SettingsDialog(window)
 settings.show();app.processEvents()
 def exercise():
  dialog=None
  try:
   dialog=window.findChildren(ReasoningDialog)[-1];until(lambda:dialog.session is not None and not dialog.saving,'loaded settings')
   assert window.controller.client.capabilities['reasoning'] is True
   dialog.level.setCurrentIndex(dialog.level.findData('medium'));dialog.mode.setCurrentIndex(dialog.mode.findData('manual'))
   QTest.mouseClick(dialog.save_session,Qt.MouseButton.LeftButton);until(lambda:dialog.note.text()=='Conversation reasoning saved.','saved manual')
   assert client.call('session.reasoning',{'sessionId':sid})['thinkingLevel']=='medium'
   dialog.tabs.setCurrentIndex(1);QTest.mouseClick(dialog.add_button,Qt.MouseButton.LeftButton)
   route=next(r for r in dialog.routes if r['route']['model']=='reasoning') if dialog.routes else None
   # Choose the reasoning fixture explicitly; the first catalog entry can be another model.
   if not route:
    for index in range(dialog.model_choice.count()):
     if dialog.model_choice.itemData(index)['model']=='reasoning':dialog.model_choice.setCurrentIndex(index);break
    QTest.mouseClick(dialog.add_button,Qt.MouseButton.LeftButton);route=next(r for r in dialog.routes if r['route']['model']=='reasoning')
   route['controls']['off'].setCurrentIndex(route['controls']['off'].findData('low'))
   external=client.call('reasoning.describe');client.call('reasoning.configure',{'expectedRevision':external['revision'],'config':external['config']})
   QTest.mouseClick(dialog.save_policy,Qt.MouseButton.LeftButton);until(lambda:'Settings changed' in dialog.note.text() and not dialog.saving,'stale policy refused')
   assert route['controls']['off'].currentData()=='low'
   QTest.mouseClick(dialog.reload_button,Qt.MouseButton.LeftButton);until(lambda:not dialog.saving and not dialog.routes,'explicit reload')
   for index in range(dialog.model_choice.count()):
    if dialog.model_choice.itemData(index)['model']=='reasoning':dialog.model_choice.setCurrentIndex(index);break
   dialog.tabs.setCurrentIndex(1);QTest.mouseClick(dialog.add_button,Qt.MouseButton.LeftButton)
   dialog.routes[0]['controls']['off'].setCurrentIndex(dialog.routes[0]['controls']['off'].findData('low'))
   QTest.mouseClick(dialog.save_policy,Qt.MouseButton.LeftButton);until(lambda:dialog.note.text()=='Adaptive policy saved.','saved mapping')
   assert client.call('reasoning.describe')['config']['routes'][0]['efforts']['off']=='low'
   dialog.tabs.setCurrentIndex(0);dialog.mode.setCurrentIndex(dialog.mode.findData('adaptive'))
   QTest.mouseClick(dialog.save_session,Qt.MouseButton.LeftButton);until(lambda:dialog.note.text()=='Conversation reasoning saved.','saved adaptive')
   assert client.call('session.reasoning',{'sessionId':sid})['adaptiveStatus']=='configured'
   if os.environ.get('AUGMENTOR_NATIVE_REASONING_SCREENSHOT'):
    assert dialog.grab().save(os.environ['AUGMENTOR_NATIVE_REASONING_SCREENSHOT'])
    dialog.tabs.setCurrentIndex(1);dialog.tabs.widget(1).ensureWidgetVisible(dialog.save_policy);app.processEvents()
    assert dialog.grab().save(os.environ['AUGMENTOR_NATIVE_REASONING_SCREENSHOT'].replace('.png','-policy.png'))
   next(b for b in dialog.findChildren(QPushButton) if b.text()=='Done').click()
  except Exception as error:
   errors.append(repr(error))
   if dialog:dialog.reject()
 QTimer.singleShot(0,exercise)
 QTest.mouseClick(next(b for b in settings.findChildren(QPushButton) if b.text()=='Reasoning'),Qt.MouseButton.LeftButton)
 assert not errors,errors
 settings.close()
 # Opening again reads committed settings, not an unsaved GUI preference.
 reopened=ReasoningDialog(window);reopened.show();until(lambda:reopened.session is not None and not reopened.saving,'reopened')
 assert reopened.mode.currentData()=='adaptive' and reopened.level.currentData()=='medium'
 assert reopened.routes[0]['controls']['off'].currentData()=='low'
 window.controller.session='other-conversation';reopened.check_context();assert reopened.closed and not reopened.isVisible()
 window.controller.session=sid
 print(json.dumps({'qualified':'native-pi-reasoning','savedEffort':'medium','revisionConflict':'draft-preserved','reopen':True,'scopeGuard':True}))
finally:
 if 'shortcuts_patch' in globals():shortcuts_patch.stop()
 current=client.call('reasoning.describe');client.call('reasoning.configure',{'expectedRevision':current['revision'],'config':initial['config']})
 current=client.call('session.reasoning',{'sessionId':sid});client.call('session.selectReasoning',{'sessionId':sid,'expectedRevision':current['revision'],'mode':original['mode'],'thinkingLevel':original['thinkingLevel']})
 if window.controller:window.controller.close();window.controller=None
 window.close();app.processEvents()
