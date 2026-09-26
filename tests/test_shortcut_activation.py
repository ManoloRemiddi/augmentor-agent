# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import errno
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import Mock, patch

from augmentor_linux.shortcut_activation import DesktopActivation


class ShortcutActivationTests(unittest.TestCase):
    def test_macos_cold_launch_uses_the_installed_native_application(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'Desktop.app/Contents/Resources/app'
            native=root.parents[1]/'MacOS/Augmentor Agent Desktop';native.parent.mkdir(parents=True);native.touch()
            with patch('augmentor_linux.shortcut_activation.ROOT',root),patch('augmentor_linux.shortcut_activation.sys.platform','darwin'):
                self.assertEqual(DesktopActivation(directory).command,[str(native)])

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
                self.assertEqual(launch.call_args.args, (command,))

    def test_connection_errors_do_not_launch_a_second_app(self):
        for error in (PermissionError(errno.EACCES, 'denied'), TimeoutError('timeout')):
            with self.subTest(error=error), patch('augmentor_linux.shortcut_activation.socket.socket') as factory:
                connection = factory.return_value.__enter__.return_value
                connection.connect.side_effect = error
                with patch('augmentor_linux.shortcut_activation.subprocess.Popen') as launch:
                    with self.assertRaises(type(error)):
                        DesktopActivation('/unused').activate()
                    launch.assert_not_called()

    def test_uncertain_send_is_not_replayed_as_a_launch(self):
        with patch('augmentor_linux.shortcut_activation.socket.socket') as factory:
            connection = factory.return_value.__enter__.return_value
            connection.sendall.side_effect = BrokenPipeError('delivery unknown')
            with patch('augmentor_linux.shortcut_activation.subprocess.Popen') as launch:
                with self.assertRaises(BrokenPipeError):
                    DesktopActivation('/unused').activate()
                launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
