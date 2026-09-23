#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Deterministic XWayland mouse/clipboard proof; isolated preview, no model calls.

Accepts an optional installation root to exercise the shipped native code.
"""
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

root=Path(__file__).resolve().parents[1]
output=Path(os.environ.get('AUGMENTOR_PROOF_OUTPUT',str(root/'outputs')))
output.mkdir(parents=True,exist_ok=True)
native_root=Path(sys.argv[1]).expanduser() if len(sys.argv)>1 else root
sys.path.insert(0,str(native_root/'apps/native'))
os.environ['QT_QPA_PLATFORM']='xcb'
from PySide6.QtCore import QPoint,QProcess,QMimeData
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from augmentor_linux.window import Window

app=QApplication([])
saved_clipboard=QMimeData();original=app.clipboard().mimeData()
if original:
    for mime in original.formats():saved_clipboard.setData(mime,original.data(mime))
w=Window(preview=True);w.setWindowTitle('Augmentor copy regression preview')
loads=[]
w.controller=SimpleNamespace(session='copy-proof',running=False,navigating=False,online=True,
    close=lambda:None,load_older=lambda:loads.append(True))
w.resize(440,600);w.show();w.raise_();app.processEvents()
w.messages=[('You' if i%2==0 else 'Augmentor',f'Message {i}: Café 😀\nA deterministic clipboard check.') for i in range(20)]
w.render_messages();app.processEvents()
t=w.transcript;bar=t.verticalScrollBar();viewport=t.viewport()

def command(program,args):
    process=QProcess();process.start(program,args)
    assert process.waitForStarted(2000),program
    for _ in range(250):
        app.processEvents();QTest.qWait(20)
        if process.state()==QProcess.ProcessState.NotRunning:break
    else:
        process.kill();raise AssertionError('Process timed out: '+program)
    assert process.exitCode()==0,bytes(process.readAllStandardError()).decode()
    return bytes(process.readAllStandardOutput()).decode()

def icon(index):
    block=t.document().begin()
    while block.isValid():
        fragments=block.begin()
        while not fragments.atEnd():
            part=fragments.fragment();fmt=part.charFormat()
            if fmt.isImageFormat() and fmt.anchorHref()==f'augmentor-copy:{index}':
                cursor=QTextCursor(t.document());cursor.setPosition(part.position())
                return t.cursorRect(cursor).center()+QPoint(int(fmt.toImageFormat().width()/2),0)
            fragments+=1
        block=block.next()
    raise AssertionError('Missing Copy icon')

results=[]
try:
    command('xdotool',['windowactivate','--sync',str(int(w.winId()))])
    QTest.qWait(200)
    for index in (19,8,9):
        for selected in (False,True):
            cursor=QTextCursor(t.document());cursor.setPosition(0)
            if selected:cursor.setPosition(8,QTextCursor.MoveMode.KeepAnchor)
            t.setTextCursor(cursor)
            if index==19:w.jump_latest()
            else:bar.setValue(bar.value()+icon(index).y()-viewport.height()//2)
            app.processEvents();point=icon(index)
            assert viewport.rect().contains(point) and t.anchorAt(point)==f'augmentor-copy:{index}'
            position=bar.value();follow=w.follow_tail;loads.clear()
            app.clipboard().setText('Clipboard sentinel')
            local=viewport.mapTo(w,point)
            command('xdotool',['mousemove','--window',str(int(w.winId())),str(round(local.x()*w.devicePixelRatioF())),str(round(local.y()*w.devicePixelRatioF())),'mousedown','1','mouseup','1'])
            assert command('xclip',['-selection','clipboard','-out'])==w.messages[index][1],'External clipboard mismatch'
            assert bar.value()==position and w.follow_tail==follow,'Mouse release scrolled'
            assert not t.textCursor().hasSelection(),'Icon selected'
            assert '/check/' in w.message_actions(index,w.messages[index][0],'#ffffff'),'No confirmation tick'
            if index==19 and not selected:w.grab().save(str(output/'copy-scroll-desktop.png'))
            QTest.qWait(1700)
            assert '/check/' not in t.toHtml(),'Tick did not expire'
            assert bar.value()==position and w.follow_tail==follow,'Tick expiry scrolled'
            assert not loads,'Copy triggered history pagination'
            results.append({'message':index,'oldSelection':selected,'scroll':position,'externalClipboardMatches':True,'scrollUnchanged':True})
    proof={'nativeRoot':str(native_root),'platform':app.platformName(),'input':'xdotool combined mouse press/release','clipboardReader':'xclip','cases':results}
    (output/'copy-scroll-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(proof),flush=True)
finally:
    command('xdotool',['mouseup','1'])
    app.clipboard().setMimeData(saved_clipboard);QTest.qWait(100)
    w.close()
