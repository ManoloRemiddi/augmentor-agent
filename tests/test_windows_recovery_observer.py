# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('source_recovery_observer', ROOT/'scripts/windows-recover-source.py')
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)


class InstallerClock:
    def __init__(self, completes_at=None, exit_code=0):
        self.elapsed = 0
        self.completes_at = completes_at
        self.exit_code = exit_code
        self.waits = []

    def clock(self):
        return self.elapsed

    def wait(self, *, timeout):
        self.waits.append(timeout)
        if self.completes_at is not None and self.elapsed + timeout >= self.completes_at:
            self.elapsed = self.completes_at
            return self.exit_code
        self.elapsed += timeout
        raise TimeoutError('The same installer is still running.')


class RecoveryObserverTests(unittest.TestCase):
    def test_large_source_installation_can_finish_after_old_five_minute_limit(self):
        installer = InstallerClock(completes_at=326)
        self.assertEqual(observer.wait_for_source_installer(installer, clock=installer.clock), 0)
        self.assertEqual(installer.elapsed, 326)
        self.assertTrue(all(0 < wait <= 5 for wait in installer.waits))

    def test_unknown_installer_outcome_has_a_bounded_preserving_deadline(self):
        installer = InstallerClock()
        with self.assertRaisesRegex(TimeoutError, 'still running.*preserved'):
            observer.wait_for_source_installer(installer, clock=installer.clock)
        self.assertEqual(installer.elapsed, 600)
        self.assertTrue(all(0 < wait <= 5 for wait in installer.waits))

    def test_terminal_installer_failure_is_returned_without_retry(self):
        installer = InstallerClock(completes_at=1, exit_code=74)
        self.assertEqual(observer.wait_for_source_installer(installer, clock=installer.clock), 74)
        self.assertEqual(len(installer.waits), 1)


if __name__ == '__main__':
    unittest.main()
