# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Handy's familiar controls, hosted in Augmentor's appearance and lifecycle."""
import threading
from PySide6.QtCore import Signal, QTimer
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QCheckBox,QComboBox,QLineEdit,QSpinBox,QScrollArea,QWidget,QMessageBox
from . import dictation
from .voice_button import VoiceButton


class DictationSettingsDialog(QDialog):
    completed=Signal(object,object)
    def __init__(self,window):
        super().__init__(window);self.busy=False;self.snapshot={};self.closed=False;self.dirty=False;self.saved_revision=None;self.model_rows={}
        self.setWindowTitle('System dictation · Powered by Handy');self.resize(460,480)
        self.completed.connect(self.receive);outer=QVBoxLayout(self);scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();layout=QVBoxLayout(body);scroll.setWidget(body);outer.addWidget(scroll)
        identity=QHBoxLayout();orb=VoiceButton(self);orb.configure(window.accent,window.preferences.values['animation']);orb.setEnabled(False)
        identity.addWidget(orb);identity.addWidget(QLabel('Handy\nLocal speech-to-text, built into Augmentor'));layout.addLayout(identity)
        self.enabled=QCheckBox('Enable system dictation');layout.addWidget(self.enabled)
        self.note=QLabel('Loading…');self.note.setWordWrap(True);layout.addWidget(self.note)
        layout.addWidget(QLabel('Activation shortcut'));self.shortcut=QLineEdit('ctrl+space');layout.addWidget(self.shortcut)
        self.activation=QComboBox();self.activation.addItem('Hold to talk','push_to_talk');self.activation.addItem('Press to start / stop','toggle');layout.addWidget(self.activation)
        layout.addWidget(QLabel('Transcription model'));self.models=QComboBox();layout.addWidget(self.models)
        buttons=QHBoxLayout();self.download=QPushButton('Download');self.select=QPushButton('Use model');buttons.addWidget(self.download);buttons.addWidget(self.select);layout.addLayout(buttons)
        self.terms=QLabel();self.terms.setWordWrap(True);self.terms.setOpenExternalLinks(True);layout.addWidget(self.terms)
        layout.addWidget(QLabel('Microphone'));self.microphone=QComboBox();layout.addWidget(self.microphone)
        layout.addWidget(QLabel('Recognition language'));self.language=QComboBox();layout.addWidget(self.language)
        self.translate=QCheckBox('Translate to English (supported models)');layout.addWidget(self.translate)
        layout.addWidget(QLabel('Insert text'));self.paste=QComboBox()
        for label,value in [('Paste · Ctrl+V','ctrl_v'),('Terminal paste · Ctrl+Shift+V','ctrl_shift_v'),('Paste · Shift+Insert','shift_insert'),('Type directly','direct'),('Copy only','none')]:self.paste.addItem(label,value)
        layout.addWidget(self.paste)
        self.clipboard=QCheckBox('Leave transcription on the clipboard');layout.addWidget(self.clipboard)
        layout.addWidget(QLabel('Recordings to keep'));self.history=QSpinBox();self.history.setRange(0,100);layout.addWidget(self.history)
        self.save=QPushButton('Save dictation settings');layout.addWidget(self.save)
        details=QLabel('Hold Ctrl+Space to record into the focused application. Release to transcribe and paste. Escape or × cancels.\n\nThe recording pill uses your Augmentor colours and animated circle. Model files are downloaded separately and remain on this computer.');details.setWordWrap(True);layout.addWidget(details)
        self.cancel=QPushButton('Cancel dictation');layout.addWidget(self.cancel)
        self.cancel_download=QPushButton('Cancel download');layout.addWidget(self.cancel_download)
        self.reload=QPushButton('Reload saved settings');layout.addWidget(self.reload)
        done=QPushButton('Done');done.clicked.connect(self.accept);outer.addWidget(done)
        self.enabled.clicked.connect(lambda value:self.run('enable',{'enabled':value}))
        self.save.clicked.connect(lambda:self.run('settings',{'revision':self.saved_revision,'values':{'shortcut':self.shortcut.text(),'activation':self.activation.currentData(),'microphone':self.microphone.currentData(),'language':self.language.currentData() or 'auto','translate':self.translate.isChecked(),'paste_method':self.paste.currentData(),'clipboard':'copy_to_clipboard' if self.clipboard.isChecked() else 'dont_modify','history_limit':self.history.value(),'retention':'preserve_limit'}}))
        self.download.clicked.connect(self.download_model)
        self.select.clicked.connect(lambda:self.run('model.select',{'id':self.models.currentData()}))
        self.cancel.clicked.connect(lambda:self.run('cancel'))
        self.cancel_download.clicked.connect(lambda:self.run('model.cancel',{'id':self.models.currentData()}))
        self.reload.clicked.connect(self.reload_settings)
        self.shortcut.textEdited.connect(self.mark_dirty)
        for control in (self.activation,self.microphone,self.language,self.paste):control.activated.connect(self.mark_dirty)
        for control in (self.translate,self.clipboard):control.clicked.connect(self.mark_dirty)
        self.history.valueChanged.connect(self.mark_dirty)
        self.models.currentIndexChanged.connect(self.show_terms)
        self.timer=QTimer(self);self.timer.setInterval(2000);self.timer.timeout.connect(self.refresh);self.timer.start()
        self.finished.connect(self.finish);self.refresh()

    def finish(self,_):self.closed=True;self.timer.stop()

    def mark_dirty(self,*_):self.dirty=True

    def reload_settings(self):
        if self.busy:return
        self.dirty=False;self.models.setCurrentIndex(-1);self.refresh()

    def show_terms(self,*_):
        import html
        row=self.model_rows.get(self.models.currentData(),{})
        url=row.get('model_card','https://handy.computer')
        self.terms.setText(html.escape(row.get('license','Publisher terms'))+' · <a href="'+html.escape(url,quote=True)+'">Model card and terms</a>'+('<br><a href="'+html.escape(row['base_model_card'],quote=True)+'">Original model terms</a>' if row.get('base_model_card') else ''))

    def download_model(self):
        row=self.model_rows.get(self.models.currentData(),{})
        answer=QMessageBox.question(self,'Download model',f"Download {row.get('name','this model')} ({row.get('size_mb','?')} MB)?\n\nReview the linked model card and original model terms first. Model licenses are separate from Handy's software license.",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
        if answer==QMessageBox.StandardButton.Yes:self.run('model.download',{'id':self.models.currentData(),'terms_reviewed':True})

    def run(self,method,params=None):
        if self.busy or self.closed:return
        self.busy=True
        self.operation=method
        for item in (self.enabled,self.save,self.download,self.select,self.cancel,self.cancel_download,self.reload):item.setEnabled(False)
        if method!='status':
            for item in (self.shortcut,self.activation,self.microphone,self.language,self.translate,self.paste,self.clipboard,self.history,self.models):item.setEnabled(False)
        def work():
            try:
                result=dictation.request(method,params,timeout=75)
                if method!='status':result=dictation.request('status')
                models=dictation.request('models') if result.get('installed',True) else []
                if models:result=dictation.request('status')
                devices=dictation.request('devices') if models else []
                value={'status':result,'models':models,'devices':devices};error=None
            except Exception as problem:value=None;error=str(problem)
            if not self.closed:self.completed.emit(value,error)
        threading.Thread(target=work,daemon=True).start()

    def refresh(self):self.run('status')

    def receive(self,value,error):
        self.busy=False
        for item in (self.enabled,self.save,self.download,self.select,self.cancel,self.cancel_download,self.reload,self.shortcut,self.activation,self.microphone,self.language,self.translate,self.paste,self.clipboard,self.history,self.models):item.setEnabled(True)
        if error:self.note.setText(error);return
        if self.operation=='settings':self.dirty=False
        self.snapshot=value['status'];s=self.snapshot.get('settings',{})
        self.enabled.setChecked(self.snapshot['enabled']);self.note.setText(self.snapshot.get('error') or self.snapshot['phase'].replace('-',' ').capitalize()+(' · '+self.snapshot['shortcut_description'] if self.snapshot.get('shortcut_description') else ''))
        if not self.dirty:
            self.shortcut.setText(s.get('shortcut','ctrl+space'))
            index=self.activation.findData(s.get('activation','push_to_talk'));self.activation.setCurrentIndex(max(0,index))
            self.saved_revision=self.snapshot.get('revision')
        selected=self.models.currentData() or s.get('model');self.models.clear()
        self.model_rows={row['id']:row for row in value['models']}
        for model in value['models']:
            detail='Installed' if model['installed'] else ('Downloading' if model['downloading'] else str(model['size_mb'])+' MB')
            self.models.addItem(model['name']+' · '+detail,model['id'])
        self.models.setCurrentIndex(max(0,self.models.findData(selected)))
        if not self.dirty and value['models']:
            self.microphone.clear();self.language.clear()
            self.microphone.addItem('System default',None)
            for device in value['devices']:self.microphone.addItem(device['name'],device['name'])
            self.microphone.setCurrentIndex(max(0,self.microphone.findData(s.get('microphone'))))
            self.language.addItem('Automatic','auto')
            languages=sorted({language for model in value['models'] for language in model['languages']})
            for language in languages:self.language.addItem(language,language)
            self.language.setCurrentIndex(max(0,self.language.findData(s.get('language','auto'))))
            self.translate.setChecked(s.get('translate',False));self.paste.setCurrentIndex(max(0,self.paste.findData(s.get('paste_method','ctrl_v'))))
            self.clipboard.setChecked(s.get('clipboard','copy_to_clipboard')=='copy_to_clipboard');self.history.setValue(s.get('history_limit',5))
            self.dirty=False
        self.show_terms()
