# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import errno
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from augmentor_linux.shortcut_activation import DesktopActivation


class ShortcutActivationTests(unittest.TestCase):
    def test_windows_cold_launch_names_main_even_if_caller_was_secondary(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'app';root.mkdir();native=root/'Augmentor.exe';native.touch()
            with patch('augmentor_linux.shortcut_activation.ROOT',root),patch('augmentor_linux.shortcut_activation.sys.platform','win32'):
                self.assertEqual(DesktopActivation(directory).command,[str(native),'--instance','main'])

    def test_macos_cold_launch_uses_the_installed_native_application(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'Desktop.app/Contents/Resources/app'
            native=root.parents[1]/'MacOS/Augmentor Agent Desktop';native.parent.mkdir(parents=True);native.touch()
            with patch('augmentor_linux.shortcut_activation.ROOT',root),patch('augmentor_linux.shortcut_activation.sys.platform','darwin'):
                self.assertEqual(DesktopActivation(directory).command,[str(native)])

    @unittest.skipIf(sys.platform == 'win32', 'Unix endpoint fixture; native Windows activation is exercised by the desktop proof')
    def test_running_app_receives_one_toggle_without_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
                server.bind(str(Path(directory)/'augmentor-linux-pi.sock'))
                server.listen(1)
                with patch('augmentor_linux.shortcut_activation.subprocess.Popen') as launch:
                    self.assertEqual(DesktopActivation(directory).activate(), 'delivered')
                    connection, _ = server.accept()
                    with connection:
                        self.assertEqual(connection.recv(100), b'toggle')
                        self.assertEqual(connection.recv(100), b'')
                    launch.assert_not_called()

    @unittest.skipIf(sys.platform == 'win32', 'Unix endpoint fixture; native Windows activation is exercised by the desktop proof')
    def test_secondary_toggle_never_reaches_primary_and_cold_launch_names_instance(self):
        with tempfile.TemporaryDirectory() as directory:
            servers = []
            try:
                for name in ('augmentor-linux-pi.sock', 'augmentor-linux-pi-secondary.sock'):
                    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    server.bind(str(Path(directory)/name)); server.listen(1); server.settimeout(.05)
                    servers.append(server)
                with patch('augmentor_linux.shortcut_activation.subprocess.Popen') as launch:
                    activation = DesktopActivation(directory, ['/app/launcher'], instance='secondary')
                    self.assertEqual(activation.activate(), 'delivered')
                    connection, _ = servers[1].accept()
                    with connection: self.assertEqual(connection.recv(100), b'toggle')
                    with self.assertRaises(TimeoutError): servers[0].accept()
                    launch.assert_not_called()
                    servers[1].close()
                    self.assertEqual(activation.activate(), 'launched')
                    self.assertEqual(launch.call_args.args[0], ['/app/launcher', '--instance', 'secondary'])
            finally:
                for server in servers: server.close()

    def test_absent_app_launches_once_while_starting_then_can_restart_after_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            child = Mock()
            child.poll.side_effect = [None, 0]
            command = ['/bundle path/python', '-B', '/bundle path/launch.py', 'desktop']
            with patch('augmentor_linux.shortcut_activation.subprocess.Popen', return_value=child) as launch:
                activation = DesktopActivation(directory, command)
                self.assertEqual(activation.activate(), 'launched')
                self.assertEqual(activation.activate(), 'starting')
                self.assertEqual(activation.activate(), 'launched')
                self.assertEqual(launch.call_count, 2)
                expected = command + (['--instance', 'main'] if sys.platform == 'win32' else [])
                self.assertEqual(launch.call_args.args, (expected,))

    def test_connection_errors_do_not_launch_a_second_app(self):
        for error in (PermissionError(errno.EACCES, 'denied'), TimeoutError('timeout')):
            with self.subTest(error=error), patch('augmentor_linux.shortcut_activation.LocalSocket') as factory:
                connection = factory.return_value.__enter__.return_value
                connection.connect.side_effect = error
                with patch('augmentor_linux.shortcut_activation.subprocess.Popen') as launch:
                    with self.assertRaises(type(error)):
                        DesktopActivation('/unused').activate()
                    launch.assert_not_called()

    def test_uncertain_send_is_not_replayed_as_a_launch(self):
        with patch('augmentor_linux.shortcut_activation.LocalSocket') as factory:
            connection = factory.return_value.__enter__.return_value
            connection.sendall.side_effect = BrokenPipeError('delivery unknown')
            with patch('augmentor_linux.shortcut_activation.subprocess.Popen') as launch:
                with self.assertRaises(BrokenPipeError):
                    DesktopActivation('/unused').activate()
                launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
