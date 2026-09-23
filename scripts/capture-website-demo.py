#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Capture actual native widgets with synthetic text and built-in skins only."""
import argparse
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
p.add_argument('--skin',choices=['Blossom lake','Futuristic'],default='Blossom lake');p.add_argument('--frames',type=int,default=150)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
# Preview never connects to a harness or reads the user's saved preferences.
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['QT_SCALE_FACTOR']='2'
sys.path.insert(0,str(ROOT/'apps/native'))
from PySide6.QtCore import Qt,QTimer,QPoint
from PySide6.QtGui import QImage,QPainter,QColor
from PySide6.QtWidgets import QApplication
from augmentor_linux.window import Window
from augmentor_linux.skins import BUILTINS
app=QApplication([]);w=Window(preview=True)
w.resize(520,670);w.move(220,220)
w.apply_appearance({**w.preferences.values,**BUILTINS[a.skin]})
w.title.setText('A little clarity for the week')
w.messages=[('You','Let’s turn these ideas into a clear plan.'),('Augmentor',
'''## Start with what matters
Choose one outcome for the week, then give it a small next step.

**Your preferences** belong in relationship memory. **The brief, decisions and next steps** belong with the project.

### A simple rhythm
1. Capture the idea — type it or say it.
2. Shape it into a useful next action.
3. Return to the project with its context close by.

Keep a second conversation open when you want to explore another direction.''')]
w.render_messages();w.composer.setPlaceholderText('Type a message, or hold the voice button…')
w.model_picker.set_catalog({'groups':[{'models':[{'provider':'demo','model':'demo','name':'Local model · demo','location':'Local'}]}]})
w.connection_dot.setStyleSheet('color:#a8d0b5');w.connection_dot.setToolTip('Demonstration connection indicator')
w.voice_button.setEnabled(True)
w.show();w.activity.configure(busy=True)
frames=a.out/'frames';frames.mkdir(exist_ok=True)
state={'frame':0}

def capture():
    canvas=w.activity.canvas;canvas.update();w.update()
    ratio=w.devicePixelRatioF();image=QImage(round(canvas.width()*ratio),round(canvas.height()*ratio),QImage.Format.Format_ARGB32_Premultiplied)
    image.setDevicePixelRatio(ratio);image.fill(Qt.GlobalColor.transparent)
    painter=QPainter(image);painter.drawPixmap(QPoint(0,0),canvas.grab())
    offset=w.mapToGlobal(QPoint(0,0))-canvas.mapToGlobal(QPoint(0,0));painter.drawPixmap(offset,w.grab());painter.end()
    index=state['frame'];image.save(str(frames/f'{index:04d}.png'))
    if index==35:
        image.save(str(a.out/'desktop-voice-butterflies.png'))
        w.grab().save(str(a.out/'desktop-voice-window.png'))
    state['frame']+=1
    if state['frame']>=a.frames:timer.stop();w.activity.canvas.close();w.close();app.quit()

timer=QTimer();timer.setInterval(40);timer.timeout.connect(capture)
QTimer.singleShot(1200,timer.start)
app.exec()
print('Captured synthetic native UI demonstration:',a.out)
