# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""A drifting, continuously morphing plasma reservoir beneath the glass."""
import math
import numpy as np
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor,QPainter,QPainterPath,QImage


def paint_smoke_glow(painter,rect,accent,phase,breath,strength):
    if strength<=0:return
    # Low-resolution continuous fields keep the animation inexpensive. There
    # are no contour paths, mirrored halves, rigid silhouettes or orbiting dots.
    w=max(24,math.ceil(rect.width()/4));h=max(24,math.ceil(rect.height()/4))
    y,x=np.mgrid[-1:1:complex(h),-1:1:complex(w)].astype(np.float32)
    t=phase
    u=x+.20*np.sin(y*3.2+t*.41)+.10*np.sin(x*2.7-y*2.1-t*.29)
    v=y+.17*np.sin(x*3.8-t*.33)+.09*np.cos(y*3.1+x*1.7+t*.51)
    density=np.zeros_like(x)
    for i in range(3):
        px=.40*math.sin(t*(.17+i*.043)+i*2.3)
        py=.34*math.cos(t*(.13+i*.037)+i*2.7)
        sx=.48+.13*math.sin(t*.21+i*1.8)
        sy=.48+.14*math.cos(t*.19+i*2.1)
        density+=np.exp(-((u-px)/sx)**2-((v-py)/sy)**2)*(.60+.17*math.sin(t*.37+i))
    # Broad turbulence stretches, folds and dissolves the luminous material.
    wave=(np.sin(u*4.1+v*2.7+t*.67)+np.sin(v*4.7-u*2.3-t*.53)+.5*np.sin(u*7.1+v*5.3-t*.81))/2.5
    cloud=np.clip(density-.16+.19*wave,0,1.6)/1.6
    folds=np.exp(-((wave+.12*np.sin(v*3+t*.31))/.21)**2)*cloud
    edge=np.clip((1-np.abs(x))/.24,0,1)*np.clip((1-np.abs(y))/.24,0,1)
    edge=edge*edge*(3-2*edge)
    pulse=.73+.20*math.sin(breath)+.07*math.sin(t*.71)
    alpha=np.clip((cloud**1.25*.39+folds*.20)*edge*pulse,0,.62)
    tint=QColor(accent).lighter(128);rgb=np.array(tint.getRgb()[:3],dtype=np.float32)
    light=.76+.23*cloud+.20*folds
    rgba=np.empty((h,w,4),dtype=np.uint8)
    rgba[...,:3]=np.clip(rgb[None,None,:]*light[...,None],0,255)
    rgba[...,3]=(alpha*255).astype(np.uint8)
    image=QImage(rgba.data,w,h,w*4,QImage.Format.Format_RGBA8888)
    painter.save();clip=QPainterPath();clip.addRoundedRect(QRectF(rect),20,20);painter.setClipPath(clip)
    painter.setOpacity(strength);painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.drawImage(QRectF(rect),image);painter.restore()
