# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Parent protocol refusal tests; synthetic sockets do not qualify native AT-SPI."""
import copy
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import threading
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('a11y_parent_under_test', Path(__file__).resolve().parents[1] / 'services/desktop/a11y_helper.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@unittest.skipUnless(sys.platform == 'linux', 'Linux SOCK_SEQPACKET accessibility parent')
class AccessibilityParentTests(unittest.TestCase):
    def setUp(self):
        self.fresh_helper()
        self.starts = patch.object(module, 'process_start', side_effect=lambda pid: {101: 'target-start', 202: 'helper-start'}[pid])
        self.starts.start()
        self.addCleanup(self.starts.stop)

    def fresh_helper(self):
        self.parent, self.peer = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.parent.setblocking(False)
        self.helper = module.AccessibilityHelper.__new__(module.AccessibilityHelper)
        self.helper.socket = self.parent
        self.helper.process = Mock(pid=202)
        self.helper.process.poll.return_value = None
        self.helper.pid = 101
        self.helper.target_start = 'target-start'
        self.helper.helper_start = 'helper-start'
        self.helper.timeout = .1
        self.helper.closed = False
        self.helper.mutex = threading.Lock()
        self.helper.epoch = None
        self.helper.pins = None
        self.addCleanup(self.peer.close)
        self.addCleanup(self.helper.close)

    def reply(self):
        return {
            'helperPid': 202, 'targetPid': 101, 'targetStart': 'target-start',
            'inputQualified': False, 'valid': True, 'serial': 4, 'observedSerial': 4,
            'epoch': 'a' * 32, 'pins': {'sessionBusId': 'b' * 32, 'launcherOwner': ':1.2',
                'accessibilityBusId': 'c' * 32, 'registryOwner': ':1.3'},
            'complete': True, 'selectedOwner': ':1.9',
            'focus': {'owner': ':1.9', 'path': '/org/a11y/atspi/accessible/entry', 'role': 61,
                'password': False, 'focused': True, 'showing': True, 'defunct': False,
                'editable': True, 'enabled': False, 'sensitive': True},
        }

    def exchange(self, mutate=None, encode=json.dumps):
        errors = []
        def serve():
            try:
                request = json.loads(self.peer.recv(8192))
                reply = self.reply()
                reply.update(nonce=request['nonce'], generation=request['generation'])
                if mutate:
                    mutate(reply)
                self.peer.send(encode(reply).encode())
            except Exception as error:
                errors.append(error)
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        try:
            return self.helper.request('focus', generation=7)
        finally:
            thread.join(timeout=1)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])

    def test_valid_reply_retains_raw_state_and_pins_epoch(self):
        result = self.exchange()
        self.assertFalse(result['focus']['enabled'])
        self.assertTrue(result['focus']['sensitive'])
        self.assertEqual(self.helper.epoch, result['epoch'])
        self.assertFalse(self.helper.closed)

    def test_invalid_identity_permanently_retires_helper(self):
        for field, bad in [('nonce', '0' * 32), ('generation', True), ('helperPid', True),
                           ('targetPid', 102), ('targetStart', 'reused'), ('inputQualified', True),
                           ('valid', False), ('serial', True), ('epoch', 'bad')]:
            with self.subTest(field=field):
                # One isolated socket/helper for each terminal rejection.
                if self.helper.closed:
                    self.peer.close()
                    self.fresh_helper()
                with self.assertRaises((RuntimeError, ValueError)):
                    self.exchange(lambda value: value.__setitem__(field, bad))
                self.assertTrue(self.helper.closed)
                self.helper.process.terminate.assert_called_once()
                with self.assertRaisesRegex(RuntimeError, 'closed'):
                    self.helper.request('focus')

    def test_changed_epoch_or_bus_pin_requires_new_helper(self):
        original = self.exchange()
        self.helper.pins = copy.deepcopy(original['pins'])
        with self.assertRaisesRegex(RuntimeError, 'owner changed'):
            self.exchange(lambda value: value['pins'].__setitem__('registryOwner', ':1.4'))
        self.assertTrue(self.helper.closed)

    def test_foreign_focus_owner_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'focus identity'):
            self.exchange(lambda value: value['focus'].__setitem__('owner', ':1.10'))
        self.assertTrue(self.helper.closed)

    def test_password_flag_must_be_boolean(self):
        with self.assertRaisesRegex(RuntimeError, 'focus identity'):
            self.exchange(lambda value: value['focus'].__setitem__('password', 0))

    def test_hidden_defunct_and_malformed_focus_rejected(self):
        for field, bad in [('showing', False), ('focused', False), ('defunct', True),
                           ('role', True), ('path', '/../../entry'), ('path', '/' + 'a' * 1025)]:
            with self.subTest(field=field):
                if self.helper.closed:
                    self.peer.close()
                    self.fresh_helper()
                with self.assertRaisesRegex(RuntimeError, 'focus identity'):
                    self.exchange(lambda value: value['focus'].__setitem__(field, bad))
                self.assertTrue(self.helper.closed)

    def test_changed_epoch_rejected(self):
        self.exchange()
        with self.assertRaisesRegex(RuntimeError, 'owner changed'):
            self.exchange(lambda value: value.__setitem__('epoch', 'd' * 32))

    def test_focus_must_have_matching_event_serial(self):
        with self.assertRaisesRegex(RuntimeError, 'focus identity'):
            self.exchange(lambda value: value.__setitem__('observedSerial', 3))

    def test_incomplete_result_cannot_export_focus(self):
        with self.assertRaisesRegex(RuntimeError, 'Incomplete'):
            self.exchange(lambda value: value.__setitem__('complete', False))

    def test_duplicate_json_field_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.exchange(encode=lambda value: json.dumps(value)[:-1] + ',"valid":true}')
        self.assertTrue(self.helper.closed)

    def test_oversized_reply_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'oversized'):
            self.exchange(lambda value: value.__setitem__('padding', 'x' * 70000))

    def test_pre_cancel_sends_no_request(self):
        cancel = threading.Event()
        cancel.set()
        with self.assertRaisesRegex(RuntimeError, 'cancelled'):
            self.helper.request('focus', cancel=cancel)
        self.assertTrue(self.helper.closed)
        self.assertEqual(self.peer.recv(8192), b'')

    def test_stalled_reply_retires_helper_and_cannot_be_accepted_later(self):
        self.helper.process.wait.side_effect = [subprocess.TimeoutExpired('owned-helper', .2), None]
        with self.assertRaisesRegex(RuntimeError, 'deadline'):
            self.helper.request('focus')
        self.assertTrue(self.helper.closed)
        self.helper.process.kill.assert_called_once()
        with self.assertRaisesRegex(RuntimeError, 'closed'):
            self.helper.request('focus')

    def test_process_reuse_rejected(self):
        module.process_start.side_effect = lambda pid: 'reused-start'
        with self.assertRaisesRegex(RuntimeError, 'process identity'):
            self.exchange()


if __name__ == '__main__':
    unittest.main()
