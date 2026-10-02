# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""The desktop's narrow identity-first settings surface, shared on Linux and macOS."""
import base64
import importlib.util
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QRectF, QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QColor, QPainter, QPainterPath, QImageReader, QPixmap
from PySide6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QPlainTextEdit, QTextBrowser, QTabWidget,
    QScrollArea, QStackedWidget, QFileDialog, QCheckBox, QMessageBox)
from .ui_scale import scaled, px
from .voice_button import paint_energy_ring
from .settings_icons import settings_icon

def identity_store():
    # This module is also shipped in the sealed app; no platform-specific paths.
    path = Path(__file__).resolve().parents[3]/'services/identity/profile.py'
    spec = importlib.util.spec_from_file_location('augmentor_identity', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PageStack(QStackedWidget):
    def minimumSizeHint(self):
        return self.currentWidget().minimumSizeHint() if self.currentWidget() else super().minimumSizeHint()
    def sizeHint(self):
        return self.currentWidget().sizeHint() if self.currentWidget() else super().sizeHint()


class AgentAvatar(QPushButton):
    def __init__(self, owner):
        super().__init__()
        self.setAutoDefault(False)
        self.owner = owner; self.phase = 0.; self.image = QPixmap()
        scaled(self).setFixedSize(96,96)
        self.setAccessibleName('Change agent image'); self.setToolTip('Change agent image')
        self.setStyleSheet('border:0;background:transparent;')
        self.motion = QTimer(self); self.motion.setInterval(40); self.motion.timeout.connect(self.advance)

    def advance(self):
        self.phase += .04; self.update()

    def set_image(self, encoded):
        self.image = QPixmap()
        if encoded: self.image.loadFromData(base64.b64decode(encoded), 'PNG')
        self.sync_motion(); self.update()

    def sync_motion(self):
        if self.isVisible() and self.image.isNull() and self.owner.preferences.values.get('animation',True): self.motion.start()
        else: self.motion.stop(); self.phase = 0.

    def showEvent(self, event):
        super().showEvent(event); self.sync_motion()

    def hideEvent(self, event):
        self.motion.stop(); super().hideEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.image.isNull():
            painter.translate(self.width()/2,self.height()/2)
            painter.scale(self.width()/28,self.height()/28)
            paint_energy_ring(painter,QColor(self.owner.accent),self.phase)
        else:
            path = QPainterPath(); path.addEllipse(QRectF(self.rect().adjusted(4,4,-4,-4))); painter.setClipPath(path)
            image = self.image.scaled(self.size(),Qt.AspectRatioMode.KeepAspectRatioByExpanding,Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap((self.width()-image.width())//2,(self.height()-image.height())//2,image)
        if self.hasFocus():
            painter.resetTransform(); painter.setClipping(False); painter.setPen(QColor(self.owner.accent)); painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(self.rect().adjusted(2,2,-2,-2))


class SettingsDialog(QDialog):
    def __init__(self, window):
        super().__init__(window); self.owner = window; self.store = identity_store(); self.pages = {}; self.shortcuts = None; self.closing = False
        self.finished.connect(lambda _:setattr(self,'closing',True))
        self.setWindowTitle('Your agent · Settings'); self.resize(px(self,450),min(px(self,780),self.screen().availableGeometry().height()-60))
        scaled(self).setMinimumWidth(320)
        outer = QVBoxLayout(self); outer.setContentsMargins(px(self,18),px(self,14),px(self,18),px(self,14)); outer.setSpacing(px(self,12))
        navigation = QHBoxLayout(); self.nav = {}
        for text, page in [('Agent','agent'),('Look','appearance'),('Voice','voice'),('More','all')]:
            button = QPushButton(text); button.setAutoDefault(False); button.setIcon(settings_icon({'agent':'memory','appearance':'appearance','voice':'voice','all':'harness'}[page],window.accent)); button.setCheckable(True); button.setAccessibleName(text+' settings')
            button.clicked.connect(lambda _=False,p=page:self.show_page(p)); navigation.addWidget(button); self.nav[page]=button
        outer.addLayout(navigation)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.stack = PageStack(); self.stack.currentChanged.connect(self.stack.updateGeometry); scroll.setWidget(self.stack); outer.addWidget(scroll)
        self.feedback = QLabel(); self.feedback.setWordWrap(True); self.feedback.setAccessibleName('Settings status'); outer.addWidget(self.feedback)
        done = QPushButton('Done'); done.clicked.connect(self.accept); outer.addWidget(done)
        try: self.identity = self.store.profile()
        except Exception as error: self.identity = None; self.feedback.setText(str(error))
        self.show_page('agent')

    def background(self, work, callback):
        self.owner.call_in_background(work,lambda result:callback(result) if not self.closing else None)

    def make_page(self, title=None, subtitle=None, back='all'):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(0,0,0,0); layout.setSpacing(px(self,12))
        if title:
            button = QPushButton('‹  Your agent' if back=='agent' else '‹  All settings'); button.clicked.connect(lambda:self.show_page(back)); layout.addWidget(button)
            heading = QLabel(title); scaled(heading).setStyleSheet('font-size:22px;font-weight:600;'); layout.addWidget(heading)
        if subtitle:
            note = QLabel(subtitle); note.setWordWrap(True); layout.addWidget(note)
        return page, layout

    def action(self, layout, text, callback, object_name=None):
        button = QPushButton(text); button.setAutoDefault(False); button.clicked.connect(callback)
        if object_name: button.setObjectName(object_name)
        layout.addWidget(button); return button

    def show_page(self, name):
        if name not in self.pages:
            try: page = getattr(self,'page_'+name)()
            except Exception as error: self.feedback.setText(str(error)); return
            self.pages[name]=page; self.stack.addWidget(page)
        self.stack.setCurrentWidget(self.pages[name]); self.feedback.clear()
        for key,button in self.nav.items(): button.setChecked(key==name or (key=='all' and name in ('conversation','connections','advanced')))
        self.avatar.sync_motion()

    def page_agent(self):
        page, layout = self.make_page()
        self.avatar = AgentAvatar(self.owner); self.avatar.clicked.connect(self.change_image); layout.addWidget(self.avatar,0,Qt.AlignmentFlag.AlignHCenter)
        self.name = QLineEdit((self.identity or {}).get('name','Augmentor')); self.name.setAccessibleName('Agent name'); self.name.setMaxLength(80); self.name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scaled(self.name).setStyleSheet('font-size:22px;font-weight:600;padding:8px;'); layout.addWidget(self.name)
        self.name.editingFinished.connect(self.save_name)
        self.avatar.set_image((self.identity or {}).get('avatar',''))
        self.default_image=self.action(layout,'Use the default energy ring',self.reset_image,'reset-avatar'); self.default_image.setVisible(bool((self.identity or {}).get('avatar')))
        connection=QLabel('Connected' if getattr(self.owner.controller,'online',False) else 'Not connected'); connection.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(connection)
        subtitle = QLabel('Make it yours'); scaled(subtitle).setStyleSheet('font-size:18px;font-weight:600;'); layout.addWidget(subtitle)
        note = QLabel('Choose how your agent behaves and see what it remembers.'); note.setWordWrap(True); layout.addWidget(note)
        for title,sub,link,destination,color in [('Soul','How I behave','Edit instructions  ↗','soul','#9d234f'),('Memory','What I know about you','View memory  ↗','memory','#235d82')]:
            button = self.action(layout,title+'\n'+sub+'\n\n'+link,lambda _=False,p=destination:self.show_page(p),destination+'-card')
            scaled(button).setMinimumHeight(120)
            scaled(button).setStyleSheet(f'QPushButton {{text-align:left;padding:16px 20px;border:0;border-radius:18px;background:{color};color:#ffffff;font-size:15px;}} QPushButton:hover {{background:{QColor(color).lighter(115).name()};}} QPushButton:focus {{border:2px solid {QColor(self.owner.accent).name()};}}')
        layout.addWidget(QLabel('Agent access'))
        self.access = QComboBox(); self.access.setAccessibleName('Agent access')
        for text,value in [('Full access','danger-full-access'),('Ask before actions','workspace-write'),('Read only','read-only')]: self.access.addItem(text,value)
        self.access.setEnabled(False); layout.addWidget(self.access)
        self.access_note = QLabel('Loading access settings…'); self.access_note.setWordWrap(True); layout.addWidget(self.access_note)
        self.permission = None
        self.background(self.read_access,self.receive_access)
        self.access.activated.connect(self.save_access)
        layout.addStretch(); return page

    def read_access(self):
        try: return self.owner.controller.client.setting('permission'),None
        except Exception as error: return None,str(error)

    def receive_access(self, result):
        value,error = result
        self.permission = value
        if not value: self.access_note.setText(error or 'Access controls are unavailable for this connection.'); return
        index = self.access.findData(value.get('value',{}).get('defaultPreset'))
        if index<0: self.access_note.setText('This connection uses a policy that cannot be edited here.'); return
        self.access.setCurrentIndex(index); self.access.setEnabled(True)
        self.access_note.setText('Applies to new chats. Existing chats keep their access level.')

    def save_access(self, _=None):
        value = self.access.currentData(); descriptor = self.permission; self.access.setEnabled(False)
        payload={'ns':'permission','ops':[{'op':'set','path':['defaultPreset'],'value':value}],'expectedRevision':descriptor['revision']}
        def work():
            try: self.owner.controller.client.call('settings.mutate',payload); return self.read_access()
            except Exception as error: return descriptor,str(error)
        def done(result):
            self.receive_access(result); self.feedback.setText(result[1] or 'Access updated for new chats.')
        self.background(work,done)

    def persist_identity(self, name, avatar):
        if not self.identity: return False
        try: self.identity=self.store.save_profile(name,avatar,self.identity['revision'])
        except Exception as error: self.feedback.setText(str(error)); return False
        self.avatar.set_image(self.identity['avatar']); self.default_image.setVisible(bool(self.identity['avatar'])); self.feedback.setText('Agent identity saved.'); return True

    def save_name(self):
        if self.identity and self.name.text().strip()!=self.identity['name']:
            if not self.persist_identity(self.name.text(),self.identity['avatar']): self.name.setText(self.identity['name'])

    def reset_image(self):
        self.persist_identity(self.name.text(),'')

    def change_image(self):
        path,_ = QFileDialog.getOpenFileName(self,'Choose an agent image','','Images (*.png *.jpg *.jpeg *.webp)')
        if not path: return
        try:
            if Path(path).stat().st_size>10*1024*1024: raise ValueError('Choose an image smaller than 10 MB.')
            reader=QImageReader(path); size=reader.size()
            if not size.isValid() or size.width()>8192 or size.height()>8192: raise ValueError('Choose an image with dimensions up to 8192 pixels.')
            reader.setAutoTransform(True); image=reader.read()
            if image.isNull(): raise ValueError('This image could not be opened.')
            image=image.scaled(256,256,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
            raw=QByteArray(); buffer=QBuffer(raw); buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            if not image.save(buffer,'PNG'): raise ValueError('This image could not be saved.')
            self.persist_identity(self.name.text(),base64.b64encode(bytes(raw)).decode('ascii'))
        except Exception as error: self.feedback.setText(str(error))

    def page_soul(self):
        page, layout = self.make_page('Soul','How I behave · Your personal instructions, saved in soul.md. Changes apply to new chats; existing conversations keep their saved instructions.','agent')
        self.soul = self.store.soul()
        self.soul_editor = QPlainTextEdit(self.soul['text']); self.soul_editor.setAccessibleName('Agent Soul instructions'); scaled(self.soul_editor).setMinimumHeight(280); layout.addWidget(self.soul_editor)
        self.action(layout,'Reset Soul to default',self.reset_soul,'reset-soul')
        row=QHBoxLayout(); cancel=QPushButton('Cancel'); cancel.clicked.connect(self.cancel_soul); row.addWidget(cancel)
        save=QPushButton('Save Soul'); save.setObjectName('save-soul'); save.clicked.connect(self.save_soul); row.addWidget(save); layout.addLayout(row); layout.addStretch(); return page

    def reset_soul(self):
        self.soul_editor.setPlainText(self.soul['default']); self.feedback.setText('Default loaded into the draft. Save Soul to apply it, or Cancel to keep your saved Soul.')

    def cancel_soul(self):
        self.soul=self.store.soul(); self.soul_editor.setPlainText(self.soul['text']); self.show_page('agent')

    def save_soul(self):
        try: self.soul=self.store.save_soul(self.soul_editor.toPlainText(),self.soul['revision'])
        except Exception as error: self.feedback.setText(str(error)); return
        self.show_page('agent'); self.feedback.setText('Soul saved for new chats.')

    def page_memory(self):
        page, layout = self.make_page('Memory','What I know about you · Stored knowledge for this conversation’s person and project.','agent')
        self.memory_tabs = QTabWidget(); self.memory_views={}
        for key,title in [('relationship','About you'),('work','Your project')]:
            text=QTextBrowser(); text.setOpenLinks(False); text.setAccessibleName(title+' remembered knowledge'); self.memory_tabs.addTab(text,title); self.memory_views[key]=text
        scaled(self.memory_tabs).setMinimumHeight(320); layout.addWidget(self.memory_tabs)
        self.memory_status=QLabel(); self.memory_status.setWordWrap(True); layout.addWidget(self.memory_status)
        self.memory_refresh=self.action(layout,'Refresh memory',self.refresh_memory)
        self.action(layout,'Memory setup && processing',lambda:self.open_memory_settings())
        self.refresh_memory(); layout.addStretch(); return page

    def refresh_memory(self):
        self.memory_refresh.setEnabled(False); self.memory_status.setText('Loading stored knowledge…')
        sid=getattr(self.owner.controller,'session',None); harness=self.owner.controller.harness
        def work():
            try:
                if not sid: return None,'Open a conversation to see its remembered knowledge.'
                from .prompt_client import PromptClient
                return PromptClient().call('memory.dual.recall',{'session':harness+':'+sid}),None
            except Exception as error: return None,str(error)
        def done(result):
            self.memory_refresh.setEnabled(True); value,error=result
            if error or not value or not value.get('enabled'):
                self.memory_status.setText(error or 'Capture and recall are paused. Stored memories are preserved.')
                for view in self.memory_views.values(): view.clear()
                return
            states=[]
            for key,view in self.memory_views.items():
                projection=value.get(key) or {}; parts=[]
                if projection.get('summary'): parts.append(projection['summary'])
                for item in projection.get('items',[]): parts.append('• '+str(item.get('text','')))
                for entry in ([] if projection.get('summary') else projection.get('pages',[])):
                    content=entry.get('content',entry.get('text','')) if isinstance(entry,dict) else str(entry)
                    if content: parts.append(content)
                view.setPlainText('\n\n'.join(parts) or 'No distilled knowledge yet. It will appear as your conversations are processed.')
                if projection.get('stale'): states.append('Some knowledge is awaiting an update.')
            self.memory_status.setText('Showing cached knowledge from automatic memory. '+(' '.join(dict.fromkeys(states)))+(' Some memory is unavailable.' if value.get('unavailable') else ''))
        self.background(work,done)

    def page_all(self):
        page,layout=self.make_page('All settings','Choose what you’d like to adjust.','agent')
        for title,description,name in [('Appearance','Theme, colours, skins & visual effects','appearance'),('Voice','Speaking voice, speed & recording','voice'),('Conversation','Thinking display & reusable prompts','conversation'),('Connections','Models, agent engine & Home','connections'),('Advanced','Shortcuts, memory setup, updates & support','advanced')]:
            button=self.action(layout,title+'\n'+description.replace('&','&&')+'    ›',lambda _=False,p=name:self.show_page(p)); scaled(button).setMinimumHeight(70); scaled(button).setStyleSheet('text-align:left;padding:14px;border-radius:12px;')
        layout.addStretch(); return page

    def page_appearance(self):
        page,layout=self.make_page('Appearance','Make your agent window feel like yours.')
        theme=QComboBox(); theme.setAccessibleName('Theme'); theme.addItems(['Dark','Light']); theme.setCurrentIndex(0 if self.owner.preferences.values['theme']=='dark' else 1)
        theme.activated.connect(lambda index:self.owner.apply_appearance({'theme':'dark' if index==0 else 'light'})); layout.addWidget(QLabel('Theme')); layout.addWidget(theme)
        animate=QCheckBox('Animate the energy ring and visual effects'); animate.setChecked(self.owner.preferences.values.get('animation',True))
        animate.toggled.connect(lambda enabled:(self.owner.apply_appearance({'animation':enabled}),self.avatar.sync_motion())); layout.addWidget(animate)
        def appearance():
            from .surfaces import AppearanceDialog
            dialog=AppearanceDialog(self.owner.preferences.values,self); dialog.changed.connect(self.owner.apply_appearance); dialog.exec(); self.avatar.sync_motion()
        self.action(layout,'Colours, skins && visual effects',appearance)
        layout.addWidget(QLabel('Your existing colours, effects, image backgrounds and saved skins are available in the appearance editor.'))
        layout.itemAt(layout.count()-1).widget().setWordWrap(True); layout.addStretch(); return page

    def page_voice(self):
        page,layout=self.make_page('Voice','Choose how your agent speaks and listens.')
        from .voice_settings import VoiceSettingsDialog
        enabled=QCheckBox('Enable Resonant Voice'); enabled.setChecked(self.owner.preferences.values.get('resonant_voice',True)); enabled.toggled.connect(self.owner.set_voice_enabled); layout.addWidget(enabled)
        self.action(layout,'Resonant Voice settings',lambda:VoiceSettingsDialog(self.owner).exec())
        note=QLabel('Speaking voice, speed, playback and hands-free recording use your existing voice controls.'); note.setWordWrap(True); layout.addWidget(note); layout.addStretch(); return page

    def page_conversation(self):
        page,layout=self.make_page('Conversation','Choose how you see and compose conversations.')
        thinking=QCheckBox('Expand thinking by default'); thinking.setChecked(self.owner.preferences.values.get('expand_thinking',True)); thinking.toggled.connect(self.set_thinking); layout.addWidget(thinking)
        self.action(layout,'Prompt library && prompt improvement',self.owner.open_prompt_library)
        layout.addStretch(); return page

    def set_thinking(self, enabled):
        if hasattr(self.owner,'set_thinking_visibility'): self.owner.set_thinking_visibility(enabled)
        else: self.owner.preferences.values['expand_thinking']=enabled; self.owner.preferences.save()

    def page_connections(self):
        page,layout=self.make_page('Connections','Choose the models and services your agent uses.')
        layout.addWidget(QLabel('Agent engine')); engine=QComboBox()
        for text,value in [('DSH','dsh'),('Pi','pi'),('Codex (development)','codex')]: engine.addItem(text,value)
        engine.setCurrentIndex(engine.findData(self.owner.controller.harness)); engine.setAccessibleName('Agent engine'); engine.activated.connect(lambda _:self.owner.switch_harness(engine.currentData())); layout.addWidget(engine)
        def setup(): self.accept(); self.owner.open_setup()
        self.action(layout,'Model connection && setup',setup)
        from .home_settings import HomeDialog
        self.action(layout,'Connect Home',lambda:HomeDialog(self.owner).exec()); layout.addStretch(); return page

    def open_memory_settings(self):
        from .memory import MemoryDialog
        MemoryDialog(self.owner).exec()

    def page_advanced(self):
        page,layout=self.make_page('Advanced','Additional controls and diagnostics.')
        from .shortcut_settings import ShortcutSettings
        layout.addWidget(QLabel('Window shortcuts')); self.shortcuts=ShortcutSettings(self.owner); layout.addWidget(self.shortcuts)
        self.action(layout,'Memory setup && processing',self.open_memory_settings)
        from .recovery import RecoveryDialog
        self.action(layout,'Recover connection',lambda:RecoveryDialog(self.owner).exec())
        from .panels import UpdatesDialog, LicensesDialog
        self.action(layout,'Versions && updates',lambda:UpdatesDialog(self.owner).exec())
        from .support import SupportDialog
        self.action(layout,'Support report',lambda:SupportDialog(self.owner).exec())
        self.action(layout,'About && licenses',lambda:LicensesDialog(self.owner).exec()); layout.addStretch(); return page

    def capture_current(self):
        return self.shortcuts.capture_current() if self.shortcuts else False

    def done(self, result):
        if hasattr(self,'soul_editor') and self.soul_editor.toPlainText()!=self.soul['text']:
            answer=QMessageBox.question(self,'Unsaved Soul','Discard your unsaved Soul draft?',QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)
            if answer!=QMessageBox.StandardButton.Discard: return
        super().done(result)
