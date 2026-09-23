# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fixed onboarding jobs and a local, acknowledged handoff to the Linux UI."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]


def memory_prompt():
    return '''Set up shared Hindsight memory for my Augmentor agents. Do the work yourself and guide me with short updates. First inspect the existing Augmentor memory configuration, available Hindsight services, container tools and model connections. Reuse a healthy compatible setup where possible. Ask only for missing choices or credentials. Explain local versus hosted memory briefly if I need to choose. Never ask me to copy terminal commands or fill technical forms when you can perform the action.

Use the installed Augmentor shared-service API through Python. Add ROOT/apps/native to sys.path, import PromptClient from augmentor_linux.prompt_client, then call memory.describe, memory.check and memory.configure. ROOT is ''' + str(ROOT) + '''. memory.check accepts endpoint, apiKey, userBank, optional projectBank and activeScope (user by default). Choose a stable new user bank automatically if none exists. Pass the returned token to memory.configure; do not modify the database directly. A blank API key reuses the stored key only for the same endpoint. Inspect the installed services/memory/provider.py for the exact supported API and version (currently Hindsight 0.9.2).

If Hindsight is missing, offer to install it locally using its official version-pinned container and persistent storage, or connect a service I already have. Check ports, dependencies and compatibility first. Inspect my existing model configuration privately to reuse a compatible provider where supported. Never print credentials, put them in chat, or send them to a different destination. Use a private local file or the app's password field if a new credential is needed. Explain provider costs before a new paid service or account is used. Do not replace existing data or disrupt running services.

After configuration, verify service health and the saved connection. Offer a harmless test fact before writing any memory. Report what actually succeeded and any remaining blocker; never claim installation or memory recall worked without checking. The resulting memory connection must be shared by both browser and Linux, with Pi and DSH. Finish by telling me I can return to the browser.'''


def start(window, topic, request_id):
    if topic != 'memory':
        raise RuntimeError('Unknown setup task.')
    try:
        uuid.UUID(request_id)
    except (ValueError, TypeError, AttributeError):
        raise RuntimeError('Invalid setup request.') from None
    ledger = window.controller.state_file.parent / 'onboarding-requests.json' if window.controller else None
    previous = {}
    if ledger and ledger.exists():
        previous = json.loads(ledger.read_text())
    if request_id in previous:
        window.bring_forward()
        return {'status': 'opened', 'reused': True}
    controller = window.controller
    if not controller or controller.running or controller.navigating or controller.recovery_lock.locked() or window.editing:
        raise RuntimeError('Finish or stop the current Linux action, then continue setup.')
    if window.composer.toPlainText().strip():
        raise RuntimeError('Send or clear your unfinished Linux message, then continue setup.')
    selection = window.model_picker.currentData()
    if not selection:
        window.bring_forward()
        raise RuntimeError('Connect a model in Augmentor Agent, then continue setup.')
    window.new_chat()
    window.bring_forward()
    # Record dispatch before starting: a lost acknowledgment must not replay setup.
    previous[request_id] = True
    ledger.parent.mkdir(parents=True, exist_ok=True)
    temporary = ledger.with_suffix('.tmp')
    temporary.write_text(json.dumps(dict(list(previous.items())[-64:])))
    temporary.chmod(0o600);temporary.replace(ledger)
    controller.send(memory_prompt(), selection)
    return {'status': 'started', 'reused': False}


def exchange(path, command):
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(3)
        client.connect(str(path))
        client.sendall(command.encode())
        data = b''
        while not data.endswith(b'\n'):
            chunk = client.recv(4096)
            if not chunk: break
            data += chunk
            if len(data) > 16384: raise RuntimeError('Invalid desktop response.')
        return json.loads(data)


def open_memory(request_id):
    uuid.UUID(request_id)
    path = Path(os.environ.get('XDG_RUNTIME_DIR', f'/tmp/augmentor-linux-pi-{os.getuid()}')) / 'augmentor-linux-pi.sock'
    try:
        status = exchange(path, 'maintenance.status')
    except (OSError, ValueError):
        launcher = [sys.executable,str(ROOT/'scripts/launch-component.py'),'desktop'] if sys.platform=='darwin' else ['/usr/bin/augmentor-agent'] if (ROOT / 'release.json').exists() else [str(ROOT / 'scripts/augmentor-linux')]
        subprocess.Popen([*launcher, '--onboarding-host'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.monotonic() + 15
        while True:
            try:
                status = exchange(path, 'maintenance.status')
                break
            except (OSError, ValueError):
                if time.monotonic() >= deadline: raise RuntimeError('Augmentor Agent did not open. Check that the desktop app is installed.') from None
                time.sleep(.15)
    if status.get('onboardingProtocol') != 1:
        raise RuntimeError('Update the Augmentor desktop and companion to use guided setup.')
    # A new desktop may still be loading its saved model catalog.
    deadline = time.monotonic() + 10
    while not status.get('modelReady') and time.monotonic() < deadline:
        time.sleep(.15);status = exchange(path, 'maintenance.status')
    result = exchange(path, 'onboarding:' + json.dumps({'topic': 'memory', 'requestId': request_id}))
    if not result.get('ok'): raise RuntimeError(result.get('error', 'Could not start setup.'))
    return result['result']


if __name__ == '__main__':
    try:
        print(json.dumps({'ok': True, 'result': open_memory(sys.argv[1])}))
    except Exception as error:
        print(json.dumps({'ok': False, 'error': str(error)}))
