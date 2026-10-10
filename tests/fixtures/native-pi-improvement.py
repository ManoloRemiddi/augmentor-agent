# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Production composer pointer/keyboard events and real Pi draft cancellation."""
import json,os,time
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from augmentor_linux.pi_client import PiClient
from augmentor_linux.window import Window
app=QApplication([]);client=PiClient();sid='draft-parent';errors=[]
pointer=Path(os.environ['AUGMENTOR_PI_STATE'])/'session.json'
pointer.write_text(json.dumps({'endpoint':client.base,'session':sid,'selection':{'provider':'fixture','model':'harness-fixture'}}));pointer.chmod(0o600)
def until(check,label):
 end=time.monotonic()+10
 while time.monotonic()<end:
  app.processEvents()
  if check():return
  QTest.qWait(10)
 raise AssertionError('Native Pi improvement timeout: '+label+' '+str(errors))
window=Window(preview=False,harness='pi');window.show();window.controller.problem.connect(errors.append)
def click():QTest.mouseClick(window.composer.improve_button,Qt.MouseButton.LeftButton)
try:
 until(lambda:window.controller.online and window.controller.connected and window.send_button.isEnabled(),'connected')
 before=client.call('session.history',{'sessionId':sid});assert window.controller.client.capabilities['promptImprovement'] is True
 window.composer.setPlainText('Native café draft');click();until(lambda:window.composer.toPlainText()=='Improved Native café draft' and not window.composer.improving,'rewrite')
 assert window.composer.improvement_undo;assert client.call('session.history',{'sessionId':sid})==before
 image=Path(__file__).resolve().parents[2]/'outputs/harness-proof/native-improvement.png';image.parent.mkdir(parents=True,exist_ok=True);window.grab().save(str(image))
 click();assert window.composer.toPlainText()=='Native café draft'
 window.composer.setPlainText('IMPROVE_INVALID');click();until(lambda:not window.composer.improving,'invalid response');assert window.composer.toPlainText()=='IMPROVE_INVALID'
 for gesture in ['escape','typing','newchat']:
  window.composer.setPlainText('IMPROVE_SLOW '+gesture);click();identity=window.composer.improvement_id;assert identity
  until(lambda:(client.call('prompt.improvementStatus',{'requestId':identity})['receipt'] or {}).get('requests')==1,'actual slow request')
  if gesture=='escape':QTest.keyClick(window.composer,Qt.Key.Key_Escape)
  elif gesture=='typing':window.composer.setPlainText('New typing stays here')
  else:QTest.mouseClick(window.new_button,Qt.MouseButton.LeftButton)
  until(lambda:not window.composer.improving,'cancelled composer')
  until(lambda:client.call('prompt.improvementStatus',{'requestId':identity})['receipt']['status']=='cancelled','cancelled SDK request')
  assert window.composer.toPlainText()==('IMPROVE_SLOW escape' if gesture=='escape' else 'New typing stays here' if gesture=='typing' else '')
 assert client.call('session.history',{'sessionId':sid})==before
 assert not errors
 print(json.dumps({'nativeImprovement':'passed'}),flush=True)
finally:
 window.controller.running=False;window.controller.close();window.controller=None;window.close()
