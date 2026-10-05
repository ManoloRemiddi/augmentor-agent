# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Endpoint readiness without executing the proof's browser/server main."""
import ast
from pathlib import Path
import unittest


def endpoint_wait(clock):
    source = Path(__file__).resolve().parents[1] / 'scripts/browser-composable-proof.py'
    tree = ast.parse(source.read_text())
    definition = next(node for node in tree.body
                      if isinstance(node, ast.FunctionDef) and node.name == 'wait_debugging_endpoint')
    namespace = {'time': clock}
    exec(compile(ast.Module(body=[definition], type_ignores=[]), str(source), 'exec'), namespace)
    return namespace['wait_debugging_endpoint']


class Clock:
    def __init__(self):
        self.now = 0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class OwnedChrome:
    def __init__(self, clock, exit_at=None):
        self.clock, self.exit_at = clock, exit_at

    def poll(self):
        return 1 if self.exit_at is not None and self.clock.now >= self.exit_at else None


class PortFile:
    def __init__(self, clock, ready_at=0, partial='', read_seconds=0):
        self.clock, self.ready_at, self.partial, self.read_seconds = clock, ready_at, partial, read_seconds

    def read_text(self):
        self.clock.now += self.read_seconds
        if self.clock.now >= self.ready_at:
            return '1234\n/devtools/browser/owned\n'
        if self.partial is None:
            raise FileNotFoundError
        return self.partial


class DebuggingEndpointTests(unittest.TestCase):
    def test_missing_or_partial_file_waits_for_complete_endpoint(self):
        for partial in (None, '', '1234\n', 'bad\n/devtools/browser/owned', '1234\nwrong'):
            with self.subTest(partial=partial):
                clock = Clock()
                lines, elapsed = endpoint_wait(clock)(OwnedChrome(clock), PortFile(clock, .2, partial))
                self.assertEqual(lines, ['1234', '/devtools/browser/owned'])
                self.assertGreaterEqual(elapsed, .2)

    def test_running_browser_can_publish_after_old_five_second_window(self):
        clock = Clock()
        _, elapsed = endpoint_wait(clock)(OwnedChrome(clock), PortFile(clock, 8))
        self.assertGreaterEqual(elapsed, 8)
        self.assertLess(elapsed, 60)

    def test_still_running_browser_refuses_at_monotonic_deadline(self):
        clock = Clock()
        with self.assertRaises(TimeoutError):
            endpoint_wait(clock)(OwnedChrome(clock), PortFile(clock, 61))
        self.assertLessEqual(clock.now, 60.000001)

    def test_owned_process_exit_refuses_before_endpoint(self):
        clock = Clock()
        with self.assertRaises(RuntimeError):
            endpoint_wait(clock)(OwnedChrome(clock, .1), PortFile(clock, 9))
        self.assertLess(clock.now, .2)

    def test_exited_process_cannot_admit_complete_stale_file(self):
        clock = Clock()
        with self.assertRaises(RuntimeError):
            endpoint_wait(clock)(OwnedChrome(clock, 0), PortFile(clock))

    def test_process_exit_during_completed_read_refuses(self):
        clock = Clock()
        with self.assertRaises(RuntimeError):
            endpoint_wait(clock)(OwnedChrome(clock, .1), PortFile(clock, read_seconds=.2))

    def test_complete_read_after_deadline_refuses(self):
        clock = Clock()
        with self.assertRaises(TimeoutError):
            endpoint_wait(clock)(OwnedChrome(clock), PortFile(clock, read_seconds=61))


if __name__ == '__main__':
    unittest.main()
