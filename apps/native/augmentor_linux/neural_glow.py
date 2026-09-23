# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""An abstract, breathing neural light field beneath the translucent panel."""
import math
from PySide6.QtCore import QPointF,QRectF,Qt
from PySide6.QtGui import QColor,QPainterPath,QPen,QRadialGradient


def paint_neural_glow(painter,rect,accent,phase,breath,strength):
    if strength<=0:return
    painter.save()
    clip=QPainterPath();clip.addRoundedRect(QRectF(rect),20,20);painter.setClipPath(clip)
    painter.setOpacity(strength)
    cx,cy=rect.center().x(),rect.center().y()-rect.height()*.035
    width=min(rect.width()*.92,rect.height()*.95);height=min(rect.height()*.51,width*.8)
    expansion=1+.035*math.sin(breath)+.012*math.sin(phase*.47)
    width*=expansion;height*=expansion
    pulse=.56+.27*math.sin(breath)+.12*math.sin(phase*.73+1.4)
    tint=QColor(accent).lighter(135)
    # Diffuse reservoirs give the filaments a soft volume, without a hard image.
    for side in (-1,1):
        center=QPointF(cx+side*width*.23,cy+height*.015*math.sin(phase*.4+side))
        gradient=QRadialGradient(center,width*.51)
        inner=QColor(tint);inner.setAlphaF(.10+.13*pulse)
        middle=QColor(accent);middle.setAlphaF(.045+.055*pulse)
        clear=QColor(accent);clear.setAlpha(0)
        gradient.setColorAt(0,inner);gradient.setColorAt(.48,middle);gradient.setColorAt(1,clear)
        painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(gradient)
        painter.drawEllipse(center,width*.51,width*.51)
        for layer in range(5):
            points=[];scale=.43+layer*.135
            for i in range(101):
                angle=i*math.tau/100
                ripple=1+.075*math.sin(angle*3+phase*(.23+layer*.021)+side*1.8)+.035*math.sin(angle*7-phase*.37+layer*1.9)
                # The inner seam bends, and each hemisphere has independent folds.
                x=side*width*(.018+(.21+.195*math.cos(angle))*scale*ripple)
                y=height*.49*math.sin(angle)*scale*ripple
                x+=width*.017*math.sin(angle*2+phase*.31+layer)
                y+=height*.018*math.sin(angle*4-phase*.26+side)
                points.append(QPointF(cx+x,cy+y))
            path=QPainterPath(points[0])
            for point in points[1:]:path.lineTo(point)
            local=.6+.4*math.sin(phase*(.43+layer*.073)+layer*2.1+side)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for pen_width,opacity in ((15,.018),(7,.038),(2,.105)):
                color=QColor(tint);color.setAlphaF(opacity*(.5+pulse)*(.55+local*.6))
                pen=QPen(color,pen_width);pen.setCapStyle(Qt.PenCapStyle.RoundCap);pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin);painter.setPen(pen);painter.drawPath(path)
            # Travelling highlights have different speeds and fade along their path.
            head=(phase*(.025+layer*.009)+side*.13+layer*.21)%1
            for j in range(12):
                i=int((head-j*.008)%1*100)
                color=QColor(tint);color.setAlphaF(.22*(1-j/12)**1.6*(.4+pulse))
                painter.setPen(QPen(color,1.4));painter.drawLine(points[i],points[i+1])
            # Tiny interrupted, angular fragments hint at circuitry inside the mist.
            if layer in (1,3):
                i=int((head+.37)%1*100);point=points[i]
                color=QColor(tint);color.setAlphaF(.08+.12*local*pulse)
                painter.setPen(QPen(color,1));painter.drawLine(point,QPointF(point.x()+side*5,point.y()))
                painter.drawLine(QPointF(point.x()+side*5,point.y()),QPointF(point.x()+side*5,point.y()+4))
    painter.restore()
