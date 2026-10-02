# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('codex_maintenance_fixture', ROOT/'scripts/maintenance.py')
maintenance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(maintenance)


class CodexMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.stack.enter_context(patch.dict(os.environ, {
            'XDG_STATE_HOME': str(self.root/'state'), 'XDG_CONFIG_HOME': str(self.root/'config'),
            'AUGMENTOR_SHARED_CONFIG': str(self.root/'config/shared'),
            'AUGMENTOR_CODEX_STATE': str(self.root/'codex'),
            'AUGMENTOR_CODEX_SOCKET': str(self.root/'codex.sock'),
        }))
        self.stack.enter_context(patch.object(maintenance, 'browser_processes', return_value=[]))
        self.desktop = self.stack.enter_context(patch.object(maintenance, 'desktop_call', return_value=None))
        self.ui = self.stack.enter_context(patch.object(maintenance, 'ui_call', return_value=None))
        self.companions = self.stack.enter_context(patch.object(maintenance, 'stop_companions'))

    def connection(self, failure=None):
        calls = []
        connection = Mock()
        def call(method, params=None):
            calls.append(method)
            if method == 'host.describe': return {'pid': 123, 'harness': 'codex'}
            if method == 'host.prepareShutdown' and failure: raise RuntimeError(failure)
            return {'ready': True, 'accepted': True}
        connection.call.side_effect = call
        def connect(path, protocol):
            if protocol == 'augmentor-pi/1': raise FileNotFoundError()
            self.assertEqual(protocol, 'augmentor-codex/1')
            self.assertEqual(path, str(self.root/'codex.sock'))
            return connection
        self.stack.enter_context(patch.object(maintenance, 'Connection', side_effect=connect))
        self.stack.enter_context(patch.object(maintenance, 'identity', return_value='fixture-start'))
        self.stack.enter_context(patch.object(maintenance, 'wait_exit'))
        return connection, calls

    def test_active_codex_refuses_before_closing_any_surface(self):
        connection, calls = self.connection('active or unconfirmed work')
        self.ui.return_value = {'pid': 456, 'busy': False}
        with self.assertRaisesRegex(RuntimeError, 'active or unconfirmed'):
            maintenance.prepare('all')
        self.assertEqual(calls, ['host.describe', 'host.prepareShutdown', 'host.cancelShutdown'])
        self.ui.assert_called_once_with('maintenance.status')
        self.companions.assert_not_called()
        connection.close.assert_called_once()

    def test_ui_becoming_busy_reopens_codex_without_shutting_it_down(self):
        _, calls = self.connection()
        self.ui.side_effect = [{'pid': 456, 'busy': False}, {'accepted': False}]
        with self.assertRaisesRegex(RuntimeError, 'became busy'):
            maintenance.prepare('all')
        self.assertEqual(calls, ['host.describe', 'host.prepareShutdown', 'host.cancelShutdown'])
        self.companions.assert_not_called()

    def test_idle_codex_is_prepared_then_stopped(self):
        _, calls = self.connection()
        maintenance.prepare('all')
        self.assertEqual(calls, ['host.describe', 'host.prepareShutdown', 'host.shutdown'])
        self.companions.assert_called_once()

    @unittest.skipUnless(Path('/proc').is_dir(), 'Linux maintenance process identity')
    def test_real_idle_host_exits_through_maintenance_rpc(self):
        child = subprocess.Popen(['node', str(ROOT/'dist/codex-runtime/src/main.js')], cwd=ROOT,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def cleanup():
            if child.poll() is None: child.kill()
            child.communicate(timeout=5)
        self.addCleanup(cleanup)
        self.assertTrue(json.loads(child.stdout.readline())['ready'])
        # Never contact an installed Pi socket during the isolated process proof.
        self.stack.enter_context(patch.object(maintenance, 'socket_path', return_value=str(self.root/'absent-pi.sock')))
        maintenance.prepare('all')
        self.assertEqual(child.wait(timeout=5), 0)
        self.assertFalse((self.root/'codex.sock').exists())

    def test_backup_preserves_codex_records_and_omits_live_socket(self):
        state = self.root/'codex'; state.mkdir()
        (state/'profiles.json').write_text('{"synthetic":true}')
        with socket.socket(socket.AF_UNIX) as listener:
            listener.bind(str(state/'runtime.sock'))
            with patch.dict(os.environ, {'XDG_STATE_HOME': str(self.root/'state'),
                    'XDG_CONFIG_HOME': str(self.root/'config'), 'XDG_DATA_HOME': str(self.root/'data'),
                    'AUGMENTOR_CODEX_STATE': str(state)}, clear=True):
                backup = maintenance.backup()
            self.assertEqual((backup/'state/codex/profiles.json').read_text(), '{"synthetic":true}')
            self.assertFalse((backup/'state/codex/runtime.sock').exists())
            self.assertEqual(backup.stat().st_mode & 0o777, 0o700)
        self.assertTrue((state/'profiles.json').exists())
