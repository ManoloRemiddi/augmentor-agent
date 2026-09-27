# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Explicit browser registration and unpacked-extension instructions for Mac preview."""
import importlib.util
from pathlib import Path
import subprocess
import sys
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QFileDialog, QLabel, QPushButton, QSizePolicy, QVBoxLayout

ROOT = Path(__file__).resolve().parents[3]


def available():
    return sys.platform == 'darwin' and (ROOT/'release.json').is_file()


class MacBrowserSetupDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.setWindowTitle('Add Augmentor to your browser'); self.resize(540, 440)
        self.directory = None; self.data_directory = None
        spec = importlib.util.spec_from_file_location('mac_browser_registrar', ROOT/'scripts/register-macos-browser.py')
        self.registrar = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.registrar)
        layout = QVBoxLayout(self)
        note = QLabel('This preview uses a manually loaded extension. Prepare it here, then open your browser’s Extensions page, enable Developer mode and choose Load unpacked. Your browser controls the final installation.')
        note.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        note.setWordWrap(True); layout.addWidget(note)
        self.browser = QComboBox()
        self.browser.setAccessibleName('Installed Chromium browser')
        for browser in self.registrar.installed_browsers():
            self.browser.addItem(browser['name'], browser['app'])
            self.browser.setItemData(self.browser.count()-1, browser['app'], Qt.ItemDataRole.ToolTipRole)
        layout.addWidget(self.browser)
        self.choose_button = QPushButton('Choose another browser app…')
        self.choose_button.clicked.connect(self.choose_browser); layout.addWidget(self.choose_button)
        self.prepare_button = QPushButton('Prepare browser extension'); self.prepare_button.clicked.connect(self.prepare); layout.addWidget(self.prepare_button)
        self.status = QLabel(''); self.status.setWordWrap(True)
        self.status.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum); layout.addWidget(self.status)
        self.data_button = QPushButton('Choose browser data folder…'); self.data_button.setVisible(False)
        self.data_button.clicked.connect(self.choose_data_directory); layout.addWidget(self.data_button)
        self.copy_button = QPushButton('Copy extension folder address'); self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(lambda: QApplication.clipboard().setText(self.directory or '')); layout.addWidget(self.copy_button)
        self.folder_button = QPushButton('Show extension folder'); self.folder_button.setEnabled(False)
        self.folder_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.directory))); layout.addWidget(self.folder_button)
        self.page_button = QPushButton('Open browser Extensions page'); self.page_button.setEnabled(False)
        self.page_button.clicked.connect(self.open_browser); layout.addWidget(self.page_button)
        done = QPushButton('Done'); done.clicked.connect(self.accept); layout.addWidget(done)
        self.browser.currentIndexChanged.connect(self.reset_browser)
        self.reset_browser()

    def reset_browser(self):
        self.directory = None; self.data_directory = None
        self.data_button.setVisible(False)
        self.prepare_button.setEnabled(self.browser.currentData() is not None)
        self.status.setText('Choose your Chromium-based browser, then click Prepare browser extension.' if self.browser.count() else 'Choose an installed Chromium-based browser app to get started.')
        for button in (self.copy_button, self.folder_button, self.page_button):button.setEnabled(False)

    def choose_browser(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose your Chromium browser', '/Applications', 'Applications (*.app)')
        if not path: return
        try:
            browser = self.registrar.browser_application(path)
            index = self.browser.findData(browser['app'])
            if index < 0:
                self.browser.addItem(browser['name'], browser['app']); index = self.browser.count()-1
                self.browser.setItemData(index, browser['app'], Qt.ItemDataRole.ToolTipRole)
            self.browser.setCurrentIndex(index)
            self.reset_browser()
        except (OSError, ValueError):
            self.status.setText('Choose an installed Chromium-based browser application. The selected app is not supported.')

    def choose_data_directory(self):
        path = QFileDialog.getExistingDirectory(self, 'Choose the browser data folder containing Local State', str(Path.home()/'Library/Application Support'))
        if path:
            self.data_directory = Path(path)
            self.prepare()

    def prepare(self):
        self.directory = None
        for button in (self.copy_button, self.folder_button, self.page_button): button.setEnabled(False)
        try:
            app = ROOT.parents[2]
            if app.parent not in (Path('/Applications'), Path.home()/'Applications'):
                raise ValueError('Drag Augmentor into Applications and open that copy before preparing your browser.')
            result = self.registrar.prepare_extension(app, self.browser.currentData(), Path.home()/'Library/Application Support', self.data_directory)
            self.directory = result['extensionDirectory']
            self.status.setText('Ready. On the Extensions page, enable Developer mode and click Load unpacked. In the folder chooser, press Shift+Command+G and paste the copied folder address. Then pin Augmentor in the browser toolbar.')
            for button in (self.copy_button, self.folder_button, self.page_button): button.setEnabled(True)
            self.data_button.setVisible(False)
        except Exception as error:
            self.status.setText(str(error) if isinstance(error, ValueError) else 'Browser setup could not finish. Existing browser settings were preserved.')
            self.data_button.setVisible(True)

    def open_browser(self):
        name = self.browser.currentText()
        result = subprocess.run(['/usr/bin/open', '-a', self.browser.currentData(), 'chrome://extensions'], capture_output=True)
        if result.returncode:
            self.status.setText('Open '+name+' and enter chrome://extensions in its address bar.')
