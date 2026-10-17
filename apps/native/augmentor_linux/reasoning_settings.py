# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Pi-owned effort and adaptive mappings. Settings never start inference."""
from copy import deepcopy
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QDialog,QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,
    QLabel,QComboBox,QCheckBox,QPushButton,QTabWidget,QScrollArea,QGroupBox)
from .ui_scale import px

TIERS={'off':'Greeting / simple text','low':'Short summary','medium':'Analysis','high':'Complex work'}
LEVELS=['off','minimal','low','medium','high','xhigh','max']

class ReasoningDialog(QDialog):
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.controller=owner.controller
        self.session_id=getattr(self.controller,'session',None);self.selection=deepcopy(getattr(self.controller,'selection',None))
        self.closed=False;self.ticket=0;self.saving=False;self.session=None;self.policy=None;self.routes=[]
        self.setWindowTitle('Reasoning');self.resize(px(self,580),px(self,650))
        outer=QVBoxLayout(self);self.tabs=QTabWidget();outer.addWidget(self.tabs)
        self.note=QLabel('Loading reasoning settings…');self.note.setWordWrap(True);self.note.setAccessibleName('Reasoning status');outer.addWidget(self.note)
        row=QHBoxLayout();outer.addLayout(row)
        self.reload_button=QPushButton('Reload saved settings');self.reload_button.clicked.connect(self.reload);row.addWidget(self.reload_button)
        done=QPushButton('Done');done.clicked.connect(self.accept);row.addWidget(done)
        self.finished.connect(self.finish)
        self.timer=QTimer(self);self.timer.setInterval(200);self.timer.timeout.connect(self.check_context);self.timer.start()
        self.reload()

    def finish(self,_):
        self.closed=True;self.ticket+=1;self.timer.stop()

    def live(self):
        c=self.owner.controller
        return (not self.closed and c is self.controller and c is not None and c.harness=='pi'
                and c.session==self.session_id and c.selection==self.selection and c.online and c.connected
                and getattr(c,'capabilities',{}).get('reasoning') is True
                and not any(getattr(c,key,False) for key in ('closed','running','navigating','preparing')))

    def check_context(self):
        if not self.live():self.reject()

    def controls(self,enabled):
        self.tabs.setEnabled(enabled);self.reload_button.setEnabled(enabled)

    def run(self,work,done):
        if not self.live():self.note.setText('Select an idle Pi conversation before changing reasoning.');self.controls(False);return
        self.ticket+=1;ticket=self.ticket;self.saving=True;self.controls(False)
        def read():
            try:return work(),None
            except Exception as error:return None,str(error)
        def loaded(result):
            if ticket!=self.ticket or not self.live():return
            self.saving=False;self.controls(True)
            if result[1]:self.note.setText(result[1]);return
            done(result[0])
        self.owner.call_in_background(read,loaded)

    def reload(self):
        if self.saving:return
        client=getattr(self.controller,'client',None)
        def read():return (client.call('session.reasoning',{'sessionId':self.session_id}),client.call('reasoning.describe'),client.call('models.list'))
        self.run(read,self.mount)

    def choice(self,label,values,value):
        box=QComboBox();box.setAccessibleName(label);box.setMinimumContentsLength(12)
        box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        for key,title in values:box.addItem(title,key)
        index=box.findData(value)
        if index<0:box.addItem(str(value)+' (unavailable)',value);index=box.count()-1
        box.setCurrentIndex(index);return box

    def label(self,text):
        label=QLabel(text);label.setWordWrap(True);return label

    def checkbox(self,text,value):
        box=QCheckBox(text);box.setChecked(value);box.setAccessibleName(text);return box

    def mount(self,result):
        self.session,self.policy,catalog=result
        while self.tabs.count():
            widget=self.tabs.widget(0);self.tabs.removeTab(0);widget.deleteLater()
        self.models=[m for group in catalog['groups'] for m in group['models'] if m.get('available')]
        conversation=QWidget();layout=QVBoxLayout(conversation);form=QFormLayout();layout.addLayout(form)
        self.mode=self.choice('Reasoning mode',[('adaptive','Adaptive'),('manual','Manual')],self.session['mode'])
        self.level=self.choice('Saved thinking effort',[(v,v) for v in self.session['availableLevels']],self.session['thinkingLevel'])
        form.addRow('Reasoning mode',self.mode);form.addRow('Saved thinking effort',self.level)
        self.effective=self.label('');layout.addWidget(self.effective);self.describe()
        layout.addWidget(self.label('Adaptive uses your explicit mappings. Manual mode or an unmapped model keeps the saved effort. Model changes never silently lower it.'))
        self.save_session=QPushButton('Save conversation');self.save_session.clicked.connect(self.save_conversation);layout.addWidget(self.save_session);layout.addStretch()
        self.tabs.addTab(conversation,'This conversation')
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QScrollArea.Shape.NoFrame);profile=QWidget();body=QVBoxLayout(profile);scroll.setWidget(profile);profile.setAutoFillBackground(False);scroll.viewport().setAutoFillBackground(False);self.tabs.addTab(scroll,'Adaptive policy')
        config=self.policy['config'];self.enabled=self.checkbox('Enable Adaptive Reasoning',config['enabled']);self.text_only=self.checkbox('Limit tools for supplied-text transformations',config['textOnly'])
        self.desktop=self.checkbox('Desktop and Harness conversations','augmentor-linux-pi' in config['presets']);self.browser=self.checkbox('Browser conversations','augmentor-browser-pi' in config['presets'])
        for box in [self.enabled,self.text_only,self.desktop,self.browser]:body.addWidget(box)
        body.addWidget(self.label('Map each task tier to an effort supported by that exact model. Unmapped models keep their effort. No extra classification model is called.'))
        self.route_area=QVBoxLayout();body.addLayout(self.route_area);self.routes=[]
        for route in config['routes']:self.add_route(route)
        self.model_choice=self.choice('Model to map',[(m,m['provider']+'/'+m['model']) for m in self.models],self.models[0] if self.models else None);body.addWidget(self.model_choice)
        self.add_button=QPushButton('Add mapping');self.add_button.setEnabled(bool(self.models));self.add_button.clicked.connect(self.add_mapping);body.addWidget(self.add_button)
        self.save_policy=QPushButton('Save adaptive policy');self.save_policy.clicked.connect(self.save_profile);body.addWidget(self.save_policy);body.addStretch()
        self.note.setText('Changes apply to subsequent requests. Reload explicitly discards this settings draft.')

    def describe(self):
        last=self.session.get('lastDecision')
        self.effective.setText('Adaptive status: '+self.session['adaptiveStatus']+'. Saved effort: '+self.session['thinkingLevel']+'. '+('Last request: '+last['thinkingLevel']+' ('+last['reason']+').' if last else 'No decision recorded in this process.'))

    def add_route(self,route):
        route=deepcopy(route);group=QGroupBox(route['provider']+'/'+route['model']);group.setToolTip(route['provider']+'/'+route['model']);layout=QVBoxLayout(group);form=QFormLayout();layout.addLayout(form)
        model=next((m for m in self.models if (m['provider'],m['model'])==(route['provider'],route['model'])),None)
        levels=model['thinkingLevels'] if model else LEVELS;controls={}
        for tier,title in TIERS.items():
            field=self.choice(title,[(v,v) for v in levels],route['efforts'][tier]);controls[tier]=field;form.addRow(title,field)
        item={'route':route,'controls':controls,'widget':group};self.routes.append(item)
        remove=QPushButton('Remove mapping');remove.clicked.connect(lambda:self.remove_route(item));layout.addWidget(remove);self.route_area.addWidget(group)

    def remove_route(self,item):
        if self.saving:return
        self.routes.remove(item);self.route_area.removeWidget(item['widget']);item['widget'].deleteLater()

    def add_mapping(self):
        if self.saving:return
        model=self.model_choice.currentData()
        if not model:self.note.setText('Choose an available model.');return
        if any((r['route']['provider'],r['route']['model'])==(model['provider'],model['model']) for r in self.routes):self.note.setText('This model already has a mapping.');return
        levels=model['thinkingLevels'];self.add_route({'provider':model['provider'],'model':model['model'],'efforts':{tier:tier if tier in levels else levels[-1] for tier in TIERS}})
        self.note.setText('Mapping added to the unsaved draft.')

    def configuration(self):
        return {'enabled':self.enabled.isChecked(),'textOnly':self.text_only.isChecked(),
                'presets':(['augmentor-linux-pi'] if self.desktop.isChecked() else [])+(['augmentor-browser-pi'] if self.browser.isChecked() else []),
                'routes':[{'provider':r['route']['provider'],'model':r['route']['model'],'efforts':{tier:field.currentData() for tier,field in r['controls'].items()}} for r in self.routes]}

    def save_conversation(self):
        if self.saving or not self.session:return
        params={'sessionId':self.session_id,'expectedRevision':self.session['revision'],'mode':self.mode.currentData(),'thinkingLevel':self.level.currentData()}
        def saved(value):self.session=value;self.describe();self.note.setText('Conversation reasoning saved.')
        self.run(lambda:self.controller.client.call('session.selectReasoning',params),saved)

    def save_profile(self):
        if self.saving or not self.policy:return
        params={'expectedRevision':self.policy['revision'],'config':self.configuration()}
        def work():
            policy=self.controller.client.call('reasoning.configure',params)
            try:return policy,self.controller.client.call('session.reasoning',{'sessionId':self.session_id}),None
            except Exception as error:return policy,None,str(error)
        def saved(value):
            self.policy=value[0]
            if value[1]:self.session=value[1];self.describe()
            self.note.setText('Adaptive policy saved.'+(' Reload to refresh the conversation status: '+value[2] if value[2] else ''))
        self.run(work,saved)
