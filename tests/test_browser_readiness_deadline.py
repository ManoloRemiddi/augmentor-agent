# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bounded, sanitized readiness diagnostics for the external Browser proof."""
import ast
import json
from pathlib import Path
import time
import unittest


class Clock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def proof_helpers():
    source = Path(__file__).resolve().parents[1] / 'scripts/browser-composable-proof.py'
    tree = ast.parse(source.read_text())
    names = {'wait_for_browser_ready', 'safe_readiness_status'}
    definitions = [node for node in tree.body
                   if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {'json': json, 'time': time}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), str(source), 'exec'), namespace)
    return namespace


class BrowserReadinessDeadlineTests(unittest.TestCase):
    def test_ready_state_before_deadline_is_accepted(self):
        clock = Clock()

        def send(_):
            clock.now += 1
            return {'harness': 'pi', 'phase': 'ready', 'modelSelected': True}

        status, elapsed = proof_helpers()['wait_for_browser_ready'](
            send, 'pi', timeout=60, clock=clock.monotonic, sleep=clock.sleep)
        self.assertEqual(status['phase'], 'ready')
        self.assertEqual(elapsed, 1)

    def test_delayed_successful_read_after_deadline_is_refused(self):
        clock = Clock()

        def send(_):
            clock.now += 60.1
            return {'harness': 'pi', 'phase': 'ready', 'modelSelected': True}

        with self.assertRaises(TimeoutError) as caught:
            proof_helpers()['wait_for_browser_ready'](
                send, 'pi', timeout=60, clock=clock.monotonic, sleep=clock.sleep)
        self.assertEqual(json.loads(str(caught.exception))['status']['phase'], 'ready')

    def test_harness_mismatch_never_passes(self):
        clock = Clock()

        def send(_):
            return {'harness': 'dsh', 'phase': 'ready'}

        with self.assertRaises(TimeoutError):
            proof_helpers()['wait_for_browser_ready'](
                send, 'pi', timeout=.2, poll_interval=.1,
                clock=clock.monotonic, sleep=clock.sleep)

    def test_failure_receipt_omits_ids_paths_raw_errors_and_model_names(self):
        safe = proof_helpers()['safe_readiness_status']
        result = safe({
            'phase': 'connecting', 'harness': 'pi', 'running': False,
            'modelSelected': False, 'portConnectEvents': 2,
            'sessionId': 'private-session-id', 'error': '/home/private/path',
            'model': 'private-model-name',
        })
        self.assertEqual(result, {
            'phase': 'connecting', 'harness': 'pi', 'running': False,
            'modelSelected': False, 'portConnectEvents': 2,
        })
        self.assertIsNone(safe(None))


if __name__ == '__main__':
    unittest.main()
