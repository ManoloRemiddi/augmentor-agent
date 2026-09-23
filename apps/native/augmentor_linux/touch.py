# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Opt-in touch sizing for the original Qt surface, with unchanged action handlers."""
import json
import os
from pathlib import Path
from PySide6.QtCore import QObject, QEvent, QTimer, Qt
from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QLayout, QMenu, QPushButton, QScrollArea, QWidget, QVBoxLayout, QScroller

TARGET = 44

class TouchLayout(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.viewport = (412, 820)
        self.command = None
        self.file = Path(os.environ['AUGMENTOR_TOUCH_VIEWPORT']) if os.environ.get('AUGMENTOR_TOUCH_VIEWPORT') else None
        window.activity.margin=8
        window.outer.setContentsMargins(8, 8, 8, 8)
        layout = window.expanded.layout()
        header = layout.itemAt(0).layout()
        controls = QHBoxLayout(); controls.setSpacing(8)
        for button in (window.new_button, window.save_button, window.history_button, window.pin_button, window.compact_button, window.more_button):
            header.removeWidget(button); controls.addWidget(button)
        controls.addStretch()
        layout.insertLayout(1, controls)
        layout.setSpacing(8)
        window.setMinimumSize(340, 300)
        window.brand.setText('Augmentor Agent')
        self.buttons = (window.new_button, window.save_button, window.history_button, window.pin_button,
                        window.compact_button, window.more_button, window.hide_button, window.voice_button,
                        window.send_button, window.stop_button, window.latest_button)
        for button in self.buttons:
            button.setFixedSize(TARGET, TARGET)
        window.model_picker.setFixedHeight(TARGET)
        window.voice_button.setToolTip('Voice uses the computer microphone and speakers. Phone audio is not connected yet.')
        window.voice_button.setAccessibleName('Voice using computer audio')
        window.composer.touch_mode=True
        window.composer.fit()
        window.composer.improve_button.setFixedSize(TARGET, TARGET)
        window.composer.setViewportMargins(0, 0, 62, 0)
        window.composer.installEventFilter(self)
        window.transcript.touch_targets = True
        window.title.setToolTip('Tap to rename this conversation')
        window.title.mouseReleaseEvent = lambda event: window.rename_chat() if event.button() == Qt.MouseButton.LeftButton else None
        window.title_editor.setFixedHeight(TARGET)
        QScroller.grabGesture(window.transcript.viewport(), QScroller.ScrollerGestureType.TouchGesture)
        self.style()
        QApplication.instance().installEventFilter(self)
        self.timer = QTimer(self); self.timer.timeout.connect(self.poll); self.timer.start(250)
        self.poll()

    def style(self):
        w = self.window
        # Preserve all original colours and artwork. Only sizing/spacing changes.
        w.setStyleSheet(w.styleSheet() + '\nQMenu::item {padding:14px 18px;} QDialog QPushButton,QDialog QComboBox,QDialog QLineEdit {min-height:30px;} QDialog QListWidget::item {min-height:30px;padding:8px;} QScrollBar:vertical {width:18px;}')
        w.composer.setMinimumHeight(58)
        w.model_picker.setFixedHeight(TARGET)
        w.composer.improve_button.move(w.composer.width()-TARGET-12, 6)

    def fit_dialog(self, dialog):
        if not dialog.isVisible(): return
        width, height = self.viewport
        if not dialog.property('touchFitted'):
            dialog.setProperty('touchFitted', True)
            # Keep the real dialog layout inside a scrollable viewport. Wide
            # legacy forms remain reachable without scaling down their buttons.
            original = dialog.layout()
            if original:
                last=original.itemAt(original.count()-1) if original.count() else None
                existing_close=last.widget() if last else None
                if not isinstance(existing_close,QPushButton) or existing_close.text().replace('&','') not in ('Done','Close'):
                    existing_close=None
                if existing_close:original.removeWidget(existing_close)
                content = QWidget(); content.setLayout(original)
                outer = QVBoxLayout(dialog); outer.setContentsMargins(6, 6, 6, 6)
                scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(content)
                outer.addWidget(scroll)
                if existing_close:outer.addWidget(existing_close)
                else:
                    close = QPushButton('Done'); close.clicked.connect(dialog.reject); outer.addWidget(close)
                QScroller.grabGesture(scroll.viewport(), QScroller.ScrollerGestureType.TouchGesture)
                outer.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
            dialog.setMinimumSize(0, 0)
        dialog.setMaximumSize(width-8, height-8)
        dialog.resize(min(dialog.width(), width-8), min(dialog.height(), height-8))
        dialog.move(max(4, (width-dialog.width())//2), max(4, (height-dialog.height())//2))

    def poll(self):
        if self.file:
            try:
                data = json.loads(self.file.read_text())
                size = (max(340, min(1600, int(data['width']))), max(300, min(1400, int(data['height']))))
                if size != self.viewport: self.viewport = size
                if data.get('show') != self.command:
                    self.command = data.get('show')
                    if self.window.compact: self.window.toggle_compact()
                    self.window.bring_forward()
            except (OSError, ValueError, KeyError): pass
        if not self.window.compact:
            self.window.setGeometry(0, 0, *self.viewport)
        for dialog in self.window.findChildren(QDialog):
            if dialog.isVisible(): self.fit_dialog(dialog)

    def fit_menu(self,menu):
        if not menu.isVisible():return
        width,height=self.viewport
        menu.move(max(4,min(menu.x(),width-menu.width()-4)),max(4,min(menu.y(),height-menu.height()-4)))

    def eventFilter(self, obj, event):
        if obj is self.window.composer and event.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, lambda: self.window.composer.improve_button.move(self.window.composer.width()-TARGET-12, 6))
        if event.type() == QEvent.Type.Show and isinstance(obj,QMenu):
            QTimer.singleShot(0,lambda m=obj:self.fit_menu(m))
        if event.type() == QEvent.Type.Show and isinstance(obj, QDialog) and obj.window() is not self.window:
            if self.window.isAncestorOf(obj): QTimer.singleShot(0, lambda d=obj: self.fit_dialog(d))
        return False
