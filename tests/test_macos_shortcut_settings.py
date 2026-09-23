# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import errno
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtGui import QKeySequence
from augmentor_linux.macos_shortcuts import ManagedShortcutManager


class ManagedShortcutSettingsTests(unittest.TestCase):
    def test_save_releases_local_before_registering_and_sends_once(self):
        manager=ManagedShortcutManager();sequence=QKeySequence('Ctrl+Alt+J');events=[]
        def request(message):
            events.append(message['operation'])
            return {'ok':True,'key':sequence[0].toCombined()}
        with patch.object(manager.local,'command'),patch.object(manager.local,'release',side_effect=lambda:events.append('release')),patch.object(manager,'ensure_service',side_effect=lambda:events.append('ready')),patch('augmentor_linux.macos_shortcut_service.request',side_effect=request):
            self.assertEqual(manager.save(sequence),sequence[0].toCombined())
        self.assertEqual(events,['release','ready','save'])
        manager.close()

    def test_invalid_key_preserves_local_registration(self):
        manager=ManagedShortcutManager()
        with patch.object(manager.local,'command',side_effect=ValueError('invalid')),patch.object(manager.local,'release') as release,patch.object(manager,'ensure_service') as ensure:
            with self.assertRaises(ValueError):manager.save(QKeySequence())
            release.assert_not_called();ensure.assert_not_called()
        manager.close()

    def test_lost_save_response_never_restores_competing_local_owner(self):
        manager=ManagedShortcutManager()
        with patch.object(manager.local,'command'),patch.object(manager.local,'release'),patch.object(manager,'ensure_service'),patch('augmentor_linux.macos_shortcut_service.request',side_effect=TimeoutError('unknown')) as request,patch.object(manager.local,'restore') as restore:
            with self.assertRaises(TimeoutError):manager.save(QKeySequence('Ctrl+Alt+J'))
            self.assertEqual(request.call_count,1);restore.assert_not_called()
        manager.close()

    def test_bootstrap_uses_bundled_registrar_with_space_safe_arguments(self):
        manager=ManagedShortcutManager()
        root=Path('/Applications/Desktop Preview.app/Contents/Resources/app')
        missing=FileNotFoundError(errno.ENOENT,'missing')
        with patch('augmentor_linux.macos_shortcuts.ROOT',root),patch('augmentor_linux.macos_shortcut_service.request',side_effect=[missing,{'protocol':1}]),patch('augmentor_linux.macos_shortcuts.subprocess.run',return_value=subprocess.CompletedProcess([],0,'','')) as run:
            manager.ensure_service()
        arguments=run.call_args.args[0]
        self.assertEqual(arguments[-3:],[str(root/'scripts/register-macos-shortcut.py'),str(root.parents[2]),'install'])
        manager.close()

    def test_opening_without_login_registration_preserves_local_choice(self):
        manager=ManagedShortcutManager()
        with tempfile.TemporaryDirectory() as directory,patch.object(Path,'home',return_value=Path(directory)),patch.object(manager.local,'restore') as restore,patch.object(manager,'ensure_service') as ensure:
            manager.restore();restore.assert_called_once();ensure.assert_not_called()
        manager.close()


if __name__ == '__main__':unittest.main()
