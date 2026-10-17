# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual production settings, Pi RPC and stale callback; disposable profile only."""
import json,os,time,threading
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from augmentor_linux.pi_client import PiClient
from augmentor_linux.window import Window
app=QApplication([]);client=PiClient();sid='inspection-parent';errors=[];opened=[]
pointer=Path(os.environ['AUGMENTOR_PI_STATE'])/'session.json'
pointer.write_text(json.dumps({'endpoint':client.base,'session':sid,'selection':{'provider':'fixture','model':'harness-fixture'}}));pointer.chmod(0o600)
def until(check,label):
 end=time.monotonic()+10
 while time.monotonic()<end:
  app.processEvents()
  if check():return
  QTest.qWait(10)
 raise AssertionError('Native Pi inspection timeout: '+label+' '+str({'errors':errors,'status':window.status.text(),'session':window.controller.session,'online':window.controller.online}))
window=Window(preview=False,harness='pi');window.show();window.controller.problem.connect(errors.append)
try:
 until(lambda:window.controller.online and window.controller.connected,'connected')
 assert window.controller.capabilities['inspection'] is True
 before=client.call('session.history',{'sessionId':sid})
 def navigate(url):opened.append(url.toString());return True
 with patch('augmentor_linux.window.QDesktopServices.openUrl',side_effect=navigate),patch.object(window,'open_inspector',wraps=window.open_inspector) as trigger:
  QTest.mouseClick(window.more_button,Qt.MouseButton.LeftButton)
  until(lambda:window.settings_panel is not None,'actual settings open')
  panel=window.settings_panel;QTest.mouseClick(panel.nav['all'],Qt.MouseButton.LeftButton)
  until(lambda:getattr(panel,'inspector_action',None) is not None and panel.inspector_action.isVisible() and panel.inspector_action.isEnabled(),'actual inspection action available')
  image=Path(__file__).resolve().parents[2]/'outputs/harness-proof/native-inspection-settings.png';image.parent.mkdir(parents=True,exist_ok=True);panel.grab().save(str(image))
  QTest.mouseClick(panel.inspector_action,Qt.MouseButton.LeftButton)
  until(lambda:len(opened)==1,'actual settings navigation calls='+str(trigger.call_count))
  assert trigger.call_count==1;assert panel.accept()
  until(lambda:window.settings_panel is None,'return to original conversation')
  controller=window.controller;original=controller.client.call;entered=threading.Event();release=threading.Event();finished=threading.Event()
  def delayed(method,params=None,**kwargs):
   if method!='inspection.open':return original(method,params,**kwargs)
   entered.set();assert release.wait(3)
   try:return original(method,params,**kwargs)
   finally:finished.set()
  delivered=threading.Event();background=window.call_in_background
  def tracked(fn,callback):
   def complete(value):
    try:callback(value)
    finally:delivered.set()
   return background(fn,complete)
  with patch.object(window,'call_in_background',side_effect=tracked):
   with patch.object(controller.client,'call',side_effect=delayed):
    window.open_inspector();until(entered.is_set,'pending inspection');controller.session='inspection-foreign';release.set();until(finished.is_set,'completed RPC');until(delivered.is_set,'stale callback delivered');assert len(opened)==1,'stale callback must not navigate';controller.session=sid
   delivered.clear()
   with patch.object(controller.client,'call',return_value={'url':'https://unrelated.invalid/#token=fixture','sessionId':sid,'mode':'read-only'}):
    window.open_inspector();until(delivered.is_set,'invalid destination callback delivered');assert len(opened)==1,'invalid destination must not navigate'
 assert client.call('session.history',{'sessionId':sid})==before
 image=Path(__file__).resolve().parents[2]/'outputs/harness-proof/native-inspection.png';image.parent.mkdir(parents=True,exist_ok=True);window.grab().save(str(image))
 assert not errors
 print(json.dumps({'nativeInspection':'passed','url':opened[0]}),flush=True)
finally:
 window.controller.running=False;window.controller.close();window.controller=None;window.close()
