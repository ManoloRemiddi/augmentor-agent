# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Guided connection to an existing local DSH installation."""
import threading
from PySide6.QtCore import Signal, QTimer
from PySide6.QtWidgets import QDialog,QVBoxLayout,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton
from .prompt_client import PromptClient


class DshSetupDialog(QDialog):
    completed=Signal(object,object)

    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.client=PromptClient()
        self.token=None;self.installed=False;self.busy=False;self.dismissed=False;self.changing=False
        self.completed.connect(lambda callback,value:callback(value) if not self.dismissed else None)
        self.setWindowTitle('Connect DSH');self.setModal(True);self.setMinimumWidth(460)
        layout=QVBoxLayout(self)
        intro=QLabel('Connect a running local DSH 0.1.5-rc.1 web profile. Augmentor adds its Linux and browser roles, shared prompts and memory. Model providers remain managed in DSH. This connection is shared by both Augmentor interfaces.');intro.setWordWrap(True);layout.addWidget(intro)
        form=QFormLayout();layout.addLayout(form)
        self.endpoint=QLineEdit();self.home=QLineEdit()
        for label,field in [('DSH URL',self.endpoint),('DSH data folder',self.home)]:
            field.setAccessibleName(label);form.addRow(label,field);field.textChanged.connect(self.invalidate)
        note=QLabel('Install integration adds Augmentor-owned presets and appends to the DSH profile, keeping a backup. It does not interrupt running tasks. Restart DSH yourself after installation, then check again. Existing custom Augmentor integration requires migration.');note.setWordWrap(True);layout.addWidget(note)
        self.note=QLabel('Loading connection…');self.note.setWordWrap(True);layout.addWidget(self.note)
        actions=QHBoxLayout();layout.addLayout(actions)
        self.later=QPushButton('Later');self.later.clicked.connect(self.reject);actions.addWidget(self.later)
        self.check=QPushButton('Check connection');self.check.clicked.connect(self.test);actions.addWidget(self.check)
        self.install=QPushButton('Install integration');self.install.clicked.connect(self.integrate);actions.addWidget(self.install)
        self.save=QPushButton('Save and use DSH');self.save.clicked.connect(self.commit);actions.addWidget(self.save)
        self.run('describe',{},self.loaded)

    def invalidate(self,*_):
        self.token=None
        if hasattr(self,'save'):self.controls()

    def controls(self):
        for field in (self.endpoint,self.home,self.check):field.setEnabled(not self.busy)
        self.install.setEnabled(not self.busy and bool(self.token) and not self.installed)
        self.save.setEnabled(not self.busy and bool(self.token) and self.installed)
        self.later.setEnabled(not self.changing)

    def run(self,action,p,callback):
        if self.busy:return
        self.busy=True;self.changing=action in ('install','save');self.controls()
        def work():
            try:result=self.client.call('dsh.'+action,p),None
            except Exception as error:result=None,str(error)
            try:self.completed.emit(finished,result)
            except RuntimeError:pass
        def finished(result):
            self.busy=False;self.changing=False;self.controls()
            if result[1]:self.note.setText(result[1]);return
            callback(result[0]);self.controls()
        threading.Thread(target=work,daemon=True).start()

    def loaded(self,value):
        self.endpoint.setText(value['endpoint']);self.home.setText(value['home'])
        self.note.setText('Check this connection before saving or installing the integration.')

    def test(self):
        self.invalidate();self.note.setText('Checking DSH and its integration…')
        def checked(value):self.token=value['token'];self.installed=value['installed'];self.note.setText(value['message'])
        self.run('check',{'endpoint':self.endpoint.text(),'home':self.home.text()},checked)

    def integrate(self):
        def installed(value):self.token=None;self.note.setText(value['message'])
        self.run('install',{'token':self.token},installed)

    def commit(self):
        if self.owner.controller and (self.owner.controller.running or self.owner.controller.navigating or self.owner.editing):
            self.note.setText('Finish the current action before changing harness settings.');return
        def saved(value):
            self.accept();QTimer.singleShot(0,lambda:self.owner.switch_harness('dsh',reconnect=True))
        self.run('save',{'token':self.token},saved)

    def reject(self):
        if self.changing:return
        self.dismissed=True;super().reject()
