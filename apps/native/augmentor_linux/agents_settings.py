# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Named desktop windows selecting independently owned DSH agents."""
from pathlib import Path
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QListWidget,QListWidgetItem,QLineEdit,QComboBox,QFormLayout,QFileDialog,QKeySequenceEdit)
from PySide6.QtGui import QKeySequence
from PySide6.QtCore import Qt
from . import agent_entries as store
from .shortcuts import clear_shortcut,current_keys,display_key,shortcut_transaction
from .instances import current_name


class AgentsSettings(QWidget):
    def __init__(self,window):
        super().__init__(window);self.owner=window;self.value=store.read();self.selected=None;self.catalog=[];self.models=[];self.saving=False
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        note=QLabel('Each entry opens its own window and chat. DSH owns agent instructions, tools and permissions.');note.setWordWrap(True);layout.addWidget(note)
        self.list=QListWidget();self.list.setAccessibleName('Desktop agents');self.list.setMinimumHeight(100);self.list.setMaximumHeight(130);layout.addWidget(self.list)
        row=QHBoxLayout()
        self.add=QPushButton('Add agent');self.add.clicked.connect(self.add_entry);row.addWidget(self.add)
        self.open=QPushButton('Open / hide');self.open.clicked.connect(self.open_entry);row.addWidget(self.open)
        self.delete=QPushButton('Remove entry');self.delete.clicked.connect(self.remove_entry);row.addWidget(self.delete)
        layout.addLayout(row)
        form=QFormLayout();form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows);form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.name=QLineEdit();self.name.setMaxLength(80);self.name.setAccessibleName('Entry name');form.addRow('Name',self.name)
        self.agent=QComboBox();self.agent.setAccessibleName('DSH agent');form.addRow('DSH agent',self.agent)
        self.refresh=QPushButton('Refresh DSH agents and models');self.refresh.clicked.connect(self.refresh_catalog);form.addRow(self.refresh)
        folder=QHBoxLayout();self.cwd=QLineEdit();self.cwd.setAccessibleName('Agent working folder');folder.addWidget(self.cwd)
        browse=QPushButton('Choose…');browse.clicked.connect(self.browse);folder.addWidget(browse);form.addRow('Working folder',folder)
        self.model=QComboBox();self.model.setAccessibleName('Entry model');form.addRow('Model',self.model)
        self.shortcut=QKeySequenceEdit();self.shortcut.setMaximumSequenceLength(1);self.shortcut.setAccessibleName('Entry shortcut');form.addRow('Shortcut',self.shortcut)
        self.shortcut_note=QLabel();self.shortcut_note.setWordWrap(True);form.addRow(self.shortcut_note)
        layout.addLayout(form)
        self.compatibility=QLabel('Independent agents use typed chat and dictation. Augmentor personal memory, identity editing, prompt improvement and conversational voice are unavailable. Branching and saved chats preserve the selected DSH agent.');self.compatibility.setWordWrap(True);layout.addWidget(self.compatibility);self.agent.currentIndexChanged.connect(lambda _:self.compatibility.setVisible(bool(self.agent.currentData())))
        self.save=QPushButton('Save entry');self.save.clicked.connect(self.save_entry);layout.addWidget(self.save)
        look=QPushButton('Appearance for this window');look.clicked.connect(window.open_appearance);layout.addWidget(look)
        self.note=QLabel();self.note.setWordWrap(True);layout.addWidget(self.note)
        self.list.currentItemChanged.connect(self.select_item)
        self.rebuild(current_name());self.refresh_catalog()

    def rebuild(self,identity=None):
        self.list.blockSignals(True);self.list.clear()
        for entry in self.value['entries']:
            item=QListWidgetItem(entry['name']+' · '+(entry['preset'] or 'Augmentor'));item.setData(Qt.ItemDataRole.UserRole,entry['id']);self.list.addItem(item)
            if entry['id']==identity:self.list.setCurrentItem(item)
        self.list.blockSignals(False)
        if not self.list.currentItem() and self.list.count():self.list.setCurrentRow(0)
        self.select_item(self.list.currentItem())

    def select_item(self,item,*_):
        if self.saving:return
        self.selected=next((e for e in self.value['entries'] if item and e['id']==item.data(Qt.ItemDataRole.UserRole)),None)
        if self.selected:self.load_fields()

    def load_fields(self):
        entry=self.selected;self.name.setText(entry['name']);self.cwd.setText(entry.get('cwd') or '')
        exists=any(e['id']==entry['id'] for e in self.value['entries'])
        self.fill_catalog();self.shortcut.clear();self.delete.setEnabled(exists and entry['id']!='main');self.open.setEnabled(exists)
        def work():
            try:return current_keys(entry['id']),None
            except Exception as e:return [],str(e)
        def done(result):
            if self.selected is not entry:return
            keys,error=result;self.shortcut_note.setText(error or 'Current: '+(', '.join(display_key(k) for k in keys) or 'Unassigned')+'. Click the field and press your shortcut. Fn may be reported as another key.')
        self.owner.call_in_background(work,done)

    def fill_catalog(self,selection=None):
        entry=selection if selection is not None else self.selected or {};self.agent.clear();self.agent.addItem('Augmentor (existing experience)',None)
        for row in self.catalog:
            label=row.get('name') or row['id'];broken=row.get('broken')
            self.agent.addItem(label+(' · unavailable' if broken else ''),row['id'])
            if broken:self.agent.model().item(self.agent.count()-1).setEnabled(False)
        index=self.agent.findData(entry.get('preset'))
        if index<0:self.agent.addItem(str(entry['preset'])+' · missing',entry['preset']);index=self.agent.count()-1
        self.agent.setCurrentIndex(index)
        self.model.clear();self.model.addItem('Keep this window’s selected model',None)
        for row in self.models:self.model.addItem(row.get('name',row['model'])+' · '+row['provider'],{k:row[k] for k in ('provider','model')})
        index=self.model.findData(entry.get('model'))
        if index<0:self.model.addItem(entry['model']['model']+' · unavailable',entry['model']);index=self.model.count()-1
        self.model.setCurrentIndex(index)

    def refresh_catalog(self):
        self.refresh.setEnabled(False);self.note.setText('Reading DSH agents…')
        def work():
            try:
                from .adapters.dsh_wire import DshClient
                client=DshClient();rows=client.call('agentPresets.list').get('presets',[]);catalog=client.model_catalog()
                return rows,[m for g in catalog.get('groups',[]) for m in g.get('models',[])],None
            except Exception as error:return [],[],str(error)
        def done(result):
            selection={'preset':self.agent.currentData(),'model':self.model.currentData()}
            self.catalog,self.models,error=result;self.refresh.setEnabled(True);self.fill_catalog(selection);self.note.setText(error or 'DSH agents refreshed. Agent and model selections are independent.')
        self.owner.call_in_background(work,done)

    def add_entry(self):
        self.list.clearSelection();self.selected={'id':store.new_id(),'name':'New agent','preset':None,'cwd':str(Path.home()),'model':None,'stateKey':None};self.load_fields();self.name.setFocus();self.name.selectAll()

    def browse(self):
        path=QFileDialog.getExistingDirectory(self,'Choose agent working folder',self.cwd.text() or str(Path.home()))
        if path:self.cwd.setText(path)

    def save_entry(self):
        if not self.selected or self.saving:return
        entry={**self.selected,'name':self.name.text().strip(),'preset':self.agent.currentData(),'cwd':self.cwd.text().strip() or None,'model':self.model.currentData()}
        if entry['preset'] and not any(r.get('id')==entry['preset'] and not r.get('broken') for r in self.catalog):self.note.setText('Selected DSH agent unavailable. Refresh or repair it in DSH.');return
        if entry['model'] and not any(all(r.get(k)==entry['model'][k] for k in ('provider','model')) for r in self.models):self.note.setText('Selected model unavailable. Refresh or select another model.');return
        try:store.validate(entry)
        except Exception as error:self.note.setText(str(error));return
        if entry['id']==current_name() and (self.owner.controller.running or self.owner.controller.navigating or getattr(self.owner,'editing',False) or getattr(self.owner,'voice_dialog',None) or getattr(self.owner,'voice_opening',False)):
            self.note.setText('Finish the current action and voice conversation before changing this entry.');return
        sequence=QKeySequence(self.shortcut.keySequence());revision=self.value['revision'];self.saving=True;self.save.setEnabled(False)
        def work():
            try:
                # Revision admission precedes OS mutation; failed commits restore the binding.
                transaction=(lambda:shortcut_transaction(entry['id'],sequence)) if not sequence.isEmpty() else None
                return store.save(entry,revision,transaction),None
            except Exception as error:return None,str(error)
        def done(result):
            value,error=result;self.saving=False;self.save.setEnabled(True)
            if error:self.note.setText(error);return
            changed=store.binding(self.selected)!=store.binding(next(e for e in value['entries'] if e['id']==entry['id']))
            self.value=value;self.rebuild(entry['id']);self.note.setText('Saved. Open this entry to change its appearance. Reopen any other open window for this entry to load changes.')
            if entry['id']==current_name():
                self.owner.setWindowTitle('Augmentor Agent · '+entry['name']);self.owner.brand.setText('Augmentor Agent · '+entry['name'])
                if changed:self.owner.switch_harness('dsh',reconnect=True)
                elif self.owner.controller.configure_entry_model(entry['model']) and entry['model']:self.owner.set_selection(entry['model'])
        self.owner.call_in_background(work,done)

    def open_entry(self):
        try:store.launch(self.selected['id'])
        except Exception as error:self.note.setText(str(error))

    def remove_entry(self):
        if not self.selected or self.selected['id']=='main':return
        if self.selected['id']==current_name():self.note.setText('Remove this entry from another window after closing it.');return
        try:self.value=store.remove(self.selected['id'],self.value['revision'],clear_shortcut,lambda:shortcut_transaction(self.selected['id'],remove=True));self.rebuild();self.note.setText('Desktop entry and shortcut removed. The DSH agent and conversations are retained.')
        except Exception as error:self.note.setText(str(error))

    def capture_current(self):
        if not self.shortcut.hasFocus() or not self.selected:return False
        try:
            keys=current_keys(current_name())
            if keys:self.shortcut.setKeySequence(QKeySequence(keys[0]));return True
        except Exception:pass
        return False
