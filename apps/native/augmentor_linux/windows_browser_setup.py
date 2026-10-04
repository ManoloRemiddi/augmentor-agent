# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Windows adapter for the shared chooser; installation owns its stable anchor."""
from pathlib import Path
import subprocess
import sys
from PySide6.QtWidgets import QFileDialog
from .browser_setup import BrowserSetupDialog

ROOT = Path(__file__).resolve().parents[3]


def available():
    if sys.platform != 'win32': return False
    from platform_adapters.windows_browser import installed_root
    try: installed_root(ROOT); return True
    except (OSError, ValueError): return False


class WindowsBrowserSetupDialog(BrowserSetupDialog):
    ready_message = 'Ready. On the Extensions page, enable Developer mode and click Load unpacked. In the folder chooser, press Alt+D and paste the copied folder address. Then pin Augmentor in the browser toolbar.'

    def load_registrar(self):
        from platform_adapters import windows_browsers
        return windows_browsers

    def choose_application(self):
        return QFileDialog.getOpenFileName(self,'Choose your Chromium browser',str(Path.home()),'Applications (*.exe)')[0]

    def prepare_extension(self):
        from platform_adapters.windows_browser import prepare_extension
        return prepare_extension(ROOT,self.browser.currentData())

    def open_browser(self):
        try:
            browser = self.registrar.browser_application(self.browser.currentData())
            subprocess.Popen([browser['executable'],'chrome://extensions'],close_fds=True,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        except (OSError,ValueError):
            self.status.setText('Open '+self.browser.currentText()+' and enter chrome://extensions in its address bar.')
