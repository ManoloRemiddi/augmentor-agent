# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Local recorded token activity, with no inference or provider billing requests."""
import json
import os
import shutil
import subprocess
from datetime import date, timedelta
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPalette, QAccessible, QAccessibleEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
from .ui_scale import px, scaled


def read_usage():
    root=Path(__file__).resolve().parents[3]
    bundled=root/'node/bin/node'
    node=os.environ.get('AUGMENTOR_PI_NODE') or (str(bundled) if bundled.is_file() else shutil.which('node'))
    if not node:raise RuntimeError('Token history is unavailable: the local runtime is missing.')
    result=subprocess.run([node,str(root/'services/usage/history.mjs')],capture_output=True,timeout=20,check=True)
    value=json.loads(result.stdout)
    if not isinstance(value,dict) or not isinstance(value.get('days'),list) or len(value['days'])>365:
        raise ValueError('Token history returned an invalid summary.')
    return value


def compact(value):
    if value>=1000000:return f'{value/1000000:.1f}M'
    if value>=1000:return f'{value/1000:.1f}K'
    return f'{value:,}'


class TokenCalendar(QWidget):
    selected=Signal(str)
    def __init__(self,owner):
        super().__init__();self.owner=owner;self.days={};self.end=date.today();self.start=self.end-timedelta(days=364)
        self.current=self.end;self.cells=[];self.maximum=0
        self.setMouseTracking(True);self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
        scaled(self).setFixedHeight(112)
        self.setAccessibleName('Recorded token activity calendar')
        self.setAccessibleDescription('One square per day. Arrow keys select a day; Home and End select the first and last day. Values appear below the calendar.')

    def set_data(self,value):
        self.start=date.fromisoformat(value['start']);self.end=date.fromisoformat(value['end']);self.current=self.end
        self.days={d['date']:d for d in value['days']};self.maximum=max((d['total'] for d in value['days']),default=0);self.update()

    def description(self,day):
        row=self.days.get(day.isoformat())
        if not row:return day.strftime('%d %b %Y')+' · No recorded tokens'
        return day.strftime('%d %b %Y')+f" · {row['total']:,} tokens · {row['input']:,} input / {row['output']:,} output"

    def choose(self,day):
        self.current=max(self.start,min(day,self.end));text=self.description(self.current)
        self.setAccessibleName('Token activity · '+text);QAccessible.updateAccessibility(QAccessibleEvent(self,QAccessible.Event.NameChanged))
        self.selected.emit(text);self.update()

    def colours(self):
        text=self.owner.palette().color(QPalette.ColorRole.WindowText)
        base=QColor(self.owner.background) if hasattr(self.owner,'background') else self.palette().color(QPalette.ColorRole.Window)
        accent=QColor(self.owner.accent)
        def blend(ratio):return QColor(round(base.red()*(1-ratio)+accent.red()*ratio),round(base.green()*(1-ratio)+accent.green()*ratio),round(base.blue()*(1-ratio)+accent.blue()*ratio))
        return text,[blend(r) for r in (.13,.3,.5,.75,1)]

    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        text,colours=self.colours();p.setPen(text);font=p.font();font.setPixelSize(px(self,10));p.setFont(font)
        beginning=self.start-timedelta(days=self.start.weekday());columns=((self.end-beginning).days//7)+1
        left=px(self,26);pitch=max(1,(self.width()-left-px(self,2))/columns);side=max(1,min(px(self,9),pitch-px(self,2)))
        top=px(self,20);row_pitch=px(self,11);self.cells=[];last_month=None;last_label=-1000
        for column in range(columns):
            day=beginning+timedelta(days=column*7);label_day=max(day,self.start);month=(label_day.year,label_day.month)
            if month!=last_month and column<columns-2 and left+column*pitch-last_label>=px(self,30):
                p.setPen(text);p.drawText(QRectF(left+column*pitch,0,pitch*4,px(self,16)),Qt.AlignmentFlag.AlignLeft,label_day.strftime('%b'));last_month=month;last_label=left+column*pitch
            for row in range(7):
                current=day+timedelta(days=row)
                if current<self.start or current>self.end:continue
                tokens=self.days.get(current.isoformat(),{}).get('total',0)
                level=0 if not tokens else min(4,max(1,((tokens*4-1)//max(1,self.maximum))+1))
                rect=QRectF(left+column*pitch,top+row*row_pitch,side,side)
                p.setPen(Qt.PenStyle.NoPen);p.setBrush(colours[level]);p.drawRoundedRect(rect,px(self,2),px(self,2));self.cells.append((rect,current))
                if self.hasFocus() and current==self.current:
                    p.setBrush(Qt.BrushStyle.NoBrush);p.setPen(text);p.drawRoundedRect(rect.adjusted(-1,-1,1,1),px(self,2),px(self,2))
        for row,label in ((0,'M'),(2,'W'),(4,'F')):
            p.setPen(text);p.drawText(QRectF(0,top+row*row_pitch-px(self,2),left-px(self,4),px(self,14)),Qt.AlignmentFlag.AlignLeft,label)
        y=px(self,100);x=max(left,self.width()-px(self,124));p.setPen(text);p.drawText(QRectF(x,y-px(self,2),px(self,28),px(self,14)),Qt.AlignmentFlag.AlignLeft,'Less')
        for i,colour in enumerate(colours):
            p.setPen(Qt.PenStyle.NoPen);p.setBrush(colour);p.drawRoundedRect(QRectF(x+px(self,30+i*12),y,px(self,9),px(self,9)),px(self,2),px(self,2))
        p.setPen(text);p.drawText(QRectF(x+px(self,94),y-px(self,2),px(self,30),px(self,14)),Qt.AlignmentFlag.AlignLeft,'More')

    def mouseMoveEvent(self,event):
        day=next((d for rect,d in self.cells if rect.contains(event.position())),None)
        self.setToolTip(self.description(day) if day else '')
        super().mouseMoveEvent(event)

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            day=next((d for rect,d in self.cells if rect.contains(event.position())),None)
            if day:self.setFocus();self.choose(day);return
        super().mousePressEvent(event)

    def keyPressEvent(self,event):
        offset={Qt.Key.Key_Left:-7,Qt.Key.Key_Right:7,Qt.Key.Key_Up:-1,Qt.Key.Key_Down:1}.get(event.key())
        if offset is not None:self.choose(self.current+timedelta(days=offset));event.accept()
        elif event.key()==Qt.Key.Key_Home:self.choose(self.start);event.accept()
        elif event.key()==Qt.Key.Key_End:self.choose(self.end);event.accept()
        else:super().keyPressEvent(event)


class TokenUsage(QWidget):
    def __init__(self,panel):
        super().__init__();self.panel=panel;self.loading=False
        self.setObjectName('agent-token-usage');self.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        layout=QVBoxLayout(self);scaled(layout).setContentsMargins(0,0,0,0);scaled(layout).setSpacing(4)
        header=QHBoxLayout();heading=QVBoxLayout();scaled(heading).setSpacing(2)
        title=QLabel('TOKEN ACTIVITY');scaled(title).setStyleSheet('font-size:11px;font-weight:600;');heading.addWidget(title)
        self.total=QLabel('Loading recorded tokens…');scaled(self.total).setStyleSheet('font-size:18px;font-weight:600;');heading.addWidget(self.total)
        header.addLayout(heading,1);self.period=QLabel('Past 12 months');scaled(self.period).setStyleSheet('font-size:11px;');header.addWidget(self.period)
        self.refresh=QPushButton('↻');self.refresh.setAccessibleName('Refresh token activity');self.refresh.setToolTip('Refresh local token history');scaled(self.refresh).setFixedSize(32,32);self.refresh.clicked.connect(self.reload);header.addWidget(self.refresh);layout.addLayout(header)
        self.calendar=TokenCalendar(panel.owner);layout.addWidget(self.calendar)
        self.detail=QLabel('Hover or select a day to see tokens.');self.detail.setWordWrap(True);scaled(self.detail).setStyleSheet('font-size:11px;');self.calendar.selected.connect(self.detail.setText);layout.addWidget(self.detail)
        self.note=QLabel('Local Augmentor history · Provider-reported counts');self.note.setWordWrap(True);scaled(self.note).setStyleSheet('font-size:10px;');layout.addWidget(self.note)
        self.reload()

    def resizeEvent(self,event):
        super().resizeEvent(event);self.period.setVisible(self.width()>=px(self,450))

    def reload(self):
        if self.loading:return
        self.loading=True;self.refresh.setEnabled(False)
        def work():
            try:return read_usage(),None
            except Exception:return None,'Recorded token history is unavailable. Try refreshing.'
        self.panel.background(work,self.receive)

    def receive(self,result):
        value,error=result;self.loading=False;self.refresh.setEnabled(True)
        if error:self.total.setText('Usage unavailable');self.note.setText(error);return
        self.calendar.set_data(value);self.total.setText(compact(value['total'])+' recorded tokens')
        self.total.setToolTip(f"{value['total']:,} provider-reported tokens over the past 365 days")
        sources=' / '.join(value.get('sources',[])) or 'Local Augmentor history'
        self.note.setText(sources+' · '+('Partial history; some counts unavailable' if value.get('incomplete') else 'Provider-reported totals'))
        self.detail.setText('Hover or select a day to see tokens.' if value.get('records') else 'No recorded usage yet. Counts appear after model responses.')
