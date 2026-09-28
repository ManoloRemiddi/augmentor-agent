# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import ctypes
from ctypes import wintypes
import sys
import threading
import unittest
from unittest.mock import Mock

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from augmentor_linux.windows_shortcuts import binding, Hotkeys, WM_HOTKEY, MOD_NOREPEAT


class WindowsShortcutMappingTests(unittest.TestCase):
    def test_portable_key_mapping_and_reserved_combinations(self):
        self.assertEqual(binding('Ctrl+Alt+Space')[:2], (3, 0x20))
        self.assertEqual(binding('Ctrl+Alt+Shift+F9')[:2], (7, 0x78))
        self.assertEqual(binding('Alt+K')[:2], (1, ord('K')))
        for sequence in ('Space', 'Shift+A', 'Meta+Space', 'Ctrl+F12', 'Fn+Space', 'Ctrl+A, Ctrl+B', 'Ctrl+;'):
            with self.subTest(sequence=sequence), self.assertRaises(ValueError): binding(sequence)

    def test_pipe_worker_commands_execute_on_qt_owner_thread(self):
        from augmentor_linux.windows_shell import Shell
        app = QApplication.instance() or QApplication([])
        target = Mock(); called = []; results = []
        target.dispatch.side_effect = lambda message: called.append((threading.get_ident(), message)) or {'active': True}
        shell = Shell(shortcuts=target)
        message = {'action': 'shortcut-status', 'instance': 'main'}
        worker = threading.Thread(target=lambda: results.append(shell.request(message)))
        timer = QTimer(); timer.timeout.connect(lambda: app.quit() if results else None)
        deadline = QTimer(); deadline.setSingleShot(True); deadline.timeout.connect(app.quit)
        try:
            worker.start(); timer.start(10); deadline.start(3000); app.exec()
            worker.join(1)
            self.assertFalse(worker.is_alive())
            self.assertEqual(called, [(threading.get_ident(), message)])
            self.assertEqual(results, [{'active': True}])
        finally: timer.stop(); deadline.stop(); shell.close()


@unittest.skipUnless(sys.platform == 'win32', 'requires actual Windows hotkey registration and event dispatch')
class WindowsNativeHotkeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def test_two_bindings_collision_failed_save_dispatch_and_cleanup(self):
        keys = Hotkeys(); received = []; persisted = []
        keys.pressed.connect(received.append)
        first, second, replacement = 'Ctrl+Alt+Shift+F9', 'Ctrl+Alt+Shift+F10', 'Ctrl+Alt+Shift+F11'
        try:
            keys.assign('main', first, persisted.append)
            keys.assign('secondary', second, persisted.append)
            original = dict(keys.active)
            with self.assertRaisesRegex(ValueError, 'other agent'):
                keys.assign('secondary', first, persisted.append)
            def failed_save(_sequence): raise PermissionError('fixture write denied')
            with self.assertRaises(PermissionError): keys.assign('main', replacement, failed_save)
            self.assertEqual(keys.active, original)
            self.assertEqual(persisted, [first, second])
            # The OS, not an in-memory duplicate check, rejects another thread's claim.
            attempts = []
            def compete():
                parsed = binding(first)
                success = keys.user.RegisterHotKey(None, 0x101, parsed[0] | MOD_NOREPEAT, parsed[1])
                attempts.append(bool(success))
                if success: keys.user.UnregisterHotKey(None, 0x101)
            worker = threading.Thread(target=compete); worker.start(); worker.join(3)
            self.assertFalse(worker.is_alive()); self.assertEqual(attempts, [False])
            # A posted WM_HOTKEY tests the real Windows/Qt dispatcher. This does
            # not simulate a physical key press or qualify keyboard layouts.
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.GetCurrentThreadId.argtypes = []; kernel.GetCurrentThreadId.restype = wintypes.DWORD
            post = keys.user.PostThreadMessageW
            post.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]; post.restype = wintypes.BOOL
            for name in ('main', 'secondary'):
                identifier, parsed = keys.active[name]
                self.assertTrue(post(kernel.GetCurrentThreadId(), WM_HOTKEY, identifier, parsed[0] | (parsed[1] << 16)))
            timer = QTimer(); timer.timeout.connect(lambda: self.app.quit() if len(received) == 2 else None)
            deadline = QTimer(); deadline.setSingleShot(True); deadline.timeout.connect(self.app.quit)
            try: timer.start(10); deadline.start(3000); self.app.exec()
            finally: timer.stop(); deadline.stop()
            self.assertEqual(received, ['main', 'secondary'])
            # A failed file save released the proposed combination as well.
            keys.assign('main', replacement, persisted.append)
        finally: keys.close()
        restored = Hotkeys()
        try:
            restored.assign('main', first); restored.assign('secondary', second)
        finally: restored.close()


if __name__ == '__main__': unittest.main()
