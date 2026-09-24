# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QLineEdit,QPushButton
from .prompt_client import PromptClient

class HomeDialog(QDialog):
    def __init__(self,window):
        super().__init__(window);self.owner=window;self.setWindowTitle('Connect Home');self.setMinimumWidth(380)
        layout=QVBoxLayout(self)
        note=QLabel('Connect this Augmentor to your NAS once. Then ask about your home in any conversation. Get a one-time pairing code from your Home owner.');note.setWordWrap(True);layout.addWidget(note)
        self.url=QLineEdit();self.url.setPlaceholderText('https://your-home-address');self.url.setAccessibleName('Home URL')
        self.name=QLineEdit('Augmentor computer');self.name.setAccessibleName('Device name')
        self.code=QLineEdit();self.code.setEchoMode(QLineEdit.EchoMode.Password);self.code.setAccessibleName('Pairing code')
        for text,widget in [('Home URL',self.url),('Device name',self.name),('One-time pairing code',self.code)]:layout.addWidget(QLabel(text));layout.addWidget(widget)
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        self.connect=QPushButton('Connect');self.connect.clicked.connect(self.pair);layout.addWidget(self.connect)
        self.disconnect=QPushButton('Disconnect');self.disconnect.clicked.connect(lambda:self.run('home.connection.disconnect',{}));layout.addWidget(self.disconnect)
        close=QPushButton('Close');close.clicked.connect(self.accept);layout.addWidget(close)
        self.run('home.connection.state',{})
    def pair(self):
        data={'url':self.url.text().strip(),'name':self.name.text().strip(),'code':self.code.text().strip()};self.code.clear();self.run('home.connection.pair',data)
    def run(self,method,data):
        self.connect.setEnabled(False);self.disconnect.setEnabled(False)
        def work():
            try:return PromptClient().call(method,data),None
            except Exception as e:return None,str(e)
        def done(value):
            result,error=value
            if error:self.status.setText(error);self.connect.setEnabled(True);self.disconnect.setEnabled(True);return
            connected=result.get('connected',False);self.status.setText('Connected. Ask Augmentor to work on your home.' if connected else 'Not connected.')
            self.connect.setEnabled(not connected);self.disconnect.setEnabled(connected)
            if result.get('url'):self.url.setText(result['url'])
        self.owner.call_in_background(work,done)
