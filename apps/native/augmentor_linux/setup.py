# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Guided Pi connection setup using the shared runtime's test/save boundary."""
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QFormLayout,QHBoxLayout,QLabel,
    QLineEdit,QSpinBox,QPushButton,QComboBox,QCheckBox)


class SetupDialog(QDialog):
    def __init__(self,window):
        super().__init__(window)
        self.owner=window;self.controller=window.controller;self.client=self.controller.client
        self.token=None;self.busy=False;self.saving=False;self.finished_setup=False;self.dismissed=False
        self.setWindowTitle('Connect a model · Pi');self.setModal(True);self.setMinimumWidth(470)
        layout=QVBoxLayout(self)
        intro=QLabel('Connect your own OpenAI-compatible model endpoint. You can manage other provider formats in Models & providers, or choose DSH in Settings.')
        intro.setWordWrap(True);layout.addWidget(intro)
        form=QFormLayout();layout.addLayout(form)
        self.name=QLineEdit('My model');self.name.setMaxLength(64)
        self.endpoint=QLineEdit();self.endpoint.setPlaceholderText('https://your-provider.example/v1')
        self.key=QLineEdit();self.key.setEchoMode(QLineEdit.EchoMode.Password);self.key.setPlaceholderText('Optional for a model on this computer')
        self.model=QLineEdit();self.model.setPlaceholderText('Exact model ID from your provider')
        self.context=QSpinBox();self.context.setRange(1024,10000000);self.context.setValue(32768)
        self.output=QSpinBox();self.output.setRange(32,1000000);self.output.setValue(4096)
        for label,field in [('Connection name',self.name),('Endpoint URL',self.endpoint),('API key',self.key),('Model ID',self.model),('Context limit (tokens)',self.context),('Response limit (tokens)',self.output)]:
            field.setAccessibleName(label);form.addRow(label,field)
            (field.textChanged if isinstance(field,QLineEdit) else field.valueChanged).connect(self.invalidate)
        self.images=QCheckBox('Model accepts images');self.images.setAccessibleName('Model accepts images');self.images.toggled.connect(self.invalidate);form.addRow(self.images)
        self.mode=QComboBox();self.mode.addItem('Ask before changes','workspace-write');self.mode.addItem('Read only','read-only');self.mode.addItem('Allow actions without asking','danger-full-access')
        self.mode.setAccessibleName('Approval mode');form.addRow('Approval mode',self.mode)
        self.permission=QLabel();self.permission.setWordWrap(True);layout.addWidget(self.permission)
        self.mode.currentIndexChanged.connect(self.describe_mode);self.describe_mode()
        privacy=QLabel('Check connection sends one short message and, if selected, a generated test image to this endpoint. Your provider may charge for it. No tools, files or chat history are sent. Save stores the key in your private user configuration, without encryption. Optional long-term memory is managed separately in Memory settings.')
        privacy.setWordWrap(True);layout.addWidget(privacy)
        self.note=QLabel('Enter the model limits published by your provider. Select image input for desktop screenshots. The check verifies accepted input formats; visual reasoning needs separate testing.');self.note.setWordWrap(True);layout.addWidget(self.note)
        buttons=QHBoxLayout();layout.addLayout(buttons)
        self.later=QPushButton('Later');self.later.clicked.connect(self.reject);buttons.addWidget(self.later)
        self.check=QPushButton('Check connection');self.check.clicked.connect(self.test);buttons.addWidget(self.check)
        self.save=QPushButton('Save and use model');self.save.setEnabled(False);self.save.clicked.connect(self.commit);buttons.addWidget(self.save)
        self.fields=[self.name,self.endpoint,self.key,self.model,self.context,self.output,self.images,self.mode]

    def describe_mode(self):
        self.permission.setText({'workspace-write':'Routine checks run directly. Augmentor asks before actions that can change files or applications.',
            'read-only':'Tools that can change state are blocked. This is a tool policy, not an operating-system sandbox.',
            'danger-full-access':'Tools can act with your user account’s access without further approval. Stop remains available.'}[self.mode.currentData()])

    def invalidate(self,*_):
        self.token=None
        if hasattr(self,'save'):self.save.setEnabled(False)

    def set_busy(self,value):
        self.busy=value
        for field in self.fields:field.setEnabled(not value)
        self.check.setEnabled(not value);self.save.setEnabled(not value and bool(self.token))

    def request(self,method,payload,callback):
        def work():
            try:return self.client.call(method,payload),None
            except Exception as error:return None,str(error)
        def finished(result):
            if self.dismissed:return
            self.saving=False;self.later.setEnabled(True)
            self.set_busy(False)
            if result[1]:self.note.setText(result[1]);return
            callback(result[0])
        self.owner.call_in_background(work,finished)

    def test(self):
        if self.busy:return
        self.invalidate();self.set_busy(True);self.note.setText('Checking the model connection…')
        payload={'name':self.name.text(),'baseUrl':self.endpoint.text(),'apiKey':self.key.text(),
                 'model':self.model.text(),'api':'openai-completions','contextWindow':self.context.value(),'maxTokens':self.output.value(),'images':self.images.isChecked()}
        def checked(result):
            self.token=result['token'];self.save.setEnabled(True);self.note.setText('Connection verified. Save to use this model.')
        self.request('setup.test',payload,checked)

    def commit(self):
        if self.busy or not self.token:return
        self.saving=True;self.later.setEnabled(False)
        self.set_busy(True);self.note.setText('Saving your model connection…')
        def saved(result):
            if self.owner.controller is not self.controller:return
            self.owner.set_models(result['catalog']);self.controller.choose_model(result['selection']);self.owner.set_selection(result['selection'])
            self.key.clear();self.finished_setup=True;self.owner.set_status('Model connected');self.accept()
        self.request('setup.save',{'token':self.token,'approvalMode':self.mode.currentData()},saved)

    def reject(self):
        if self.saving:return
        self.dismissed=True;self.key.clear()
        if not self.finished_setup:
            self.controller.task(lambda:self.client.call('setup.cancel'))
        super().reject()
