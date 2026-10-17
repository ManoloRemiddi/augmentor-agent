# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise the recovered panel in the current Native window on authored data."""
import os
import tempfile
import uuid
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QPushButton
from augmentor_linux.window import Window
from augmentor_linux.maintenance import MaintenanceBusy
from augmentor_linux.settings_host import bind_appearance
from augmentor_linux.surfaces import AppearanceDialog


class SettingsHostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        environment = patch.dict(os.environ, {
            'AUGMENTOR_PI_CONFIG': temporary.name + '/preferences',
            'AUGMENTOR_IDENTITY_DIR': temporary.name + '/identity',
            'AUGMENTOR_AGENT_ENTRIES': temporary.name + '/agents.json',
            'XDG_CONFIG_HOME': temporary.name + '/config',
            'XDG_STATE_HOME': temporary.name + '/state',
        })
        environment.start()
        self.addCleanup(environment.stop)
        self.window = Window(preview=True)
        self.window.preferences.values['animation'] = False
        self.window.show()
        self.app.processEvents()
        self.addCleanup(self.dispose)

    def dispose(self):
        self.window.controller = None
        panel = self.window.settings_panel
        if panel:
            panel.closing = True
            self.window.close_settings()
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_header_opens_inline_and_return_preserves_chat_draft_history_and_bounds(self):
        window = self.window
        window.composer.setPlainText('An unsent synthetic task')
        window.messages = [('You', 'Synthetic history')]
        before = window.geometry()
        composer = window.composer
        QTest.mouseClick(window.more_button, Qt.MouseButton.LeftButton)
        self.app.processEvents()
        panel = window.settings_panel
        self.assertIs(window.stack.currentWidget(), panel)
        self.assertEqual(window.size(), panel.frame_size())
        self.assertFalse(panel.isWindow())
        self.assertFalse(window.maintenance_state()['accepted'])
        with self.assertRaises(MaintenanceBusy):
            window.maintenance.control('host.maintenance.prepare', {})
        self.assertTrue(panel.accept())
        self.app.processEvents()
        self.assertIsNone(window.settings_panel)
        self.assertEqual(window.geometry(), before)
        self.assertIs(window.composer, composer)
        self.assertEqual(composer.toPlainText(), 'An unsent synthetic task')
        self.assertEqual(window.messages, [('You', 'Synthetic history')])

    def test_unsaved_identity_blocks_escape_close_and_compaction(self):
        window = self.window
        window.open_settings()
        panel = window.settings_panel
        panel.show_page('soul')
        panel.soul_editor.setPlainText('An unsaved synthetic identity')
        window.escape()
        self.assertIs(window.settings_panel, panel)
        self.assertFalse(window.close())
        window.toggle_compact()
        self.assertFalse(window.compact)
        self.assertIs(window.settings_panel, panel)
        panel.discard_and_return()
        self.assertIsNone(window.settings_panel)

    def test_settings_zoom_respects_screen_bounds_and_restores_original_chat_size(self):
        window = self.window
        original = window.size()
        window.composer.setPlainText('Preserve this draft through zoom')
        window.open_settings()
        for scale in (150, 75, 125, 100):
            window.apply_ui_scale(scale)
            self.app.processEvents()
            self.assertEqual(window.size(), window.settings_panel.frame_size())
        window.settings_panel.accept()
        self.assertEqual(window.size(), original)
        self.assertEqual(window.composer.toPlainText(), 'Preserve this draft through zoom')

    def test_model_setup_stays_inside_panel_and_chat_cannot_submit(self):
        window = self.window
        window.open_settings()
        window.controller = SimpleNamespace(running=False, navigating=False)
        dialog = QDialog(window)
        with patch.object(window, 'make_setup_dialog', return_value=dialog) as create:
            window.open_setup()
        create.assert_called_once()
        self.assertIs(window.settings_panel.editor, dialog)
        self.assertFalse(dialog.isWindow())
        window.composer.setPlainText('Keep this draft')
        window.send()
        self.assertEqual(window.composer.toPlainText(), 'Keep this draft')

    def test_inspection_action_tracks_current_connection_and_preserves_handy_and_quit(self):
        window = self.window
        window.controller = SimpleNamespace(harness='pi', client=SimpleNamespace(),
            session=None, online=False, running=False, closed=False, task=lambda work: work(), capabilities={'inspection': True})
        with patch('augmentor_linux.token_usage.read_usage', return_value={'start':'2026-10-01','end':'2026-10-17','days':[], 'total':0,'records':0,'sources':[],'incomplete':0}):
            window.open_settings()
        panel = window.settings_panel
        panel.show_page('all')
        self.assertFalse(panel.inspector_action.isEnabled())
        window.controller.session = 'synthetic-session'
        window.controller.online = True
        panel.update_activity()
        self.assertTrue(panel.inspector_action.isEnabled())
        window.controller.harness = 'dsh'
        panel.update_activity()
        self.assertFalse(panel.inspector_action.isEnabled())
        self.assertTrue(any('Handy' in b.text() for b in panel.findChildren(QPushButton)))
        with patch.object(window, 'quit_augmentor') as quit_app:
            panel.quit_agent()
        quit_app.assert_called_once()

    def test_appearance_publishes_current_shared_changes_and_themes_remain_readable(self):
        window = self.window
        window.open_settings()
        panel = window.settings_panel
        dialog = AppearanceDialog(window.preferences.values, window)
        self.addCleanup(dialog.deleteLater)
        with patch.object(window, 'publish_dictation_appearance') as publish:
            bind_appearance(window, dialog)
            for theme in ('light', 'dark'):
                dialog.changed.emit({'theme': theme})
                self.app.processEvents()
                self.assertEqual(window.preferences.values['theme'], theme)
                ink = panel.name.palette().color(QPalette.ColorRole.Text)
                contrast = ink.lightnessF() - window.background.lightnessF()
                self.assertGreater(contrast if theme == 'dark' else -contrast, 0.5)
        self.assertEqual(publish.call_count, 2)
        self.assertIs(window.settings_panel, panel)

    def test_pi_reasoning_and_mcp_remain_accessible_inside_the_restored_panel(self):
        window = self.window
        window.controller = SimpleNamespace(harness='pi', client=SimpleNamespace(),
            session=None, online=False, running=False, closed=False, task=lambda work: work(),
            capabilities={'inspection': True, 'reasoning': True, 'mcpManagement': True})
        reasoning, mcp = QDialog(window), QDialog(window)
        usage = {'start':'2026-10-01','end':'2026-10-17','days':[], 'total':0,
                 'records':0,'sources':[],'incomplete':0}
        with patch('augmentor_linux.token_usage.read_usage', return_value=usage):
            window.open_settings()
        panel = window.settings_panel
        with patch('augmentor_linux.reasoning_settings.ReasoningDialog', return_value=reasoning), \
             patch('augmentor_linux.mcp_settings.McpDialog', return_value=mcp):
            panel.show_page('all')
        for capability, dialog in [('reasoning', reasoning), ('mcpManagement', mcp)]:
            button = panel.pi_settings_actions[capability]
            self.assertTrue(button.isEnabled())
            button.click()
            self.assertIs(panel.editor, dialog)
            self.assertFalse(dialog.isWindow())
            self.assertTrue(panel.leave_editor())
            panel.show_page('all')
        window.controller.capabilities = {}
        panel.update_activity()
        self.assertTrue(all(not b.isEnabled() for b in panel.pi_settings_actions.values()))

    def test_pending_maintenance_cannot_open_settings(self):
        token = uuid.uuid4().hex
        self.window.maintenance.control('host.maintenance.prepare', {'token': token})
        try:
            self.window.open_settings()
            self.assertIsNone(self.window.settings_panel)
        finally:
            self.window.maintenance.control('host.maintenance.cancel', {'token': token})
