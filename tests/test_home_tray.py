# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'apps/native'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton
from augmentor_linux import home_tray


class HomeTrayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.env = patch.dict(os.environ, {'XDG_CONFIG_HOME': self.folder.name})
        self.env.start(); self.addCleanup(self.env.stop)

    def test_remembers_address_without_credentials(self):
        url = 'http://nas.local:8123/home-lighting/lights'
        home_tray.save_url(url)
        self.assertEqual(home_tray.load_url(), url)
        self.assertEqual(stat.S_IMODE(home_tray.config_path().stat().st_mode), 0o600)
        for invalid in ('file:///etc/passwd', 'https://user:password@nas/',
                        'http://nas/?token=secret', 'https://nas/#key=secret',
                        '--app=evil', 'http://nas:bad/', 'http://nas/\npath'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                home_tray.save_url(invalid)
        self.assertEqual(home_tray.load_url(), url)

    def test_uses_existing_browser_without_a_shell_or_new_profile(self):
        url = 'https://home.example/home-lighting/lights'
        command = home_tray.browser_command(url, lambda name: '/usr/bin/chromium' if name == 'chromium' else None)
        self.assertEqual(command, ('/usr/bin/chromium', ['--app='+url, '--class=AugmentorHome']))
        self.assertIsNone(home_tray.browser_command(url, lambda _: None))

    def test_open_and_save_do_not_require_agent_pairing(self):
        opened = []
        tray = home_tray.HomeTray(self.app, opened.append)
        self.addCleanup(tray.tray.hide)
        tray.open_home()
        dialog = tray.dialog
        self.assertIsNotNone(dialog)
        tray.show_settings()
        self.assertIs(tray.dialog, dialog)
        dialog.findChild(QLineEdit).setText('http://nas.local:8123/home-lighting/lights')
        next(b for b in dialog.findChildren(QPushButton) if b.text() == 'Save and open').click()
        self.assertEqual(opened, ['http://nas.local:8123/home-lighting/lights'])
        tray.open_action.trigger()
        self.assertEqual(len(opened), 2)

    def test_stable_launcher_follows_selection(self):
        spec = importlib.util.spec_from_file_location('home_launch', ROOT/'scripts/home-launch.py')
        launch = importlib.util.module_from_spec(spec); spec.loader.exec_module(launch)
        data = Path(self.folder.name)/'data'; (data/'augmentor').mkdir(parents=True)
        release = Path(self.folder.name)/'release with spaces'
        (release/'apps/native/augmentor_linux').mkdir(parents=True)
        (release/'apps/native/augmentor_linux/home_tray.py').touch()
        (data/'augmentor/desktop.json').write_text(json.dumps({'root':str(release),'python':'/venv/python'}))
        with patch.dict(os.environ, {'XDG_DATA_HOME':str(data)}), patch.object(launch.os, 'execve') as execute:
            launch.main(['--background'])
            command = execute.call_args.args
            self.assertEqual(command[0], '/venv/python')
            self.assertEqual(command[1][-1], '--background')
            self.assertEqual(command[2]['PYTHONPATH'], str(release/'apps/native'))
            (release/'apps/native/augmentor_linux/home_tray.py').unlink()
            with self.assertRaisesRegex(RuntimeError, 'no Home launcher'):
                launch.main([])


if __name__ == '__main__':
    unittest.main()
