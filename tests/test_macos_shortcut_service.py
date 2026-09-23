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

    def test_second_owner_cannot_remove_first_owners_socket(self):
        self.service.start()
        other = ShortcutService()
        try:
            with self.assertRaises(BlockingIOError):other.start()
            self.assertEqual(request({'operation': 'status'})['pid'], os.getpid())
        finally:other.close()

    def test_invalid_request_preserves_binding_and_listener(self):
        self.service.start()
        request({'operation':'save','sequence':'Ctrl+Alt+J'})
        child = self.service.manager.process
        for message in ({'operation':'activate'}, {'operation':'save','sequence':42},
                        {'operation':'save','sequence':'Ctrl+J, Ctrl+K'}):
            with self.subTest(message=message), self.assertRaises(RuntimeError):request(message)
        self.assertIs(self.service.manager.process, child)
        self.assertTrue(request({'operation':'status'})['active'])

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
