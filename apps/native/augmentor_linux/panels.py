# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
from datetime import datetime
import json
from pathlib import Path
import sys
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,
    QListWidget,QListWidgetItem,QPushButton,QCheckBox,QComboBox,QMessageBox,QTextEdit,QWidget,QTabWidget,QTextBrowser,QScrollArea)
from . import __version__


class HistoryDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.owner=window;self.rows=[]
        self.setWindowTitle('Conversation history');self.resize(500,520)
        layout=QVBoxLayout(self)
        self.search=QLineEdit();self.search.setPlaceholderText('Search titles…');self.search.setClearButtonEnabled(True);layout.addWidget(self.search)
        filters=QHBoxLayout()
        self.saved=QCheckBox('Saved only');self.all=QCheckBox('All agents');self.all.hide()
        filters.addWidget(self.saved);filters.addWidget(self.all);layout.addLayout(filters)
        self.list=QListWidget();layout.addWidget(self.list)
        self.note=QLabel('Loading history…');self.note.setWordWrap(True);layout.addWidget(self.note)
        buttons=QHBoxLayout()
        refresh=QPushButton('Refresh');refresh.clicked.connect(window.controller.list_sessions);buttons.addWidget(refresh)
        self.open=QPushButton('Open conversation');self.open.clicked.connect(self.open_selected);buttons.addWidget(self.open)
        close=QPushButton('Close');close.clicked.connect(self.reject);buttons.addWidget(close);layout.addLayout(buttons)
        self.search.textChanged.connect(self.render);self.saved.toggled.connect(self.render);self.all.toggled.connect(self.render)
        self.list.itemDoubleClicked.connect(lambda _:self.open_selected())
        window.controller.sessions.connect(self.receive)
        self.finished.connect(self.disconnect_sessions)
        window.controller.list_sessions()

    def disconnect_sessions(self,_):
        try:self.owner.controller.sessions.disconnect(self.receive)
        except (TypeError,RuntimeError):pass

    def receive(self,rows):
        self.rows=rows;self.render()

    def render(self):
        self.list.clear();query=self.search.text().casefold()
        for row in self.rows:
            if row.get('archived') or row.get('blank'):continue
            if not self.all.isChecked() and row.get('agentPreset')!=getattr(self.owner.controller,'preset','augmentor-linux-pi'):continue
            if self.saved.isChecked() and not row.get('saved'):continue
            title=str(row.get('title') or row['sessionId'])
            if query not in (title+' '+row['sessionId']).casefold():continue
            stamp=datetime.fromtimestamp(row.get('updatedAt',0)/1000).strftime('%d %b · %H:%M')
            item=QListWidgetItem(('★ ' if row.get('saved') else '')+title+'\n'+stamp+' · '+str(row.get('agentPreset') or 'Pi'))
            item.setData(Qt.ItemDataRole.UserRole,row);self.list.addItem(item)
        self.note.setText(f'{self.list.count()} conversations in this harness.')

    def open_selected(self):
        item=self.list.currentItem()
        if item:
            self.owner.controller.open_session(item.data(Qt.ItemDataRole.UserRole));self.accept()


class AccessDialog(QDialog):
    def __init__(self,window):
        super().__init__(window);self.owner=window;self.descriptor=None
        self.setWindowTitle('Approval mode · new chats');self.resize(380,220)
        layout=QVBoxLayout(self)
        note=QLabel('Choose whether tools may change files or run actions. Existing chats keep their policy. These controls are tool permissions, not an OS sandbox.');note.setWordWrap(True);layout.addWidget(note)
        self.mode=QComboBox()
        for label,value in [('Read only','read-only'),('Ask before actions','workspace-write'),('Automatic · full access','danger-full-access')]:self.mode.addItem(label,value)
        layout.addWidget(self.mode)
        self.apply=QPushButton('Apply to new chats');self.apply.setEnabled(False);self.apply.clicked.connect(self.save);layout.addWidget(self.apply)
        self.note=QLabel('Loading approval settings…');self.note.setWordWrap(True);layout.addWidget(self.note)
        window.call_in_background(lambda:window.controller.client.setting('permission'),self.receive)

    def receive(self,value):
        if not value:self.note.setText('This harness has no editable approval settings.');return
        self.descriptor=value;self.mode.setCurrentIndex(self.mode.findData(value.get('value',{}).get('defaultPreset')))
        self.apply.setEnabled(True);self.note.setText('Choose the policy for future chats.')

    def save(self):
        value=self.mode.currentData()
        if value=='danger-full-access' and self.descriptor.get('value',{}).get('defaultPreset')!=value:
            if QMessageBox.question(self,'Automatic execution','Use full access without approval prompts for new chats?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.apply.setEnabled(False)
        payload={'ns':'permission','ops':[{'op':'set','path':['defaultPreset'],'value':value}],'expectedRevision':self.descriptor['revision']}
        self.owner.call_in_background(lambda:self.owner.controller.client.call('settings.mutate',payload),lambda _:(self.owner.set_status('Approval mode updated for new chats'),self.accept()))


class UpdatesDialog(QDialog):
    def __init__(self,window):
        super().__init__(window);self.owner=window;self.setWindowTitle('Versions & updates');self.resize(410,250)
        layout=QVBoxLayout(self)
        self.info=QLabel();self.info.setWordWrap(True);self.info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);layout.addWidget(self.info)
        check=QPushButton('Check installed versions');check.clicked.connect(self.check);layout.addWidget(check)
        close=QPushButton('Done');close.clicked.connect(self.accept);layout.addWidget(close);self.check()

    def check(self):
        if sys.platform == 'darwin':
            self.info.setText(f'Augmentor Agent {__version__} · macOS preview\n\nAutomatic updates are not available yet. Do not replace the app while Augmentor or its browser companion is working. Read the Mac guide at https://augmentoragent.com/macos.html for the current release and update instructions.')
            return
        self.info.setText('Checking the selected harness…')
        def read():
            client=self.owner.controller.client
            host=client.call('host.describe')
            return host
        def show(host):
            self.info.setText(f"Native app: {__version__}\nHarness: {self.owner.controller.harness}\nPi: {host.get('piVersion','unknown')}\nRuntime: {host.get('version','unknown')}\nProtocol: {host.get('protocol','unknown')}\n\nUse the installer to update this application. Your settings and conversations are preserved.")
        self.owner.call_in_background(read,show)


class LicensesDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.setWindowTitle('About & licenses'); self.resize(620, 500)
        layout = QVBoxLayout(self)
        title = QLabel(f'Augmentor Agent {__version__}\nCopyright © 2026 Manolo Remiddi · MIT with Augmentor Resale Restriction')
        title.setWordWrap(True); layout.addWidget(title)
        note = QLabel('Built with PySide6 and Qt under LGPL terms. These libraries remain replaceable. Third-party components retain their own licenses.')
        note.setWordWrap(True); layout.addWidget(note)
        root = Path(__file__).resolve().parents[3]
        choices = QComboBox(); layout.addWidget(choices)
        text = QTextEdit(); text.setReadOnly(True); layout.addWidget(text)
        documents = [('Augmentor · MIT with Augmentor Resale Restriction', root / 'LICENSE'),
                     ('Distribution and library replacement', root / 'docs/LICENSING.md'),
                     ('Mac library sources and replacement', root / 'docs/MACOS-LIBRARY-REPLACEMENT.md'),
                     ('LGPL version 3', root / 'licenses/LGPL-3.0.txt'),
                     ('GPL version 3 (incorporated by LGPL)', root / 'licenses/GPL-3.0.txt')]
        for file in sorted((root / 'licenses/upstream').glob('*.txt')):
            documents.append((file.stem, file))
        for label, _ in documents: choices.addItem(label)
        def select(index):
            file = documents[index][1]
            text.setPlainText(file.read_text() if file.exists() else 'License file unavailable. Reinstall the complete Augmentor package.')
        choices.currentIndexChanged.connect(select); select(0)
        if (root / 'licenses/node.txt').exists():
            documents.append(('Node and its bundled components', root / 'licenses/node.txt'))
            choices.addItem(documents[-1][0])
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        notices = QPushButton('Open all component notices')
        notices.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(root / 'licenses'))))
        layout.addWidget(notices)
        close = QPushButton('Close'); close.clicked.connect(self.accept); layout.addWidget(close)


class SettingsDialog(QDialog):
    def __init__(self,window):
        from .instances import current_name
        super().__init__(window);self.owner=window
        self.setWindowTitle('Settings · '+('First agent' if current_name()=='main' else 'Second agent'));self.setMinimumWidth(400)
        outer=QVBoxLayout(self);scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content=QWidget();layout=QVBoxLayout(content);scroll.setWidget(content);content.setAutoFillBackground(False);outer.addWidget(scroll)
        self.resize(460,min(820,self.screen().availableGeometry().height()-80))
        from .settings_icons import settings_icon,settings_label
        from .voice_settings import VoiceSettingsDialog
        voice=QPushButton('Resonant Voice')
        voice.clicked.connect(lambda:VoiceSettingsDialog(window).exec())
        layout.addWidget(voice)
        layout.addWidget(settings_label('Harness','harness',window.accent))
        engine=QComboBox();engine.addItem('Pi','pi');engine.addItem('DSH','dsh')
        engine.setCurrentIndex(engine.findData(getattr(window.controller,'harness','pi')))
        engine.setAccessibleName('Harness')
        engine.activated.connect(lambda _:window.switch_harness(engine.currentData()))
        layout.addWidget(engine)
        from .dsh_setup import DshSetupDialog
        dsh=QPushButton('Connect DSH');dsh.clicked.connect(lambda:DshSetupDialog(window).exec());layout.addWidget(dsh)
        from .home_settings import HomeDialog
        home=QPushButton('Connect Home');home.clicked.connect(lambda:HomeDialog(window).exec());layout.addWidget(home)
        from .recovery import RecoveryDialog
        recovery=QPushButton('Recover connection');recovery.clicked.connect(lambda:RecoveryDialog(window).exec());layout.addWidget(recovery)
        from .shortcut_settings import ShortcutSettings
        layout.addWidget(settings_label('Window shortcuts','keyboard',window.accent))
        self.shortcuts=ShortcutSettings(window);layout.addWidget(self.shortcuts)
        note=QLabel('Appearance, skins and voice settings are saved for this agent window. The second agent starts with a copy of the first agent’s settings.');note.setWordWrap(True);layout.addWidget(note)
        appearance=QPushButton('Colours && visual effects');appearance.clicked.connect(window.open_appearance);layout.addWidget(appearance)
        prompts=QPushButton('Prompt library');prompts.clicked.connect(window.open_prompt_library);layout.addWidget(prompts)
        from .memory import MemoryDialog
        memory=QPushButton('Memory');memory.clicked.connect(lambda:MemoryDialog(window).exec());layout.addWidget(memory)
        from .support import SupportDialog
        support=QPushButton('Support report');support.clicked.connect(lambda:SupportDialog(window).exec());layout.addWidget(support)
        done=QPushButton('Done');done.clicked.connect(self.accept);outer.addWidget(done)
        for button,name in [(voice,'voice'),(dsh,'connect'),(recovery,'recover'),(appearance,'appearance'),(prompts,'prompts'),(memory,'memory'),(support,'support'),(done,'done')]:
            button.setIcon(settings_icon(name,window.accent))

    def capture_current(self):
        return self.shortcuts.capture_current()


class PromptLibraryDialog(QDialog):
    def __init__(self,window):
        super().__init__(window);self.owner=window;self.original=None;self.prompt_id=None;self.revision=None;self.rows=[]
        self.client=window.composer.prompt_menu.catalog.client;self.loading=False;self.saving=False
        self.setWindowTitle('Prompt library');self.resize(560,500)
        outer=QVBoxLayout(self);self.tabs=QTabWidget();outer.addWidget(self.tabs)
        saved=QWidget();layout=QVBoxLayout(saved);self.tabs.addTab(saved,'Saved prompts')
        from .improvement_settings import ImprovementSettings
        self.improvement=ImprovementSettings(window,self.client);self.tabs.addTab(self.improvement,'Improve prompt')
        self.search=QLineEdit();self.search.setPlaceholderText('Search saved prompts…');self.search.setAccessibleName('Search saved prompts');layout.addWidget(self.search)
        self.list=QListWidget();layout.addWidget(self.list);self.search.textChanged.connect(self.filter_prompts)
        self.name=QLineEdit();self.name.setPlaceholderText('Shortcut name, e.g. summarise');layout.addWidget(self.name)
        self.content=QTextEdit();self.content.setPlaceholderText('Reusable prompt text')
        editor_tabs=QTabWidget();editor_tabs.addTab(self.content,'Prompt text');preview=QTextBrowser();preview.setOpenLinks(False);editor_tabs.addTab(preview,'Preview');layout.addWidget(editor_tabs)
        self.content.textChanged.connect(lambda:preview.setMarkdown(self.content.toPlainText()))
        self.content.setAcceptRichText(False)
        self.content.setAccessibleName('Prompt text')
        insert_row=QHBoxLayout()
        self.clipboard_button=QPushButton('Insert clipboard')
        self.clipboard_button.setToolTip('Insert [clipboard] at the cursor. It becomes your copied text when you choose this /prompt.')
        self.clipboard_button.clicked.connect(self.insert_clipboard)
        insert_row.addWidget(self.clipboard_button);insert_row.addStretch();layout.addLayout(insert_row)
        hint=QLabel('[clipboard] is replaced with the current clipboard text when you choose this /prompt. You can review it before sending.')
        hint.setWordWrap(True);layout.addWidget(hint)
        self.note=QLabel('Type / in the composer to insert a saved prompt.');self.note.setWordWrap(True);layout.addWidget(self.note)
        buttons=QHBoxLayout()
        for label,callback in [('New',self.new),('Refresh',self.refresh),('Reload',self.reload_selected),('Save',self.save),('Delete',self.delete)]:
            button=QPushButton(label);button.clicked.connect(callback);buttons.addWidget(button)
        layout.addLayout(buttons);done=QPushButton('Done');done.clicked.connect(self.accept);outer.addWidget(done)
        self.list.currentRowChanged.connect(self.select);self.refresh()
        self.poll=QTimer(self);self.poll.setInterval(1500);self.poll.timeout.connect(self.refresh);self.poll.start();self.finished.connect(lambda _:self.poll.stop())

    def refresh(self):
        if self.loading or self.saving:return
        self.loading=True
        def read():
            try:return self.client.call('prompts.list'),None
            except Exception as error:return None,str(error)
        def receive(result):
            self.loading=False
            if result[1]:self.note.setText(result[1])
            else:self.receive(result[0])
        self.owner.call_in_background(read,receive)
    def insert_clipboard(self):
        from .prompts import CLIPBOARD_TOKEN
        self.content.insertPlainText(CLIPBOARD_TOKEN)
        self.content.setFocus()
    def receive(self,result):
        self.improvement.receive(result.get('improvement'))
        self.rows=result['prompts'];self.list.blockSignals(True);self.list.clear()
        for row in self.rows:self.list.addItem('/'+row['name'])
        index=next((i for i,row in enumerate(self.rows) if row.get('id')==self.prompt_id),-1)
        self.list.setCurrentRow(index);self.list.blockSignals(False)
        if self.prompt_id and (index<0 or self.rows[index]['revision']!=self.revision):
            self.note.setText('This prompt changed elsewhere. Your draft is kept. Press Reload to replace the draft with the latest version.')
        self.owner.composer.prompt_menu.catalog.replace(self.rows);self.filter_prompts()
    def filter_prompts(self):
        query=self.search.text().casefold()
        for i,row in enumerate(self.rows):self.list.item(i).setHidden(query not in (row['name']+' '+row['content']).casefold())
    def reload_selected(self):
        index=next((i for i,row in enumerate(self.rows) if row.get('id')==self.prompt_id),-1)
        if index>=0:self.select(index);self.note.setText('Latest version loaded.')
    def new(self):self.original=None;self.prompt_id=None;self.revision=None;self.name.clear();self.content.clear();self.list.setCurrentRow(-1)
    def select(self,index):
        if 0<=index<len(self.rows):
            row=self.rows[index];self.original=row['name'];self.prompt_id=row.get('id');self.revision=row['revision'];self.name.setText(row['name']);self.content.setPlainText(row['content'])
    def save(self):
        import re
        name=self.name.text().strip();content=self.content.toPlainText()
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}',name) or not content.strip():self.note.setText('Enter a shortcut name using letters, numbers, - or _, and some prompt text.');return
        if self.original is None and any(r['name']==name for r in self.rows):self.note.setText('That name exists. Select it to edit.');return
        original=self.original;revision=self.revision;identity=self.prompt_id
        self.mutate('prompts.save',{'name':name,'content':content,'original':original,'id':identity,'expectedRevision':revision})
    def delete(self):
        if not self.original:return
        name=self.original;revision=self.revision;identity=self.prompt_id
        if QMessageBox.question(self,'Delete prompt','Delete /'+name+'?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.mutate('prompts.delete',{'name':name,'id':identity,'expectedRevision':revision})
    def mutate(self,method,params):
        if self.saving:return
        self.saving=True
        controls=[self.name,self.content,self.list,*self.findChildren(QPushButton)]
        for control in controls:control.setEnabled(False)
        def work():
            try:return self.client.call(method,params),None
            except Exception as error:return None,str(error)
        def completed(result):
            self.saving=False
            for control in controls:control.setEnabled(True)
            if result[1]:self.note.setText(result[1]);return
            self.receive(result[0]);self.new();self.note.setText('Prompt saved.' if method.endswith('save') else 'Prompt deleted.')
        self.owner.call_in_background(work,completed)


class ModelsDialog(QDialog):
    def __init__(self,window):
        super().__init__(window);self.owner=window;self.setWindowTitle('Models & providers');self.resize(520,420)
        layout=QVBoxLayout(self)
        note=QLabel('Model providers use Pi’s models.json format. API keys can reference environment variables. Save a configuration, then select its model in the conversation.');note.setWordWrap(True);layout.addWidget(note)
        self.editor=QTextEdit();self.editor.setAcceptRichText(False);layout.addWidget(self.editor)
        self.note=QLabel();self.note.setWordWrap(True);layout.addWidget(self.note)
        save=QPushButton('Save model configuration');save.clicked.connect(self.save);layout.addWidget(save)
        done=QPushButton('Done');done.clicked.connect(self.accept);layout.addWidget(done)
        self.path=None
        def loaded(host):
            self.path=Path(host['configDir'])/'agent/models.json'
            self.editor.setPlainText(self.path.read_text() if self.path.exists() else '{"providers": {}}')
        window.call_in_background(lambda:window.controller.client.call('host.describe'),loaded)
    def save(self):
        if not self.path:return
        try:
            value=json.loads(self.editor.toPlainText())
            if not isinstance(value,dict) or not isinstance(value.get('providers'),dict):raise ValueError('A providers object is required.')
        except ValueError as exc:self.note.setText(str(exc));return
        self.owner.call_in_background(lambda:self.owner.controller.client.call('models.configure',{'config':value}),lambda _:(self.note.setText('Models updated.'),self.owner.controller.refresh_models()))
