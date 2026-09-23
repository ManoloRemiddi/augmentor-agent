# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtGui import QKeySequence
from augmentor_linux.shortcuts import save_shortcut,COMPONENT

class ShortcutTests(unittest.TestCase):
    def test_packaged_shortcut_creates_activatable_entries_and_rolls_back_failure(self):
        sequence=QKeySequence('Ctrl+Alt+J');key=sequence[0].toCombined()
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{'XDG_DATA_HOME':root}):
            template=Path(root)/'system.desktop';template.write_text('[Desktop Entry]\nName=Augmentor Agent\nExec=augmentor-agent\n')
            paths=[Path(root)/place/COMPONENT for place in ('applications','kglobalaccel')]
            def reply(method,*args):
                if method=='isGlobalShortcutAvailable':return '(true,)'
                if method=='doRegister':
                    for path in paths:
                        self.assertIn('Exec=augmentor-agent',path.read_text())
                        self.assertIn('X-KDE-Shortcuts=Ctrl+Alt+J',path.read_text())
                        self.assertTrue(path.stat().st_mode & 0o100,'KDE must trust the user-owned launcher after restart')
                return f'([{key}],)' if method=='setShortcut' else '()'
            with patch('augmentor_linux.shortcuts.PACKAGED',True),patch('augmentor_linux.shortcuts.SYSTEM_DESKTOP',template),patch('augmentor_linux.shortcuts.current_keys',return_value=[]),patch('augmentor_linux.shortcuts.call',side_effect=reply):
                save_shortcut(sequence)
            for path in paths:path.unlink()
            paths[0].write_text('Original launcher\n');paths[0].chmod(0o644)
            with patch('augmentor_linux.shortcuts.PACKAGED',True),patch('augmentor_linux.shortcuts.SYSTEM_DESKTOP',template),patch('augmentor_linux.shortcuts.current_keys',return_value=[]),patch('augmentor_linux.shortcuts.call',side_effect=['(true,)','()','(@ai [],)','(@ai [],)']):
                with self.assertRaisesRegex(RuntimeError,'previous shortcut'):save_shortcut(sequence)
            self.assertEqual(paths[0].read_text(),'Original launcher\n')
            self.assertEqual(paths[0].stat().st_mode & 0o777,0o644)
            self.assertFalse(paths[1].exists(),'Failed registration left a new launcher behind')

    def test_conflict_keeps_existing_binding_and_does_not_register(self):
        with patch('augmentor_linux.shortcuts.current_keys',return_value=[123]),patch('augmentor_linux.shortcuts.call',return_value='(false,)') as call:
            with self.assertRaisesRegex(ValueError,'already assigned'):save_shortcut(QKeySequence('Ctrl+Alt+J'))
            self.assertEqual([c.args[0] for c in call.call_args_list],['isGlobalShortcutAvailable'])

    def test_existing_owned_key_can_be_saved_and_persisted(self):
        sequence=QKeySequence('Ctrl+Alt+J');key=sequence[0].toCombined()
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{'XDG_DATA_HOME':root}):
            path=Path(root)/'applications'/COMPONENT;path.parent.mkdir();path.write_text('[Desktop Entry]\nName=Augmentor Agent\nX-KDE-Shortcuts=Hangul\n')
            def reply(method,*args):
                if method=='isGlobalShortcutAvailable':self.fail('An existing owned key is not a conflict')
                if method=='setShortcut':
                    self.assertTrue(int(args[-1]) & 2,'KDE must activate the shortcut, not only save its keys')
                return f'([{key}],)' if method=='setShortcut' else '()'
            with patch('augmentor_linux.shortcuts.current_keys',return_value=[key]),patch('augmentor_linux.shortcuts.call',side_effect=reply):
                self.assertEqual(save_shortcut(sequence),key)
            self.assertIn('X-KDE-Shortcuts=Ctrl+Alt+J',path.read_text())
            self.assertIn('Name=Augmentor Agent',path.read_text())

    def test_failed_assignment_restores_previous_binding(self):
        with patch('augmentor_linux.shortcuts.current_keys',return_value=[123]),patch('augmentor_linux.shortcuts.call',side_effect=['(true,)','()','(@ai [],)','([123],)']) as call:
            with self.assertRaisesRegex(RuntimeError,'previous shortcut'):save_shortcut(QKeySequence('Ctrl+Alt+J'))
            self.assertEqual(call.call_args.args[0],'setShortcut')
            self.assertEqual(call.call_args.args[2],'[123]')
            self.assertTrue(int(call.call_args.args[3]) & 2,'Rollback must reactivate the previous shortcut')
