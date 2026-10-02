# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""The desktop's narrow identity-first settings surface, shared on Linux and macOS."""
import base64
import importlib.util
import sys
from pathlib import Path
from PySide6.QtCore import Signal, Qt, QTimer, QEvent, QSize, QRectF, QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QColor, QIcon, QPalette, QPainter, QPainterPath, QImageReader, QPixmap, QRadialGradient
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QPlainTextEdit, QTextBrowser, QTabWidget,
    QScrollArea, QStackedLayout, QFileDialog, QCheckBox, QSizePolicy, QLayout, QGridLayout, QBoxLayout, QTextEdit, QAbstractSpinBox, QFormLayout, QListWidget, QStyle, QStyleOptionButton)
from .ui_scale import scaled, px, factor
from .voice_button import paint_energy_ring
from .settings_icons import settings_icon

def identity_store():
    # This module is also shipped in the sealed app; no platform-specific paths.
    path = Path(__file__).resolve().parents[3]/'services/identity/profile.py'
    spec = importlib.util.spec_from_file_location('augmentor_identity', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CurrentPageLayout(QStackedLayout):
    def minimumSize(self):
        page=self.currentWidget()
        return page.minimumSizeHint().expandedTo(page.minimumSize()) if page else QSize(0,0)
    def sizeHint(self):
        return self.currentWidget().sizeHint() if self.currentWidget() else QSize(0,0)
    def hasHeightForWidth(self):
        # The scroll area must allow flexible lists/editors to shrink; Qt's
        # generic height-for-width uses their preferred (rather than minimum) size.
        return False
    def heightForWidth(self,width):
        page=self.currentWidget()
        return page.layout().minimumHeightForWidth(width) if page else -1


class PageStack(QWidget):
    currentChanged=Signal(int)
    def __init__(self):
        super().__init__();self.pages=CurrentPageLayout(self)
        self.pages.setContentsMargins(0,0,0,0)
        self.pages.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.pages.currentChanged.connect(self.currentChanged)
    def addWidget(self,page):return self.pages.addWidget(page)
    def removeWidget(self,page):self.pages.removeWidget(page)
    def currentWidget(self):return self.pages.currentWidget()
    def setCurrentWidget(self,page):self.pages.setCurrentWidget(page)
    def minimumSizeHint(self):return self.pages.minimumSize()
    def sizeHint(self):return self.pages.sizeHint()


class SettingsStatus(QLabel):
    def setText(self,text):
        super().setText(text);self.setVisible(bool(text))
    def clear(self):self.setText('')


class AgentAvatar(QPushButton):
    def __init__(self, owner):
        super().__init__()
        self.setAutoDefault(False)
        self.owner = owner; self.phase = 0.; self.image = QPixmap()
        scaled(self).setFixedSize(148,148)
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
            glow=QRadialGradient(self.rect().center(),self.width()/2)
            colour=QColor(self.owner.accent);colour.setAlpha(32);glow.setColorAt(0,colour);colour.setAlpha(0);glow.setColorAt(1,colour)
            painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(glow);painter.drawEllipse(QRectF(self.rect()))
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


class AgentAction(QPushButton):
    def __init__(self,owner,title,description,icon,colour):
        super().__init__(title);self.owner=owner;self.colour=QColor(colour)
        self.setAccessibleName(title+' · '+description);self.setToolTip(description);self.setAutoDefault(False)
        self.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
        scaled(self).setFixedHeight(60)
        row=QHBoxLayout(self);scaled(row).setContentsMargins(16,8,16,8);scaled(row).setSpacing(12)
        self.glyph=QLabel();self.glyph.setPixmap(settings_icon(icon,self.colour).pixmap(px(self,26),px(self,26)));row.addWidget(self.glyph)
        text=QVBoxLayout();scaled(text).setSpacing(2)
        self.heading=QLabel(title);self.heading.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred);scaled(self.heading).setStyleSheet('font-size:15px;font-weight:600;');text.addWidget(self.heading)
        self.description=QLabel(description);self.description.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred);scaled(self.description).setStyleSheet('font-size:11px;');text.addWidget(self.description)
        row.addLayout(text,1);self.arrow=QLabel('›');scaled(self.arrow).setStyleSheet('font-size:23px;');row.addWidget(self.arrow)
        for label in self.findChildren(QLabel):label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.restyle()

    def restyle(self):
        colour=self.colour;ink=self.owner.palette().color(QPalette.ColorRole.WindowText).name()
        scaled(self).setStyleSheet(f'QPushButton {{background:rgba({colour.red()},{colour.green()},{colour.blue()},24);border:1px solid rgba({colour.red()},{colour.green()},{colour.blue()},65);border-radius:14px;}} QPushButton:hover {{background:rgba({colour.red()},{colour.green()},{colour.blue()},48);}} QPushButton:focus {{border:2px solid {QColor(self.owner.accent).name()};}} QLabel {{color:{ink};background:transparent;border:0;}}')
        self.description.setStyleSheet(f'font-size:{px(self,11)}px;color:{ink};')

    def paintEvent(self,event):
        option=QStyleOptionButton();self.initStyleOption(option);option.text=''
        painter=QPainter(self);self.style().drawControl(QStyle.ControlElement.CE_PushButton,option,painter,self)


class SettingsPanel(QWidget):
    closed = Signal()
    def __init__(self, window):
        super().__init__(window); self.owner = window; self.store = identity_store(); self.pages = {}; self.shortcuts = None; self.closing = False
        self.editor = None; self.editor_page = None; self.editor_return = 'all'; self.leaving_editor = False
        self.fit_timer=QTimer(self);self.fit_timer.setSingleShot(True);self.fit_timer.timeout.connect(self.request_fit)
        self.setObjectName('agentSettings'); self.setAccessibleName('Your agent settings')
        outer = QVBoxLayout(self); scaled(outer).setContentsMargins(6,12,6,12); scaled(outer).setSpacing(8)
        header = QHBoxLayout(); scaled(header).setContentsMargins(12,0,12,0)
        back = QPushButton('‹  Back to chat'); back.setObjectName('settings-back'); back.clicked.connect(self.accept); header.addWidget(back)
        self.stop = QPushButton('Stop'); self.stop.clicked.connect(lambda:self.owner.controller.stop()); header.addWidget(self.stop)
        hide = QPushButton('Hide'); hide.clicked.connect(self.owner.hide); header.addWidget(hide); outer.addLayout(header)
        self.update_activity()
        navigation = QHBoxLayout(); scaled(navigation).setSpacing(4); scaled(navigation).setContentsMargins(12,0,12,0); self.nav = {}
        for text, page in [('Agent','agent'),('Look','appearance'),('Voice','voice'),('More','all')]:
            button = QPushButton(text); button.setAutoDefault(False); button.setIcon(settings_icon({'agent':'memory','appearance':'appearance','voice':'voice','all':'harness'}[page],window.accent)); button.setCheckable(True); button.setAccessibleName(text+' settings')
            scaled(button).setStyleSheet('padding:7px 4px;font-size:12px;'); scaled(button).setIconSize(QSize(14,14))
            button.setProperty('settingsIconName',{'agent':'memory','appearance':'appearance','voice':'voice','all':'harness'}[page])
            button.clicked.connect(lambda _=False,p=page:self.open_appearance() if p=='appearance' else self.open_voice() if p=='voice' else self.show_page(p)); navigation.addWidget(button); self.nav[page]=button
        outer.addLayout(navigation)
        scroll = QScrollArea(); self.scroll = scroll; scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.Shape.NoFrame); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.stack = PageStack(); self.stack.layout().setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint); self.stack.setMinimumSize(0,0); self.stack.currentChanged.connect(self.stack.updateGeometry); scroll.setWidget(self.stack); self.stack.setAutoFillBackground(False); scroll.viewport().setAutoFillBackground(False); outer.addWidget(scroll)
        self.feedback = SettingsStatus(); self.feedback.hide(); self.feedback.setWordWrap(True); self.feedback.setAccessibleName('Settings status'); outer.addWidget(self.feedback)
        self.exit_choices = QWidget(); choices = QHBoxLayout(self.exit_choices); choices.setContentsMargins(0,0,0,0)
        for text,callback in [('Save',self.save_and_return),('Discard',self.discard_and_return),('Keep editing',self.keep_editing)]:
            button = QPushButton(text.replace('&','&&')); button.clicked.connect(callback); choices.addWidget(button)
        outer.addWidget(self.exit_choices); self.exit_choices.hide()
        try: self.identity = self.store.profile()
        except Exception as error: self.identity = None; self.feedback.setText(str(error))
        self.show_page('agent')

    def resizeEvent(self,event):
        super().resizeEvent(event);self.sync_navigation()
        if hasattr(self,'hero'):
            narrow=self.width()<px(self,450)
            self.hero.setDirection(QBoxLayout.Direction.TopToBottom if narrow else QBoxLayout.Direction.LeftToRight)
            scaled(self.avatar).setFixedSize(112 if narrow else 148,112 if narrow else 148)
        QTimer.singleShot(0,self.request_fit)

    def sync_navigation(self):
        for button in getattr(self,'nav',{}).values():
            colour=QColor(self.owner.background) if button.isChecked() and hasattr(self.owner,'background') else self.owner.palette().color(QPalette.ColorRole.WindowText)
            icon=settings_icon(button.property('settingsIconName'),colour)
            button.setIcon(QIcon() if self.isVisible() and self.width()<px(self,300) else icon)
        for action in getattr(self,'profile_actions',[]):action.restyle()
        if hasattr(self,'usage'):self.usage.calendar.update()

    def eventFilter(self,widget,event):
        if event.type()==QEvent.Type.LayoutRequest and not self.closing:
            self.fit_timer.start(0)
        return super().eventFilter(widget,event)

    def frame_size(self):
        area=self.owner.screen().availableGeometry()
        width,height=area.width(),area.height()-px(self,24)
        if getattr(self.owner,'touch_layout',None):
            width=min(width,self.owner.touch_layout.viewport[0])
            height=min(height,self.owner.touch_layout.viewport[1])
        return QSize(min(px(self,700),width),min(px(self,760),height))

    def request_fit(self):
        # Keep the frame stable. Wrapped text and fields determine the body’s
        # minimum height; long forms scroll instead of compressing their rows.
        page=self.stack.currentWidget()
        if not page or self.closing:return
        width=self.scroll.viewport().width()
        margins=page.layout().contentsMargins()
        if self.editor and self.editor.layout():
            layout=self.editor.layout();layout.activate()
            content_width=max(1,width-margins.left()-margins.right())
            height=layout.minimumHeightForWidth(content_width)
            self.editor.setMinimumHeight(max(layout.minimumSize().height(),height))
        page.layout().activate()
        height=page.layout().minimumHeightForWidth(width)
        page.setMinimumHeight(max(page.layout().minimumSize().height(),height))
        self.stack.updateGeometry()

    def prepare_inputs(self,widget):
        for field in widget.findChildren(QLineEdit)+widget.findChildren(QComboBox)+widget.findChildren(QAbstractSpinBox):
            if isinstance(field,QLineEdit) and isinstance(field.parent(),(QComboBox,QAbstractSpinBox)):continue
            scaled(field).setMinimumHeight(max(40,round(field.minimumHeight()/factor(field))))
            field.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        for form in widget.findChildren(QFormLayout):
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
            scaled(form).setVerticalSpacing(10)
        for label in widget.findChildren(QLabel):
            if label.wordWrap():label.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Fixed)

    def background(self, work, callback):
        self.owner.call_in_background(work,lambda result:callback(result) if not self.closing else None)

    def make_page(self, title=None, subtitle=None, back='all'):
        page = QWidget(); layout = QVBoxLayout(page); scaled(layout).setContentsMargins(12,0,12,8); scaled(layout).setSpacing(8)
        if title:
            heading = QLabel(title); scaled(heading).setStyleSheet('font-size:22px;font-weight:600;'); layout.addWidget(heading)
        if subtitle:
            note = QLabel(subtitle); note.setWordWrap(True); layout.addWidget(note)
        page.installEventFilter(self)
        return page, layout

    def action(self, layout, text, callback, object_name=None):
        button = QPushButton(text); button.setAutoDefault(False); button.clicked.connect(callback)
        if object_name: button.setObjectName(object_name)
        layout.addWidget(button); return button

    def show_page(self, name):
        if not self.leave_editor(): return
        if name not in self.pages:
            try: page = getattr(self,'page_'+name)()
            except Exception as error: self.feedback.setText(str(error)); return
            self.prepare_inputs(page); self.pages[name]=page; self.stack.addWidget(page)
        self.stack.setCurrentWidget(self.pages[name]); self.feedback.clear()
        for key,button in self.nav.items(): button.setChecked(key==name or (key=='all' and name in ('conversation','connections','advanced')))
        self.avatar.sync_motion();self.sync_navigation();QTimer.singleShot(0,self.request_fit)

    def page_agent(self):
        page,layout=self.make_page();scaled(layout).setSpacing(8)
        self.hero=QBoxLayout(QBoxLayout.Direction.LeftToRight);scaled(self.hero).setSpacing(20)
        self.avatar=AgentAvatar(self.owner);self.avatar.clicked.connect(self.change_image);self.hero.addWidget(self.avatar,0,Qt.AlignmentFlag.AlignHCenter)
        details=QVBoxLayout();scaled(details).setSpacing(4);details.addStretch()
        caption_row=QHBoxLayout();caption=QLabel('YOUR AGENT');scaled(caption).setStyleSheet('font-size:11px;font-weight:600;');caption_row.addWidget(caption,1)
        self.default_image=self.action(caption_row,'Reset image',self.reset_image,'reset-avatar');scaled(self.default_image).setStyleSheet('font-size:11px;padding:2px;border:0;text-align:left;');self.default_image.setVisible(bool((self.identity or {}).get('avatar')));details.addLayout(caption_row)
        self.name=QLineEdit((self.identity or {}).get('name','Augmentor'));self.name.setAccessibleName('Agent name');self.name.setMaxLength(80)
        self.name.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed);scaled(self.name).setMinimumHeight(52)
        scaled(self.name).setStyleSheet('QLineEdit {font-size:27px;font-weight:600;padding:6px 0;border:0;background:transparent;} QLineEdit:focus {border-bottom:1px solid palette(highlight);}')
        details.addWidget(self.name);self.name.editingFinished.connect(self.save_name)
        self.connection=QLabel();details.addWidget(self.connection)
        hint=QLabel('Edit your name or tap the image to make it yours.');hint.setWordWrap(True);scaled(hint).setStyleSheet('font-size:11px;');details.addWidget(hint)
        details.addStretch();self.hero.addLayout(details,1);layout.addLayout(self.hero)
        self.avatar.set_image((self.identity or {}).get('avatar',''))
        self.profile_actions=[]
        for title,description,icon,destination,colour in [('Agent Identity','How I behave · Personality and instructions','prompts','soul','#ae5677'),('Agent Memory','What I know · About you and your projects','memory','memory','#4d91ac')]:
            button=AgentAction(self.owner,title,description,icon,colour);button.setObjectName(destination+'-card');button.clicked.connect(lambda _=False,p=destination:self.show_page(p));self.profile_actions.append(button);layout.addWidget(button)
        access_row=QHBoxLayout();label=QLabel('Agent access');scaled(label).setStyleSheet('font-size:13px;font-weight:600;');access_row.addWidget(label)
        self.access=QComboBox();self.access.setAccessibleName('Agent access')
        for text,value in [('Full access','danger-full-access'),('Ask before actions','workspace-write'),('Read only','read-only')]:self.access.addItem(text,value)
        self.access.setEnabled(False);access_row.addWidget(self.access,1);layout.addLayout(access_row)
        self.access_note=QLabel('Loading access settings…');self.access_note.setWordWrap(True);scaled(self.access_note).setStyleSheet('font-size:11px;');layout.addWidget(self.access_note)
        self.permission=None;self.background(self.read_access,self.receive_access);self.access.activated.connect(self.save_access)
        layout.addStretch(1)
        from .token_usage import TokenUsage
        self.usage=TokenUsage(self);layout.addWidget(self.usage)
        self.update_activity();return page

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
        self.access_note.setText('Applies to new chats. Existing access stays unchanged.'); QTimer.singleShot(0,self.request_fit)

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
        self.avatar.set_image(self.identity['avatar']); self.default_image.setVisible(bool(self.identity['avatar'])); self.feedback.setText('Agent identity saved.'); QTimer.singleShot(0,self.request_fit); return True

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
        page, layout = self.make_page('Agent Identity','How I behave · Your personal instructions, saved in soul.md. Changes apply to new chats; existing conversations keep their saved instructions.','agent')
        self.soul = self.store.soul()
        self.soul_editor = QPlainTextEdit(self.soul['text']); self.soul_editor.setAccessibleName('Agent Identity instructions'); scaled(self.soul_editor).setMinimumHeight(280); layout.addWidget(self.soul_editor)
        self.action(layout,'Reset to default',self.reset_soul,'reset-soul')
        row=QHBoxLayout(); cancel=QPushButton('Cancel'); cancel.clicked.connect(self.cancel_soul); row.addWidget(cancel)
        save=QPushButton('Save'); save.setObjectName('save-soul'); save.clicked.connect(self.save_soul); row.addWidget(save); layout.addLayout(row); layout.addStretch(); return page

    def reset_soul(self):
        self.soul_editor.setPlainText(self.soul['default']); self.feedback.setText('Default loaded into the draft. Save to apply it, or Cancel to keep your saved instructions.')

    def cancel_soul(self):
        self.soul=self.store.soul(); self.soul_editor.setPlainText(self.soul['text']); self.show_page('agent')

    def save_soul(self):
        try: self.soul=self.store.save_soul(self.soul_editor.toPlainText(),self.soul['revision'])
        except Exception as error: self.feedback.setText(str(error)); return
        self.show_page('agent'); self.feedback.setText('Agent Identity saved for new chats.')

    def page_memory(self):
        page, layout = self.make_page('Agent Memory','What I know about you · Stored knowledge for this conversation’s person and project.','agent')
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
        from .panels import UpdatesDialog, LicensesDialog
        entries=[('Prompt library',self.open_prompts),('Conversation',lambda:self.show_page('conversation')),
                 ('Agent setup' if getattr(self.owner.controller,'harness','dsh')=='dsh' else 'Connect a model',self.open_setup),
                 ('Open DSH in browser' if getattr(self.owner.controller,'harness','dsh')=='dsh' else 'Models && providers',self.open_models),
                 ('Connections && Home',lambda:self.show_page('connections')),
                 ('Versions && updates',lambda:self.open_editor('Versions & updates',lambda:UpdatesDialog(self.owner))),
                 ('Advanced',lambda:self.show_page('advanced')),
                 ('About && licenses',lambda:self.open_editor('About & licenses',lambda:LicensesDialog(self.owner)))]
        if sys.platform=='darwin':
            from .macos_browser_setup import available, MacBrowserSetupDialog
            if available(): entries.append(('Set up browser extension',lambda:self.open_editor('Browser extension',lambda:MacBrowserSetupDialog(self.owner))))
        for text,callback in entries:
            self.action(layout,text+'    ›',callback)
        self.action(layout,'Quit Augmentor',self.quit_agent,'quit-agent')
        layout.addStretch(); return page

    def open_access(self):
        self.show_page('agent')
        self.access.setFocus()
        self.access.ensurePolished()
        self.scroll.ensureWidgetVisible(self.access)

    def quit_agent(self):
        if self.accept(): self.owner.close()

    def open_appearance(self):
        from .surfaces import AppearanceDialog
        def create():
            dialog=AppearanceDialog(self.owner.preferences.values,self.owner)
            dialog.changed.connect(self.owner.apply_appearance)
            return dialog
        self.open_editor('Appearance',create)

    def open_voice(self):
        from .voice_settings import VoiceSettingsDialog
        self.open_editor('Voice',lambda:VoiceSettingsDialog(self.owner))

    def open_editor(self,title,factory,back='all'):
        if not self.leave_editor(): return
        try: dialog=factory()
        except Exception as error: self.feedback.setText(str(error)); return
        page,layout=self.make_page(title,back=back)
        # Reuse the established form and its lifecycle as a child widget. Never
        # show/exec a top-level settings dialog or run a nested modal loop.
        dialog.setParent(page,Qt.WindowType.Widget)
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.setModal(False)
        self.prepare_editor(dialog);dialog.installEventFilter(self)
        scaled(dialog).setMinimumSize(0,0)
        layout.addWidget(dialog,1)
        self.editor=dialog; self.editor_page=page; self.editor_return=back
        dialog.finished.connect(self.editor_finished)
        self.stack.addWidget(page); self.stack.setCurrentWidget(page); dialog.show()
        self.feedback.clear()
        for key,button in self.nav.items():button.setChecked(key==('appearance' if title=='Appearance' else 'voice' if title=='Voice' else 'all'))
        self.avatar.sync_motion();self.sync_navigation();QTimer.singleShot(0,self.request_fit)

    def prepare_editor(self,dialog):
        if dialog.layout():
            scaled(dialog.layout()).setContentsMargins(0,0,0,0)
            if not (dialog.findChildren(QTextEdit)+dialog.findChildren(QPlainTextEdit)+dialog.findChildren(QListWidget)):
                dialog.layout().setAlignment(Qt.AlignmentFlag.AlignTop)
        self.prepare_inputs(dialog)
        dialog.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        for button in dialog.findChildren(QPushButton):
            if button.text().replace('&','') in ('Done','Close'):button.hide()
        if dialog.__class__.__name__=='PromptLibraryDialog':
            scaled(dialog.list).setMinimumHeight(112)
            scaled(dialog.content).setMinimumHeight(180)
            if self.frame_size().width()>=px(self,600):
                # Browse beside the editor, keeping the action row visible while
                # giving reusable prompt text most of the available height.
                layout=dialog.tabs.widget(0).layout()
                items=[layout.takeAt(0) for _ in range(layout.count())]
                columns=QHBoxLayout();scaled(columns).setSpacing(12)
                browser=QWidget();left=QVBoxLayout(browser);scaled(left).setContentsMargins(0,0,0,0)
                scaled(browser).setMaximumWidth(210)
                left.addWidget(items[0].widget());left.addWidget(items[1].widget(),1)
                editor=QWidget();right=QVBoxLayout(editor);scaled(right).setContentsMargins(0,0,0,0)
                for item in items[2:-2]:
                    if item.widget():right.addWidget(item.widget(),1 if isinstance(item.widget(),QTabWidget) else 0)
                    else:right.addLayout(item.layout())
                columns.addWidget(browser,1);columns.addWidget(editor,2);layout.addLayout(columns,1)
                layout.addWidget(items[-2].widget());layout.addLayout(items[-1].layout())
            else:
                scaled(dialog.list).setMaximumHeight(112)
        # Appearance's legacy nested scroll area becomes part of the single
        # settings body; text editors retain their own vertical content scrolling.
        if dialog.__class__.__name__=='AppearanceDialog':
            layout=dialog.layout()
            for i in range(layout.count()):
                scroll=layout.itemAt(i).widget()
                if isinstance(scroll,QScrollArea):
                    content=scroll.takeWidget();layout.removeWidget(scroll);layout.insertWidget(i,content);scroll.hide();scroll.deleteLater();break
        for widget in dialog.findChildren(QTextEdit)+dialog.findChildren(QPlainTextEdit):
            scaled(widget).setMinimumHeight(max(120,round(widget.minimumHeight()/factor(widget))))
            widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            widget.setLineWrapMode(widget.LineWrapMode.WidgetWidth)
        # On screens narrower than a form's action row, wrap its existing buttons
        # without changing actions, keyboard focus or editor contents.
        margin=2*self.owner.activity.margin if hasattr(self.owner,'activity') else 0
        available=max(px(self,128),self.frame_size().width()-margin-px(self,136))
        for row in dialog.findChildren(QHBoxLayout):
            buttons=[row.itemAt(i).widget() for i in range(row.count())]
            parent=row.parent()
            if len(buttons)<3 or not all(isinstance(b,QPushButton) for b in buttons) or not isinstance(parent,QBoxLayout) or row.minimumSize().width()<=available:continue
            index=next((i for i in range(parent.count()) if parent.itemAt(i).layout() is row),None)
            if index is None:continue
            columns=max(1,min(len(buttons),available//max(b.minimumSizeHint().width()+px(self,8) for b in buttons)))
            holder=QWidget();grid=QGridLayout(holder)
            scaled(grid).setContentsMargins(0,0,0,0)
            for i,button in enumerate(buttons):row.removeWidget(button);grid.addWidget(button,i//columns,i%columns)
            parent.takeAt(index);parent.insertWidget(index,holder);row.deleteLater()

    def editor_finished(self,*_):
        if self.leaving_editor: return
        back=self.editor_return
        self.retire_editor()
        self.show_page(back)

    def retire_editor(self):
        if self.editor_page:
            self.stack.removeWidget(self.editor_page)
            self.editor_page.deleteLater()
        self.editor=None; self.editor_page=None

    def leave_editor(self):
        if not self.editor: return True
        dialog=self.editor; finished=[]
        def closed(*_): finished.append(True)
        dialog.finished.connect(closed)
        self.leaving_editor=True
        try: dialog.reject()
        finally:
            self.leaving_editor=False; dialog.finished.disconnect(closed)
        if not finished:
            self.feedback.setText('Wait for the current settings operation to finish.'); return False
        self.retire_editor(); return True

    def page_conversation(self):
        page,layout=self.make_page('Conversation','Choose how you see and compose conversations.')
        thinking=QCheckBox('Expand thinking by default'); thinking.setChecked(self.owner.preferences.values.get('expand_thinking',True)); thinking.toggled.connect(self.set_thinking); layout.addWidget(thinking)
        self.action(layout,'Prompt library && prompt improvement',self.open_prompts)
        layout.addStretch(); return page

    def set_thinking(self, enabled):
        if hasattr(self.owner,'set_thinking_visibility'): self.owner.set_thinking_visibility(enabled)
        else: self.owner.preferences.values['expand_thinking']=enabled; self.owner.preferences.save()

    def open_prompts(self):
        from .panels import PromptLibraryDialog
        self.open_editor('Prompt library',lambda:PromptLibraryDialog(self.owner))

    def open_setup(self):
        controller=self.owner.controller
        if not controller: return
        if controller.running or controller.navigating:
            self.feedback.setText('Finish the current action before configuring a model.'); return
        self.open_editor('Model connection & setup',self.owner.make_setup_dialog)

    def open_models(self):
        if self.owner.controller.harness=='dsh': self.owner.open_pi()
        else:
            from .panels import ModelsDialog
            self.open_editor('Models & providers',lambda:ModelsDialog(self.owner))

    def page_connections(self):
        page,layout=self.make_page('Connections','Choose the models and services your agent uses.')
        layout.addWidget(QLabel('Agent engine')); engine=QComboBox()
        for text,value in [('DSH','dsh'),('Pi','pi'),('Codex (development)','codex')]: engine.addItem(text,value)
        engine.setCurrentIndex(engine.findData(getattr(self.owner.controller,'harness','dsh'))); engine.setAccessibleName('Agent engine')
        engine.setEnabled(bool(self.owner.controller)); engine.activated.connect(lambda _:self.owner.switch_harness(engine.currentData())); layout.addWidget(engine)
        self.action(layout,'Model connection && setup',self.open_setup)
        from .home_settings import HomeDialog
        self.action(layout,'Connect Home',lambda:self.open_editor('Home',lambda:HomeDialog(self.owner))); layout.addStretch(); return page

    def open_memory_settings(self):
        from .memory import MemoryDialog
        self.open_editor('Memory setup & processing',lambda:MemoryDialog(self.owner),back='memory' if self.stack.currentWidget()==self.pages.get('memory') else 'all')

    def page_advanced(self):
        page,layout=self.make_page('Advanced','Additional controls and diagnostics.')
        from .shortcut_settings import ShortcutSettings
        layout.addWidget(QLabel('Window shortcuts')); self.shortcuts=ShortcutSettings(self.owner); layout.addWidget(self.shortcuts)
        self.action(layout,'Memory setup && processing',self.open_memory_settings)
        from .recovery import RecoveryDialog
        self.action(layout,'Recover connection',lambda:self.open_editor('Recover connection',lambda:RecoveryDialog(self.owner)))
        from .support import SupportDialog
        self.action(layout,'Support report',lambda:self.open_editor('Support',lambda:SupportDialog(self.owner)))
        layout.addStretch(); return page

    def update_activity(self):
        running=bool(self.owner.controller and getattr(self.owner.controller,'running',False))
        self.stop.setVisible(running); self.stop.setEnabled(running)
        if hasattr(self,'connection'):
            self.connection.setText('●  Connected' if getattr(self.owner.controller,'online',False) else '○  Not connected')

    def capture_current(self):
        return self.shortcuts.capture_current() if self.shortcuts else False

    def accept(self):
        if not self.leave_editor(): return False
        if hasattr(self,'soul_editor') and self.soul_editor.toPlainText()!=self.soul['text']:
            self.show_page('soul'); self.feedback.setText('Your Agent Identity draft has unsaved changes.'); self.exit_choices.show(); return False
        self.save_name(); self.closing=True; self.closed.emit(); return True

    def keep_editing(self):
        self.exit_choices.hide(); self.feedback.clear(); self.soul_editor.setFocus()

    def discard_and_return(self):
        self.cancel_soul(); self.exit_choices.hide(); self.accept()

    def save_and_return(self):
        self.save_soul()
        if self.soul_editor.toPlainText()==self.soul['text']:
            self.exit_choices.hide(); self.accept()


SettingsDialog = SettingsPanel
