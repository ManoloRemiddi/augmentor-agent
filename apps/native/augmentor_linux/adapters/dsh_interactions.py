# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Ephemeral DSH interaction ownership; never retry an answer automatically."""
import threading
import uuid

from ..pi_client import ContractError


class NativeInteractions:
    def __init__(self, operation, session, emit):
        self.operation, self.session, self.emit = operation, session, emit
        self.owner = str(uuid.uuid4())
        self.pending = {}
        self.attempted = set()
        self.closed = False
        self.lock = threading.RLock()

    def request(self, operation, **values):
        return self.operation(sessionId=self.session, owner=self.owner,
                              operation=operation, **values)

    def claim(self):
        with self.lock:
            if self.closed:
                raise ContractError('This interaction connection is closed.')
            self.request('claim')

    def poll(self):
        with self.lock:
            if self.closed:
                return
            rows = self.request('poll')['pending']
            current = {row['id']: row for row in rows}
            for identifier in self.pending.keys() - current.keys():
                self.emit({'method': 'interaction/resolved', 'rpcId': identifier,
                           'payload': {'sessionId': self.session}})
            for identifier, row in current.items():
                if identifier in self.pending or identifier in self.attempted:
                    continue
                kind = row['kind']
                if kind not in ('approval', 'question'):
                    raise ContractError('Unsupported DSH interaction.')
                payload = {**row['payload'], 'sessionId': self.session}
                if kind == 'approval':
                    payload['approvalId'] = identifier
                    payload['reason'] = payload.get('reason') or ''
                self.emit({'method': kind + '/requested', 'rpcId': identifier,
                           'payload': payload})
            self.pending = current

    def respond(self, identifier, value):
        with self.lock:
            row = self.pending.get(identifier)
            if self.closed or identifier in self.attempted or row is None or value.get('sessionId') != self.session:
                raise ContractError('This DSH interaction is no longer pending.')
            if row['kind'] == 'approval':
                if value.get('approvalId') != identifier:
                    raise ContractError('The approval identifier does not match.')
                answer = value.get('outcome')
            else:
                answer = value.get('answer')
            # Consume locally before I/O: a lost acknowledgement must not replay
            # the same decision, including after another poll.
            self.attempted.add(identifier)
            del self.pending[identifier]
            return self.request('answer', id=identifier, value=answer)

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            for identifier in self.pending:
                self.emit({'method': 'interaction/resolved', 'rpcId': identifier,
                           'payload': {'sessionId': self.session}})
            self.pending.clear()
            self.request('release')
