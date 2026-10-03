# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bounded, transport-independent Live transcript and backend correlation."""
import time
import math
import uuid

INSTRUCTIONS = """You are Augmentor's voice interface. The application owns reasoning, memory and tools.
Delegate EVERY user request to the client, including questions, greetings and follow-ups.
Do not answer from your own knowledge or perform tasks. Remain silent until the application
supplies verified public results in commentary. Speak only those results naturally, preserving
their uncertainty. Never invent progress or claim an action succeeded. Let the user finish.
Stop speaking when interrupted. No unprompted greetings or independent conversation."""


class LiveDialogue:
    def __init__(self, submit, send, clear, pause_ms=800, hands_free=False, clock=time.monotonic):
        self.submit, self.send, self.clear, self.clock = submit, send, clear, clock
        self.pause = pause_ms / 1000
        self.hands_free = hands_free
        self.fragments = []
        self.consumed_ms = -1
        self.last_input = self.clock()
        self.last_speech = self.clock()
        self.manual_pending = False
        self.manual_recording = False
        self.delegation = None
        self.delegations = set()
        self.requests = {}
        self.current = None
        self.output_allowed = False
        self.awaiting_output = set()
        self.seconds = None
        self.seen = set()
        self.live_turn = None
        self.backend_seq = -1

    @property
    def working(self):
        return bool(self.current and not self.requests[self.current]['done'])

    def interrupt(self):
        self.output_allowed = False
        self.awaiting_output.clear()
        self.clear()

    def receive(self, event):
        kind = event.get('type')
        if kind == 'session.input_transcript.delta':
            text, end = event.get('delta'), event.get('end_ms')
            if not isinstance(text, str) or not isinstance(end, (int, float)) or end <= self.consumed_ms:
                return
            identifier = event.get('event_id')
            if identifier and identifier in self.seen: return
            if identifier:
                if len(self.seen) >= 4096: raise ValueError('Voice event limit reached. Reopen Voice.')
                self.seen.add(identifier)
            if sum(len(v[0]) for v in self.fragments) + len(text) > 8192:
                raise ValueError('Voice transcript is too long. Reopen Voice.')
            if not self.fragments: self.interrupt()
            self.fragments.append((text, end))
            self.last_input = self.clock()
        elif kind == 'session.delegation.created':
            value = event.get('delegation', {})
            if value.get('target') != 'client': raise ValueError('Voice must delegate to Augmentor.')
            identifier = value.get('id')
            if not isinstance(identifier, str) or len(identifier) > 256: raise ValueError('Invalid delegation identity')
            if identifier in self.delegations: return
            if len(self.delegations) >= 2048: raise ValueError('Voice delegation limit reached. Reopen Voice.')
            self.delegations.add(identifier)
            self.delegation = identifier
        elif kind == 'session.commentary.appended':
            identifier = event.get('client_event_id')
            if identifier in self.awaiting_output:
                self.awaiting_output.remove(identifier)
                self.output_allowed = True
        elif kind in ('session.usage.updated', 'session.closed'):
            seconds = event.get('usage', {}).get('seconds')
            if type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0: self.seconds = seconds

    def begin(self):
        self.interrupt()
        self.manual_pending = False
        self.manual_recording = True

    def end(self):
        self.manual_recording = False
        self.manual_pending = True
        self.last_input = self.clock()

    def tick(self):
        if not self.fragments or self.manual_recording: return
        if not self.hands_free and not self.manual_pending: return
        if self.clock() - max(self.last_input, self.last_speech) < self.pause: return
        text = ''.join(v[0] for v in self.fragments).strip()
        self.consumed_ms = max(v[1] for v in self.fragments)
        self.fragments.clear()
        self.manual_pending = False
        if not text: return
        if len(self.requests) >= 256: raise ValueError('Voice request limit reached. Reopen Voice.')
        identifier = str(uuid.uuid4())
        self.current = identifier
        self.requests[identifier] = {'text': text, 'delegation': self.delegation, 'turn': None,
                                     'done': False, 'answers': [], 'accepted': False}
        self.delegation = None
        self.submit({'requestId': identifier, 'text': text, 'prefix': 'augmentor-voice:'})

    def submission(self, result):
        identifier = result.get('id', '').removeprefix('augmentor-voice:')
        row = self.requests.get(identifier)
        if not row: return
        if result.get('accepted') is not True:
            row['done'] = True
            self.interrupt()
            raise ValueError('Voice submission was not confirmed. Check the conversation before retrying.')
        row['accepted'] = True
        if result.get('turnId'): row['turn'] = result['turnId']

    def observe(self, event):
        seq = event.get('seq')
        if type(seq) is int:
            if seq <= self.backend_seq:return
            self.backend_seq=seq
        row = self.requests.get(self.current)
        if not row or row['done']: return
        kind, data, turn = event.get('type'), event.get('data', {}), event.get('turnId')
        if not isinstance(data, dict):return
        if kind == 'turn/start':
            self.live_turn = turn or ('seq:' + str(event.get('seq')))
            return
        turn = turn or self.live_turn
        if kind == 'user/message':
            request = data.get('requestId') or data.get('source', {}).get('rpcId')
            text = '\n'.join(p.get('text', '') for p in data.get('content', []) if p.get('type') == 'text')
            # Pi has no client ID in user events. Exact submitted text + live turn
            # identity supplies its binding; historical events are never observed.
            if request != 'augmentor-voice:' + self.current and not (request is None and text == row['text']): return
            row['accepted'] = True
            row['turn'] = turn or ('request:' + self.current)
            if self.live_turn is None: self.live_turn = row['turn']
            row['answers'] = []
            return
        if not row['accepted'] or not row['turn'] or turn != row['turn']: return
        if kind == 'assistant/message':
            text = '\n'.join(p.get('text', '') for p in data.get('message', {}).get('content', []) if p.get('type') == 'text')
            if text: row['answers'].append(text)
        elif kind == 'tool/result':
            voice = data.get('meta', {}).get('resonantVoice') or {}
            if voice.get('version') == 1 and isinstance(voice.get('text'), str) and not data.get('isError'):
                row['answers'].append(voice['text'])
        elif kind == 'turn/end':
            row['done'] = True
            if data.get('reason', {}).get('kind') != 'completed':
                self.interrupt(); return
            answer = '\n'.join(row['answers'])
            if len(answer) > 65536: raise ValueError('Spoken answer is too long. Read the result in the conversation.')
            # Up to 400 UTF-8 bytes guarantees <500 tokens even for non-Latin text.
            chunk = ''
            for char in answer:
                if len((chunk + char).encode('utf-8')) > 400:
                    self.commentary(chunk, row['delegation']); chunk = ''
                chunk += char
            if chunk: self.commentary(chunk, row['delegation'])

    def commentary(self, text, delegation):
        identifier = 'voice-result-' + uuid.uuid4().hex
        self.awaiting_output.add(identifier)
        self.send({'type': 'session.commentary.append', 'event_id': identifier,
                   'delegation_id': delegation, 'content': text})
