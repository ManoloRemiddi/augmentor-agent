# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Mac adapter for the shared browser chooser and preview instructions."""
import importlib.util
from pathlib import Path
import subprocess
import sys
from PySide6.QtWidgets import QFileDialog
from .browser_setup import BrowserSetupDialog

ROOT = Path(__file__).resolve().parents[3]


def available():
    return sys.platform == 'darwin' and (ROOT/'release.json').is_file()


class MacBrowserSetupDialog(BrowserSetupDialog):
    supports_data_folder = True
    ready_message = 'Ready. On the Extensions page, enable Developer mode and click Load unpacked. In the folder chooser, press Shift+Command+G and paste the copied folder address. Then pin Augmentor in the browser toolbar.'

    def load_registrar(self):
        spec = importlib.util.spec_from_file_location('mac_browser_registrar', ROOT/'scripts/register-macos-browser.py')
        registrar = importlib.util.module_from_spec(spec); spec.loader.exec_module(registrar)
        return registrar

    def choose_application(self):
        return QFileDialog.getOpenFileName(self, 'Choose your Chromium browser', '/Applications', 'Applications (*.app)')[0]

    def choose_data_directory(self):
        path = QFileDialog.getExistingDirectory(self, 'Choose the browser data folder containing Local State', str(Path.home()/'Library/Application Support'))
        if path:
            self.data_directory = Path(path)
            self.prepare()

    def prepare_extension(self):
        app = ROOT.parents[2]
        if app.parent not in (Path('/Applications'), Path.home()/'Applications'):
            raise ValueError('Drag Augmentor into Applications and open that copy before preparing your browser.')
        return self.registrar.prepare_extension(app, self.browser.currentData(), Path.home()/'Library/Application Support', self.data_directory)

    def open_browser(self):
        name = self.browser.currentText()
        result = subprocess.run(['/usr/bin/open', '-a', self.browser.currentData(), 'chrome://extensions'], capture_output=True)
        if result.returncode:
            self.status.setText('Open '+name+' and enter chrome://extensions in its address bar.')
