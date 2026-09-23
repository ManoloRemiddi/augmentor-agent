# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Independently versioned instructions for rewriting composer drafts."""
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QTextEdit,QTextBrowser,QPushButton,QTabWidget

class ImprovementSettings(QWidget):
    def __init__(self,owner,client):
        super().__init__();self.owner=owner;self.client=client;self.current=None;self.saving=False
        layout=QVBoxLayout(self)
        hint=QLabel('These instructions power ✦ Improve prompt in the input box. Customize how drafts are rewritten. Your saved /prompts stay separate.');hint.setWordWrap(True);layout.addWidget(hint)
        tabs=QTabWidget();layout.addWidget(tabs)
        self.editor=QTextEdit();self.editor.setAcceptRichText(False);self.editor.setAccessibleName('Prompt improvement instructions');tabs.addTab(self.editor,'Instructions')
        self.preview=QTextBrowser();self.preview.setOpenLinks(False);tabs.addTab(self.preview,'Preview')
        self.editor.textChanged.connect(lambda:self.preview.setMarkdown(self.editor.toPlainText()))
        self.note=QLabel('Loading instructions…');self.note.setWordWrap(True);layout.addWidget(self.note)
        row=QHBoxLayout();layout.addLayout(row)
        self.save_button=QPushButton('Save instructions');self.save_button.clicked.connect(self.save);row.addWidget(self.save_button)
        self.reload_button=QPushButton('Reload');self.reload_button.clicked.connect(self.reload);row.addWidget(self.reload_button)
        self.default_button=QPushButton('Use default');self.default_button.clicked.connect(self.use_default);row.addWidget(self.default_button)
        self.controls(False)
    def controls(self,enabled):
        for widget in (self.editor,self.save_button,self.reload_button,self.default_button):widget.setEnabled(enabled)
    def receive(self,value):
        if not value:self.note.setText('Restart the prompt service to load these settings.');return
        if self.current is None:
            self.current=dict(value);self.editor.setPlainText(value['content']);self.controls(True);self.note.setText('Changes take effect after saving.')
        elif value['revision']!=self.current['revision']:
            self.note.setText('Instructions changed elsewhere. Your draft is kept. Reload to load the latest version.')
    def reload(self):
        if self.saving:return
        self.controls(False)
        def work():
            try:return self.client.call('prompts.list')['improvement'],None
            except Exception as e:return None,str(e)
        def done(result):
            self.controls(True)
            if result[1]:self.note.setText(result[1]);return
            self.current=None;self.receive(result[0])
        self.owner.call_in_background(work,done)
    def use_default(self):
        if self.current:self.editor.setPlainText(self.current['defaultContent']);self.note.setText('Default instructions loaded. Save to apply them.')
    def save(self):
        if not self.current or self.saving:return
        content=self.editor.toPlainText()
        if not content.strip() or len(content)>8000:self.note.setText('Enter instructions up to 8,000 characters.');return
        revision=self.current['revision'];self.saving=True;self.controls(False)
        def work():
            try:return self.client.call('prompts.improvement.save',{'content':content,'expectedRevision':revision}),None
            except Exception as e:return None,str(e)
        def done(result):
            self.saving=False;self.controls(True)
            if result[1]:self.note.setText(result[1]);return
            self.current=dict(result[0]['improvement']);self.note.setText('Instructions saved. Improve prompt will use them for the next draft.')
        self.owner.call_in_background(work,done)
