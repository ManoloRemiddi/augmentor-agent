# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise the actual native wire adapter against an isolated fixture host."""
import json
import os
import threading
from augmentor_linux.adapters.codex import CodexAdapter
from augmentor_linux.pi_client import EventStream

client = CodexAdapter()
assert client.call('host.describe')['harness'] == 'codex'
selection = {'provider': 'local-fixture', 'model': 'fixture-model'}
assert client.validate_model(selection)['valid']
sid = 'native-adapter-fixture'
created = client.call('session.create', {'sessionId': sid, 'cwd': os.environ['AUGMENTOR_CODEX_WORKSPACE'], 'selection': selection})
assert created['agentPreset'] == client.preset
assert client.call('session.selectModel', {'sessionId': sid, **selection})['current'] == selection
done = threading.Event()
events = []
approvals = []


def frame(value):
    if value.get('method') == 'approval/requested':
        approvals.append(value)
        client.respond(value['rpcId'], {'sessionId': sid, 'approvalId': value['payload']['approvalId'], 'outcome': 'rejected'})
    if value.get('method') == 'session/event':
        event = value['payload']['event']
        events.append(event)
        if event['type'] == 'turn/end': done.set()


stream = EventStream(client, sid, frame, lambda message: done.set())
try:
    stream.start()
    result = client.call('session.prompt', {'sessionId': sid, 'requestId': 'native-request-one', 'content': [{'type': 'text', 'text': 'Exercise the native adapter.'}]})
    assert result['accepted']
    assert done.wait(15)
    assert any(event['type'] == 'assistant/message' for event in events)
    assert sid in client.saved_chats('save', sid)
    assert any(row['sessionId'] == sid for row in client.session_rows())
    assert client.call('session.models', {'sessionId': sid})['current'] == selection
    print(json.dumps({'nativeAdapter': 'passed', 'events': len(events), 'approvalsDenied': len(approvals)}))
finally:
    stream.close()
