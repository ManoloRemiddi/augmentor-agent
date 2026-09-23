# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""A wrapped, scrollable draft that grows from one to five visual lines."""
import math
import uuid
from PySide6.QtCore import Qt, QTimer, QEvent, Signal, QPoint
from PySide6.QtWidgets import QTextEdit, QPushButton, QToolTip
from PySide6.QtGui import QTextCursor, QColor
from .prompt_animation import LetterRoll

class Composer(QTextEdit):
    submit_requested = Signal()
    improve_requested = Signal()
    improvement_changed = Signal()
    improvement_result = Signal(str, object, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)
        self.setPlaceholderText('Ask Augmentor…')
        self.setAccessibleName('Message draft')
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.document().setDocumentMargin(2)
        self.document().documentLayout().documentSizeChanged.connect(self.fit)
        self.textChanged.connect(self.fit)
        self.preedit_active=False
        self.improving=False;self.improvement_available=False;self.improvement_id=None;self.improvement_original='';self.roll=None;self.improvement_undo=None
        self.roll_colours=(QColor('#1e3033'),QColor('#edf3f3'),QColor('#a6d6c8'))
        self.setViewportMargins(0,0,47,0)
        self.improve_button=QPushButton('✦',self);self.improve_button.setFixedSize(24,24)
        self.improve_button.setAccessibleName('Improve prompt');self.improve_button.setToolTip('Improve prompt')
        self.improve_button.setStyleSheet('QPushButton {padding:0;border:0;background:transparent;border-radius:5px;font-size:16px;} QPushButton:hover {background:rgba(127,150,150,45);}')
        self.improve_button.clicked.connect(self.improve_clicked)
        self.textChanged.connect(self.draft_changed)
        self.improvement_result.connect(self.receive_improvement)
        from .prompts import PromptMenu, PromptCatalog
        self.prompt_menu=PromptMenu(self,PromptCatalog(parent=self))
        self.textChanged.connect(self.prompt_menu.refresh)
        self.cursorPositionChanged.connect(self.prompt_menu.refresh)
        self.fitting=False
        self.fit();self.refresh_improve_button()

    def improve_clicked(self):
        if self.improving:self.cancel_improvement()
        elif self.improvement_undo:
            original,_=self.improvement_undo;self.improvement_undo=None
            cursor=self.textCursor();cursor.beginEditBlock();cursor.select(QTextCursor.SelectionType.Document);cursor.insertText(original);cursor.endEditBlock();self.setTextCursor(cursor);self.setFocus();self.refresh_improve_button()
        else:self.improve_requested.emit()

    def refresh_improve_button(self):
        self.improve_button.setEnabled(self.improving or bool(self.improvement_undo) or (self.improvement_available and bool(self.toPlainText().strip()) and not self.preedit_active))
        self.improve_button.setText("×" if self.improving else "↶" if self.improvement_undo else "✦")
        label="Cancel prompt improvement" if self.improving else "Undo prompt improvement" if self.improvement_undo else "Improve prompt"
        self.improve_button.setToolTip(label);self.improve_button.setAccessibleName(label)

    def draft_changed(self):
        if self.improvement_undo and self.toPlainText()!=self.improvement_undo[1]:self.improvement_undo=None
        if self.improving and self.toPlainText()!=self.improvement_original:self.cancel_improvement()
        self.refresh_improve_button()

    def begin_improvement(self):
        self.improvement_id=uuid.uuid4().hex;self.improvement_original=self.toPlainText();self.improving=True
        self.prompt_menu.hide();self.roll=LetterRoll(self)
        self.roll.background,self.roll.foreground,self.roll.accent=self.roll_colours
        self.roll.raise_();self.refresh_improve_button();self.improvement_changed.emit()
        return self.improvement_id

    def cancel_improvement(self):
        self.improvement_id=None;self.improving=False
        if self.roll:self.roll.timer.stop();self.roll.hide();self.roll.deleteLater();self.roll=None
        self.refresh_improve_button();self.improvement_changed.emit()

    def receive_improvement(self,identity,result,error):
        if identity!=self.improvement_id or not self.improving:return
        if self.toPlainText()!=self.improvement_original:self.cancel_improvement();return
        if error or not isinstance(result,dict) or result.get("kind")!="rewrite":
            self.cancel_improvement()
            message=error or (result or {}).get("text","Could not improve the prompt.")
            self.improve_button.setToolTip(message);QToolTip.showText(self.improve_button.mapToGlobal(QPoint(0,0)),message,self.improve_button)
            return
        replacement=result.get("text","")
        if not isinstance(replacement,str) or not replacement.strip():self.cancel_improvement();return
        self.roll.settle(replacement)
        QTimer.singleShot(700,lambda:self.commit_improvement(identity,replacement))

    def commit_improvement(self,identity,text):
        if identity!=self.improvement_id or self.toPlainText()!=self.improvement_original:return
        original=self.improvement_original
        self.cancel_improvement()
        cursor=self.textCursor();cursor.beginEditBlock();cursor.select(QTextCursor.SelectionType.Document);cursor.insertText(text);cursor.endEditBlock();self.setTextCursor(cursor)
        self.improvement_undo=(original,text);self.refresh_improve_button();self.setFocus()

    def fit(self, *_):
        if getattr(self,'fitting',False):return
        self.fitting=True
        try:
            line=self.fontMetrics().lineSpacing()
            # Viewport margins include stylesheet padding and the frame.
            chrome=self.height()-self.viewport().height()
            content=self.document().size().height()
            minimum=line+2*self.document().documentMargin()
            maximum=5*line+2*self.document().documentMargin()
            self.setFixedHeight(max(58 if getattr(self,'touch_mode',False) else 0,math.ceil(max(minimum,min(maximum,content))+chrome)))
        finally:self.fitting=False

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,"improve_button"):
            self.improve_button.move(self.width()-self.improve_button.width()-22,5);self.improve_button.raise_()
        if getattr(self,"roll",None):self.roll.resize(self.viewport().size())
        QTimer.singleShot(0,self.fit)

    def inputMethodEvent(self,event):
        self.preedit_active=bool(event.preeditString())
        super().inputMethodEvent(event)

    def keyPressEvent(self,event):
        if self.improving:
            if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter):event.accept();return
            if event.key()==Qt.Key.Key_Escape:self.cancel_improvement();event.accept();return
            if event.text() or event.key() in (Qt.Key.Key_Backspace,Qt.Key.Key_Delete):self.cancel_improvement()
        if self.prompt_menu.key(event):event.accept();return
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter) and event.modifiers() in (Qt.KeyboardModifier.NoModifier,Qt.KeyboardModifier.ControlModifier) and not self.preedit_active:
            if not event.isAutoRepeat():self.submit_requested.emit()
            event.accept();return
        super().keyPressEvent(event)

    def event(self,event):
        if event.type()==QEvent.Type.ShortcutOverride and getattr(self,'improving',False) and event.key()==Qt.Key.Key_Escape:event.accept();return True
        if event.type()==QEvent.Type.ShortcutOverride and hasattr(self,'prompt_menu') and self.prompt_menu.isVisible() and event.key()==Qt.Key.Key_Escape:
            event.accept();return True
        return super().event(event)

    def focusInEvent(self,event):
        super().focusInEvent(event)
        self.prompt_menu.refresh()

    def focusOutEvent(self,event):
        if hasattr(self,'prompt_menu'):self.prompt_menu.hide()
        super().focusOutEvent(event)

    def hideEvent(self,event):
        self.prompt_menu.hide();super().hideEvent(event)
