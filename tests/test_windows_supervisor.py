# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))
import windows_supervisor as owner
from platform_adapters.paths import private_directory


class SupervisorSafetyTests(unittest.TestCase):
    def test_published_profile_cannot_be_stopped_as_failed_setup(self):
        supervisor = owner.Supervisor()
        supervisor.child = Mock(); supervisor.child.poll.return_value = None
        with patch.dict(os.environ, {'XDG_DATA_HOME': '/fixture/data'}), \
             patch('dsh.setup.current', return_value={'home': str(owner.managed_directory()/'home')}):
            with self.assertRaisesRegex(ValueError, 'already selected'):
                supervisor.dispatch({'action': 'stop-failed-setup'})
        supervisor.child.terminate.assert_not_called()

    def test_exit_requires_no_running_component(self):
        supervisor = owner.Supervisor()
        supervisor.child = Mock(); supervisor.child.poll.return_value = None
        with self.assertRaisesRegex(ValueError, 'running component'):
            supervisor.dispatch({'action': 'exit-if-empty'})
        self.assertFalse(supervisor.shutdown.is_set())
        supervisor.child.terminate.assert_not_called()

    def test_finished_child_job_is_closed_before_reporting_stopped(self):
        supervisor = owner.Supervisor()
        child = Mock(); child.poll.return_value = 7; child.wait.return_value = 7
        supervisor.child = child
        self.assertEqual(supervisor.status()['dsh'], {'running': False, 'exitCode': 7})
        child.wait.assert_called_once(); self.assertIsNone(supervisor.child)


@unittest.skipUnless(sys.platform == 'win32', 'requires real Windows named-pipe ownership')
class WindowsSupervisorTests(unittest.TestCase):
    def test_competing_startups_produce_one_authenticated_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = private_directory(Path(temporary)/'private')
            env = {**os.environ, 'XDG_RUNTIME_DIR': str(private_directory(root/'run')),
                   'XDG_CONFIG_HOME': str(private_directory(root/'config')),
                   'XDG_DATA_HOME': str(private_directory(root/'data'))}
            processes = [subprocess.Popen([sys.executable, '-I', '-Xutf8', '-B',
                str(ROOT/'services/windows_supervisor.py')], env=env, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW) for _ in range(2)]
            try:
                endpoint = Path(env['XDG_RUNTIME_DIR'])/'supervisor'
                deadline = time.monotonic()+15
                while True:
                    try:
                        status = owner.request('status', owner=endpoint); break
                    except FileNotFoundError:
                        if time.monotonic() > deadline: self.fail('No Windows supervisor became ready.')
                        time.sleep(.1)
                self.assertFalse(status['dsh']['running'])
                # Save/restore crosses the named-pipe worker into the real owner
                # event loop. The second window cannot steal the first binding.
                first = owner.request('shortcut-save', owner=endpoint, instance='main', sequence='Ctrl+Alt+Shift+F9')
                self.assertTrue(first['active'])
                second = owner.request('shortcut-save', owner=endpoint, instance='secondary', sequence='Ctrl+Alt+Shift+F10')
                with self.assertRaisesRegex(ValueError, 'other agent'):
                    owner.request('shortcut-save', owner=endpoint, instance='secondary', sequence='Ctrl+Alt+Shift+F9')
                self.assertEqual(owner.request('shortcut-status', owner=endpoint, instance='secondary')['key'], second['key'])
                while all(p.poll() is None for p in processes) and time.monotonic() < deadline: time.sleep(.1)
                self.assertEqual(sum(p.poll() is None for p in processes), 1)
                with self.assertRaisesRegex(ValueError, 'Unsupported'):
                    owner.request('run-arbitrary-command', owner=endpoint)
                with self.assertRaisesRegex(ValueError, 'different Augmentor'):
                    owner.request('status', root=root/'wrong-app', owner=endpoint)
                owner.request('exit-if-empty', owner=endpoint)
                for process in processes:
                    _out, errors = process.communicate(timeout=10)
                    self.assertEqual(process.returncode, 0, errors.decode('utf-8', errors='replace'))
            finally:
                for process in processes:
                    if process.poll() is None: process.kill()
                    process.communicate(timeout=10)


if __name__ == '__main__': unittest.main()
