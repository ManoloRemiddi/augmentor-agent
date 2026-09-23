# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One-click recovery with worker-thread progress and a durable visible outcome."""
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPlainTextEdit, QPushButton


class RecoveryDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.controller = owner.controller
        self.active = False
        self.setWindowTitle('Recover connection')
        self.setMinimumSize(500, 340)
        layout = QVBoxLayout(self)
        note = QLabel('Checks your connection, starts a stopped runtime, and repairs verified history conflicts with a backup. Your messages will not be resent.')
        note.setWordWrap(True); layout.addWidget(note)
        self.progress = QPlainTextEdit()
        self.progress.setReadOnly(True)
        self.progress.setAccessibleName('Recovery progress')
        layout.addWidget(self.progress)
        self.retry = QPushButton('Run recovery')
        self.retry.clicked.connect(self.start); layout.addWidget(self.retry)
        self.close_button = QPushButton('Close')
        self.close_button.clicked.connect(self.accept); layout.addWidget(self.close_button)
        self.controller.repair_progress.connect(self.progress.appendPlainText)
        self.controller.repair_finished.connect(self.finished_repair)
        self.finished.connect(self.disconnect_controller)
        # Clicking Settings → Recover connection immediately runs the checks.
        QTimer.singleShot(0, self.start)

    def start(self):
        if self.active: return
        self.progress.clear()
        previous = self.controller.last_connection_error
        if previous: self.progress.appendPlainText('Last connection error: '+previous)
        if not self.controller.repair_connection():
            self.progress.appendPlainText('Finish the current action before running recovery, then try again.')
            return
        self.active = True
        self.retry.setEnabled(False); self.close_button.setEnabled(False)
        self.retry.setText('Recovering…')

    def finished_repair(self, ok, message):
        self.active = False
        self.progress.appendPlainText(message)
        self.retry.setText('Check again' if ok else 'Try recovery again')
        self.retry.setEnabled(True); self.close_button.setEnabled(True)

    def disconnect_controller(self, *_):
        self.controller.repair_progress.disconnect(self.progress.appendPlainText)
        self.controller.repair_finished.disconnect(self.finished_repair)

    def accept(self):
        if not self.active: super().accept()

    def reject(self):
        if not self.active: super().reject()

    def closeEvent(self, event):
        if self.active: event.ignore()
        else: super().closeEvent(event)
