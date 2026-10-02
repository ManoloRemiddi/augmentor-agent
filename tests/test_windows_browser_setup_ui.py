# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication
from augmentor_linux import windows_browser_setup as setup


class WindowsBrowserSetupUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.registrar = SimpleNamespace(installed_browsers=lambda:[], browser_application=Mock())
        registrar = self.registrar
        # PySide inspects QObject class methods when connecting signals. A
        # MagicMock class method crashes Ubuntu's 6.10.2 binding at that boundary.
        class FixtureDialog(setup.WindowsBrowserSetupDialog):
            def load_registrar(self): return registrar
        self.dialog = FixtureDialog(None)
        self.addCleanup(self.dialog.close)

    def test_unlisted_executable_choice_prepare_and_exact_browser_launch(self):
        details = {'name':'Comet','app':r'C:\Chosen Browser\comet.exe','executable':r'C:\Chosen Browser\comet.exe'}
        self.registrar.browser_application.return_value = details
        self.assertFalse(self.dialog.prepare_button.isEnabled())
        with patch.object(setup.QFileDialog,'getOpenFileName',return_value=(details['app'],'')) as picker:
            self.dialog.choose_button.click()
        self.assertEqual(picker.call_args.args[-1],'Applications (*.exe)')
        self.assertEqual(self.dialog.browser.currentData(),details['app'])
        with patch.object(self.dialog,'prepare_extension',return_value={'extensionDirectory':r'C:\Data\Extension'}):
            self.dialog.prepare_button.click()
        self.assertIn('Alt+D',self.dialog.status.text())
        self.assertTrue(self.dialog.page_button.isEnabled())
        self.assertTrue(self.dialog.data_button.isHidden())
        with patch.object(setup.subprocess,'Popen') as launch, patch.object(setup.subprocess,'CREATE_NO_WINDOW',0x08000000,create=True):
            self.dialog.page_button.click()
        self.assertEqual(launch.call_args.args[0],[details['executable'],'chrome://extensions'])
        self.dialog.browser.addItem('Another',r'C:\Other\browser.exe')
        self.dialog.browser.setCurrentIndex(1)
        self.assertIsNone(self.dialog.directory)
        self.assertFalse(self.dialog.page_button.isEnabled())

    def test_cancel_invalid_selection_and_failed_preparation_preserve_user_choice(self):
        self.dialog.browser.addItem('Selected',r'C:\Selected\browser.exe')
        with patch.object(setup.QFileDialog,'getOpenFileName',return_value=('','')):
            self.dialog.choose_browser()
        self.assertEqual(self.dialog.browser.currentData(),r'C:\Selected\browser.exe')
        self.registrar.browser_application.side_effect = ValueError('Not Chromium')
        with patch.object(setup.QFileDialog,'getOpenFileName',return_value=(r'C:\invalid.exe','')):
            self.dialog.choose_browser()
        self.assertEqual(self.dialog.browser.currentData(),r'C:\Selected\browser.exe')
        with patch.object(self.dialog,'prepare_extension',side_effect=ValueError('Open the installed copy')):
            self.dialog.prepare_button.click()
        self.assertIn('installed copy',self.dialog.status.text())
        self.assertFalse(self.dialog.page_button.isEnabled())
        self.assertTrue(self.dialog.data_button.isHidden())


if __name__ == '__main__': unittest.main()
