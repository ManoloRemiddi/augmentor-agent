# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Shared update controls that remain usable without a model connection."""
from datetime import datetime
import threading

from PySide6.QtCore import QObject, QTimer, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QCheckBox, QComboBox, QSystemTrayIcon, QToolTip)
from .prompt_client import PromptClient
from .ui_scale import px
from .instances import current_name


class UpdateClient(QObject):
    received = Signal(object)
    failed = Signal(str)

    def __init__(self, parent, client=None):
        super().__init__(parent)
        self.client = client or PromptClient()
        self.pending = False
        self.action = None
        self.received.connect(self.finished)
        self.failed.connect(self.finished)

    def finished(self, _):
        self.pending = False

    def call(self, method='status', params=None):
        if self.pending: return False
        self.pending = True
        self.action = method
        def work():
            try:
                result = self.client.call('updates.' + method, params or {})
                self.received.emit(result)
            except Exception as error:
                try: self.failed.emit(str(error))
                except RuntimeError: pass  # The owning window was closed.
        threading.Thread(target=work, name='augmentor-update-ui', daemon=True).start()
        return True


class UpdatesDialog(QDialog):
    def __init__(self, window, client=None):
        super().__init__(window)
        self.state = None; self.dirty = False; self.draft_revision = None
        self.setWindowTitle('Versions & updates'); self.resize(px(self, 480), px(self, 500))
        layout = QVBoxLayout(self)
        self.info = QLabel('Loading update information…'); self.info.setWordWrap(True)
        layout.addWidget(self.info)
        self.checks = QCheckBox('Check for updates automatically'); layout.addWidget(self.checks)
        self.interval = QComboBox(); self.interval.addItem('Every day', 24); self.interval.addItem('Every two days', 48)
        self.interval.setAccessibleName('Update check frequency'); layout.addWidget(self.interval)
        self.channel = QComboBox(); self.channel.addItem('Stable releases', 'stable'); self.channel.addItem('Preview releases', 'preview')
        self.channel.setAccessibleName('Update channel'); layout.addWidget(self.channel)
        self.downloads = QCheckBox('Download new versions automatically'); layout.addWidget(self.downloads)
        self.installs = QCheckBox('Install automatically when Augmentor is idle'); layout.addWidget(self.installs)
        self.explanation = QLabel(); self.explanation.setWordWrap(True); layout.addWidget(self.explanation)
        self.note = QLabel(); self.note.setWordWrap(True); layout.addWidget(self.note)
        self.save_button = QPushButton('Save update preferences'); self.save_button.clicked.connect(self.save); layout.addWidget(self.save_button)
        reload_button = QPushButton('Reload saved preferences'); reload_button.clicked.connect(self.reload); layout.addWidget(reload_button)
        actions = QHBoxLayout(); layout.addLayout(actions)
        self.check_button = QPushButton('Check now'); self.check_button.clicked.connect(lambda: self.perform('check')); actions.addWidget(self.check_button)
        self.download_button = QPushButton('Download update'); self.download_button.clicked.connect(lambda: self.perform('download')); actions.addWidget(self.download_button)
        self.cancel_button = QPushButton('Cancel download'); self.cancel_button.clicked.connect(lambda: self.perform('cancel')); actions.addWidget(self.cancel_button)
        self.release_button = QPushButton('Open release and installation instructions'); self.release_button.clicked.connect(self.open_release); layout.addWidget(self.release_button)
        self.folder_button = QPushButton('Show downloaded files'); self.folder_button.clicked.connect(lambda: self.perform('reveal')); layout.addWidget(self.folder_button)
        reminders = QHBoxLayout(); layout.addLayout(reminders)
        self.remind_button = QPushButton('Remind me tomorrow'); self.remind_button.clicked.connect(lambda: self.perform('postpone', {'hours': 24})); reminders.addWidget(self.remind_button)
        self.skip_button = QPushButton('Skip this release'); self.skip_button.clicked.connect(lambda: self.perform('skip')); reminders.addWidget(self.skip_button)
        close = QPushButton('Done'); close.clicked.connect(self.accept); layout.addWidget(close)
        self.controls = (self.checks, self.interval, self.channel, self.downloads, self.installs)
        for control in self.controls:
            control.setEnabled(False)
            if isinstance(control, QCheckBox): control.clicked.connect(self.edited)
            else: control.activated.connect(self.edited)
        self.client = UpdateClient(self, client)
        self.client.received.connect(self.receive); self.client.failed.connect(self.failed)
        self.timer = QTimer(self); self.timer.setInterval(2500)
        self.timer.timeout.connect(lambda: self.client.call() if not self.dirty else None)
        self.finished.connect(lambda _: self.timer.stop())
        self.timer.start(); self.client.call()

    def edited(self, *_):
        self.dirty = True; self.save_button.setEnabled(bool(self.state) and not self.state['busy'])
        self.check_button.setEnabled(False); self.download_button.setEnabled(False)

    def failed(self, error):
        self.note.setText(error)
        if self.state:
            for control in self.controls: control.setEnabled(not self.state['busy'])
            self.installs.setEnabled(self.state['automaticInstallAvailable'] and not self.state['busy'])

    def receive(self, value):
        if not isinstance(value, dict): return
        if self.client.action == 'reveal':
            QDesktopServices.openUrl(QUrl.fromLocalFile(value['folder'])); return
        if self.client.action == 'configure': self.dirty = False
        self.state = value
        current = value['installed']; candidate = value.get('candidate')
        last = value.get('lastSuccessfulCheck')
        stamp = datetime.fromtimestamp(last).strftime('%d %b %Y, %H:%M') if last else 'Never'
        build = 'unknown' if current.get('buildKnown') is False else current['build']
        text = f"Installed: {current['version']} · build {build}\nLast successful check: {stamp}"
        if candidate: text += f"\nAvailable: {candidate['version']} · build {candidate['build']}"
        elif value['phase'] == 'current': text += '\nNo newer compatible release was found.'
        if value['phase'] == 'ready': text += '\nDownload ready. Open the release instructions to install.'
        if value['phase'] == 'downloading': text += f"\nDownloading: {value.get('bytesDownloaded', 0) / 1024**2:.1f} MB"
        self.info.setText(text); self.note.setText(value.get('error') or '')
        self.explanation.setText('Downloads use your internet connection and disk space. Settings are shared with the browser. '
            + ('Automatic installation waits for all Augmentor work to finish.' if value['automaticInstallAvailable'] else
               'Automatic installation is not available for this installed build. Use the release installation instructions.'))
        if not self.dirty:
            self.draft_revision = value['revision']
            prefs = value['preferences']
            self.checks.setChecked(prefs['automaticChecks']); self.interval.setCurrentIndex(self.interval.findData(prefs['intervalHours']))
            self.channel.setCurrentIndex(self.channel.findData(prefs['channel']))
            self.downloads.setChecked(prefs['automaticDownload']); self.installs.setChecked(prefs['automaticInstall'])
        busy = value['busy']
        for control in self.controls: control.setEnabled(not busy)
        self.installs.setEnabled(value['automaticInstallAvailable'] and not busy)
        self.check_button.setEnabled(not busy and not self.dirty); self.download_button.setEnabled(bool(candidate) and not busy and not self.dirty)
        self.cancel_button.setEnabled(busy and value['phase'] in ('checking','downloading')); self.release_button.setEnabled(bool(candidate))
        self.folder_button.setEnabled(value['phase'] == 'ready')
        self.remind_button.setEnabled(bool(candidate)); self.skip_button.setEnabled(bool(candidate))
        self.save_button.setEnabled(self.dirty and not busy)

    def perform(self, action, params=None):
        self.client.call(action, params)

    def save(self):
        if not self.state: return
        prefs = {'automaticChecks': self.checks.isChecked(), 'intervalHours': self.interval.currentData(),
                 'channel': self.channel.currentData(), 'automaticDownload': self.downloads.isChecked(),
                 'automaticInstall': self.installs.isChecked()}
        if self.client.call('configure', {'revision': self.draft_revision, 'preferences': prefs}):
            for control in self.controls: control.setEnabled(False)

    def reload(self):
        if not self.client.pending:
            self.dirty = False; self.client.call()

    def open_release(self):
        if self.state and self.state.get('candidate'):
            QDesktopServices.openUrl(QUrl(self.state['candidate']['releaseUrl']))


class UpdateMonitor(QObject):
    """One primary-window notification; no model requests and no modal interruption."""
    def __init__(self, window):
        super().__init__(window); self.window = window
        self.client = UpdateClient(self)
        self.client.received.connect(self.notify)
        self.timer = QTimer(self); self.timer.setInterval(60000); self.timer.timeout.connect(self.poll)
        self.timer.start(); QTimer.singleShot(30000, self.poll)
        self.client.call('status')  # Start the independent scheduler at app boot.

    def poll(self):
        window = self.window
        if current_name() != 'main' or window.maintenance.phase() != 'ready': return
        if not window.isVisible() and not hasattr(window, 'app_tray'): return
        self.client.call('notification')

    def notify(self, release):
        if not release or 'installed' in release: return
        window = self.window
        text = f"Augmentor {release['version']} (build {release['build']}) is available. Open Versions & updates to download it."
        window.more_button.setToolTip(text)
        if hasattr(window, 'app_tray'):
            window.app_tray.showMessage('Augmentor update available', text, QSystemTrayIcon.MessageIcon.Information, 10000)
        else:
            QToolTip.showText(window.more_button.mapToGlobal(window.more_button.rect().bottomLeft()), text, window.more_button, msecShowTime=10000)
