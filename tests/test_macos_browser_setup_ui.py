# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from augmentor_linux import macos_browser_setup as setup


class MacBrowserSetupUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dialog = setup.MacBrowserSetupDialog(None)
        self.dialog.browser.clear()
        self.addCleanup(self.dialog.close)

    def test_picker_selects_exact_app_and_open_uses_that_path(self):
        browser={'name':'Comet','app':'/Applications/Comet.app'}
        with patch.object(setup.QFileDialog,'getOpenFileName',return_value=(browser['app'],'')), \
             patch.object(self.dialog.registrar,'browser_application',return_value=browser):
            self.dialog.choose_button.click()
        self.assertEqual(self.dialog.browser.currentData(),browser['app'])
        with patch.object(setup,'ROOT',Path('/Applications/Augmentor.app/Contents/Resources/app')), \
             patch.object(self.dialog.registrar,'prepare_extension',return_value={'extensionDirectory':'/fixture/extension'}) as prepare:
            self.dialog.prepare_button.click()
        self.assertEqual(prepare.call_args.args[1],browser['app'])
        self.assertTrue(self.dialog.page_button.isEnabled());self.assertTrue(self.dialog.browser.isEnabled())
        with patch.object(setup.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as launch:
            self.dialog.page_button.click()
        self.assertEqual(launch.call_args.args[0],['/usr/bin/open','-a',browser['app'],'chrome://extensions'])
        self.dialog.browser.addItem('Different browser','/Applications/Other.app')
        self.dialog.browser.setCurrentIndex(1)
        self.assertIsNone(self.dialog.directory);self.assertFalse(self.dialog.page_button.isEnabled())

    def test_cancel_and_invalid_app_preserve_selection_and_no_browser_means_no_prepare(self):
        self.assertFalse(self.dialog.prepare_button.isEnabled())
        self.dialog.browser.addItem('Comet','/Applications/Comet.app')
        with patch.object(setup.QFileDialog,'getOpenFileName',return_value=('','')):
            self.dialog.choose_browser()
        self.assertEqual(self.dialog.browser.currentData(),'/Applications/Comet.app')
        with patch.object(setup.QFileDialog,'getOpenFileName',return_value=('/Applications/Safari.app','')), \
             patch.object(self.dialog.registrar,'browser_application',side_effect=ValueError('wrong engine')):
            self.dialog.choose_browser()
        self.assertEqual(self.dialog.browser.currentData(),'/Applications/Comet.app')
        self.assertIn('not supported',self.dialog.status.text())

    def test_failed_prepare_disables_old_result_and_exposes_data_folder_choice(self):
        self.dialog.browser.addItem('Custom','/Applications/Custom.app')
        self.dialog.directory='/old/extension';self.dialog.page_button.setEnabled(True)
        with patch.object(setup,'ROOT',Path('/Applications/Augmentor.app/Contents/Resources/app')), \
             patch.object(self.dialog.registrar,'prepare_extension',side_effect=ValueError('Open Custom once')):
            self.dialog.prepare()
        self.assertIsNone(self.dialog.directory);self.assertFalse(self.dialog.page_button.isEnabled())
        self.assertFalse(self.dialog.data_button.isHidden());self.assertEqual(self.dialog.status.text(),'Open Custom once')
