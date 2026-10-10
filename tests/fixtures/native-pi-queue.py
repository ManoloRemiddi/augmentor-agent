# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual Qt queue controls and Pi socket, with independently authored synthetic inputs."""
import json,time,sys
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QPushButton
from augmentor_linux.pi_client import PiClient
from augmentor_linux.controller import Controller
from augmentor_linux.window import Window

app=QApplication([]);client=PiClient();client.call('host.describe');assert client.supports_queue
steering='--steer' in sys.argv
sid='steer-native' if steering else 'queue-native';controller=Controller(client=client,harness='pi');controller.session=sid;controller.online=True;controller.running=True
window=Window();window.controller=controller
controller.queue_changed.connect(window.queue_panel.replace);controller.queue_result.connect(window.queue_panel.submission_result)
controller.queue_action_result.connect(window.queue_panel.action_result);controller.event.connect(window.on_event);controller.busy.connect(window.set_busy)
window.set_models([{'provider':'test','model':'test','name':'Fixture'}]);window.show();window.set_busy(True)

def until(check):
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        app.processEvents()
        if check():return
        QTest.qWait(10)
    raise AssertionError('Native Pi queue fixture timed out')

def enter(text):
    window.composer.setPlainText(text);QTest.keyClick(window.composer,Qt.Key.Key_Return)
    assert window.composer.toPlainText()==''
    until(lambda:any(row['message']['content'][0]['text']==text for row in window.queue_panel.items))
    return next(row['id'] for row in window.queue_panel.items if row['message']['content'][0]['text']==text)

def click(key,label):
    index=next(i for i,row in enumerate(window.queue_panel.items) if row['id']==key)
    widget=window.queue_panel.rows.itemAt(index).widget();button=next(b for b in widget.findChildren(QPushButton) if b.text()==label)
    assert button.isEnabled();QTest.mouseClick(button,Qt.MouseButton.LeftButton)

try:
    controller.subscribe(sid)
    until(lambda:getattr(controller,'queue_turn_id',None))
    if steering:
        correction=enter('QUEUE_FAST correction native');followup=enter('QUEUE_FAST follow-up native')
        click(correction,'Steer')
        until(lambda:not client.call('session.queue',{'sessionId':sid})['items'] and not controller.running)
        until(lambda:not window.queue_panel.items and not window.queue_panel.pending)
        users=[row['event'] for row in client.call('session.history',{'sessionId':sid})['events'] if row['event']['type']=='user/message']
        assert [row['data']['source']['rpcId'] for row in users[1:]]==[correction,followup]
        assert users[0]['turnId']==users[1]['turnId'] and users[1]['turnId']!=users[2]['turnId']
        texts=[text for who,text in window.messages if who=='You']
        assert texts.count('QUEUE_FAST correction native')==1 and texts.count('QUEUE_FAST follow-up native')==1
        print(json.dumps({'nativePiSteering':'passed','correction':correction}),flush=True)
        sys.exit(0)
    removed=enter('QUEUE_FAST removed native');kept=enter('QUEUE_FAST kept native')
    click(removed,'×');until(lambda:not any(row['id']==removed for row in window.queue_panel.items))
    controller.stream.close();window.queue_panel.reset();controller.subscribe(sid)
    until(lambda:any(row['id']==kept for row in window.queue_panel.items))
    assert window.stop_button.isVisible();assert window.send_button.isEnabled()
    QTest.mouseClick(window.stop_button,Qt.MouseButton.LeftButton)
    until(lambda:not controller.running)
    until(lambda:any(row['id']==kept and row.get('stateLabel')=='Paused' for row in window.queue_panel.items))
    window.composer.setPlainText('QUEUE_FAST newer native');QTest.keyClick(window.composer,Qt.Key.Key_Return)
    until(lambda:not client.call('session.queue',{'sessionId':sid})['items'] and not controller.running)
    until(lambda:not window.queue_panel.items and not window.queue_panel.pending)
    delivered=[row['event']['data']['source']['rpcId'] for row in client.call('session.history',{'sessionId':sid})['events'] if row['event']['type']=='user/message']
    assert kept in delivered and removed not in delivered
    texts=[text for who,text in window.messages if who=='You']
    assert texts.index('QUEUE_FAST kept native')<texts.index('QUEUE_FAST newer native')
    print(json.dumps({'nativePiQueue':'passed','kept':kept}),flush=True)
finally:
    controller.running=False;controller.close();window.controller=None;window.close()
