from .surface_design import SURFACE
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Native Augmentor surface with independent conversation and circular activity layouts."""
import argparse
from .instances import configure, current_name, validate_name, ipc_basename, window_label
import re
import html
import json
import os
import sys
import subprocess
import uuid
import threading
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QLockFile, QUrl, Signal, QSize, QPoint, QRect, QVariantAnimation, QEasingCurve
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtGui import QColor, QPainter, QKeySequence, QShortcut, QRegion, QDesktopServices, QPalette, QIcon
from PySide6.QtWidgets import (QApplication,QWidget,QFrame,QLabel,QPushButton,QVBoxLayout,QHBoxLayout,
    QStackedLayout,QTextEdit,QTextBrowser,QMessageBox,QInputDialog,QMenu,QSizePolicy,QLayout,QDialog)
from .controller import Controller
from .voice_button import VoiceButton
from .design import COPY_FEEDBACK_MS
from .queue_panel import QueuePanel
from .question_dialog import QuestionDialog
from .composer import Composer
from .activity import ActivityHalo
from .markdown import render_markdown, code_blocks
from .transcript import Transcript
from .preferences import Preferences
from .resize import ResizeBorders
from .workspaces import pin_kwin, release_kwin
from .surfaces import Orb, ModelPicker, AppearanceDialog, TitleEditor
from .panels import HistoryDialog, AccessDialog, UpdatesDialog, SettingsDialog, PromptLibraryDialog, ModelsDialog, LicensesDialog


class Window(QWidget):
    completed = Signal(object, object)

    def __init__(self, preview=True, harness=None):
        super().__init__()
        self.setWindowTitle(window_label())
        self.setWindowIcon(QIcon(str(Path(__file__).parent/'assets/augmentor.svg')))
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(364,364);self.resize(424,484)
        self.preferences=Preferences(not preview)
        if not preview and current_name()!='main':
            # Materialize the independent voice profile at first open, not
            # when the user eventually visits Voice settings. No microphone.
            from .voice_settings import voice_request
            def initialize_voice_profile():
                try:voice_request('preferences')
                except Exception:pass  # Optional offline voice must not prevent chat.
            threading.Thread(target=initialize_voice_profile,daemon=True).start()
        if harness in ('pi','dsh'):
            self.preferences.values['harness']=harness;self.preferences.save()
        self.controller=None if preview else Controller(self,harness=self.preferences.values['harness'])
        self.setup_dialog=None;self.appearance_dialog=None;self.setup_offered=False
        self.messages=[];self.partial='';self.seen_events=set();self.message_events={};self.reasoning_index=None;self.expanded_thinking=set();self.editing=None
        self.rendered_messages=None;self.rendered_partial=''
        self.pending_prompt=None;self.submitted_draft=None;self.morphing=False;self.compact=False;self.close_pending=False;self.read_only=False;self.is_saved=False
        self.expanded_size=self.size();self.follow_tail=True;self.rendering=False
        self.title_text='Augmentor Agent'
        self.hidden_geometry=None;self.hidden_layout=None;self.hidden_dialogs=[];self.shortcut_dialog=None
        self.completed.connect(lambda callback,value:callback(value))
        self.render_timer=QTimer(self);self.render_timer.setSingleShot(True);self.render_timer.setInterval(33);self.render_timer.timeout.connect(self.render_messages)
        self.copied_message=None;self.copied_code=None
        self.copy_feedback_timer=QTimer(self);self.copy_feedback_timer.setSingleShot(True);self.copy_feedback_timer.setInterval(COPY_FEEDBACK_MS)
        self.copy_feedback_timer.timeout.connect(self.clear_copy_feedback)
        self.preferences_timer=QTimer(self);self.preferences_timer.setSingleShot(True);self.preferences_timer.setInterval(200);self.preferences_timer.timeout.connect(self.preferences.save)
        self.activity=ActivityHalo(self)
        self.outer=QVBoxLayout(self);self.outer.setContentsMargins(*([self.activity.margin]*4));self.outer.setSpacing(0)
        self.stack=QStackedLayout();self.outer.addLayout(self.stack)
        self.outer.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.stack.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.expanded=QFrame();self.stack.addWidget(self.expanded)
        layout=QVBoxLayout(self.expanded);layout.setContentsMargins(*([SURFACE['inset']]*4));layout.setSpacing(SURFACE['gap'])
        header=QHBoxLayout();header.setSpacing(SURFACE['headerGap'])
        self.title=QLabel('New conversation');self.title.setTextFormat(Qt.TextFormat.PlainText)
        self.title.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        self.title.setStyleSheet('font-size:11px;font-weight:400;padding-left:8px;')
        self.title.setToolTip('Double-click to rename this conversation')
        self.title.mouseDoubleClickEvent=lambda _:self.rename_chat()
        identity=QVBoxLayout();identity.setSpacing(2);identity.setContentsMargins(0,0,0,0)
        self.brand=QLabel(window_label());self.brand.setStyleSheet('font-size:13px;font-weight:600;padding-left:8px;')
        identity.addWidget(self.brand)
        self.title_stack=QStackedLayout();self.title_stack.setContentsMargins(0,0,0,0)
        self.title_stack.addWidget(self.title)
        self.title_editor=TitleEditor();self.title_editor.setAccessibleName('Session title')
        self.title_editor.setFixedHeight(18)
        self.title_editor.setStyleSheet('QLineEdit {font-size:11px;padding:0 0 0 8px;border:0;border-radius:0;background:transparent;}')
        self.title_editor.returnPressed.connect(self.save_inline_title)
        self.title_editor.cancelled.connect(self.cancel_inline_title)
        self.title_stack.addWidget(self.title_editor);self.title_stack.setCurrentWidget(self.title)
        self.rename_session=None;identity.addLayout(self.title_stack);header.addLayout(identity,1)
        self.new_button=self.icon_button(SURFACE['glyphs']['newchat'],'New chat · right-click for approval mode',self.new_chat)
        self.new_button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.new_button.customContextMenuRequested.connect(lambda _:self.open_access())
        self.save_button=self.icon_button(SURFACE['glyphs']['save'],'Save this chat',self.toggle_save)
        self.history_button=self.icon_button(SURFACE['glyphs']['sessions'],'Conversation history',self.open_history)
        self.pin_button=self.icon_button(SURFACE['glyphs']['pin'],'Follow me across all desktops',self.toggle_pin,checkable=True)
        self.pin_button.setChecked(self.preferences.values['pinned'])
        self.compact_button=self.icon_button(SURFACE['glyphs']['compact'],'Circular activity view',self.toggle_compact)
        self.more_button=self.icon_button(SURFACE['glyphs']['more'],'More options',self.open_menu)
        self.hide_button=self.icon_button(SURFACE['glyphs']['hide'],'Hide Augmentor',self.hide)
        for button in (self.new_button,self.save_button,self.history_button,self.pin_button,self.compact_button,self.more_button,self.hide_button):header.addWidget(button,0,Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(header)
        self.status=QLabel('UI preview' if preview else 'Connecting…');self.status.hide()
        self.model_picker=ModelPicker();self.model_picker.selected.connect(self.model_selected)
        self.model_picker.pin_requested.connect(self.pin_model)
        self.model_picker.refresh_requested.connect(lambda:self.controller.refresh_models() if self.controller else None)
        self.model_picker.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
        self.model_picker.setMinimumWidth(0);self.model_picker.setFixedHeight(24)
        self.model_picker.setStyleSheet('text-align:left;border:0;background:transparent;padding:0;font-size:11px;')
        self.body=QFrame();body=QVBoxLayout(self.body);body.setContentsMargins(0,0,0,0);body.setSpacing(0)
        self.transcript=Transcript();self.transcript.setOpenExternalLinks(False);self.transcript.setOpenLinks(False)
        self.transcript.setAccessibleName('Conversation');self.transcript.setStyleSheet('QTextBrowser {background:transparent;border:0;padding:2px;}')
        self.transcript.verticalScrollBar().valueChanged.connect(self.scrolled)
        self.transcript.anchorClicked.connect(self.message_action)
        body.addWidget(self.transcript,1);layout.addWidget(self.body,1)
        self.input_stack=QFrame();input_layout=QVBoxLayout(self.input_stack)
        input_layout.setContentsMargins(0,0,0,0);input_layout.setSpacing(0);layout.addWidget(self.input_stack)
        self.queue_panel=QueuePanel();input_layout.addWidget(self.queue_panel)
        self.queue_session=None
        self.queue_panel.action_requested.connect(lambda item,action:self.controller.update_queue(item,action) if self.controller else None)
        self.composer=Composer()
        self.composer.improve_requested.connect(self.improve_prompt)
        self.composer.improvement_changed.connect(self.update_controls)
        self.edit_bar=QFrame();edit_layout=QHBoxLayout(self.edit_bar);edit_layout.setContentsMargins(2,0,2,0)
        edit_label=QLabel('Editing latest message');edit_layout.addWidget(edit_label,1)
        self.cancel_edit_button=QPushButton('Cancel');self.cancel_edit_button.clicked.connect(self.cancel_edit);edit_layout.addWidget(self.cancel_edit_button)
        self.edit_bar.setToolTip('Resubmit from before this message. The previous conversation stays in History.')
        self.edit_bar.hide();input_layout.addWidget(self.edit_bar)
        self.composer.submit_requested.connect(self.send);input_layout.addWidget(self.composer)
        self.voice_opening=False;self.voice_epoch=0;self.voice_gesture_mode=None;self.voice_input=None
        footer=QHBoxLayout();footer.setSpacing(SURFACE['footerGap']);footer.addWidget(self.model_picker,1)
        self.connection_dot=QLabel('●');self.connection_dot.setToolTip('Connecting to the harness');self.connection_dot.setFixedWidth(12);footer.addWidget(self.connection_dot)
        self.voice_dialog=None
        self.voice_button=VoiceButton(self)
        self.voice_button.pressed.connect(self.voice_pressed)
        self.voice_button.hands_free_requested.connect(self.start_gesture_hands_free)
        self.voice_button.hold_started.connect(self.begin_voice)
        self.voice_button.released.connect(self.end_voice)
        self.voice_button.cancelled.connect(self.cancel_voice_recording)
        footer.addWidget(self.voice_button)
        self.latest_button=self.icon_button(SURFACE['glyphs']['latest'],'Return to latest message',self.jump_latest);self.latest_button.hide();footer.addWidget(self.latest_button)
        self.send_button=self.icon_button(SURFACE['glyphs']['send'],'Send · Enter (Shift+Enter for a new line)',self.send);self.send_button.setEnabled(False);footer.addWidget(self.send_button)
        self.stop_button=self.icon_button(SURFACE['glyphs']['stop'],'Stop current turn',self.stop);self.stop_button.hide();footer.addWidget(self.stop_button)
        layout.addLayout(footer)
        self.orb=Orb();self.stack.addWidget(self.orb);self.orb.expand_requested.connect(self.toggle_compact);self.orb.stop_requested.connect(self.stop)
        self.orb.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu);self.orb.customContextMenuRequested.connect(self.orb_menu)
        self.apply_appearance(self.preferences.values)
        self.shared_appearance_timer=QTimer(self)
        self.shared_appearance_timer.setInterval(1500)
        self.shared_appearance_timer.timeout.connect(self.refresh_shared_appearance)
        if not preview and getattr(self.preferences,'persistent',False):self.shared_appearance_timer.start()
        self.transcript.setHtml('<p>How can I help?</p>')
        self.save_button.setEnabled(False)
        for button in (self.new_button,self.history_button):button.setEnabled(not preview)
        QShortcut(QKeySequence('Ctrl+Shift+Space'),self,activated=self.toggle_compact)
        QShortcut(QKeySequence('Ctrl+Return'),self,activated=self.send)
        QShortcut(QKeySequence('Escape'),self,activated=self.escape)
        QShortcut(QKeySequence('Ctrl+Home'),self,activated=self.jump_top)
        QShortcut(QKeySequence('Ctrl+End'),self,activated=self.jump_latest)
        if self.controller:self.bind_controller()
        self.sync_orb()
        self.resize_borders=ResizeBorders(self)
        self.restore_placement()
        self.touch_layout=None
        if os.environ.get('AUGMENTOR_TOUCH_MODE')=='1':
            from .touch import TouchLayout
            self.touch_layout=TouchLayout(self)
        if self.preferences.retired_harness and not preview:
            QTimer.singleShot(0,lambda:QMessageBox.information(self,'Connect DSH',
                'OpenCode support has been retired. Its conversations and configuration are retained. '
                'DSH is selected for this window; connect it in Settings. '
                'No OpenCode conversation has been transferred or replayed.'))

    def switch_harness(self,harness,reconnect=False):
        if self.voice_dialog or self.voice_input or self.voice_opening:self.close_voice_panel()
        if harness not in ('pi','dsh') or not self.controller:return
        if self.controller.harness==harness and not reconnect:return
        if self.controller.running or self.controller.navigating or self.editing or getattr(self.controller,'repairing',False):
            self.set_status('Finish the current action before switching harness.');return
        if self.composer.improving:self.composer.cancel_improvement()
        old=self.controller;old.close()
        for signal_name in ('status','models','selection_changed','session_info','busy','event','problem','interaction','sent','page','recovered','connection'):
            try:getattr(old,signal_name).disconnect()
            except TypeError:pass
        self.preferences.values['harness']=harness;self.preferences.save()
        self.controller=Controller(self,harness=harness)
        self.messages=[];self.message_events={};self.partial='';self.rendered_messages=None;self.copied_message=None;self.copied_code=None
        self.read_only=False;self.seen_events=set();self.follow_tail=True
        self.render_messages();self.set_models({'groups':[]});self.bind_controller()

    def bind_controller(self):
        self.controller.status.connect(self.set_status);self.controller.models.connect(self.set_models)
        self.controller.selection_changed.connect(self.set_selection);self.controller.session_info.connect(self.session_changed)
        self.controller.busy.connect(self.set_busy);self.controller.event.connect(self.on_event)
        self.controller.problem.connect(self.on_problem);self.controller.interaction.connect(self.on_interaction)
        self.controller.sent.connect(self.message_sent)
        self.controller.submission_failed.connect(self.message_not_sent)
        self.controller.queue_changed.connect(self.queue_panel.replace)
        self.controller.queue_result.connect(self.queue_panel.submission_result)
        self.controller.queue_action_result.connect(self.queue_panel.action_result)
        self.controller.page.connect(self.restore_page)
        self.controller.recovered.connect(self.restore_recovery)
        self.controller.connection.connect(self.connection_changed)
        self.controller.start_monitor()

    def connection_changed(self,online):
        self.update_controls()
        if not self.setup_offered and self.controller and self.controller.harness=='dsh' and not self.controller.session and not getattr(self.controller.client,'product',False):
            self.setup_offered=True
            QTimer.singleShot(0,self.open_setup)
        if online and not self.setup_offered and self.controller and self.controller.harness=='pi':
            self.setup_offered=True
            available=any(model.get('available') for group in self.model_picker.catalog.get('groups',[]) for model in group.get('models',[]))
            if not available and not self.controller.session:QTimer.singleShot(0,self.open_setup)

    def open_setup(self):
        if not self.controller:return
        if self.controller.running or self.controller.navigating:
            self.set_status('Finish the current action before configuring a model.');return
        if self.setup_dialog and self.setup_dialog.isVisible():self.setup_dialog.raise_();return
        from .setup import SetupDialog
        from .dsh_setup import DshSetupDialog
        self.setup_dialog=(SetupDialog if self.controller.harness=='pi' else DshSetupDialog)(self);self.setup_dialog.show()
    def icon_button(self,text,tooltip,callback,checkable=False):
        button=QPushButton(text);button.setFixedSize(SURFACE['iconSize'],SURFACE['iconSize']);button.setStyleSheet('QPushButton {padding:0;font-size:15px;border:0;background:transparent;} QPushButton:hover {background:rgba(127,150,150,55);color:palette(window-text);}')
        button.setToolTip(tooltip);button.setAccessibleName(tooltip);button.setCheckable(checkable);button.clicked.connect(callback);return button

    def call_in_background(self,fn,callback):
        if not self.controller:return
        def work():
            value=fn()
            if not self.controller.closed:self.completed.emit(callback,value)
        self.controller.task(work)

    def set_status(self,text):
        self.status.setText(text);self.connection_dot.setToolTip(text);self.title.setToolTip(text+' · double-click to rename');self.sync_orb()

    def sync_orb(self):
        selection=self.model_picker.currentData() or {}
        self.orb.set_activity(self.status.text(),bool(self.controller and self.controller.running),selection.get('name',selection.get('model','Pi')))

    def set_models(self,catalog):
        if isinstance(catalog,list):catalog={'groups':[{'provider':'Pi','name':'Pi','models':catalog}]}
        self.model_picker.set_catalog(catalog)
        self.model_selected(self.model_picker.currentData(),persist=False)
        self.update_controls()

    def set_selection(self,selection):
        self.model_picker.set_catalog(self.model_picker.catalog,preferred=selection);self.model_selected(self.model_picker.currentData(),persist=False)

    def pin_model(self,model,pinned):
        self.call_in_background(lambda:self.controller.client.call('models.pin',{**model,'pinned':pinned}),self.set_models)

    def model_selected(self,selection,persist=True):
        if not selection:return
        if persist and self.controller:self.controller.choose_model(selection)
        self.sync_orb();self.update_controls()

    def set_voice_enabled(self, enabled):
        self.preferences.values['resonant_voice']=bool(enabled)
        self.preferences.save()
        if not enabled:self.close_voice_panel()
        self.update_controls()

    def request_voice(self):
        self.bring_forward()
        if self.compact:self.toggle_compact()
        remaining=[120]
        def ready():
            if not self.controller or self.controller.closed:return
            if self.controller.online and self.model_picker.currentData():
                self.open_voice();return
            remaining[0]-=1
            if remaining[0]>0:QTimer.singleShot(500,ready)
            else:self.set_status('Voice could not connect. Check the DSH connection and try the voice button again.')
        ready()

    def voice_is_hands_free(self):
        return (self.voice_gesture_mode or self.preferences.values.get('voice_mode','manual'))=='hands-free'

    def start_gesture_hands_free(self):
        # A mode gesture cancels an unfinished manual hold; releasing the same
        # pointer must neither submit that hold nor stop the new conversation.
        if not self.voice_opening:self.close_voice_panel()
        self.voice_gesture_mode='hands-free'
        self.voice_button.hands_free=True
        self.open_voice()
        self.update_controls()

    def prepare_voice_input(self):
        if self.voice_input:return
        from .voice_input import EarlyVoiceInput
        capture=EarlyVoiceInput(self);self.voice_input=capture
        def changed():
            if capture is self.voice_input and not self.voice_dialog:
                self.voice_button.recording_available=capture.receiving
                self.voice_button.refresh_tip();self.voice_button.update()
        def failed(message):
            if capture is self.voice_input:
                self.close_voice_panel();self.voice_button.set_state('error',message);self.set_status(message)
        capture.changed.connect(changed);capture.failed.connect(failed)

    def refresh_voice_preferences(self):
        if not self.voice_dialog and not self.voice_opening and getattr(self.preferences,'persistent',False):
            latest=Preferences()
            for key in ('resonant_voice','voice_mode','voice_pause_ms'):
                self.preferences.values[key]=latest.values[key]
            self.voice_button.hands_free=self.voice_is_hands_free()

    def voice_pressed(self):
        self.refresh_voice_preferences()
        voice=self.voice_dialog
        if self.voice_is_hands_free():
            if voice or self.voice_opening:self.close_voice_panel()
            else:self.open_voice()
            return
        if self.voice_button.locked and voice and voice.capture:
            self.voice_button.disarm();self.voice_button.setDown(False)
            voice.end();return
        if voice and (voice.closed or (not voice.connected and voice.state!='connecting')):
            self.close_voice_panel();voice=None
        if voice:
            voice.interrupt()
        else:self.open_voice()

    def begin_voice(self):
        if self.voice_is_hands_free():return
        if self.voice_button.holding and self.voice_dialog and self.voice_dialog.can_record:
            self.voice_dialog.begin()

    def end_voice(self):
        if self.voice_is_hands_free():return
        if self.voice_dialog and not self.voice_button.locked:self.voice_dialog.end()

    def cancel_voice_recording(self):
        if self.voice_input or (self.voice_dialog and (self.voice_dialog.capture or getattr(self.voice_dialog,'hands_free',False))):
            # Disconnect discards the unfinished utterance; never send `end` on cancellation.
            self.close_voice_panel()

    def voice_state_changed(self):
        voice=self.voice_dialog
        if not voice:return
        self.voice_button.recording_available=voice.recording_available
        self.voice_button.set_state(voice.state,voice.status_text)
        if voice.state=='error':self.set_status(voice.status_text)
        if voice.state=='ready' and self.voice_button.holding:
            QTimer.singleShot(0,self.begin_voice)

    def close_voice_panel(self):
        self.voice_epoch+=1;self.voice_opening=False;self.voice_gesture_mode=None
        voice=self.voice_dialog;self.voice_dialog=None
        early=self.voice_input;self.voice_input=None
        if early:early.close()
        if voice:
            voice.panel_closed.disconnect(self.close_voice_panel)
            voice.changed.disconnect(self.voice_state_changed)
            voice.recording_progress.disconnect(self.voice_button.set_recording_progress)
            if self.controller:
                try:self.controller.queue_result.disconnect(voice.submission_result)
                except (RuntimeError,TypeError):pass
            voice.close()
        self.voice_button.recording_available=False
        self.voice_button.set_state('off')
        self.update_controls()

    def open_voice(self):
        if getattr(getattr(self,'preferences',None),'persistent',False):self.refresh_voice_preferences()
        if not self.preferences.values.get('resonant_voice',True):
            self.set_status('Enable Resonant Voice in Settings to use the microphone.');return
        if self.editing:
            self.set_status('Finish or cancel the message edit before opening Voice.');return
        if self.voice_dialog or not self.controller:return
        if self.voice_is_hands_free():self.prepare_voice_input()
        if self.voice_opening:return
        controller=self.controller;selection=self.model_picker.currentData()
        self.voice_opening=True;self.voice_epoch+=1;epoch=self.voice_epoch
        self.voice_button.set_state('connecting')
        def work():
            try:return controller.prepare_voice(selection),None
            except Exception as error:return None,str(error)
        def ready(result):
            # prepare_voice has released its navigation lock. Refresh every control,
            # including after cancellation, so new-chat setup cannot leave them disabled.
            self.update_controls()
            if epoch!=self.voice_epoch:return
            self.voice_opening=False
            ticket,error=result
            if error:
                self.voice_button.set_state('error',error)
                self.set_status('Voice unavailable. '+error);return
            if not self.preferences.values.get('resonant_voice',True) or controller is not self.controller or controller.closed or controller.session!=ticket['sessionId']:
                self.close_voice_panel();return
            from .voice import VoiceSession
            voice=VoiceSession(self,ticket,hands_free=self.voice_is_hands_free(),early_input=self.voice_input);self.voice_dialog=voice
            voice.transcript.connect(self.voice_transcript)
            controller.queue_result.connect(voice.submission_result)
            voice.panel_closed.connect(self.close_voice_panel)
            voice.changed.connect(self.voice_state_changed)
            voice.recording_progress.connect(self.voice_button.set_recording_progress)
            self.voice_state_changed()
        self.call_in_background(work,ready)

    def voice_transcript(self,event):
        controller=self.controller
        if not self.voice_dialog or self.voice_dialog.closed or not controller or controller.session!=event['sessionId'] or controller.read_only:return
        if controller.running:
            accepted=controller.queue_prompt(event['text'],'resonant-voice:'+event['requestId'],mode='steer')
        else:
            accepted=controller.send(event['text'],self.model_picker.currentData(),request_id='resonant-voice:'+event['requestId'])
        if not accepted and self.voice_dialog:
            self.voice_dialog.set_status('Message was not submitted. '+event['text'])
            if getattr(self.voice_dialog,'hands_free',False):self.voice_dialog.shutdown()

    def session_changed(self,info):
        if self.voice_dialog and 'sessionId' in info and info['sessionId']!=self.voice_dialog.session_id:self.voice_dialog.close()
        if 'sessionId' in info and info['sessionId']!=self.queue_session:
            if self.composer.improving:self.composer.cancel_improvement()
            if self.queue_session is not None or info['sessionId'] is None:self.queue_panel.reset()
            self.queue_session=info['sessionId']
        if self.editing and info.get('sessionId') and info['sessionId']!=self.editing['sessionId']:
            fork=info.get('fork',{})
            if fork.get('mode')=='edit' and fork.get('sessionId')==self.editing['sessionId']:
                self.editing['sessionId']=info['sessionId'];self.editing['prepared']=True
            else:self.cancel_edit()
        if 'readOnly' in info:self.read_only=info['readOnly']
        if 'saved' in info:self.is_saved=info['saved']
        if 'title' in info:self.title_text=str(info['title'] or 'Augmentor Agent');self.title.setText(self.title_text)
        self.save_button.setText('★' if self.is_saved else '☆')
        self.save_button.setToolTip('Unsave this conversation' if self.is_saved else 'Save this conversation')
        self.model_selected(self.model_picker.currentData(),persist=False);self.update_controls()
        if self.read_only:self.set_status('History view')

    def update_controls(self):
        self.voice_button.hands_free=self.voice_is_hands_free()
        self.voice_button.refresh_tip()
        self.voice_button.setVisible(self.preferences.values.get('resonant_voice',True))
        self.voice_button.setEnabled(bool(self.controller and getattr(self.controller,'harness',None)=='dsh' and getattr(self.controller,'online',False) and not getattr(self.controller,'read_only',False) and (not getattr(self.controller,'navigating',False) or self.voice_opening)))
        running=bool(self.controller and (self.controller.running or getattr(self.controller,'navigating',False)))
        can_queue=bool(self.controller and getattr(getattr(self.controller,'client',None),'supports_queue',False))
        self.send_button.setEnabled(bool(self.controller and self.model_picker.currentData()) and (not running or can_queue) and not getattr(self.controller,'navigating',False) and not self.read_only and getattr(self.controller,'online',True))
        if self.composer.improving or getattr(self.controller,'repairing',False):self.send_button.setEnabled(False)
        self.composer.improvement_available=bool(self.controller and hasattr(getattr(self.controller,'client',None),'improve_prompt') and self.model_picker.currentData() and not self.read_only and getattr(self.controller,'online',False))
        self.composer.refresh_improve_button()
        self.model_picker.setEnabled(not running and not self.read_only)
        self.new_button.setEnabled(bool(self.controller) and not running)
        self.history_button.setEnabled(bool(self.controller) and not running)
        self.save_button.setEnabled(bool(self.controller and self.controller.session) and not self.read_only)
        working=bool(self.controller and self.controller.running)
        self.stop_button.setVisible(working);self.stop_button.setEnabled(working);self.send_button.setVisible(not working or can_queue)
        self.send_button.setToolTip('Queue prompt · Enter' if working and can_queue else 'Send · Enter (Shift+Enter for a new line)')
        self.queue_panel.online=bool(self.controller and getattr(self.controller,'online',False));self.queue_panel.running=working;self.queue_panel.render()
        self.connection_dot.setStyleSheet('color:'+('#a6d6c8' if not self.controller or getattr(self.controller,'online',False) else '#d8ae70')+';font-size:8px;')
        self.sync_orb()

    def set_busy(self,busy):
        self.activity.configure(busy=busy)
        self.update_controls();self.set_status('Working…' if busy else ('History view' if self.read_only else 'Ready'))
        self.cancel_edit_button.setEnabled(not busy)
        self.rendered_messages=None;self.render_timer.start()
        if not busy and self.close_pending:QTimer.singleShot(0,self.close)

    def new_chat(self):
        if self.controller and not self.controller.running and not self.controller.navigating and not self.controller.recovery_lock.locked():
            self.cancel_edit();self.controller.new_chat();self.rendered_messages=None;self.messages=[];self.partial='';self.seen_events=set();self.message_events={};self.reasoning_index=None;self.expanded_thinking=set();self.transcript.clear();self.composer.clear();self.follow_tail=True;self.set_status('New conversation')

    def improve_prompt(self):
        if not self.controller or self.composer.improving:return
        adapter=self.controller.client;selection=dict(self.model_picker.currentData() or {})
        original=self.composer.toPlainText()
        if not original.strip() or not hasattr(adapter,'improve_prompt'):return
        identity=self.composer.begin_improvement()
        def work():
            result=None;error=''
            try:
                from .prompt_client import PromptClient
                settings=PromptClient().call('prompts.list').get('improvement')
                if not settings:raise ValueError('Restart the prompt service to load Improve prompt settings.')
                template=settings['content']
                result=adapter.improve_prompt(original,template,selection)
            except Exception as exc:error=str(exc)
            try:self.composer.improvement_result.emit(identity,result,error)
            except RuntimeError:pass
        threading.Thread(target=work,daemon=True,name='augmentor-improve-prompt').start()

    def send(self):
        if self.composer.improving:return
        text=self.composer.toPlainText().strip()
        if self.controller and self.send_button.isEnabled() and text:
            if self.controller.running:
                request_id=uuid.uuid4().hex
                self.queue_panel.submitted(request_id,text);self.composer.clear()
                if not self.controller.queue_prompt(text,request_id):
                    self.queue_panel.consumed(request_id);self.composer.setPlainText(text)
                return
            self.submitted_draft=self.composer.toPlainText()
            self.composer.clear()
            self.pending_prompt=text;self.render_messages();self.jump_latest()
            if self.editing and not self.editing.get('prepared'):accepted=self.controller.send(text,self.model_picker.currentData(),edit_from=dict(self.editing))
            else:accepted=self.controller.send(text,self.model_picker.currentData())
            if accepted is False:
                self.restore_unaccepted_prompt();self.pending_prompt=None;self.rendered_messages=None;self.render_messages()

    def restore_unaccepted_prompt(self):
        if self.submitted_draft is None:return
        draft=self.submitted_draft;self.submitted_draft=None
        if not self.composer.toPlainText():self.composer.setPlainText(draft)
        else:self.messages.append(('Status','Prompt not confirmed as sent (your newer draft is preserved):\n'+draft))

    def message_not_sent(self,text):
        # Idle/history/errors are independent of this particular submission.
        # Only its own failed/cancelled result can restore the submitted draft.
        if self.pending_prompt!=text:return
        self.restore_unaccepted_prompt()
        self.pending_prompt=None;self.render_timer.start()

    def message_sent(self,text):
        self.submitted_draft=None
        if self.editing and not self.composer.toPlainText():
            self.composer.setPlainText(self.editing['draft'])
        self.editing=None;self.edit_bar.hide();self.send_button.setToolTip('Send · Enter (Shift+Enter for a new line)')

    def cancel_edit(self):
        if self.editing:
            self.composer.setPlainText(self.editing['draft'])
            self.editing=None;self.edit_bar.hide();self.send_button.setToolTip('Send · Enter (Shift+Enter for a new line)')
            self.rendered_messages=None;self.render_messages()

    def can_change_message(self):
        return bool(self.controller and self.controller.session and not self.read_only and getattr(self.controller,'online',True)
                    and not self.controller.running and not getattr(self.controller,'navigating',False) and not self.editing)

    def message_key(self,index):
        # Keep the feedback attached to its message across paging and chat switches.
        return (getattr(self.controller,'session',None),self.message_events.get(index,{}).get('seq',('index',index)))

    def clear_copy_feedback(self):
        self.copied_message=None;self.copied_code=None
        self.rendered_messages=None;self.render_messages()

    def message_action(self,url):
        action=url.scheme();index_text=url.path()
        if action in ('http','https','mailto','tel','ftp','ssh','sftp'):
            if not QDesktopServices.openUrl(url):self.set_status('Could not open link in the default application')
            return
        if action=='augmentor-code' and re.fullmatch(r'\d+:\d+',index_text):
            index,block=map(int,index_text.split(':'))
            text=self.messages[index][1] if index<len(self.messages) else self.partial if index==len(self.messages) else ''
            codes=code_blocks(text)
            if block<len(codes):
                clipboard=QApplication.clipboard();clipboard.setText(codes[block])
                if clipboard.text()!=codes[block]:self.set_status('Could not copy');return
                self.copied_code=(self.message_key(index),block);self.copy_feedback_timer.start()
                self.rendered_messages=None;self.render_messages();self.set_status('Copied')
            return
        if action=='augmentor-think' and index_text.isdigit():
            index=int(index_text)
            if index<len(self.messages) and self.messages[index][0]=='Thinking':
                collapsing=index in self.expanded_thinking
                self.expanded_thinking.symmetric_difference_update({index})
                self.follow_tail=False
                self.rendered_messages=None;self.render_messages()
                if collapsing:self.transcript.scrollToAnchor(f'thinking-{index}')
            return
        if action not in ('augmentor-copy','augmentor-branch','augmentor-edit') or not index_text.isdigit():return
        index=int(index_text)
        if not 0<=index<len(self.messages):return
        role,text=self.messages[index]
        if role not in ('You','Augmentor'):return
        if action=='augmentor-copy':
            clipboard=QApplication.clipboard();clipboard.setText(text)
            if clipboard.text()!=text:self.set_status('Could not copy message');return
            self.copied_message=self.message_key(index);self.copy_feedback_timer.start()
            self.rendered_messages=None;self.render_messages();self.set_status('Copied message');return
        event=self.message_events.get(index)
        if not event or not self.can_change_message():return
        if not getattr(self.controller,'capabilities',{'branch':True,'edit':True}).get(action.removeprefix('augmentor-')):return
        if action=='augmentor-branch' and role=='Augmentor':
            if any(p.get('type')=='toolCall' for p in event.get('data',{}).get('message',{}).get('content',[])):return
            self.controller.branch(event['seq'])
        elif action=='augmentor-edit' and role=='You' and index==max(i for i,(r,_) in enumerate(self.messages) if r=='You'):
            self.editing={'sessionId':self.controller.session,'seq':event['seq'],'draft':self.composer.toPlainText()}
            self.composer.setPlainText(text);self.composer.setFocus();self.edit_bar.show()
            self.send_button.setToolTip('Resubmit edited message · Enter')
            self.set_status('Edit your message, then send. The previous conversation stays in History.')
            self.rendered_messages=None;self.render_messages()

    def message_actions(self,index,role,accent):
        if role not in ('You','Augmentor'):return ''
        links=[self.transcript.action_link('copy',index,accent,icon='check' if self.copied_message==self.message_key(index) else 'copy')]
        event=self.message_events.get(index)
        if event and self.can_change_message():
            if getattr(self.controller,'capabilities',{'edit':True}).get('edit') and role=='You' and index==max(i for i,(r,_) in enumerate(self.messages) if r=='You'):
                links.append(self.transcript.action_link('edit',index,accent))
            elif getattr(self.controller,'capabilities',{'branch':True}).get('branch') and role=='Augmentor' and not any(p.get('type')=='toolCall' for p in event.get('data',{}).get('message',{}).get('content',[])):
                links.append(self.transcript.action_link('branch',index,accent))
        return '<p style="margin-top:6px;">'+' &nbsp; '.join(links)+'</p>'

    def stop(self):
        if self.voice_dialog:self.voice_dialog.close()
        elif getattr(self,'voice_input',None) or getattr(self,'voice_opening',False):self.close_voice_panel()
        if self.controller:self.controller.stop()

    def scrolled(self,value):
        if self.rendering:return
        bar=self.transcript.verticalScrollBar();self.follow_tail=bar.maximum()-value<=12
        self.latest_button.setVisible(not self.follow_tail)
        if value<=24 and self.controller and not self.follow_tail:self.controller.load_older()

    def jump_top(self):
        self.follow_tail=False;self.transcript.verticalScrollBar().setValue(0);self.latest_button.setVisible(True)

    def jump_latest(self):
        self.follow_tail=True;self.transcript.verticalScrollBar().setValue(self.transcript.verticalScrollBar().maximum());self.latest_button.hide()

    def render_messages(self):
        bar=self.transcript.verticalScrollBar()
        if bar.isSliderDown():
            self.render_timer.start();return
        position=bar.value();follow=self.follow_tail
        cursor=self.transcript.textCursor();anchor,selection=cursor.anchor(),cursor.position()
        self.rendering=True
        accent=self.accent.name()
        same_history=self.rendered_messages==self.messages and getattr(self,'partial_start',None) is not None
        blocks=[]
        for index,(role,text) in ([] if same_history else enumerate(self.messages)):
            content=render_markdown(text,self.preferences.values['theme'],accent,tuple(sorted(self.preferences.values.get('format_colours',{}).items())),str(index),self.copied_code[1] if self.copied_code and self.copied_code[0]==self.message_key(index) else None) if role!='Status' and (role!='Thinking' or index in self.expanded_thinking) else '<p>'+html.escape(text).replace(chr(10),'<br>')+'</p>'
            if role=='Thinking':
                expanded=index in self.expanded_thinking
                label='▾ Thinking' if expanded else '▸ Thinking'
                blocks.append(f'<table width="100%" border="0" cellspacing="0" cellpadding="0" bgcolor="{ "#293238" if self.preferences.values["theme"]=="dark" else "#edf1f7" }"><tr><td style="padding-top:7px;padding-bottom:7px;padding-left:12px;padding-right:12px;"><p style="margin:0"><a name="thinking-{index}" href="augmentor-think:{index}" style="color:{accent};text-decoration:none">{label}</a></p>'+(content+f'<p style="margin:8px 0 0"><a href="augmentor-think:{index}" style="color:{accent};text-decoration:none">▴ Collapse thinking</a></p>' if expanded else '')+'</td></tr></table>')
                continue
            actions=self.message_actions(index,role,accent)
            if role=='You':
                blocks.append(f'<table width="86%" align="right" border="0" cellspacing="0" cellpadding="10"><tr><td><p align="right" style="margin:0 0 5px 0;color:{accent};"><b>You</b></p>{content}{actions}</td></tr></table>')
            else:blocks.append(f'<p style="color:{accent}"><b>{html.escape(role)}</b></p>{content}{actions}')
        from PySide6.QtGui import QTextCursor
        same_history=self.rendered_messages==self.messages and getattr(self,'partial_start',None) is not None
        if not same_history:
            self.transcript.setHtml(''.join(blocks))
            tail=QTextCursor(self.transcript.document());tail.movePosition(QTextCursor.MoveOperation.End)
            tail.insertBlock();self.partial_start=tail.position()
        else:
            tail=QTextCursor(self.transcript.document());tail.setPosition(self.partial_start)
            tail.movePosition(QTextCursor.MoveOperation.End,QTextCursor.MoveMode.KeepAnchor)
            tail.removeSelectedText()
        if self.pending_prompt:
            tail.insertHtml(f'<table width="86%" align="right" border="0" cellspacing="0" cellpadding="10"><tr><td><p align="right" style="color:{accent}"><b>You</b> · Sending…</p><p>'+html.escape(self.pending_prompt).replace('\n','<br>')+'</p></td></tr></table>')
        if self.partial:
            tail.insertHtml(f'<p style="color:{accent}"><b>Augmentor</b></p>'+render_markdown(self.partial,self.preferences.values['theme'],accent,tuple(sorted(self.preferences.values.get('format_colours',{}).items())),str(len(self.messages)),self.copied_code[1] if self.copied_code and self.copied_code[0]==self.message_key(len(self.messages)) else None))
        self.rendered_messages=list(self.messages);self.rendered_partial=self.partial
        if anchor!=selection:
            from PySide6.QtGui import QTextCursor
            cursor=self.transcript.textCursor();limit=self.transcript.document().characterCount()-1
            cursor.setPosition(min(anchor,limit));cursor.setPosition(min(selection,limit),QTextCursor.MoveMode.KeepAnchor);self.transcript.setTextCursor(cursor)
        bar.setValue(bar.maximum() if follow else min(position,bar.maximum()))
        self.rendering=False;self.follow_tail=follow;self.latest_button.setVisible(not follow)

    def restore_recovery(self,events,has_more):
        follow=self.follow_tail
        self.render_timer.stop()
        self.messages=[];self.partial='';self.seen_events=set();self.message_events={};self.reasoning_index=None;self.expanded_thinking=set()
        for event in events:self.fold_event(event)
        self.follow_tail=follow;self.render_messages()

    def restore_history(self,events):
        self.restore_page(events,False,False)

    def restore_page(self,events,has_more,older):
        self.render_timer.stop();bar=self.transcript.verticalScrollBar()
        if bar.isSliderDown():
            controller=self.controller;sid=getattr(controller,'session',None)
            def restore_when_released():
                if self.controller is not controller or getattr(controller,'session',None)!=sid:return
                # The page snapshot can precede a completed reply by seconds
                # while the reader holds the scrollbar. Use the current cache.
                latest=getattr(controller,'loaded_events',events)
                self.restore_page(latest,has_more,older)
            QTimer.singleShot(50,restore_when_released);return
        position=bar.value();oldmax=bar.maximum()
        anchor=self.transcript.cursorForPosition(QPoint(2,2))
        old_y=self.transcript.cursorRect(anchor).top()
        old_text=self.transcript.toPlainText()
        self.messages=[];self.partial='';self.seen_events=set();self.message_events={};self.reasoning_index=None;self.expanded_thinking=set()
        for event in events:self.fold_event(event)
        self.follow_tail=not older;self.render_messages()
        if older:
            # Anchor the old visible text; new output arriving during the fetch
            # must not be counted as prepended history height.
            new_text=self.transcript.toPlainText()
            offset=new_text.find(old_text) if old_text else -1
            self.rendering=True
            if offset>=0:
                from PySide6.QtGui import QTextCursor
                cursor=QTextCursor(self.transcript.document());cursor.setPosition(min(offset+anchor.position(),self.transcript.document().characterCount()-1))
                bar.setValue(bar.value()+self.transcript.cursorRect(cursor).top()-old_y)
            else:bar.setValue(position+bar.maximum()-oldmax)
            self.rendering=False;self.follow_tail=False;self.latest_button.show()

    def add_reasoning(self,text,replace=False):
        if not text:return
        if self.reasoning_index is None:
            self.reasoning_index=len(self.messages);self.messages.append(('Thinking',text))
        else:
            previous=self.messages[self.reasoning_index][1]
            self.messages[self.reasoning_index]=('Thinking',text if replace else previous+text)

    def fold_event(self,event):
        seq=event.get('seq')
        if seq is not None:
            if seq in self.seen_events:return False
            self.seen_events.add(seq)
        kind,data=event.get('type'),event.get('data',{})
        if kind=='tool/result':
            reply=data.get('meta',{}).get('resonantVoice') if isinstance(data.get('meta'),dict) else None
            blocks=data.get('message',{}).get('content',[])
            failed=any(b.get('isError') for b in blocks if isinstance(b,dict))
            if isinstance(reply,dict) and reply.get('version')==1 and isinstance(reply.get('text'),str) and not failed:
                self.reasoning_index=None;self.partial=''
                self.messages.append(('Augmentor',reply['text']))
                return True
        if kind=='user/message':
            if data.get('source',{}).get('kind')!='user':return False
            self.queue_panel.consumed(data.get('source',{}).get('rpcId'))
            text='\n'.join(p.get('text','') for p in data.get('content',[]) if p.get('type')=='text')
            if text:
                if text==self.pending_prompt:self.pending_prompt=None;self.submitted_draft=None
                self.message_events[len(self.messages)]=event
                self.messages.append(('You',text))
            return bool(text)
        if kind=='command/run':
            text='/'+data.get('name','')+data.get('args','')
            if text==self.pending_prompt:self.pending_prompt=None
            self.messages.append(('You',text));return True
        if kind=='command/done':
            # Hide only the routine opening policy notice, including history
            # replay. Keep the DSH event and all other command/recovery notices.
            if data.get('kind')=='success' and data.get('text')==(
                'Harness: Saved reasoning: minimal; requested reasoning: xhigh '
                '(request policy). Backend enforcement is provider-dependent.'
            ):return False
            self.messages.append(('DSH',data.get('text') or ('Command completed.' if data.get('kind')=='success' else 'Command failed.')))
            return True
        if kind=='assistant/chunk':
            chunk=data.get('chunk',{})
            if chunk.get('type')=='text-delta':self.partial+=chunk.get('text','');return True
            if chunk.get('type')=='reasoning-delta':
                self.add_reasoning(chunk.get('text',''));self.set_status('Thinking…');return True
        elif kind=='assistant/message':
            if any(p.get('type')=='tool-call' and p.get('name') in ('resonant_voice_reply','resonant_voice_demo') for p in data.get('message',{}).get('content',[])):
                self.partial='';return True
            reasoning='\n'.join(p.get('text','') for p in data.get('message',{}).get('content',[]) if p.get('type')=='reasoning')
            if reasoning:self.add_reasoning(reasoning,replace=True)
            self.reasoning_index=None
            text='\n'.join(p.get('text','') for p in data.get('message',{}).get('content',[]) if p.get('type')=='text')
            if text:
                self.message_events[len(self.messages)]=event
                self.messages.append(('Augmentor',text))
            self.partial='';return True
        elif kind=='tool/call':self.set_status('Using '+str(data.get('name','a tool'))[:60])
        elif kind=='turn/end':
            self.reasoning_index=None
            reason=data.get('reason',{}).get('kind')
            if reason=='max-tokens':
                self.set_status('Output limit — review result')
                self.messages.append(('Status','This turn reached a model output limit. Any recovery is recorded above. Check the deliverables; this end-of-turn does not establish task completion.'))
                return True
            self.set_status('Stopped' if reason=='aborted' else 'Interrupted' if reason=='interrupted' else 'Ready')
            if reason=='interrupted':self.messages.append(('Status',data.get('message','Runtime interrupted.')));return True
        elif kind=='session/title':
            title=data.get('title')
            if title:self.title_text=title;self.title.setText(title)
        return False

    def on_event(self,event):
        if self.voice_dialog and event.get('seq') not in self.seen_events:self.voice_dialog.observe(event)
        if self.fold_event(event) and not self.render_timer.isActive():self.render_timer.start()

    def on_problem(self,message):
        self.update_controls()
        self.rendered_messages=None
        self.set_status('Needs attention');self.messages.append(('Status',message));self.render_messages()

    def toggle_save(self):
        if self.controller:self.controller.toggle_saved()

    def open_history(self):
        if self.controller:HistoryDialog(self).exec()

    def open_pi(self):
        if self.controller and getattr(self.controller,'harness','pi')=='dsh':
            QDesktopServices.openUrl(QUrl(self.controller.client.base));return
        if self.controller:ModelsDialog(self).exec()

    def rename_chat(self):
        if not self.controller or not self.controller.session:return
        self.rename_session=self.controller.session
        self.title_editor.setText(self.title_text)
        self.title_stack.setCurrentWidget(self.title_editor)
        self.title_editor.setFocus();self.title_editor.selectAll()

    def cancel_inline_title(self):
        self.rename_session=None
        self.title_stack.setCurrentWidget(self.title)

    def save_inline_title(self):
        title=self.title_editor.text().strip();session=self.rename_session
        self.cancel_inline_title()
        if title and self.controller and session==self.controller.session and title!=self.title_text:
            self.controller.rename(title)

    def open_access(self):
        if self.controller:AccessDialog(self).exec()

    def open_settings(self):
        self.shortcut_dialog=SettingsDialog(self)
        self.shortcut_dialog.exec()
        self.shortcut_dialog=None

    def open_menu(self):
        menu=QMenu(self)
        menu.addAction('Settings',self.open_settings).setEnabled(bool(self.controller))
        menu.addAction('Colors & skins',self.open_appearance)
        menu.addAction('Prompt library',self.open_prompt_library).setEnabled(bool(self.controller))
        menu.addAction('Connect a model',self.open_setup).setEnabled(bool(self.controller))
        menu.addAction('Models & providers',self.open_pi).setEnabled(bool(self.controller))
        menu.addAction('Versions & updates',self.open_updates).setEnabled(bool(self.controller))
        menu.addAction('Approval mode',self.open_access).setEnabled(bool(self.controller))
        menu.addAction('About & licenses',lambda:LicensesDialog(self).exec())
        menu.addSeparator();menu.addAction('Quit Augmentor',self.close)
        menu.exec(self.more_button.mapToGlobal(self.more_button.rect().bottomLeft()))

    def open_updates(self):
        if self.controller:UpdatesDialog(self).exec()

    def open_appearance(self):
        if self.appearance_dialog is not None:
            self.appearance_dialog.show();self.appearance_dialog.raise_();self.appearance_dialog.activateWindow();return
        dialog=AppearanceDialog(self.preferences.values,self)
        # A modeless tool keeps the parent enabled and avoids modal-parent dimming.
        dialog.setWindowFlag(Qt.WindowType.Tool,True)
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.changed.connect(self.apply_appearance)
        dialog.finished.connect(lambda _:setattr(self,'appearance_dialog',None))
        self.appearance_dialog=dialog
        dialog.show();dialog.raise_();dialog.activateWindow()

    def open_prompt_library(self):
        if self.controller:PromptLibraryDialog(self).exec()

    def refresh_shared_appearance(self):
        # Shared colour changes never replace per-window placement, model or draft.
        if self.preferences_timer.isActive() or (self.appearance_dialog and self.appearance_dialog.isVisible()):return
        latest=Preferences().values
        keys=('theme','hue','brightness','accent_hue','accent_brightness','format_colours')
        changed={key:latest[key] for key in keys if latest[key]!=self.preferences.values[key]}
        if changed:self.apply_appearance(changed)

    def apply_appearance(self,values):
        self.preferences.values.update(values);v=self.preferences.values
        dark=v['theme']=='dark'
        light=(.12 if dark else .92)+v['brightness']/150
        self.background=QColor.fromHslF(v['hue']/360,v.get('saturation',48)/100*.5625,max(.025,min(.99,light)))
        self.user_bubble=QColor.fromHslF(v['hue']/360,v.get('saturation',48)/100*(.23/.48),min(.995,max(.025,light)+(.09 if dark else .045)))
        self.transcript.bubble_color=self.user_bubble
        self.background_alpha=round(255*v['opacity']/100);self.background.setAlpha(self.background_alpha)
        self.accent=QColor.fromHslF(v['accent_hue']/360,v.get('saturation',48)/100,max(.15,min(.9,(.73 if dark else .30)+v['accent_brightness']/150)))
        self.voice_button.configure(self.accent,v['animation'])
        scenic=v.get('background') in ('blossom-lake','uploaded')
        text=('#fff0e3' if dark else '#243840') if scenic else ('#edf3f3' if dark else '#152b2c')
        reading=f'rgba({self.background.red()},{self.background.green()},{self.background.blue()},{155 if dark else 205})' if scenic else 'transparent'
        self.transcript.setStyleSheet(f'QTextBrowser {{background:{reading};border:0;border-radius:12px;padding:8px;}}' if scenic else 'QTextBrowser {background:transparent;border:0;padding:2px;}')
        solid=QColor(self.background);solid.setAlpha(255)
        field=solid.lighter(125) if dark else solid.darker(105)
        self.composer.roll_colours=(QColor(field),QColor(text),QColor(self.accent))
        self.transcript.menu_style=f'QMenu {{background:{solid.name()};color:{text};border:1px solid {self.accent.name()};padding:4px;}} QMenu::item {{padding:6px 18px;background:transparent;}} QMenu::item:selected {{background:{self.accent.name()};color:{solid.name()};}} QMenu::item:disabled {{color:#879493;}}'

        self.setStyleSheet(f"""
          QWidget {{ color:{text};font-family:'DejaVu Sans';font-size:13px; }}
          QDialog,QMenu,QScrollArea,QWidget#appearanceControls {{ background:{solid.name()}; }}
          QLabel,QFrame {{ background:transparent; }}
          QPushButton {{ background:rgba(127,150,150,24);border:1px solid rgba(127,160,155,70);border-radius:8px;padding:7px 10px; }}
          QPushButton:hover,QPushButton:checked {{ background:{self.accent.name()};color:{solid.name()}; }}
          QPushButton:disabled {{ color:rgba(127,150,150,150); }}
          QTextEdit,QPlainTextEdit,QLineEdit,QListWidget,QComboBox,QSpinBox {{ background:{field.name()};border:1px solid rgba(127,160,155,70);border-radius:9px;padding:7px;selection-background-color:{self.accent.name()};selection-color:{solid.name()}; }}
          QTabWidget::pane {{ background:{solid.name()};border:1px solid rgba(127,160,155,70);border-radius:8px; }}
          QTabWidget > QWidget > QWidget {{ background:{solid.name()}; }}
          QTabBar::tab {{ background:{field.name()};padding:7px 12px; }}
          QTabBar::tab:selected {{ background:{self.accent.name()};color:{solid.name()}; }}
          QListWidget::item {{ padding:8px 5px; }}
          QListWidget::item:selected {{ background:{self.accent.name()};color:{solid.name()};border-radius:6px; }}
          QSlider::groove:horizontal {{ height:4px;background:{field.name()};border-radius:2px; }}
          QSlider::handle:horizontal {{ width:14px;margin:-5px 0;background:{self.accent.name()};border-radius:7px; }}
          QScrollBar:vertical {{ background:transparent;width:10px; }}
          QScrollBar::handle:vertical {{ background:rgba(127,160,155,150);min-height:25px;border-radius:5px; }}
          QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{ height:0; }}
        """)
        for button in (self.new_button,self.save_button,self.history_button,self.compact_button,self.more_button,self.hide_button):
            button.setStyleSheet(f'QPushButton {{padding:0;font-size:15px;border:0;background:transparent;color:{text};}} QPushButton:hover {{background:rgba(127,150,150,55);color:{text};}} QPushButton:disabled {{color:#879493;}}')
        self.pin_button.setStyleSheet(f'QPushButton {{padding:0;border:0;font-size:15px;}} QPushButton:checked {{background:{self.accent.name()};color:{solid.name()};border-radius:6px;}}')
        self.model_picker.setStyleSheet(f'QPushButton {{text-align:left;border:0;background:transparent;padding:0;font-size:11px;color:{text};}} QPushButton:hover,QPushButton:pressed,QPushButton:focus {{background:transparent;color:{text};}} QPushButton:disabled {{color:rgba(127,150,150,150);}}')
        self.composer.prompt_menu.setStyleSheet(f'QListWidget {{background:{solid.name()};color:{text};border:1px solid {self.accent.name()};border-radius:10px;padding:4px;}} QListWidget::item {{padding:7px;}} QListWidget::item:selected {{background:{self.accent.name()};color:{solid.name()};border-radius:6px;}}')
        self.composer.fit()
        self.rendered_messages=None
        self.brand.setStyleSheet('font-size:13px;font-weight:600;padding-left:8px;color:'+self.accent.name())
        self.status.setStyleSheet('font-size:11px;color:'+self.accent.name())
        if v.get('background')=='uploaded':
            from .backgrounds import uploaded_butterfly_colours
            butterfly_palette=uploaded_butterfly_colours(v['background_image'])
        elif v.get('background')=='blossom-lake':
            from .scenery import landscape_butterfly_colours
            butterfly_palette=landscape_butterfly_colours()
        else:
            from .nature import ButterflySwarm
            butterfly_palette=ButterflySwarm.palette
        self.activity.configure(animated=v['animation'],enabled=v['flares'],effect=v.get('effect','plasma'),colours=butterfly_palette)
        self.orb.scenic=scenic;self.orb.dark=dark;self.orb.background_image=v.get('background_image','')
        self.orb.effect=v.get('effect','plasma');self.orb.accent=QColor(self.accent);self.orb.background=QColor(self.background);self.orb.set_animated(v['animation'])
        if getattr(self,'touch_layout',None):self.touch_layout.style()
        self.preferences_timer.start();self.update()
        if self.messages or self.partial:self.render_messages()

    def set_background_opacity(self,value):
        self.apply_appearance({'opacity':value})

    def toggle_pin(self):
        self.preferences.values['pinned']=not self.preferences.values['pinned'];self.pin_button.setChecked(self.preferences.values['pinned']);self.preferences_timer.start();self.apply_pin()

    def apply_pin(self):
        if QApplication.platformName() == 'cocoa':
            from .macos_windows import pin_spaces
            try:pin_spaces(self,self.preferences.values['pinned'])
            except (OSError,RuntimeError):self.set_status('Workspace pin could not be applied')
            return
        if QApplication.platformName() not in ('offscreen','minimal') and pin_kwin(self.preferences.values['pinned']):return
        if QApplication.platformName() not in ('xcb','x11'):
            return
        pinned=self.preferences.values['pinned'];wid=hex(int(self.winId()))
        try:
            if pinned:
                subprocess.run(['wmctrl','-ir',wid,'-t','-1'],check=True,timeout=2,capture_output=True)
                subprocess.run(['wmctrl','-ir',wid,'-b','add,sticky'],check=True,timeout=2,capture_output=True)
            else:
                desktops=subprocess.run(['wmctrl','-d'],check=True,timeout=2,capture_output=True,text=True).stdout
                current=next(line.split()[0] for line in desktops.splitlines() if '*' in line.split()[:2])
                subprocess.run(['wmctrl','-ir',wid,'-b','remove,sticky'],check=True,timeout=2,capture_output=True)
                subprocess.run(['wmctrl','-ir',wid,'-t',current],check=True,timeout=2,capture_output=True)
        except (OSError,subprocess.SubprocessError,StopIteration):self.set_status('Workspace pin could not be applied')

    def showEvent(self,event):
        super().showEvent(event);QTimer.singleShot(100,self.apply_pin)
        self.activity.sync()
        QTimer.singleShot(0,self.focus_composer)
        if self.hidden_geometry is not None:QTimer.singleShot(100,self.restore_saved_position)

    def toggle_compact(self):
        if self.voice_dialog or self.voice_opening:self.close_voice_panel()
        if self.morphing:return
        start=QRect(self.geometry());was_compact=self.compact
        snapshot=self.grab() if self.isVisible() and self.preferences.values['animation'] else None
        if not was_compact:self.expanded_size=self.size()
        self.compact=not was_compact
        # Collapse into the clicked header control; dragging the orb moves
        # the matching expansion anchor with it.
        if self.compact:
            anchor=self.compact_button.mapToGlobal(self.compact_button.rect().center())
            self.compact_anchor_offset=anchor-start.topLeft()
            origin=anchor-QPoint(51,51)
        else:
            origin=start.center()-getattr(self,'compact_anchor_offset',QPoint(self.expanded_size.width()-116,56))
        target=QRect(origin,QSize(104,104) if self.compact else self.expanded_size)
        self.clearMask();self.setMinimumSize(0,0);self.setMaximumSize(16777215,16777215)
        self.outer.setContentsMargins(*([0 if self.compact else self.activity.margin]*4))
        self.stack.setCurrentWidget(self.orb if self.compact else self.expanded)
        def finish():
            self.morphing=False;self.setGeometry(target)
            self.stack.currentWidget().show()
            if self.compact:
                self.setMaximumSize(104,104);self.setMask(QRegion(1,1,102,102,QRegion.RegionType.Ellipse))
            else:self.setMinimumSize(364,364);QTimer.singleShot(0,self.focus_composer)
            if getattr(self,'morph_surface',None):self.morph_surface.deleteLater();self.morph_surface=None
            self.resize_borders.update();self.sync_orb();self.activity.sync();self.apply_pin();self.update()
        if snapshot is None:finish();return
        from .surfaces import MorphSurface
        self.morphing=True;self.activity.sync()
        source_anchor=self.compact_anchor_offset if self.compact else QPoint(51,51)
        fixed_anchor=anchor if self.compact else start.center()
        orb_snapshot=None
        if self.compact:
            self.orb.resize(104,104);orb_snapshot=self.orb.grab();self.orb.hide()
        self.morph_surface=MorphSurface(self,snapshot,source_anchor,fixed_anchor,orb_snapshot);self.morph_surface.show();self.morph_surface.raise_()
        self.morph_animation=QVariantAnimation(self);self.morph_animation.setDuration(240)
        self.morph_animation.setStartValue(0.);self.morph_animation.setEndValue(1.)
        self.morph_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        def step(value):
            values=[round(a+(b-a)*value) for a,b in zip(start.getRect(),target.getRect())]
            self.setGeometry(QRect(*values));self.morph_surface.setGeometry(self.rect());self.morph_surface.progress=value;self.morph_surface.update()
        self.morph_animation.valueChanged.connect(step);self.morph_animation.finished.connect(finish);self.morph_animation.finished.connect(self.morph_animation.deleteLater);self.morph_animation.start()

    def orb_menu(self,point):
        menu=QMenu(self);menu.addAction('Expand conversation',self.toggle_compact)
        pin=menu.addAction('Follow all workspaces',self.toggle_pin);pin.setCheckable(True);pin.setChecked(self.preferences.values['pinned'])
        menu.addAction('Colors & skins',self.open_appearance)
        menu.addAction('Stop',self.stop);menu.addAction('Hide',self.hide);menu.addAction('Quit',self.close)
        menu.exec(self.orb.mapToGlobal(point))

    def surface_rect(self):
        margin=8 if self.compact else self.activity.margin
        return self.rect().adjusted(margin,margin,-margin,-margin)

    def paintEvent(self,event):
        if self.compact:return
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.activity.paint_backdrop(painter,self.surface_rect().adjusted(1,1,-1,-1),self.accent)
        painter.setBrush(self.background);edge=QColor(self.accent);edge.setAlpha(75);painter.setPen(edge)
        painter.drawRoundedRect(self.surface_rect().adjusted(1,1,-1,-1),20,20)
        if self.preferences.values.get('background') in ('blossom-lake','uploaded'):
            from .scenery import paint_landscape
            paint_landscape(painter,self.surface_rect().adjusted(1,1,-1,-1),
                            self.preferences.values['theme']=='dark',self.background_alpha/255,
                            encoded=self.preferences.values.get('background_image',''),tint=self.background)
        elif self.activity.effect in ("butterflies", "butterflies-large"):
            from .nature import paint_foliage
            paint_foliage(painter,self.surface_rect().adjusted(1,1,-1,-1),self.accent)

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton and self.surface_rect().contains(event.position().toPoint()) and event.position().y()<self.surface_rect().top()+54 and self.windowHandle():self.windowHandle().startSystemMove()
        super().mousePressEvent(event)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'resize_borders'):self.resize_borders.update()

    def on_interaction(self, frame):
        if frame['method'] == 'interaction/resolved':
            if not hasattr(self,'resolved_interactions'):self.resolved_interactions=set()
            self.resolved_interactions.add(frame['rpcId'])
            dialog=getattr(self,'interaction_dialogs',{}).get(frame['rpcId'])
            if dialog:dialog.reject()
            return
        if frame['rpcId'] in getattr(self,'resolved_interactions',set()):return
        payload = frame['payload']
        if frame['method'] == 'approval/requested':
            box = QMessageBox(self)
            box.setWindowTitle('Augmentor · approval')
            box.setTextFormat(Qt.TextFormat.PlainText)
            box.setText('Allow this action once?\n\n' + payload.get('toolName', 'Tool') + '\n' + payload.get('reason', ''))
            box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            box.setDefaultButton(QMessageBox.StandardButton.No)
            if not hasattr(self,'interaction_dialogs'):self.interaction_dialogs={}
            self.interaction_dialogs[frame['rpcId']]=box
            result = box.exec()
            self.interaction_dialogs.pop(frame['rpcId'],None)
            if frame['rpcId'] in getattr(self,'resolved_interactions',set()):return
            self.controller.answer(frame, {'sessionId': payload['sessionId'], 'approvalId': payload['approvalId'], 'outcome': 'allowed-once' if result == QMessageBox.StandardButton.Yes else 'rejected'})
        else:
            answers = []
            for question in payload.get('questions', []):
                dialog=QuestionDialog(question,self)
                if not hasattr(self,'interaction_dialogs'):self.interaction_dialogs={}
                self.interaction_dialogs[frame['rpcId']]=dialog
                accepted=dialog.exec()
                self.interaction_dialogs.pop(frame['rpcId'],None)
                if frame['rpcId'] in getattr(self,'resolved_interactions',set()):return
                if not accepted:
                    self.controller.stop()
                    return
                answers.append(dialog.answer())
            self.controller.answer(frame, {'sessionId': payload['sessionId'], 'answer': {'answers': answers}})

    def escape(self):
        if (self.voice_dialog or self.voice_opening) and self.voice_is_hands_free():
            self.close_voice_panel();return
        if self.voice_button.isDown() or (self.voice_dialog and self.voice_dialog.capture):
            self.voice_button.cancel_hold();return
        if self.controller and self.controller.running:
            self.controller.stop()
        else:
            self.close()

    def closeEvent(self, event):
        if self.voice_dialog or self.voice_input or self.voice_opening:self.close_voice_panel()
        if self.controller and getattr(self.controller,'repairing',False):
            event.ignore();return
        if self.controller and self.controller.running:
            self.close_pending = True
            self.controller.stop()
            self.set_status('Stopping before closing…')
            event.ignore()
            return
        if self.controller:
            self.controller.close()
        self.preferences.save()
        release_kwin()
        super().closeEvent(event)
        if self.controller:QApplication.instance().quit()

    @staticmethod
    def screen_layout():
        return [[s.name(),*s.geometry().getRect(),s.devicePixelRatio()] for s in QApplication.screens()]

    def remember_placement(self):
        self.hidden_layout=self.screen_layout()
        self.hidden_geometry=QRect(self.geometry())
        rect=self.hidden_geometry
        expanded=self.expanded_size if self.compact else self.size()
        self.preferences.values['placement']={'x':rect.x(),'y':rect.y(),'width':rect.width(),'height':rect.height(),'compact':self.compact,'expanded_width':expanded.width(),'expanded_height':expanded.height(),'screen_layout':self.hidden_layout,'halo_margin':self.activity.margin}
        self.preferences.save()

    def restore_placement(self):
        saved=dict(self.preferences.values.get('placement',{}))
        if not all(type(saved.get(k)) is int for k in ('x','y','width','height')):return
        # Old placements measured the panel itself; keep its size and position.
        if 'halo_margin' not in saved:
            padding=2*self.activity.margin
            for key in ('expanded_width','expanded_height'):
                if type(saved.get(key)) is int:saved[key]+=padding
            if not saved.get('compact'):
                saved['x']-=self.activity.margin;saved['y']-=self.activity.margin
                saved['width']+=padding;saved['height']+=padding
        self.hidden_layout=saved.get('screen_layout',self.screen_layout())
        if saved.get('compact') is True and not self.compact:self.toggle_compact()
        if self.compact:
            width=saved.get('expanded_width',424);height=saved.get('expanded_height',484)
            self.expanded_size=QSize(max(364,min(2000,width if type(width) is int else 424)),max(364,min(2000,height if type(height) is int else 484)))
        self.hidden_geometry=QRect(saved['x'],saved['y'],max(self.minimumWidth(),min(2000,saved['width'])),max(self.minimumHeight(),min(2000,saved['height'])))
        self.restore_saved_position()

    def restore_saved_position(self):
        if self.hidden_geometry is None or not self.isVisible():return
        target=QRect(self.hidden_geometry)
        # Qt/XWayland can expose gaps in scaled multi-monitor coordinates.
        # An unchanged screen layout must restore the exact saved rectangle.
        if self.hidden_layout==self.screen_layout():
            self.setGeometry(target);return
        screen=QApplication.screenAt(target.center()) or self.screen()
        area=screen.availableGeometry()
        target.setWidth(min(target.width(),area.width()));target.setHeight(min(target.height(),area.height()))
        target.moveLeft(max(area.left(),min(target.x(),area.right()-target.width()+1)))
        target.moveTop(max(area.top(),min(target.y(),area.bottom()-target.height()+1)))
        self.setGeometry(target)

    def hideEvent(self,event):
        if getattr(self,'voice_dialog',None) or getattr(self,'voice_opening',False):self.close_voice_panel()
        self.activity.timer.stop()
        self.remember_placement()
        self.hidden_dialogs=[d for d in self.findChildren(QDialog) if d.isVisible()]
        for dialog in self.hidden_dialogs:dialog.hide()
        super().hideEvent(event)

    def toggle_visibility(self):
        if self.shortcut_dialog and self.shortcut_dialog.capture_current():return
        if self.isVisible() and not self.isMinimized():self.hide()
        else:self.bring_forward()

    def focus_composer(self):
        if not self.isVisible() or self.compact:return
        if QApplication.activeModalWidget() or QApplication.activePopupWidget():return
        if any(dialog.isVisible() for dialog in self.findChildren(QDialog)):return
        self.composer.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def changeEvent(self,event):
        if event.type()==event.Type.ActivationChange and not self.isActiveWindow() and hasattr(self,'voice_button') and not self.voice_button.locked and not self.voice_button.hands_free:
            self.voice_button.cancel_hold()
        super().changeEvent(event)
        if hasattr(self,'activity'):self.activity.sync()

    def bring_forward(self):
        self.showNormal();self.restore_saved_position()
        self.raise_();self.activateWindow()
        for dialog in self.hidden_dialogs:
            dialog.show();dialog.raise_()
        self.hidden_dialogs=[]
        QTimer.singleShot(0,self.focus_composer)


def main():
    sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'services/lifecycle'))
    from lease import hold
    hold('desktop')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screenshot', type=Path, help='Save the app window only, then exit (for UI verification).')
    parser.add_argument('--voice', action='store_true', help='Open Resonant Voice in the existing desktop conversation.')
    parser.add_argument('--ensure-running', action='store_true', help='Start at login without toggling an existing window.')
    parser.add_argument('--compact', action='store_true', help='Open the circular activity view.')
    parser.add_argument('--preview', action='store_true', help='Open without connecting to a harness.')
    parser.add_argument('--onboarding-host', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--harness', choices=['pi','dsh'], help='Open the shared UI with this harness.')
    parser.add_argument('--instance', type=validate_name, default=current_name(), help='Named independent window (for example secondary); repeated launches toggle that window.')
    args = parser.parse_args()
    configure(args.instance)
    from .browser import refresh_accessibility_bus
    refresh_accessibility_bus()
    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName('Augmentor Agent')
    app.setWindowIcon(QIcon(str(Path(__file__).parent/'assets/augmentor.svg')))
    from .shortcuts import COMPONENT
    app.setDesktopFileName(COMPONENT.removesuffix('.desktop'))
    if not args.preview and not args.screenshot:
        runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/tmp/augmentor-linux-pi-{os.getuid()}'))
        runtime.mkdir(mode=0o700, exist_ok=True)
        socket_name = str(runtime / (ipc_basename()+'.sock'))
        client = QLocalSocket()
        client.connectToServer(socket_name)
        if client.waitForConnected(300):
            client.write(b'maintenance.status' if args.onboarding_host or args.ensure_running else b'voice' if args.voice else ('harness:'+args.harness).encode() if args.harness else b'toggle')
            client.waitForBytesWritten(500)
            return 0
        app.instance_lock = QLockFile(str(runtime / (ipc_basename()+'.lock')))
        if not app.instance_lock.tryLock(200):
            return 1
        QLocalServer.removeServer(socket_name)
        app.instance_server = QLocalServer()
        app.instance_server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        if not app.instance_server.listen(socket_name):
            return 1
    window = Window(preview=args.preview or bool(args.screenshot),harness=args.harness)
    if hasattr(app, 'instance_server'):
        def activate():
            client = app.instance_server.nextPendingConnection()
            if client:
                if not client.bytesAvailable():client.waitForReadyRead(200)
                command=bytes(client.readAll()).decode()
                if command in ('maintenance.status','maintenance.close','maintenance.recover'):
                    running=bool(window.controller and window.controller.running)
                    busy=running or window.composer.improving or window.voice_opening or window.voice_input is not None or bool(window.voice_dialog and window.voice_dialog.capture) or any(dialog.isVisible() for dialog in window.findChildren(QDialog))
                    controller = window.controller
                    accepted = not busy
                    if command == 'maintenance.recover':
                        accepted = bool(controller and controller.repair_connection())
                    client.write(json.dumps({'pid':os.getpid(),'running':running,'busy':busy,'accepted':accepted,'onboardingProtocol':1,'modelReady':bool(window.model_picker.currentData()),
                        'online':bool(controller and controller.online), 'repairing':bool(controller and controller.repairing),
                        'lastError':controller.last_connection_error if controller else '',
                        'sessionRestoreError':controller.session_restore_error if controller else '',
                        'buildRoot':str(Path(__file__).resolve().parents[3]),
                        'voiceAvailable':hasattr(window, 'voice_button'),
                        'voiceTiming':dict(window.voice_dialog.timings) if window.voice_dialog else None,
                        'voiceBufferStarvations':window.voice_dialog.playback_buffer.starvations if window.voice_dialog else 0,
                        'voiceOutputUnderflows':window.voice_dialog.output_underflows if window.voice_dialog else 0}).encode()+b'\n')
                    client.waitForBytesWritten(500)
                    if command=='maintenance.close' and not busy:
                        window.close()
                elif command.startswith('onboarding:'):
                    try:
                        from .onboarding import start
                        data=json.loads(command[len('onboarding:'):]);result=start(window,data.get('topic'),data.get('requestId'))
                        response={'ok':True,'result':result}
                    except Exception as error:response={'ok':False,'error':str(error)}
                    client.write(json.dumps(response).encode()+b'\n');client.waitForBytesWritten(500)
                elif command=='voice':window.request_voice()
                elif command.startswith('harness:'):
                    window.switch_harness(command.split(':',1)[1])
                    if not window.isVisible():window.toggle_visibility()
                    window.bring_forward()
                else:window.toggle_visibility()
                client.disconnectFromServer()
                client.deleteLater()
        app.instance_server.newConnection.connect(activate)
    window.bring_forward()
    if args.voice:QTimer.singleShot(0,window.request_voice)
    if sys.platform=='darwin' and not args.preview and not args.screenshot:
        from .macos_shortcuts import initialize
        initialize(window)
    if args.compact: window.toggle_compact()
    if args.screenshot:
        def capture():
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            ok = window.grab().save(str(args.screenshot))
            app.exit(0 if ok else 1)
        QTimer.singleShot(200, capture)
    return app.exec()
