# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from PySide6.QtWidgets import QApplication,QDialog
from augmentor_linux.window import Window
from augmentor_linux.ui_testing import dispatch


class UiTestingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_disabled_launch_rejects_every_operation_without_touching_window(self):
        for action in ['inspect','send','capture','draft','zoom','pin','shortcut-settings','runtime-markers']:
            with self.assertRaisesRegex(ValueError,'disabled'):
                dispatch(None,{'action':action})

    def test_runtime_markers_need_optin_and_exact_fields_and_do_not_inspect_window(self):
        from augmentor_linux import platform_runtime
        from platform_adapters import recipient_runtime_markers
        with patch.object(recipient_runtime_markers, 'collect', return_value={'markers':'synthetic'}) as collect:
            with self.assertRaisesRegex(ValueError,'additional'):
                dispatch(None,{'action':'runtime-markers','path':'foreign'},enabled=True)
            collect.assert_not_called()
            self.assertEqual(dispatch(None,{'action':'runtime-markers'},enabled=True),{'markers':'synthetic'})
            collect.assert_called_once_with()

    def test_draft_control_requires_exact_expected_input(self):
        window=Window(preview=True)
        try:
            window.composer.setPlainText('preserve')
            with self.assertRaisesRegex(ValueError,'exact expected'):
                dispatch(window,{'action':'draft','expected':'','text':'new'},enabled=True)
            self.assertEqual(window.composer.toPlainText(),'preserve')
            result=dispatch(window,{'action':'draft','expected':'preserve','text':'fixture'},enabled=True)
            self.assertEqual(result,{'draft':'fixture'})
        finally:window.close()

    def test_submission_never_replaces_a_draft_or_operates_behind_a_dialog(self):
        window=Window(preview=True);window.show()
        window.controller=SimpleNamespace(online=True,running=False,navigating=False,
            repairing=False,close=Mock())
        window.send_button.setEnabled(True)
        try:
            window.composer.setPlainText('An unsent user draft')
            with self.assertRaisesRegex(ValueError,'empty composer'):
                dispatch(window,{'action':'send','text':'A test'},enabled=True)
            self.assertEqual(window.composer.toPlainText(),'An unsent user draft')
            window.composer.clear();dialog=QDialog(window);dialog.show()
            with self.assertRaisesRegex(ValueError,'no dialogs'):
                dispatch(window,{'action':'send','text':'A test'},enabled=True)
            self.assertEqual(window.composer.toPlainText(),'')
        finally:
            window.controller=None;window.close()

    def test_capture_cannot_replace_an_existing_file(self):
        window=Window(preview=True)
        try:
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'image.png';path.write_bytes(b'preserve')
                with self.assertRaises(FileExistsError):
                    dispatch(window,{'action':'capture','path':str(path)},enabled=True)
                self.assertEqual(path.read_bytes(),b'preserve')
        finally:window.close()

    def test_pin_control_refuses_stale_state_and_hidden_window(self):
        window=Window(preview=True);window.show()
        try:
            with self.assertRaisesRegex(ValueError,'exact expected state'):
                dispatch(window,{'action':'pin','expected':False,'pinned':False},enabled=True)
            self.assertIs(window.preferences.values['pinned'],True)
            window.hide()
            with self.assertRaisesRegex(ValueError,'visible window'):
                dispatch(window,{'action':'pin','expected':True,'pinned':False},enabled=True)
            self.assertIs(window.preferences.values['pinned'],True)
        finally:window.close()

    def test_shortcut_settings_uses_real_widgets_and_async_save_with_stale_state_refusal(self):
        from concurrent.futures import ThreadPoolExecutor
        from PySide6.QtTest import QTest
        from augmentor_linux.panels import SettingsDialog
        window=Window(preview=True);window.show()
        executor=ThreadPoolExecutor(max_workers=1)
        window.controller=SimpleNamespace(closed=False,running=False,navigating=False,
            repairing=False,task=executor.submit)
        dialog=None
        def request(operation,**values):
            return dispatch(window,{'action':'shortcut-settings','operation':operation,**values},enabled=True)
        def wait(predicate):
            for _ in range(100):
                QTest.qWait(10)
                if predicate():return
            self.fail('Actual asynchronous shortcut callback did not finish.')
        with patch('augmentor_linux.shortcut_settings.current_keys',return_value=[]),\
             patch('augmentor_linux.shortcut_settings.save_shortcut',side_effect=lambda sequence,name:sequence[0].toCombined()) as save:
            try:
                dialog=SettingsDialog(window);window.shortcut_dialog=dialog;dialog.show()
                wait(lambda:all(r['ready'] for r in request('inspect')['rows'].values()))
                before=request('inspect')['rows']['secondary']['current']
                with self.assertRaisesRegex(ValueError,'changed'):
                    request('choose',instance='secondary',sequence='Ctrl+Alt+F10',expectedCurrent='stale')
                save.assert_not_called()
                chosen=request('choose',instance='secondary',sequence='Ctrl+Alt+F10',expectedCurrent=before)
                self.assertEqual(chosen['rows']['secondary']['sequence'],'Ctrl+Alt+F10')
                with self.assertRaisesRegex(ValueError,'exact selected'):
                    request('save',instance='secondary',expectedSequence='Ctrl+Alt+F9',expectedCurrent=before)
                save.assert_not_called()
                request('save',instance='secondary',expectedSequence='Ctrl+Alt+F10',expectedCurrent=before)
                wait(lambda:not request('inspect')['rows']['secondary']['saving'])
                self.assertTrue(request('inspect')['rows']['secondary']['note'].startswith('Saved.'))
                self.assertEqual(save.call_args.args[1],'secondary')
                current=request('inspect')['rows']['secondary']['current']
                save.side_effect=ValueError('already assigned to another launcher')
                request('choose',instance='secondary',sequence='Ctrl+Alt+F12',expectedCurrent=current)
                request('save',instance='secondary',expectedSequence='Ctrl+Alt+F12',expectedCurrent=current)
                wait(lambda:not request('inspect')['rows']['secondary']['saving'])
                row=request('inspect')['rows']['secondary']
                self.assertEqual(row['current'],current);self.assertIn('already assigned',row['note'])
                request('close');self.assertFalse(dialog.isVisible())
            finally:
                if dialog:dialog.close()
                executor.shutdown(wait=True)
                window.shortcut_dialog=None;window.controller=None;window.close()

    def test_shortcut_settings_open_is_deferred_and_rechecks_visibility(self):
        window=Window(preview=True);window.show()
        try:
            with patch.object(window,'open_settings') as opened:
                dispatch(window,{'action':'shortcut-settings','operation':'open'},enabled=True)
                opened.assert_not_called();window.hide();self.app.processEvents()
                opened.assert_not_called();self.assertFalse(window._shortcut_proof_opening)
        finally:window.close()

    def test_shortcut_settings_refuses_foreign_dialog_draft_and_extra_fields(self):
        window=Window(preview=True);window.show();dialog=QDialog(window)
        try:
            dialog.show()
            with self.assertRaisesRegex(ValueError,'another dialog'):
                dispatch(window,{'action':'shortcut-settings','operation':'inspect'},enabled=True)
            dialog.close();window.composer.setPlainText('retain this draft')
            with self.assertRaisesRegex(ValueError,'no draft'):
                dispatch(window,{'action':'shortcut-settings','operation':'open'},enabled=True)
            self.assertEqual(window.composer.toPlainText(),'retain this draft')
            window.composer.clear()
            with self.assertRaisesRegex(ValueError,'bounded'):
                dispatch(window,{'action':'shortcut-settings','operation':'inspect','widget':'arbitrary'},enabled=True)
        finally:dialog.close();window.close()
