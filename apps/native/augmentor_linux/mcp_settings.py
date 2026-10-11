# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Explicit MCP commands on the existing Pi session; authorization URLs stay transient."""
from uuid import uuid4
from PySide6.QtCore import QTimer,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,QLineEdit,QWidget,QPlainTextEdit
from .ui_scale import px

def active(row):return bool(row) and row.get('state') in ('running','cancel-requested')

class McpDialog(QDialog):
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.controller=owner.controller;self.session_id=getattr(self.controller,'session',None)
        self.closed=False;self.reading=False;self.ticket=0;self.servers=[];self.receipt=None;self.authorization_url=None;self.blocked=False;self.available=False
        self.setWindowTitle('MCP servers');self.resize(px(self,550),px(self,430));body=QVBoxLayout(self)
        intro=QLabel('Actions use this conversation’s Pi session. No prompt is sent. Sign-out deletes stored credentials. Reconnect does not replay a tool.');intro.setWordWrap(True);body.addWidget(intro)
        self.server=QComboBox();self.server.setAccessibleName('MCP server');self.server.currentIndexChanged.connect(self.selected_server);body.addWidget(self.server)
        row=QHBoxLayout();body.addLayout(row);self.actions={}
        for kind,label in [('login','Sign in'),('logout','Sign out'),('reconnect','Reconnect')]:
            button=QPushButton(label);button.clicked.connect(lambda _,kind=kind:self.action(kind));row.addWidget(button);self.actions[kind]=button
        config_row=QHBoxLayout();body.addLayout(config_row)
        self.enable_button=QPushButton('Enable server');self.enable_button.clicked.connect(self.enable_server);config_row.addWidget(self.enable_button)
        self.exposure=QComboBox();self.exposure.setAccessibleName('MCP tool exposure');self.exposure.addItems(['codemode','deferred','direct','hidden']);config_row.addWidget(self.exposure)
        self.exposure_button=QPushButton('Apply exposure');self.exposure_button.clicked.connect(lambda:self.configure({'operation':'set-exposure','server':self.server.currentData(),'exposure':self.exposure.currentText()}));config_row.addWidget(self.exposure_button)
        self.edit_button=QPushButton('Edit profile JSON');self.edit_button.clicked.connect(self.edit_profile);body.addWidget(self.edit_button)
        self.editor=QWidget();editor_body=QVBoxLayout(self.editor);body.addWidget(self.editor);self.editor.hide();self.profile_revision=None
        editor_note=QLabel('This private profile may contain credentials. Saving can start or stop configured servers. Log retention and automatic codemode changes refresh approved extensions in idle conversations.');editor_note.setWordWrap(True);editor_body.addWidget(editor_note)
        self.profile=QPlainTextEdit();self.profile.setAccessibleName('MCP profile JSON');self.profile.setMinimumHeight(px(self,160));editor_body.addWidget(self.profile)
        self.save_button=QPushButton('Save profile');self.save_button.clicked.connect(lambda:self.configure({'operation':'save-profile','expectedRevision':self.profile_revision,'text':self.profile.toPlainText()}));editor_body.addWidget(self.save_button)
        close_editor=QPushButton('Close editor');close_editor.clicked.connect(self.close_editor);editor_body.addWidget(close_editor)
        self.note=QLabel('Loading MCP registrations…');self.note.setWordWrap(True);self.note.setAccessibleName('MCP management status');body.addWidget(self.note)
        self.evidence=QLabel('');self.evidence.setWordWrap(True);body.addWidget(self.evidence)
        self.open_sign_in=QPushButton('Open sign-in page');self.open_sign_in.clicked.connect(self.open_url);self.open_sign_in.hide();body.addWidget(self.open_sign_in)
        self.redirect=QWidget();redirect_body=QVBoxLayout(self.redirect);body.addWidget(self.redirect);self.redirect.hide()
        redirect_note=QLabel('If your browser is on another machine, paste its full redirected URL. Pi verifies that it belongs to this sign-in.');redirect_note.setWordWrap(True);redirect_body.addWidget(redirect_note)
        self.redirect_input=QLineEdit();self.redirect_input.setAccessibleName('MCP redirected URL');self.redirect_input.setEchoMode(QLineEdit.EchoMode.Password);self.redirect_input.setMaxLength(8192);redirect_body.addWidget(self.redirect_input)
        self.redirect_submit=QPushButton('Submit redirected URL');self.redirect_submit.clicked.connect(self.submit_redirect);redirect_body.addWidget(self.redirect_submit)
        self.cancel_button=QPushButton('Cancel management');self.cancel_button.clicked.connect(self.cancel);body.addWidget(self.cancel_button)
        self.reload_button=QPushButton('Reload');self.reload_button.clicked.connect(self.reload);body.addWidget(self.reload_button)
        done=QPushButton('Done');done.clicked.connect(self.accept);body.addWidget(done)
        self.finished.connect(self.finish);self.timer=QTimer(self);self.timer.setInterval(500);self.timer.timeout.connect(self.poll);self.timer.start();self.reload()

    def live(self):
        c=self.owner.controller
        return (not self.closed and c is not None and c is self.controller and c.harness=='pi' and c.session==self.session_id
                and c.online and c.connected and getattr(c,'capabilities',{}).get('mcpManagement') is True
                and not any(getattr(c,key,False) for key in ('closed','running','navigating','preparing')))

    def finish(self,_):
        self.closed=True;self.ticket+=1;self.timer.stop();self.authorization_url=None;self.close_editor()
        if active(self.receipt):self.cancel_receipt(self.receipt['requestId'])

    def cancel_receipt(self,request_id):
        client=self.controller.client;sid=self.session_id
        self.owner.call_in_background(lambda:client.call('session.mcpCancelAction',{'sessionId':sid,'requestId':request_id}),lambda _:None)

    def poll(self):
        if not self.live():self.reject();return
        if not self.reading:self.reload()

    def controls(self,*_):
        name=self.server.currentData();server=next((row for row in self.servers if row['name']==name),{})
        for kind,button in self.actions.items():button.setEnabled(not self.reading and not self.blocked and self.available and kind in server.get('managementActions',[]))
        self.server.setEnabled(not self.reading and not self.blocked);self.reload_button.setEnabled(not self.reading)
        self.cancel_button.setEnabled(not self.reading and active(self.receipt) and self.receipt.get('state')!='cancel-requested')
        self.enable_button.setText('Disable server' if server.get('enabled') else 'Enable server')
        configurable=self.controller.capabilities.get('mcpConfiguration') is True
        for button in [self.enable_button,self.exposure,self.exposure_button]:button.setEnabled(not self.reading and not self.blocked and self.available and configurable and bool(server))
        for button in [self.edit_button,self.save_button]:button.setEnabled(not self.reading and not self.blocked and self.available and configurable)

    def selected_server(self,*_):
        if not hasattr(self,'exposure'):return
        server=next((row for row in self.servers if row['name']==self.server.currentData()),{})
        self.exposure.setCurrentText(server.get('exposure','codemode'));self.controls()

    def reload(self):
        if self.reading or not self.live():return
        self.reading=True;self.ticket+=1;ticket=self.ticket;self.controls();client=self.controller.client;sid=self.session_id
        def read():
            try:
                info=client.call('session.mcpInfo',{'sessionId':sid});receipt=info.get('management',{}).get('lastReceipt')
                if receipt:receipt=client.call('session.mcpActionStatus',{'sessionId':sid,'requestId':receipt['requestId']})
                return info,receipt,None
            except Exception:return None,None,'MCP management could not be read. Reload to inspect its receipt.'
        def loaded(result):
            if ticket!=self.ticket or not self.live():return
            self.reading=False;info,receipt,error=result
            if error:self.note.setText(error);self.controls();return
            selected=self.server.currentData();self.servers=info.get('servers',[]);self.server.blockSignals(True);self.server.clear()
            for row in self.servers:self.server.addItem(row['name']+' · '+row['transport']+' · '+row['exposure']+' · '+str(row['toolCount'])+' tools',row['name'])
            index=self.server.findData(selected)
            if index>=0:self.server.setCurrentIndex(index)
            self.server.blockSignals(False);self.receipt=receipt;self.available=info.get('available') is True and info.get('management',{}).get('available') is True;self.blocked=info.get('management',{}).get('busy') is True
            if self.server.currentData()!=selected:self.selected_server()
            self.authorization_url=receipt.get('authorizationUrl') if receipt else None;self.open_sign_in.setVisible(bool(self.authorization_url))
            waiting=bool(receipt and receipt.get('waitingForRedirect'));self.redirect.setVisible(waiting)
            if not waiting:self.redirect_input.clear()
            self.note.setText((receipt['action']+' · '+receipt['server']+' · '+receipt['state']+' · '+receipt['result']+(' · cancellation requested; credentials were not rolled back' if receipt.get('cancelRequested') else '')) if receipt else info.get('reason') or ('Select a server and an explicit action.' if self.servers else 'No MCP servers are registered in this Pi profile.'))
            row=next((row for row in self.servers if row['name']==self.server.currentData()),{});observation=row.get('authorization',{}).get('lastObserved')
            evidence='Last recorded HTTP authorization: '+observation['state']+'. This is historical evidence.' if observation else 'Connection and credential health are not probed by this catalog.'
            configuration=info.get('configuration',{})
            if configuration.get('registrationPending'):evidence+=' Configuration is pending for this conversation.'
            if configuration.get('pendingSessionOptions'):evidence+=' MCP session options have not settled yet.'
            connection=row.get('connection',{});current=connection.get('current')
            if current:evidence+=' Observed connection: '+current['state']+(' · protocol negotiation observed' if current.get('protocolNegotiated') else ' · protocol negotiation not observed')+(' · last problem: '+current['lastProblem']['event'] if current.get('lastProblem') else '')+'.'
            if connection.get('unsavedObservations'):evidence+=' '+str(connection['unsavedObservations'])+' connection observations could not be saved.'
            self.evidence.setText(evidence);self.controls()
        self.owner.call_in_background(read,loaded)

    def action(self,kind):
        if not self.live() or self.reading or self.blocked or not self.available:return
        client=self.controller.client;sid=self.session_id;request_id=str(uuid4());name=self.server.currentData();self.reading=True;self.ticket+=1;ticket=self.ticket;self.controls()
        def submit():
            try:return client.call('session.mcpAction',{'sessionId':sid,'requestId':request_id,'server':name,'action':kind}),None
            except Exception:return None,'MCP command was not acknowledged. Reload to inspect its receipt before another action.'
        def accepted(result):
            receipt,error=result
            if ticket!=self.ticket or not self.live():
                if receipt and active(receipt):self.cancel_receipt(request_id)
                return
            self.reading=False
            if error:self.note.setText(error);self.controls();return
            self.receipt=receipt;self.blocked=active(receipt);self.controls();self.reload()
        self.owner.call_in_background(submit,accepted)

    def cancel(self):
        if self.live() and active(self.receipt):self.cancel_receipt(self.receipt['requestId'])

    def close_editor(self):
        self.profile.clear();self.profile_revision=None;self.editor.hide()

    def edit_profile(self):
        if not self.live() or self.reading or self.blocked or not self.available:return
        self.reading=True;self.ticket+=1;ticket=self.ticket;self.controls();client=self.controller.client;sid=self.session_id
        def read():
            try:return client.call('session.mcpProfile',{'sessionId':sid}),None
            except Exception:return None,'The private MCP profile could not be read.'
        def loaded(result):
            if ticket!=self.ticket or not self.live():return
            self.reading=False;profile,error=result
            if error:self.note.setText(error)
            else:self.profile.setPlainText(profile['text']);self.profile_revision=profile['revision'];self.editor.show()
            self.controls()
        self.owner.call_in_background(read,loaded)

    def enable_server(self):
        server=next((row for row in self.servers if row['name']==self.server.currentData()),None)
        if server:self.configure({'operation':'set-enabled','server':server['name'],'enabled':not server['enabled']})

    def configure(self,params):
        if not self.live() or self.reading or self.blocked or not self.available:return
        client=self.controller.client;sid=self.session_id;request_id=str(uuid4());self.reading=True;self.ticket+=1;ticket=self.ticket;self.controls()
        def submit():
            try:
                if 'expectedRevision' not in params:params['expectedRevision']=client.call('session.mcpProfile',{'sessionId':sid,'metadataOnly':True})['revision']
                return client.call('session.mcpConfigure',{'sessionId':sid,'requestId':request_id,**params}),None
            except Exception:return None,'Configuration was not acknowledged. Reload the profile and inspect the receipt before another save. Your draft is kept.'
        def accepted(result):
            receipt,error=result
            if ticket!=self.ticket or not self.live():
                if receipt and active(receipt):self.cancel_receipt(request_id)
                return
            self.reading=False
            if error:self.note.setText(error);self.controls();return
            self.receipt=receipt;self.blocked=active(receipt);self.controls();self.reload()
        self.owner.call_in_background(submit,accepted)

    def open_url(self):
        if self.live() and self.authorization_url:QDesktopServices.openUrl(QUrl(self.authorization_url))

    def submit_redirect(self):
        if not self.live() or not self.receipt or not self.receipt.get('waitingForRedirect'):return
        client=self.controller.client;sid=self.session_id;request_id=self.receipt['requestId'];url=self.redirect_input.text();self.redirect_input.clear()
        def submit():
            try:client.call('session.mcpSubmitRedirect',{'sessionId':sid,'requestId':request_id,'url':url});return True
            except Exception:return False
        def submitted(ok):
            if not self.live():return
            if ok:self.reload()
            else:self.note.setText('The redirected URL was not accepted. Reload to inspect the sign-in receipt.')
        self.owner.call_in_background(submit,submitted)
