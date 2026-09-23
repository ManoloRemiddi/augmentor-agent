# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Pending prompts, separate from delivered conversation messages."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QScrollArea, QWidget, QApplication, QSizePolicy


class PromptPreview(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.full_text=' '.join(text.split())
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        self.setAccessibleName(self.full_text)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.setText(self.fontMetrics().elidedText(self.full_text,Qt.TextElideMode.ElideRight,max(0,self.contentsRect().width())))


class QueuePanel(QScrollArea):
    action_requested = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMaximumHeight(100)
        self.content=QWidget();self.rows=QVBoxLayout(self.content)
        self.rows.setContentsMargins(12,0,12,0);self.rows.setSpacing(2)
        self.setWidget(self.content)
        self.setStyleSheet('QScrollArea {background:transparent;border:0;}')
        self.content.setAutoFillBackground(False);self.viewport().setAutoFillBackground(False)
        self.pending={};self.items=[];self.changing=set();self.errors={};self.delivered=set();self.online=True;self.running=False
        self.hide()

    def reset(self):
        self.pending.clear();self.items=[];self.changing.clear();self.errors.clear();self.delivered.clear();self.render()

    def submitted(self, rpc_id, text):
        self.pending[rpc_id]={'text':text,'state':'Queuing…'};self.render()

    def submission_result(self, result):
        if result.get('command') and result.get('accepted'):
            self.consumed(result['id']);return
        entry=self.pending.get(result['id'])
        if entry is not None:
            entry['state']='Queued' if result.get('accepted') else 'Not confirmed — '+result.get('error','connection failed')
            entry['failed']=not result.get('accepted')
        self.render()

    def consumed(self, rpc_id):
        if rpc_id is None:return
        self.delivered.add(rpc_id)
        if len(self.delivered)>2048:self.delivered={rpc_id}
        self.pending.pop(rpc_id,None)
        self.items=[row for row in self.items if row.get('rpcId')!=rpc_id]
        self.render()

    def replace(self, items):
        self.items=[row for row in items if row.get('placement') in ('queued','steering') and row.get('rpcId') not in self.delivered]
        for row in self.items:self.pending.pop(row.get('rpcId'),None)
        self.changing.intersection_update(row['id'] for row in self.items)
        self.render()

    def action_result(self, result):
        self.changing.discard(result['id'])
        if result.get('error'):self.errors[result['id']]=result['error']
        else:self.errors.pop(result['id'],None)
        self.render()

    def act(self, item_id, action):
        if item_id in self.changing:return
        self.changing.add(item_id);self.render();self.action_requested.emit(item_id,action)

    def render(self):
        while self.rows.count():
            widget=self.rows.takeAt(0).widget()
            if widget:widget.hide();widget.setParent(None);widget.deleteLater()
        entries=[(row['id'],'Steering…' if row['placement']=='steering' else 'Queued',
                  '\n'.join(p.get('text','') for p in row['message']['content'] if p.get('type')=='text'),row) for row in self.items]
        entries += [(key,row['state'],row['text'],None) for key,row in self.pending.items()]
        for key,state,text,item in entries:
            if key in self.errors:state+=' — '+self.errors[key][:120]
            frame=QFrame();frame.setObjectName('queuedPrompt')
            frame.setStyleSheet('QFrame#queuedPrompt {background:rgba(127,150,150,12);border:1px solid rgba(127,160,155,55);border-bottom:0;border-top-left-radius:8px;border-top-right-radius:8px;} QPushButton {background:transparent;border:0;padding:2px 3px;font-size:11px;border-radius:4px;} QPushButton:hover {background:rgba(127,150,150,45);}')
            frame.setFixedHeight(32)
            layout=QHBoxLayout(frame);layout.setContentsMargins(9,3,5,3);layout.setSpacing(5)
            prefix='' if state=='Queued' else state+' · '
            label=PromptPreview(prefix+text);label.setToolTip(state+'\n'+text)
            label.setStyleSheet('font-size:12px;')
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(label,1)
            if item:
                steer=QPushButton('Steer');steer.setAccessibleName('Steer queued prompt')
                steer.setToolTip('Use this prompt at the next step of the current response')
                steer.setEnabled(self.online and self.running and item['placement']=='queued' and key not in self.changing)
                steer.clicked.connect(lambda checked=False,k=key:self.act(k,'steer'));layout.addWidget(steer)
                remove=QPushButton('×');remove.setAccessibleName('Remove queued prompt');remove.setFixedWidth(18);remove.setStyleSheet('padding:0;')
                remove.setEnabled(self.online and key not in self.changing)
                remove.clicked.connect(lambda checked=False,k=key:self.act(k,'remove'));layout.addWidget(remove)
            elif self.pending[key].get('failed'):
                copy=QPushButton('Copy');copy.clicked.connect(lambda checked=False,t=text:QApplication.clipboard().setText(t));layout.addWidget(copy)
                remove=QPushButton('×');remove.setFixedWidth(18);remove.setStyleSheet('padding:0;')
                remove.clicked.connect(lambda checked=False,k=key:self.consumed(k));layout.addWidget(remove)
            self.rows.addWidget(frame)
        self.setVisible(bool(entries));self.setFixedHeight(min(100, max(0,len(entries)*34-2)))
