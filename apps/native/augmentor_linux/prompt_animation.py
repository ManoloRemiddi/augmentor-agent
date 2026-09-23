# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""A paint-only rolling-letter preview; the draft is never scrambled or sent."""
import math,time
from PySide6.QtCore import Qt,QTimer,QRectF,QPointF,QTextBoundaryFinder
from PySide6.QtGui import QPainter,QColor,QTextLayout,QTextOption
from PySide6.QtWidgets import QWidget


class LetterRoll(QWidget):
    def __init__(self, editor):
        super().__init__(editor.viewport())
        self.editor=editor;self.started=time.monotonic();self.settling=None
        self.text=editor.toPlainText();self.background=QColor('#1e3033');self.foreground=QColor('#edf3f3');self.accent=QColor('#a6d6c8')
        self.timer=QTimer(self);self.timer.setInterval(33);self.timer.timeout.connect(self.update)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.timer.start();self.show();self.resize(editor.viewport().size())

    def settle(self,text):
        self.text=text;self.settling=time.monotonic();self.update()

    def paintEvent(self,event):
        painter=QPainter(self);painter.fillRect(self.rect(),self.background)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        font=self.editor.font();painter.setFont(font)
        metrics=painter.fontMetrics();height=metrics.height();margin=self.editor.document().documentMargin()
        text=self.text[:8000];layout=QTextLayout(text.replace('\n','\u2028'),font)
        option=QTextOption();option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere);layout.setTextOption(option)
        layout.beginLayout();y=margin
        while True:
            line=layout.createLine()
            if not line.isValid():break
            line.setLineWidth(max(1,self.width()-2*margin));line.setPosition(QPointF(margin,y));y+=line.height()
            if y>self.height()+height:break
        layout.endLayout()
        now=time.monotonic();elapsed=now-self.started
        progress=None if self.settling is None else min(1,(now-self.settling)/.68)
        encoded=text.encode('utf-16-le');finder=QTextBoundaryFinder(QTextBoundaryFinder.BoundaryType.Grapheme,text)
        start=0;index=0
        while True:
            end=finder.toNextBoundary()
            if end<0:break
            char=encoded[start*2:end*2].decode('utf-16-le');line=layout.lineForTextPosition(start)
            if not line.isValid() or line.y()>self.height():break
            x=line.cursorToX(start)[0]+margin;right=line.cursorToX(end)[0]+margin
            width=abs(right-x);x=min(x,right);top=line.y();baseline=top+line.ascent()
            stable=char.isspace() or not char.isascii() or not char.isalnum()
            threshold=.12+.78*((index*37%101)/100)
            settled=progress is not None and progress>=threshold
            phase=elapsed*(7+(index%5)*.65)+index*.71
            fraction=phase-math.floor(phase)
            if stable or settled:
                painter.setPen(self.foreground);painter.drawText(QPointF(x,baseline),char)
            elif width>0:
                alphabet='0123456789' if char.isdigit() else 'abcdefghijklmnopqrstuvwxyz'
                current=char if int(phase)%4==0 else alphabet[(int(phase)+index*13)%len(alphabet)]
                next_char=char if progress is not None and progress+.14>=threshold else alphabet[(int(phase)+index*13+1)%len(alphabet)]
                painter.save();painter.setClipRect(QRectF(x,top,width,height))
                painter.setPen(self.accent if index%4==0 else self.foreground)
                painter.drawText(QPointF(x,baseline-fraction*height),current)
                painter.drawText(QPointF(x,baseline+(1-fraction)*height),next_char)
                painter.restore()
            start=end;index+=1
