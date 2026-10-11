# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual production menu, Pi RPC and stale callback; disposable profile only."""
import json,os,time,threading
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt,QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QMenu
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
 def choose():
  menu=app.activePopupWidget();assert isinstance(menu,QMenu)
  action=next(action for action in menu.actions() if action.text()=='Trajectory && Context');assert action.isEnabled()
  menu.setActiveAction(action)
  image=Path(__file__).resolve().parents[2]/'outputs/harness-proof/native-inspection-menu.png';image.parent.mkdir(parents=True,exist_ok=True);menu.grab().save(str(image))
  QTest.keyClick(menu,Qt.Key.Key_Return)
 def navigate(url):opened.append(url.toString());return True
 with patch('augmentor_linux.window.QDesktopServices.openUrl',side_effect=navigate),patch.object(window,'open_inspector',wraps=window.open_inspector) as trigger:
  QTimer.singleShot(50,choose);QTest.mouseClick(window.more_button,Qt.MouseButton.LeftButton)
  until(lambda:len(opened)==1,'actual menu navigation calls='+str(trigger.call_count))
  controller=window.controller;original=controller.client.call;entered=threading.Event();release=threading.Event();finished=threading.Event()
  def delayed(method,params=None,**kwargs):
   if method!='inspection.open':return original(method,params,**kwargs)
   entered.set();assert release.wait(3)
   try:return original(method,params,**kwargs)
   finally:finished.set()
  with patch.object(controller.client,'call',side_effect=delayed):
   window.open_inspector();until(entered.is_set,'pending inspection');controller.session='inspection-foreign';release.set();until(finished.is_set,'completed RPC');QTest.qWait(100);app.processEvents();assert len(opened)==1,'stale callback must not navigate';controller.session=sid
  with patch.object(controller.client,'call',return_value={'url':'https://unrelated.invalid/#token=fixture','sessionId':sid,'mode':'read-only'}):
   window.open_inspector();QTest.qWait(100);app.processEvents();assert len(opened)==1,'invalid destination must not navigate'
 assert client.call('session.history',{'sessionId':sid})==before
 image=Path(__file__).resolve().parents[2]/'outputs/harness-proof/native-inspection.png';image.parent.mkdir(parents=True,exist_ok=True);window.grab().save(str(image))
 assert not errors
 print(json.dumps({'nativeInspection':'passed','url':opened[0]}),flush=True)
finally:
 window.controller.running=False;window.controller.close();window.controller=None;window.close()
