# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json
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
from platform_adapters.transport import LocalSocket


class SupervisorSafetyTests(unittest.TestCase):
    def test_owner_reservation_fences_restarts_and_refuses_commit_while_children_live(self):
        supervisor=owner.Supervisor(shell=Mock());token='b'*32
        control=lambda action:supervisor.dispatch({'action':'maintenance','method':'host.maintenance.'+action,'params':{'token':token}})['maintenance']
        supervisor.child=Mock();supervisor.child.poll.return_value=None
        self.assertEqual(control('prepare')['phase'],'prepared')
        for action in ('start-dsh','start-prompts','start-memory','stop-failed-setup','exit-if-empty'):
            with self.assertRaises(owner.MaintenanceBusy):supervisor.dispatch({'action':action})
        with self.assertRaises(owner.MaintenanceBusy):
            supervisor.dispatch({'action':'shortcut-save','instance':'main','sequence':'Ctrl+Alt+Space'})
        self.assertTrue(supervisor.dispatch({'action':'status'})['dsh']['running'])
        with self.assertRaises(owner.MaintenanceBusy):control('commit')
        self.assertFalse(supervisor.shutdown.is_set());supervisor.child.terminate.assert_not_called()
        self.assertEqual(control('cancel')['phase'],'ready')
        supervisor.child=None
        self.assertEqual(control('prepare')['phase'],'prepared')
        self.assertEqual(control('commit')['phase'],'closing')
        self.assertFalse(supervisor.shutdown.is_set(),'dispatch must not exit before the handler acknowledges')

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
    def test_companions_have_one_owner_and_die_with_it(self):
        import win32api
        import win32con
        import win32event

        def call(endpoint, method):
            with LocalSocket() as connection:
                connection.settimeout(5)
                connection.connect(str(endpoint))
                connection.sendall((json.dumps({'protocol': 'augmentor-prompts/1',
                    'id': 'ownership-check', 'method': method, 'params': {}})+'\n').encode())
                with connection.makefile('rb') as stream:
                    response = json.loads(stream.readline(1024*1024+1))
            self.assertNotIn('error', response)
            return response['result']

        def ready(operation):
            deadline = time.monotonic()+20
            while True:
                try: return operation()
                except FileNotFoundError:
                    if time.monotonic() > deadline: self.fail('An owned companion did not become ready.')
                    time.sleep(.1)

        with tempfile.TemporaryDirectory() as temporary:
            root = private_directory(Path(temporary)/'private')
            env = {**os.environ, **{key: str(private_directory(root/name)) for key, name in (
                ('XDG_RUNTIME_DIR', 'run'), ('XDG_CONFIG_HOME', 'config'),
                ('XDG_DATA_HOME', 'data'), ('XDG_STATE_HOME', 'state'),
                ('AUGMENTOR_SHARED_STATE', 'shared'), ('AUGMENTOR_SHARED_DATA', 'shared-data'))}}
            process = subprocess.Popen([sys.executable, '-I', '-Xutf8', '-B',
                str(ROOT/'services/windows_supervisor.py')], env=env, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
            handles = []
            try:
                endpoint = Path(env['XDG_RUNTIME_DIR'])/'supervisor'
                ready(lambda: owner.request('status', owner=endpoint))
                for name, filename, method in (
                    ('prompts', 'prompts.sock', 'host.describe'),
                    ('memory', 'dual-memory.sock', 'memory.dual.describe')):
                    first = owner.request('start-'+name, owner=endpoint)['companions'][name]
                    self.assertTrue(first['running'])
                    details = ready(lambda: call(Path(env['AUGMENTOR_SHARED_STATE'])/filename, method))
                    self.assertIsInstance(details['pid'], int)
                    self.assertNotEqual(details['pid'], first['ownerProcessPid'])
                    handles.append(win32api.OpenProcess(win32con.SYNCHRONIZE, False, details['pid']))
                    repeated = owner.request('start-'+name, owner=endpoint)['companions'][name]
                    self.assertEqual(repeated['ownerProcessPid'], first['ownerProcessPid'])
                with self.assertRaisesRegex(ValueError, 'running component'):
                    owner.request('exit-if-empty', owner=endpoint)
                with self.assertRaisesRegex(ValueError, 'Unsupported'):
                    owner.request('start-prompts', owner=endpoint, command='untrusted')
                process.kill()  # Deliberate fixture fault, not a normal Quit.
                process.communicate(timeout=10)
                for handle in handles:
                    self.assertEqual(win32event.WaitForSingleObject(handle, 5000), win32event.WAIT_OBJECT_0)
            finally:
                if process.poll() is None: process.kill()
                _out, errors = process.communicate(timeout=10)
                for handle in handles:
                    win32event.WaitForSingleObject(handle, 5000)
                    handle.Close()
                if errors: print(errors.decode('utf-8', errors='replace'))

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
                token='a'*32
                def control(action):
                    return owner.request('maintenance',owner=endpoint,method='host.maintenance.'+action,
                        params={'token':token})['maintenance']
                self.assertEqual(control('prepare')['phase'],'prepared')
                with self.assertRaisesRegex(ValueError,'maintenance'):
                    owner.request('shortcut-save',owner=endpoint,instance='main',sequence='Ctrl+Alt+F8')
                self.assertEqual(owner.request('shortcut-status',owner=endpoint,instance='main')['key'],first['key'])
                self.assertEqual(control('cancel')['phase'],'ready')
                self.assertEqual(control('prepare')['phase'],'prepared')
                self.assertEqual(control('commit')['phase'],'closing')
                for process in processes:
                    _out, errors = process.communicate(timeout=10)
                    self.assertEqual(process.returncode, 0, errors.decode('utf-8', errors='replace'))
                restarted = subprocess.Popen([sys.executable, '-I', '-Xutf8', '-B',
                    str(ROOT/'services/windows_supervisor.py')], env=env, stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
                processes.append(restarted)
                deadline = time.monotonic()+15
                while True:
                    try:
                        restored = owner.request('shortcut-status', owner=endpoint, instance='main'); break
                    except FileNotFoundError:
                        if time.monotonic() > deadline: self.fail('No restarted shortcut owner became ready.')
                        time.sleep(.1)
                self.assertTrue(restored['active']); self.assertEqual(restored['key'], first['key'])
                self.assertEqual(owner.request('shortcut-status', owner=endpoint, instance='secondary')['key'], second['key'])
                owner.request('exit-if-empty', owner=endpoint)
                _out, errors = restarted.communicate(timeout=10)
                self.assertEqual(restarted.returncode, 0, errors.decode('utf-8', errors='replace'))
            finally:
                for process in processes:
                    if process.poll() is None: process.kill()
                    process.communicate(timeout=10)


if __name__ == '__main__': unittest.main()
