# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real offscreen Qt transcript actions and composer through the shared Codex host."""
import json, time
from PySide6.QtCore import Qt, QUrl
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from augmentor_linux.controller import Controller
from augmentor_linux.window import Window

app=QApplication([])
controller=Controller(harness='codex')
controller.session='native-fork-source';controller.online=True
controller.selection={'provider':'fixture','model':'fixture'}
window=Window();window.controller=controller
for name,slot in [('session_info',window.session_changed),('selection_changed',window.set_selection),
                  ('page',window.restore_page),('event',window.on_event),('busy',window.set_busy),
                  ('sent',window.message_sent),('submission_failed',window.message_not_sent),
                  ('connection',window.connection_changed),('problem',window.on_problem)]:
    getattr(controller,name).connect(slot)
problems=[];controller.problem.connect(problems.append)
pages=[];controller.page.connect(lambda *args:pages.append(args))
window.set_models([{'provider':'fixture','model':'fixture','name':'Fixture'}]);window.show()

def until(check):
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        app.processEvents()
        if check():return
        QTest.qWait(10)
    raise AssertionError('Native fork timeout: '+str(problems)+' '+str(window.messages))

def activate(action,index):
    # The rendered transcript anchor and its actual Window/Controller handler.
    href='augmentor-'+action+':'+str(index)
    window.rendered_messages=None;window.render_messages()
    assert href in window.transcript.toHtml(),href
    window.transcript.anchorClicked.emit(QUrl(href))

try:
    controller.load_page();controller.subscribe(controller.session)
    until(lambda:controller.connected and len([r for r in window.messages if r[0]=='Augmentor'])==2)
    before=controller.client.call('session.history',{'sessionId':controller.session,'maxMessages':100})
    first=next(i for i,(role,_) in enumerate(window.messages) if role=='Augmentor')
    page_count=len(pages)
    activate('branch',first)
    # Worker navigation completes before the queued child transcript renders.
    # Wait for the actual child page; the source page has two assistant replies.
    until(lambda:controller.session!='native-fork-source' and not controller.navigating and controller.connected and window.send_button.isEnabled() and len(pages)>page_count and len([r for r in window.messages if r[0]=='Augmentor'])==1)
    branch=controller.session
    assert branch.startswith('augmentor-linux-codex-')
    assert not any('NATIVE_SOURCE_SECOND' in text for _,text in window.messages)
    assert controller.client.call('session.history',{'sessionId':'native-fork-source','maxMessages':100})==before
    window.composer.setPlainText('RESTORED_DRAFT')
    user=next(i for i,(role,_) in enumerate(window.messages) if role=='You')
    activate('edit',user)
    assert window.editing and window.composer.toPlainText()=='NATIVE_SOURCE_FIRST'
    window.composer.setPlainText('NATIVE_EDITED_FIRST')
    until(lambda:window.send_button.isEnabled())
    page_count=len(pages)
    QTest.keyClick(window.composer,Qt.Key.Key_Return)
    until(lambda:controller.session!=branch and not controller.running and not window.editing and len(pages)>page_count)
    until(lambda:any(role=='Augmentor' for role,_ in window.messages) and [text for role,text in window.messages if role=='You']==['NATIVE_EDITED_FIRST'])
    edited=controller.session
    assert window.composer.toPlainText()=='RESTORED_DRAFT'
    assert [text for role,text in window.messages if role=='You']==['NATIVE_EDITED_FIRST']
    assert controller.pending_branch is None
    saved=json.loads(controller.state_file.read_text())
    assert saved['session']==edited and saved['pendingBranch'] is None
    print(json.dumps({'nativeFork':'passed','branch':branch,'edited':edited}),flush=True)
finally:
    controller.running=False;controller.close();window.controller=None;window.close()
