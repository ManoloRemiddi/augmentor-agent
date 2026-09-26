#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Capture deterministic Qt preview surfaces and frame timing without a live agent.

Usage: python -B scripts/flare-fidelity-proof.py APP_ROOT OUTPUT_DIRECTORY
Use QT_SCALE_FACTOR=2 for synthetic high-DPI coverage; this is not a Retina
hardware test. Native Cocoa captures only the fixture widgets. It does not read
or capture the user's conversations, desktop, credentials or preferences.
"""
import os,sys,tempfile,json,time,statistics,random
from pathlib import Path
from unittest.mock import patch
root=Path(sys.argv[1]); output=Path(sys.argv[2]);output.mkdir(parents=True,exist_ok=True)
state=tempfile.TemporaryDirectory(prefix='augmentor-flare-')
for name in ('XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_RUNTIME_DIR','AUGMENTOR_PI_CONFIG','AUGMENTOR_PI_STATE','AUGMENTOR_SHARED_STATE','AUGMENTOR_SHARED_DATA'):
 os.environ[name]=str(Path(state.name)/name);Path(os.environ[name]).mkdir()
sys.path.insert(0,str(root/'apps/native'))
from PySide6.QtCore import Qt,QPointF
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter,QColor
from augmentor_linux.window import Window
from augmentor_linux.activity import FlowNoise
app=QApplication([]); window=Window(preview=True)
window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating);window.resize(424,484);window.move(300,300);window.show();app.processEvents()
a=window.activity
with patch('augmentor_linux.activity.random.Random',return_value=random.Random(714)):
 a.noise=FlowNoise()
a.busy=True;a.strength=1.;a.breath_phase=2.;a.pointer=QPointF(-10000,-10000)
a.position_canvas();a.canvas.show();a.timer.stop();a.flare={'start':0.,'duration':3.,'side':0,'position':.5,'width':55.,'travel':150.}
rect=a.canvas_surface_rect();times=[]
for i in range(18):
 a.phase=.6+i*.04;start=time.perf_counter();a.render_field(rect,window.accent);times.append((time.perf_counter()-start)*1000)
# Capture the real Cocoa QWidget canvases. Composite on a neutral desktop solely for a readable proof.
a.timer.stop();canvas=a.canvas.grab();panel=window.grab();dpr=canvas.devicePixelRatio()
canvas.save(str(output/'canvas.png'));panel.save(str(output/'window.png'))
image=QImage(canvas.size(),QImage.Format.Format_RGB32);image.setDevicePixelRatio(dpr);image.fill(QColor('#23262b'))
p=QPainter(image);p.drawPixmap(0,0,canvas);p.drawPixmap(160,160,panel);p.end();image.save(str(output/'proof.png'))
report={'passed': not canvas.isNull() and not panel.isNull() and a.frame.width() == a.image_width, 'platform':app.platformName(),'screens':[{'name':s.name(),'dpr':s.devicePixelRatio(),'geometry':list(s.geometry().getRect())} for s in app.screens()], 'canvas':[a.canvas.width(),a.canvas.height()],'field':[a.image_width,a.image_height],'dpr':dpr,'frameMsMedian':statistics.median(times[2:]),'frameMsMax':max(times[2:]),'firstMs':times[0]}
(output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));window.close()
