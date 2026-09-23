# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Explicit answers to agent questions, including multiple selections and reviews."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QLabel,QTextEdit,QListWidget,
    QListWidgetItem,QAbstractItemView,QDialogButtonBox)


class QuestionDialog(QDialog):
    def __init__(self, question, parent=None):
        super().__init__(parent)
        self.question=question
        self.setWindowTitle(question.get('header') or 'Augmentor question')
        self.resize(480,400)
        layout=QVBoxLayout(self)
        label=QLabel(question.get('question',''));label.setTextFormat(Qt.TextFormat.PlainText);label.setWordWrap(True)
        layout.addWidget(label)
        if question.get('detail'):
            detail=QTextEdit();detail.setReadOnly(True);detail.setPlainText(question['detail'])
            detail.setAccessibleName('Question details');layout.addWidget(detail)
        self.options=QListWidget();self.options.setAccessibleName('Answer choices')
        self.options.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection if question.get('multiSelect') else QAbstractItemView.SelectionMode.SingleSelection)
        for option in question.get('options',[]):
            text=option['label']+('\n'+option['description'] if option.get('description') else '')
            item=QListWidgetItem(text);item.setData(Qt.ItemDataRole.UserRole,option['label']);self.options.addItem(item)
        if self.options.count():
            layout.addWidget(QLabel('Select all that apply.' if question.get('multiSelect') else 'Select one option, or write an answer.'))
            layout.addWidget(self.options)
        else:self.options.hide()
        self.custom=QTextEdit();self.custom.setAcceptRichText(False);self.custom.setAccessibleName('Custom answer')
        self.custom.setPlaceholderText('Write an answer…');self.custom.setPlainText(question.get('prefill') or '')
        layout.addWidget(self.custom)
        self.buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept);self.buttons.rejected.connect(self.reject);layout.addWidget(self.buttons)
        self.options.itemSelectionChanged.connect(self.validate);self.custom.textChanged.connect(self.validate)
        self.validate()

    def validate(self):
        text=self.custom.toPlainText()
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            len(text)<=16000 and bool(self.options.selectedItems() or text.strip()))

    def answer(self):
        result={'id':self.question['id'],'selected':[item.data(Qt.ItemDataRole.UserRole) for item in self.options.selectedItems()]}
        text=self.custom.toPlainText()
        if text.strip():result['custom']=text
        return result
