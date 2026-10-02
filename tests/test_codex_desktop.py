# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real desktop socket/client protocol with an isolated synthetic OS boundary."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('codex_desktop_client', ROOT / 'services/desktop/client.py')
client = importlib.util.module_from_spec(spec); spec.loader.exec_module(client)


class CodexDesktopProtocolTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='codex-desktop-socket-', dir='/tmp' if sys.platform == 'darwin' else None); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        environment = patch.dict(os.environ, {'XDG_RUNTIME_DIR': str(self.root), 'AUGMENTOR_DESKTOP_NO_AUTOSTART': '1'})
        environment.start(); self.addCleanup(environment.stop)
    def start(self):
        child = subprocess.Popen([sys.executable, str(ROOT / 'tests/fixtures/codex/desktop-service.py'), str(self.root)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def close():
            child.terminate(); child.communicate(timeout=5)
        self.addCleanup(close)
        self.assertTrue(json.loads(child.stdout.readline())['ready'])
    def call(self, method, owner='codex:one', **params):
        return client.call({'method': method, 'owner': owner, 'params': params}, start=False)
    def test_absent_status_is_inactive_without_starting_a_desktop_process(self):
        with patch.object(client.subprocess, 'Popen', side_effect=AssertionError('Must not autostart')):
            self.assertEqual(self.call('status', allowAbsent=True)['result'], {'active': False, 'sharing': False, 'owner': None, 'available': False})
            self.assertTrue(self.call('stop')['result']['stopped'])
            with self.assertRaisesRegex(RuntimeError, 'not connected'): self.call('status')
    def test_codex_namespace_is_accepted_but_other_owners_and_reused_tokens_are_refused(self):
        self.start()
        self.assertFalse(self.call('connect', 'invented:one')['ok'])
        self.assertTrue(self.call('connect')['result']['sharing'])
        self.assertFalse(self.call('stop', 'codex:other')['ok'])
        self.assertFalse(self.call('connect', 'dsh:other')['ok'])
        observation = self.call('capture')['result']
        self.assertEqual(observation['image']['mimeType'], 'image/jpeg')
        self.assertTrue(self.call('action', token=observation['token'], kind='click', x=1, y=1)['result']['dispatched'])
        self.assertFalse(self.call('action', token=observation['token'], kind='click', x=1, y=1)['ok'])
        self.assertTrue(self.call('stop')['result']['stopped'])
        self.assertFalse(self.call('status')['result']['active'])
        self.assertTrue(self.call('connect', 'pi:other')['ok'])
        self.assertTrue(self.call('stop', 'pi:other')['ok'])
