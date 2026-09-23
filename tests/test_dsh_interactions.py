# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from augmentor_linux.adapters.dsh_interactions import NativeInteractions
from augmentor_linux.pi_client import ContractError
from augmentor_linux.adapters.dsh_wire import DshClient, EventStream


class InteractionsTest(unittest.TestCase):
    def test_stream_close_releases_owner_without_clearing_replacement(self):
        old=Mock(); replacement=Mock()
        client=SimpleNamespace(interactions=replacement)
        stream=EventStream(client,'session',Mock(),Mock())
        stream.interactions=old
        stream.close()
        old.close.assert_called_once()
        self.assertIs(client.interactions,replacement)
        self.assertTrue(stream.closed.is_set())

    def test_wire_reply_requires_active_owner(self):
        client=DshClient.__new__(DshClient)
        client.interactions=None
        with self.assertRaises(ContractError):client.respond('id',{})
        client.interactions=Mock()
        client.respond('id',{'sessionId':'session'})
        client.interactions.respond.assert_called_once_with('id',{'sessionId':'session'})

    def make_client(self):
        self.rows = [{'id': 'approval', 'kind': 'approval', 'payload': {'toolName': 'bash'}}]
        self.calls, self.frames = [], []

        def operation(**payload):
            self.calls.append(payload)
            return {'pending': self.rows}

        return NativeInteractions(operation, 'session', self.frames.append)

    def test_poll_emits_once_and_resolves_cancelled_request(self):
        client = self.make_client()
        client.claim(); client.poll(); client.poll()
        self.assertEqual(len(self.frames), 1)
        self.assertEqual(self.frames[0]['payload']['reason'], '')
        self.rows = []
        client.poll()
        self.assertEqual(self.frames[-1]['method'], 'interaction/resolved')
        with self.assertRaises(ContractError):
            client.respond('approval', {'sessionId': 'session'})

    def test_lost_answer_acknowledgement_is_not_replayed_after_poll(self):
        client = self.make_client(); client.claim(); client.poll()
        original = client.operation

        def operation(**payload):
            result = original(**payload)
            if payload['operation'] == 'answer':
                raise TimeoutError('Lost acknowledgement')
            return result

        client.operation = operation
        value = {'sessionId': 'session', 'approvalId': 'approval', 'outcome': 'allowed-once'}
        with self.assertRaises(TimeoutError): client.respond('approval', value)
        client.poll()
        with self.assertRaises(ContractError): client.respond('approval', value)
        self.assertEqual(sum(c['operation'] == 'answer' for c in self.calls), 1)
        self.assertEqual(len(self.frames), 1)

    def test_close_releases_without_answering_and_refuses_other_session(self):
        client = self.make_client(); client.claim(); client.poll()
        with self.assertRaises(ContractError):
            client.respond('approval', {'sessionId': 'other'})
        client.close(); client.close()
        self.assertEqual(self.frames[-1]['method'], 'interaction/resolved')
        self.assertEqual(sum(c['operation'] == 'release' for c in self.calls), 1)
        self.assertFalse(any(c['operation'] == 'answer' for c in self.calls))


if __name__ == '__main__':
    unittest.main()
