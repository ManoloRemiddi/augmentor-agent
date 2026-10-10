# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Production Qt Window/Controller/Pi socket with synthetic native branch history."""
import json,os,time
from pathlib import Path
from PySide6.QtCore import Qt,QPoint,QUrl
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from augmentor_linux.pi_client import PiClient
from augmentor_linux.window import Window

app=QApplication([]);client=PiClient();parent='branch-native';windows=[];problems=[]
pointer=Path(os.environ['AUGMENTOR_PI_STATE'])/'session.json'
pointer.write_text(json.dumps({'endpoint':client.base,'session':parent,'selection':{'provider':'test','model':'test'}}));pointer.chmod(0o600)

def until(check,label):
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        app.processEvents()
        if check():return
        QTest.qWait(10)
    raise AssertionError('Native Pi branch fixture timed out: '+label+'; problems='+repr(problems))

def open_window():
    window=Window(preview=False,harness='pi');windows.append(window)
    window.controller.problem.connect(problems.append);window.show()
    until(lambda:window.controller.online and window.controller.connected and window.send_button.isEnabled(),'connected production Window')
    return window

def close_window(window):
    if window.controller:window.controller.close();window.controller=None
    window.close();app.processEvents()

def history(sid):return client.call('session.history',{'sessionId':sid,'maxMessages':100})
def human(window):return [text for who,text in window.messages if who=='You']
def settled(window,sid):
    until(lambda:window.controller.session==sid and not window.controller.running and not window.controller.navigating and not window.controller.preparing and window.can_change_message(),'settled '+sid)

def click_anchor(window,action,seq):
    index=next(index for index,event in window.message_events.items() if event['seq']==seq)
    href='augmentor-'+action+':'+str(index)
    window.render_messages();app.processEvents();document=window.transcript.document();block=document.begin()
    while block.isValid():
        fragments=block.begin()
        while not fragments.atEnd():
            fragment=fragments.fragment();fragments+=1
            if not fragment.isValid() or fragment.charFormat().anchorHref()!=href:continue
            cursor=QTextCursor(document);cursor.setPosition(fragment.position());window.transcript.setTextCursor(cursor);window.transcript.ensureCursorVisible();app.processEvents()
            rect=window.transcript.cursorRect(cursor);point=QPoint(rect.left()+4,rect.center().y())
            assert window.transcript.anchorAt(point)==href,(href,window.transcript.anchorAt(point))
            QTest.mouseClick(window.transcript.viewport(),Qt.MouseButton.LeftButton,pos=point);return
        block=block.next()
    raise AssertionError('Visible message anchor missing: '+href)

def send(window,text):
    window.composer.setPlainText(text);QTest.keyClick(window.composer,Qt.Key.Key_Return)
    assert window.composer.toPlainText()=='','Enter must capture the draft before the backend runs'

try:
    window=open_window();settled(window,parent)
    until(lambda:'NATIVE_BRANCH_PARENT_TWO' in human(window),'parent history rendered')
    original=history(parent);reply=next(row['event'] for row in original['events'] if row['event']['type']=='assistant/message' and not any(part['type']=='toolCall' for part in row['event']['data']['message']['content']))
    click_anchor(window,'branch',reply['seq'])
    until(lambda:window.controller.session!=parent and not window.controller.navigating,'reply branch selected');child=window.controller.session;settled(window,child)
    until(lambda:human(window)==['NATIVE_BRANCH_PARENT_ONE'],'exact branch display')
    assert not any(row['kind']=='model/request' for row in client.call('observation.list',{'sessionId':child})['records'])
    assert history(parent)==original
    send(window,'/native_branch_fixture original');settled(window,child)
    until(lambda:'/native_branch_fixture original' in human(window),'original template submission rendered')
    child_before=history(child);target=next(row['event'] for row in reversed(child_before['events']) if row['event']['type']=='user/message')
    assert target['data']['content'][0]['text']=='NATIVE_BRANCH_CHILD original',target['data']
    assert target['data']['submittedContent'][0]['text']=='/native_branch_fixture original'
    count=len(client.session_rows());window.composer.setPlainText('Native saved draft')
    click_anchor(window,'edit',target['seq']);assert window.composer.toPlainText()=='/native_branch_fixture original'
    assert window.edit_bar.isVisible() and len(client.session_rows())==count
    QTest.mouseClick(window.cancel_edit_button,Qt.MouseButton.LeftButton);assert window.composer.toPlainText()=='Native saved draft'
    assert len(client.session_rows())==count and history(child)==child_before
    click_anchor(window,'edit',target['seq']);send(window,'NATIVE_BRANCH_REVISED')
    until(lambda:window.controller.session!=child,'edit child selected');edited=window.controller.session
    settled(window,edited);until(lambda:window.editing is None and window.composer.toPlainText()=='Native saved draft','edited response and prior draft')
    until(lambda:human(window)==['NATIVE_BRANCH_PARENT_ONE','NATIVE_BRANCH_REVISED'],'edited display prefix')
    assert history(parent)==original and history(child)==child_before
    assert json.loads(pointer.read_text())['session']==edited
    close_window(window);window=open_window();settled(window,edited)
    until(lambda:human(window)==['NATIVE_BRANCH_PARENT_ONE','NATIVE_BRANCH_REVISED'],'saved child restored')
    assert window.composer.toPlainText()=='' and window.editing is None
    screenshot=os.environ.get('AUGMENTOR_NATIVE_BRANCH_SCREENSHOT')
    if screenshot:assert window.grab().save(screenshot)
    send(window,'NATIVE_INPUT_HANDLED');settled(window,edited)
    until(lambda:window.pending_prompt is None and 'handled by an input extension' in window.transcript.toPlainText(),'handled input without an optimistic human message')
    assert human(window)==['NATIVE_BRANCH_PARENT_ONE','NATIVE_BRANCH_REVISED']
    send(window,'SLOW native branch stop');until(lambda:window.controller.running and window.partial and window.stop_button.isVisible(),'slow native request')
    before=len(client.session_rows());window.transcript.anchorClicked.emit(QUrl('augmentor-branch:0'));assert len(client.session_rows())==before
    QTest.mouseClick(window.stop_button,Qt.MouseButton.LeftButton);settled(window,edited)
    assert history(parent)==original and history(child)==child_before
    assert not problems,problems
    print(json.dumps({'nativePiBranch':'passed','parent':parent,'child':child,'edited':edited}),flush=True)
finally:
    for window in windows:close_window(window)
