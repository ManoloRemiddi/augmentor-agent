# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Nonblocking slash completion from the shared Pi Prompt library plugin."""
import re
import threading
import time
from PySide6.QtCore import Qt, QPoint, QObject, QTimer, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication, QListWidget, QListWidgetItem
from .prompt_client import PromptClient
from .templates import expand_template
from .pi_client import ContractError

CLIPBOARD_TOKEN='[clipboard]'


def expand_clipboard(content):
    """Read one plain-text snapshot when inserting a template, never on save/send."""
    if CLIPBOARD_TOKEN not in content:return content
    copied=QApplication.clipboard().text()
    return expand_template(content,copied)


class PromptCatalog(QObject):
    """Keep networking off the Qt thread and revalidate while the picker is open."""
    changed = Signal()
    completed = Signal(object, str, int)

    def __init__(self, client=None, parent=None):
        super().__init__(parent)
        self.client=client or PromptClient()
        self.prompts=[]; self.loaded=False; self.pending=False; self.error=''; self.last_read=0; self.generation=0
        self.completed.connect(self.receive)

    def refresh(self):
        if self.pending or time.monotonic()-self.last_read < 1:return
        self.pending=True
        generation=self.generation
        def read():
            try:
                section=self.client.setting('prompt-library')
                if section is None:raise ContractError('Prompt library is unavailable.')
                prompts=section['value'].get('prompts',[])
                self.completed.emit(prompts,'',generation)
            except Exception as exc:
                try:self.completed.emit(None,'Cannot load shared prompts. '+str(exc),generation)
                except RuntimeError:pass # The window was disposed during shutdown.
        threading.Thread(target=read,daemon=True).start()

    def replace(self,prompts):
        # A library save is newer than any in-flight picker refresh.
        self.generation+=1
        self.receive(prompts,'',self.generation)

    def receive(self,prompts,error,generation):
        if generation!=self.generation:return
        self.pending=False;self.last_read=time.monotonic();self.error=error
        if prompts is not None:self.prompts=prompts;self.loaded=True
        self.changed.emit()


def slash_query(text, position):
    match = re.fullmatch(r'/([a-zA-Z0-9_-]*)', text[:position])
    return match.group(1).lower() if match else None


def matching_prompts(prompts, query):
    return sorted((p for p in prompts if query in p['name']),
                  key=lambda p: (not p['name'].startswith(query), p['name']))


class PromptMenu(QListWidget):
    def __init__(self, composer, catalog):
        super().__init__(composer.window())
        self.composer, self.catalog = composer, catalog
        catalog.changed.connect(self.refresh)
        self.poll=QTimer(self);self.poll.setInterval(1500)
        self.poll.timeout.connect(lambda:self.refresh() if self.isVisible() else None)
        self.poll.start()
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAccessibleName('Saved prompts')
        self.setStyleSheet('QListWidget {background:#243537;color:#edf3f3;border:1px solid #607d7d;border-radius:10px;padding:4px;} QListWidget::item {padding:7px;} QListWidget::item:selected {background:#426760;color:#ffffff;border-radius:6px;}')
        self.itemClicked.connect(lambda _:self.choose())
        self.items=[]; self.dismissed=None

    def refresh(self):
        editor=self.composer; query=slash_query(editor.toPlainText(),editor.textCursor().position())
        if query is None or editor.preedit_active or getattr(editor,'improving',False) or not editor.hasFocus():
            self.hide(); self.dismissed=None; return
        if self.dismissed == editor.toPlainText():return
        selected=self.currentItem().data(Qt.ItemDataRole.UserRole) if self.currentItem() else None
        self.catalog.refresh()
        self.clear(); self.items=[]
        if not self.catalog.error:
            self.items=matching_prompts(self.catalog.prompts,query)
            for item in self.items:
                row=QListWidgetItem('/'+item['name']+'  ·  Tab to insert\n'+' '.join(item['content'].split())[:75])
                row.setToolTip(item['content']);row.setData(Qt.ItemDataRole.UserRole,item['id']);self.addItem(row)
        if not self.items:
            self.addItem(self.catalog.error or ('No matching prompts' if self.catalog.prompts else 'Add prompts in More → Prompt library' if self.catalog.loaded else 'Loading prompts…'))
        self.setCurrentRow(next((i for i,p in enumerate(self.items) if p["id"]==selected),0))
        self.setFixedWidth(max(260,editor.width()))
        self.setFixedHeight(min(230,max(70,self.sizeHintForRow(0)*min(5,self.count())+18)))
        point=editor.mapToGlobal(QPoint(0,0));area=editor.screen().availableGeometry()
        x=max(area.left(),min(point.x(),area.right()-self.width()+1))
        y=point.y()-self.height()-5
        if y < area.top(): y=min(area.bottom()-self.height()+1,editor.mapToGlobal(QPoint(0,editor.height())).y()+5)
        self.move(x,max(area.top(),y));self.show();self.raise_()

    def choose(self):
        index=self.currentRow();editor=self.composer
        if not (0<=index<len(self.items)):return
        cursor=editor.textCursor();start=cursor.position()
        if slash_query(editor.toPlainText(),start) is None:return
        try:content=expand_clipboard(self.items[index]['content'])
        except ValueError as error:
            editor.window().set_status(str(error))
            return
        text=editor.toPlainText()
        while start<len(text) and re.match(r'[a-zA-Z0-9_-]',text[start]):start+=1
        cursor.setPosition(0);cursor.setPosition(start,QTextCursor.MoveMode.KeepAnchor)
        cursor.beginEditBlock();cursor.insertText(content);cursor.endEditBlock()
        editor.setTextCursor(cursor);self.hide();editor.setFocus()

    def key(self,event):
        if not self.isVisible() or event.modifiers()!=Qt.KeyboardModifier.NoModifier:return False
        if event.key() in (Qt.Key.Key_Up,Qt.Key.Key_Down):
            delta=1 if event.key()==Qt.Key.Key_Down else -1
            self.setCurrentRow((self.currentRow()+delta)%self.count());return True
        # Enter always submits the draft; Tab/click explicitly expands a prompt.
        # This keeps same-named harness commands reachable without renaming prompts.
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter):
            self.hide();return False
        if event.key()==Qt.Key.Key_Tab:
            if not event.isAutoRepeat():self.choose()
            return True
        if event.key()==Qt.Key.Key_Escape:
            self.dismissed=self.composer.toPlainText();self.hide();return True
        return False
