# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import errno
import os
from pathlib import Path
import socket
import shlex
import sys
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtGui import QKeySequence
from augmentor_linux.macos_shortcut_service import ShortcutService, request, receive
from augmentor_linux.macos_shortcuts import RemoteShortcutManager, select_manager


class MacShortcutServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='ash-')
        self.root = Path(self.directory.name)
        helper = self.root/'helper'
        script = self.root/'helper.py'
        script.write_text('import json,sys\n'
                          'if sys.argv[1]=="--resolve":\n'
                          ' print(json.dumps({"keyCode":38}));sys.exit()\n'
                          'print(json.dumps({"event":"ready"}),flush=True)\n'
                          'sys.stdin.read()\n')
        helper.write_text('#!/bin/sh\nexec '+shlex.quote(sys.executable)+' '+shlex.quote(str(script))+' "$@"\n')
        helper.chmod(0o700)
        self.environment = patch.dict(os.environ, {
            'XDG_RUNTIME_DIR': str(self.root/'run'),
            'XDG_CONFIG_HOME': str(self.root/'config'),
            'AUGMENTOR_MACOS_HOTKEY': str(helper),
        })
        self.environment.start()
        self.service = ShortcutService()

    def tearDown(self):
        self.service.close()
        self.environment.stop()
        self.directory.cleanup()

    def test_settings_use_one_service_owner_and_survive_client_close(self):
        self.service.start()
        client = select_manager()
        self.assertIsInstance(client, RemoteShortcutManager)
        sequence = QKeySequence('Ctrl+Alt+J')
        self.assertEqual(client.save(sequence), sequence[0].toCombined())
        child = self.service.manager.process
        self.assertTrue(request({'operation': 'status'})['active'])
        client.close()
        self.assertIsNone(child.poll())
        self.assertEqual(client.save(sequence), sequence[0].toCombined())
        self.assertIs(self.service.manager.process, child)
        self.service.close()
        self.assertIsNotNone(child.poll())
        replacement = ShortcutService()
        try:
            replacement.start()
            self.assertTrue(request({'operation': 'status'})['active'])
            self.assertEqual(replacement.manager.key, sequence[0].toCombined())
        finally:
            replacement.close()

    def test_other_named_windows_can_edit_the_global_shortcuts(self):
        self.service.start()
        with patch.dict(os.environ,{'AUGMENTOR_WINDOW_ID':'qualification'}):
            client=select_manager()
            self.assertEqual(client.instance,'main')
            client.save(QKeySequence('Ctrl+Alt+K'),'secondary')
        self.assertEqual(request({'operation':'status'})['key'],'Fn+Space')
        self.assertTrue(request({'operation':'status','instance':'secondary'})['active'])

    def test_fn_space_is_persisted_on_first_launch_and_restored(self):
        self.service.start()
        self.assertEqual(request({'operation':'status'})['key'],'Fn+Space')
        self.assertEqual(self.service.manager.binding[-2:],['49','131072'])
        self.assertIn('Fn+Space',(self.root/'config/augmentor/shortcut.json').read_text())
        child=self.service.manager.process
        self.assertEqual(RemoteShortcutManager().save('Fn+Space'),'Fn+Space')
        self.assertIs(child,self.service.manager.process)
        self.service.close()
        replacement=ShortcutService()
        try:
            replacement.start()
            self.assertEqual(request({'operation':'status'})['key'],'Fn+Space')
            self.assertTrue(request({'operation':'status'})['active'])
        finally:replacement.close()

    def test_second_owner_cannot_remove_first_owners_socket(self):
        self.service.start()
        other = ShortcutService()
        try:
            with self.assertRaises(BlockingIOError):other.start()
            self.assertEqual(request({'operation': 'status'})['pid'], os.getpid())
        finally:other.close()

    def test_secondary_is_unassigned_then_persists_without_changing_primary(self):
        self.service.start()
        main_file = self.root/'config/augmentor/shortcut.json'
        original = main_file.read_bytes()
        primary = self.service.manager.process
        self.assertFalse(request({'operation': 'status', 'instance': 'secondary'})['active'])
        key = RemoteShortcutManager().save(QKeySequence('Ctrl+Shift+K'), 'secondary')
        self.assertEqual(request({'operation': 'status', 'instance': 'secondary'})['key'], key)
        self.assertEqual(main_file.read_bytes(), original)
        self.assertIs(self.service.manager.process, primary)
        self.service.close()
        replacement = ShortcutService()
        try:
            replacement.start()
            self.assertEqual(request({'operation': 'status'})['key'], 'Fn+Space')
            self.assertEqual(request({'operation': 'status', 'instance': 'secondary'})['key'], key)
            self.assertTrue(request({'operation': 'status', 'instance': 'secondary'})['active'])
        finally:
            replacement.close()

    def test_cross_window_conflict_and_bad_instance_preserve_both_keys(self):
        self.service.start()
        client = RemoteShortcutManager()
        client.save(QKeySequence('Ctrl+Shift+K'), 'secondary')
        before = {p.name: p.read_bytes() for p in (self.root/'config/augmentor').glob('shortcut*.json')}
        processes = {name: manager.process for name, manager in self.service.managers.items()}
        for message in ({'operation': 'save', 'instance': 'secondary', 'sequence': 'Fn+Space'},
                        {'operation': 'save', 'instance': '../main', 'sequence': 'Ctrl+J'},
                        {'operation': 'status', 'instance': []}):
            with self.assertRaises(RuntimeError): request(message)
        self.assertEqual(before, {p.name: p.read_bytes() for p in (self.root/'config/augmentor').glob('shortcut*.json')})
        for name, process in processes.items():
            self.assertIs(self.service.managers[name].process, process)
            self.assertIsNone(process.poll())

    def test_invalid_request_preserves_binding_and_listener(self):
        self.service.start()
        request({'operation':'save','sequence':'Ctrl+Alt+J'})
        child = self.service.manager.process
        for message in ({'operation':'activate'}, {'operation':'save','sequence':42},
                        {'operation':'save','sequence':'Ctrl+J, Ctrl+K'}):
            with self.subTest(message=message), self.assertRaises(RuntimeError):request(message)
        self.assertIs(self.service.manager.process, child)
        self.assertTrue(request({'operation':'status'})['active'])

    def test_live_update_reservation_defers_busy_work_and_fences_saves_and_activation(self):
        self.service.start()
        token='a'*32
        def control(action):
            return request({'operation':'maintenance','method':'host.maintenance.'+action,
                            'params':{} if action=='status' else {'token':token}})['maintenance']
        original=(self.root/'config/augmentor/shortcut.json').read_bytes()
        child=self.service.manager.process
        with self.service.admission.work():
            with self.assertRaises(RuntimeError):control('prepare')
            self.assertEqual(control('status')['active'],1)
        self.assertEqual(control('prepare')['phase'],'prepared')
        with self.assertRaises(RuntimeError):request({'operation':'save','sequence':'Ctrl+Alt+J'})
        with patch.object(self.service.activations['main'],'activate') as launch:
            self.service.activate('main');launch.assert_not_called()
            self.assertEqual(control('cancel')['phase'],'ready')
            self.service.activate('main');launch.assert_called_once()
        self.assertEqual((self.root/'config/augmentor/shortcut.json').read_bytes(),original)
        self.assertIs(self.service.manager.process,child);self.assertIsNone(child.poll())

    def test_observed_commit_acknowledges_before_normal_shortcut_service_cleanup(self):
        self.service.start()
        token='b'*32
        def control(action):
            return request({'operation':'maintenance','method':'host.maintenance.'+action,'params':{'token':token}})
        prepared=control('prepare');self.assertEqual(prepared['maintenance']['phase'],'prepared')
        self.assertEqual(prepared['pid'],os.getpid());self.assertEqual(prepared['maintenanceAdmission'],1)
        child=self.service.manager.process
        self.assertEqual(control('commit')['maintenance']['phase'],'closing')
        self.assertTrue(self.service.stopping.wait(2))
        self.assertIsNone(child.poll())
        self.service.close();self.assertIsNotNone(child.poll())

    def test_uncertain_service_probe_does_not_take_local_ownership(self):
        for error in (TimeoutError('uncertain'), PermissionError(errno.EACCES, 'denied')):
            with patch('augmentor_linux.macos_shortcut_service.request', side_effect=error):
                with self.assertRaises(type(error)):select_manager()

    def test_oversized_message_does_not_stop_service(self):
        self.service.start()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(3)
            connection.connect(str(self.root/'run/shortcut-control.sock'))
            connection.sendall(b'x'*4097)
            self.assertFalse(receive(connection)['ok'])
        self.assertTrue(request({'operation':'status'})['ok'])


if __name__ == '__main__':unittest.main()
