# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Explicit browser registration and unpacked-extension instructions for Mac preview."""
import importlib.util
from pathlib import Path
import subprocess
import sys
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QLabel, QPushButton, QVBoxLayout

ROOT = Path(__file__).resolve().parents[3]


def available():
    return sys.platform == 'darwin' and (ROOT/'release.json').is_file()


class MacBrowserSetupDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.setWindowTitle('Add Augmentor to your browser'); self.resize(500, 310)
        self.directory = None
        layout = QVBoxLayout(self)
        note = QLabel('This preview uses a manually loaded extension. Prepare it here, then open your browser’s Extensions page, enable Developer mode and choose Load unpacked. Your browser controls the final installation.')
        note.setWordWrap(True); layout.addWidget(note)
        self.browser = QComboBox(); self.browser.addItem('Google Chrome', 'chrome'); self.browser.addItem('Chromium', 'chromium')
        layout.addWidget(self.browser)
        self.prepare_button = QPushButton('Prepare browser extension'); self.prepare_button.clicked.connect(self.prepare); layout.addWidget(self.prepare_button)
        self.status = QLabel(''); self.status.setWordWrap(True); layout.addWidget(self.status)
        self.copy_button = QPushButton('Copy extension folder address'); self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(lambda: QApplication.clipboard().setText(self.directory or '')); layout.addWidget(self.copy_button)
        self.folder_button = QPushButton('Show extension folder'); self.folder_button.setEnabled(False)
        self.folder_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.directory))); layout.addWidget(self.folder_button)
        self.page_button = QPushButton('Open browser Extensions page'); self.page_button.setEnabled(False)
        self.page_button.clicked.connect(self.open_browser); layout.addWidget(self.page_button)
        done = QPushButton('Done'); done.clicked.connect(self.accept); layout.addWidget(done)
        self.browser.currentIndexChanged.connect(self.reset_browser)

    def reset_browser(self):
        self.directory = None
        self.status.setText('Click Prepare browser extension for the selected browser.')
        for button in (self.copy_button, self.folder_button, self.page_button):button.setEnabled(False)

    def prepare(self):
        try:
            app = ROOT.parents[2]
            if app.parent not in (Path('/Applications'), Path.home()/'Applications'):
                raise ValueError('Drag Augmentor into Applications and open that copy before preparing your browser.')
            spec = importlib.util.spec_from_file_location('mac_browser_registrar', ROOT/'scripts/register-macos-browser.py')
            registrar = importlib.util.module_from_spec(spec); spec.loader.exec_module(registrar)
            result = registrar.prepare_extension(app, self.browser.currentData(), Path.home()/'Library/Application Support')
            self.directory = result['extensionDirectory']
            self.status.setText('Ready. On the Extensions page, enable Developer mode and click Load unpacked. In the folder chooser, press Shift+Command+G and paste the copied folder address. Then pin Augmentor in the browser toolbar.')
            for button in (self.copy_button, self.folder_button, self.page_button): button.setEnabled(True)
            self.browser.setEnabled(False)
        except Exception as error:
            self.status.setText(str(error) if isinstance(error, ValueError) else 'Browser setup could not finish. Existing browser settings were preserved.')

    def open_browser(self):
        name = 'Google Chrome' if self.browser.currentData() == 'chrome' else 'Chromium'
        result = subprocess.run(['/usr/bin/open', '-a', name, 'chrome://extensions'], capture_output=True)
        if result.returncode:
            self.status.setText('Open '+name+' and enter chrome://extensions in its address bar.')
