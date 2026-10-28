# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Explicit interactive Windows qualification; all input targets this authored widget.
import sys,json,time,traceback,threading,os,tempfile,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'services/desktop'))
from PySide6.QtWidgets import QApplication,QPlainTextEdit
from PySide6.QtCore import QTimer,QObject,Signal
from windows import WindowsDesktop,scene
events=[]
class Editor(QPlainTextEdit):
 def keyPressEvent(self,event):
  before=self.textCursor().position();super().keyPressEvent(event)
  events.append({'text':event.text(),'key':event.key(),'before':before,'after':self.textCursor().position()})
 def inputMethodEvent(self,event):
  events.append({'commit':event.commitString(),'preedit':event.preeditString(),'cursor':self.textCursor().position()});super().inputMethodEvent(event)
app=QApplication([]);editor=Editor();editor.setWindowTitle('Augmentor authored desktop verification');editor.resize(500,300);editor.show();editor.raise_();editor.activateWindow();editor.setFocus();backend=WindowsDesktop(lambda *_:None);results={}
service_mode='--service' in sys.argv
if service_mode:
 from client import call
 private=tempfile.TemporaryDirectory(prefix='augmentor-proof-')
 from platform_adapters.paths import private_directory
 proof_runtime=private_directory(Path(private.name)/'runtime')
 os.environ['AUGMENTOR_DESKTOP_SOCKET']=str(proof_runtime/'proof.sock')
 class Remote:
  def request(self,method,owner=None,params=None):
   request={'method':method,'owner':owner,'params':params or {}}
   if '--tool' in sys.argv:
    node=os.environ['AUGMENTOR_PI_NODE'];bridge=Path(__file__).with_name('windows-desktop-tool.mjs')
    completed=subprocess.run([node,str(bridge)],input=json.dumps(request),capture_output=True,text=True,encoding='utf-8',timeout=110)
    response=json.loads(completed.stdout)
   else:response=call(request)
   if not response.get('ok'):raise RuntimeError(response.get('error'))
   return response['result']
  def connect(self,owner):return self.request('connect',owner)
  def status(self):return self.request('status')
  def capture(self,owner):return self.request('capture',owner)
  def action(self,owner,params):return self.request('action',owner,params)
  def stop(self):return self.request('stop','pi:authored-verification')
 backend=Remote()
class Bridge(QObject):
 read=Signal();done=Signal()
bridge=Bridge();value={};event=threading.Event()
def read_main():value['text']=editor.toPlainText();event.set()
def finish_main():editor.close();app.quit()
bridge.read.connect(read_main);bridge.done.connect(finish_main)
def text():
 time.sleep(.2);event.clear();bridge.read.emit();assert event.wait(3);return value['text']
def run():
 try:
  backend.connect('pi:authored-verification');before=scene();assert before['window']['pid']==__import__('os').getpid(),before
  results['backend']=backend.status();results['inputBytes']=__import__('ctypes').sizeof(__import__('windows').Input)
  snap=backend.capture('pi:authored-verification');results['image']={k:v for k,v in snap['image'].items() if k!='data'};results['screens']=before['screens']
  backend.action('pi:authored-verification',{'token':snap['token'],'kind':'type','text':'Augmentor café 日本語 😀'});assert text()=='Augmentor café 日本語 😀',repr(value.get('text'));results['unicode']=True
  try:backend.action('pi:authored-verification',{'token':snap['token'],'kind':'type','text':'duplicate'})
  except RuntimeError:results['singleUse']=True
  snap=backend.capture('pi:authored-verification');backend.action('pi:authored-verification',{'token':snap['token'],'kind':'key','keys':['CTRL','A']})
  snap=backend.capture('pi:authored-verification');backend.action('pi:authored-verification',{'token':snap['token'],'kind':'type','text':'Replaced once'});assert text()=='Replaced once',repr(value.get('text'));results['chord']=True
  # Extended navigation keys must reach the target as well as ordinary chords.
  snap=backend.capture('pi:authored-verification');backend.action('pi:authored-verification',{'token':snap['token'],'kind':'key','keys':['HOME']})
  snap=backend.capture('pi:authored-verification');backend.action('pi:authored-verification',{'token':snap['token'],'kind':'type','text':'First: '});assert text()=='First: Replaced once';results['extendedKey']=True
  snap=backend.capture('pi:authored-verification');backend.action('pi:authored-verification',{'token':snap['token'],'kind':'key','keys':['CTRL','A']})
  long_text=('café 日本語 😀 '*30)[:256];started=time.monotonic()
  snap=backend.capture('pi:authored-verification');backend.action('pi:authored-verification',{'token':snap['token'],'kind':'type','text':long_text});assert text()==long_text,repr(value.get('text'));results['maxLengthText']={'characters':len(long_text),'seconds':round(time.monotonic()-started,2)}
  results['stop']=backend.stop()['stopped'];results['ok']=True;results['serviceMode']=service_mode;results['registeredToolBoundary']='--tool' in sys.argv
 except Exception:results['error']=traceback.format_exc();results['events']=events[-100:];results['ok']=False
 finally:
  backend.stop()
  if service_mode:
   try:backend.request('shutdown')
   except Exception as error:results['shutdownError']=str(error);results['ok']=False
  Path(__file__).with_name('proof-result.json').write_text(json.dumps(results));bridge.done.emit()
QTimer.singleShot(2000,lambda:threading.Thread(target=run,daemon=True).start());QTimer.singleShot(90000,app.quit);app.exec()
if service_mode:
 for attempt in range(50):
  try:private.cleanup();break
  except PermissionError:
   if attempt==49:raise
   time.sleep(.1)
sys.exit(0 if results.get('ok') else 1)
