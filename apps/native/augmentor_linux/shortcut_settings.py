# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Two independently editable launcher shortcuts, in either window's Settings."""
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QKeySequenceEdit
from PySide6.QtGui import QKeySequence
from .shortcuts import current_keys,save_shortcut,display_key
from .instances import current_name
from .settings_icons import settings_icon


class ShortcutSettings(QWidget):
    def __init__(self,window):
        super().__init__(window);self.owner=window;self.rows={}
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        for name,label in [('main','First agent'),('secondary','Second agent')]:
            heading=QLabel(label+' — open / hide');layout.addWidget(heading)
            current=QLabel('Reading shortcut…');layout.addWidget(current)
            row=QHBoxLayout();editor=QKeySequenceEdit();editor.setMaximumSequenceLength(1);editor.setClearButtonEnabled(True)
            editor.setObjectName('shortcut-'+name);editor.setAccessibleName(label+' shortcut')
            button=QPushButton('Save');button.setAccessibleName('Save '+label.lower()+' shortcut');button.setIcon(settings_icon('keyboard',window.accent));button.setEnabled(False)
            row.addWidget(editor,1);row.addWidget(button);layout.addLayout(row)
            note=QLabel();note.setWordWrap(True);layout.addWidget(note)
            self.rows[name]={'editor':editor,'button':button,'current':current,'note':note,'keys':None,'saving':False}
            editor.keySequenceChanged.connect(lambda sequence,n=name:self.changed(n,sequence))
            button.clicked.connect(lambda _,n=name:self.save(n))
        note=QLabel('Click a field and press the combination you want, then Save. Fn is handled by your keyboard: the detected key may have another name. Each shortcut opens or hides its own window.');note.setWordWrap(True);layout.addWidget(note)
        self.refresh()

    def refresh(self):
        def read():
            result={}
            for name in self.rows:
                try:result[name]=(current_keys(name),None)
                except Exception as error:result[name]=(None,str(error))
            return result
        def loaded(result):
            for name,(keys,error) in result.items():
                row=self.rows[name];row['keys']=keys
                row['current'].setText('Current: '+(', '.join(display_key(key) for key in keys) or 'Unassigned') if keys is not None else 'Shortcut unavailable')
                row['note'].setText(error or '')
                self.changed(name,row['editor'].keySequence())
        self.owner.call_in_background(read,loaded)

    def changed(self,name,sequence):
        row=self.rows[name];row['button'].setEnabled(row['keys'] is not None and not sequence.isEmpty() and not row['saving'])

    def save(self,name):
        row=self.rows[name];sequence=QKeySequence(row['editor'].keySequence());row['saving']=True;row['button'].setEnabled(False);row['note'].setText('Saving…')
        def work():
            try:return save_shortcut(sequence,name),None
            except Exception as error:return None,str(error)
        def done(result):
            key,error=result;row['saving']=False
            if error:row['note'].setText(error);self.changed(name,row['editor'].keySequence());return
            row['keys']=[key];row['current'].setText('Current: '+display_key(key));row['note'].setText('Saved. Press the shortcut to test this window.');row['editor'].clear()
        self.owner.call_in_background(work,done)

    def capture_current(self):
        # When this window's assigned key is intercepted by KDE, record that
        # actual binding in the focused editor instead of hiding the dialog.
        keys=self.rows[current_name() if current_name() in self.rows else 'main']['keys']
        for row in self.rows.values():
            if self.isVisible() and row['editor'].hasFocus() and keys:
                row['editor'].setKeySequence(QKeySequence(keys[0]));return True
        return False
