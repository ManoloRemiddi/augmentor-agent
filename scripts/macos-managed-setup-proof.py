#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Isolated real launchd/DSH first-run proof with a deterministic local model.

Run on a graphical ARM64 Mac using bundled Python. This creates one uniquely
named temporary LaunchAgent, removes that exact job afterward, and never uses
the owner's configured DSH profile or a real provider key.
"""
import argparse
import http.server
import importlib.util
import json
import os
import re
from pathlib import Path
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'darwin': parser.error('Requires macOS launchd.')
    root = args.app_root.resolve(); args.out.mkdir(parents=True, exist_ok=False)
    os.umask(0o077)
    calls = []
    class Model(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            assert self.headers['Authorization'] == 'Bearer fixture-only-key'
            calls.append(body)
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream' if body.get('stream') else 'application/json')
            self.end_headers()
            if body.get('stream'):
                for delta, finish in [({'role': 'assistant', 'content': 'Managed setup verified.'}, None), ({}, 'stop')]:
                    event = {'id': 'fixture', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'fixture',
                             'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
                    self.wfile.write(('data: '+json.dumps(event)+'\n\n').encode()); self.wfile.flush()
                self.wfile.write(b'data: [DONE]\n\n')
            else:
                self.wfile.write(json.dumps({'id': 'fixture', 'object': 'chat.completion', 'created': 1, 'model': 'fixture',
                    'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'OK'}, 'finish_reason': 'stop'}]}).encode())
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Model)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    spec = importlib.util.spec_from_file_location('managed_setup_proof', root/'scripts/setup-macos.py')
    managed = importlib.util.module_from_spec(spec); spec.loader.exec_module(managed)
    work = Path(tempfile.mkdtemp(prefix='amsetup-', dir='/tmp')).resolve()
    os.environ.update(XDG_CONFIG_HOME=str(work/'config'), XDG_DATA_HOME=str(work/'data'),
        XDG_STATE_HOME=str(work/'state'), XDG_RUNTIME_DIR=str(work/'run'),
        AUGMENTOR_SHARED_STATE=str(work/'shared-run'), AUGMENTOR_SHARED_DATA=str(work/'shared-data'),
        AUGMENTOR_SHARED_CONFIG=str(work/'shared-config'), AUGMENTOR_DSH_WORKSPACE_ROOT=str(work/'workspace'),
        PYTHONDONTWRITEBYTECODE='1')
    state = work/'managed'; label = 'com.augmentor.Agent.SetupProof.'+uuid.uuid4().hex
    agent = managed.LaunchAgent(root, state, label=label)
    request = {'url': f'http://127.0.0.1:{server.server_port}/v1', 'model': 'fixture',
               'apiKey': 'fixture-only-key', 'context': 32768}
    report = {'passed': False, 'scope': 'Real managed DSH/launchd with isolated state and a deterministic model; not notarized install acceptance.'}
    def wait_for(check, seconds=60):
        until = time.monotonic()+seconds
        while time.monotonic() < until:
            try:
                result = check()
                if result: return result
            except (OSError, RuntimeError, ValueError): pass
            time.sleep(.2)
        raise AssertionError('Managed setup proof timed out.')
    try:
        result = managed.provision(root, state, request, agent=agent)
        assert result['saved'] and agent.loaded()
        sys.path[:0] = [str(root/'apps/native'), str(root/'services')]
        from augmentor_linux.adapters.dsh import DshAdapter
        adapter = DshAdapter(); adapter.call('host.describe')
        assert adapter.product
        catalog = adapter.model_catalog()
        assert any(m.get('id', m.get('model')) == 'fixture' for group in catalog['groups'] for m in group['models']), catalog
        session = 'managed-setup-'+uuid.uuid4().hex
        adapter.call('session.create', {'sessionId': session, 'agentPreset': 'augmentor-linux-product', 'cwd': str(work)})
        adapter.call('session.selectModel', {'sessionId': session, 'provider': 'augmentor-model', 'model': 'fixture'})
        before = len(calls)
        adapter.call('session.prompt', {'sessionId': session, 'mode': 'queue',
            'content': [{'type': 'text', 'text': 'Reply to the isolated managed setup fixture.'}]})
        wait_for(lambda: len(calls) > before and not next(r for r in adapter.call('session.list')['items'] if r['sessionId'] == session)['running'])
        history = adapter.call('session.history', {'sessionId': session})
        assert 'Managed setup verified.' in json.dumps(history)
        repeated = managed.provision(root, state, request, agent=agent)
        assert repeated == result
        # Stop/start the precise owned job: saved provider credentials and
        # conversation must survive, with no detached replacement process.
        agent.stop_failed_setup(); assert not agent.loaded()
        agent.start(); wait_for(lambda: adapter.call('host.describe'))
        restored = adapter.call('session.history', {'sessionId': session})
        assert 'Managed setup verified.' in json.dumps(restored)
        report.update(passed=True, providerRequests=len(calls), modelAvailable=True,
                      chatCompleted=True, conversationRestored=True, repeatedSetupPreserved=True)
    except BaseException:
        # Only this isolated synthetic fixture is eligible for report excerpts.
        # Never copy runtime.json, auth stores or an installed user's logs.
        report['fixtureDiagnostics'] = {}
        for name in ('setup-dsh.log', 'runtime.log', 'startup-check.json'):
            file = state/name
            if file.is_file():
                excerpt = file.read_text(errors='replace')[-10000:]
                excerpt = re.sub(r'token=[A-Za-z0-9_-]+', 'token=[redacted]', excerpt)
                report['fixtureDiagnostics'][name] = excerpt.replace('fixture-only-key', '[redacted]')
        raise
    finally:
        try:
            agent.stop_failed_setup()
            if agent.owned(): agent.path.unlink()
            assert not agent.loaded()
            report['temporaryLaunchAgentRemoved'] = True
            # DSH may have contacted shared prompt/memory services. Those are
            # separate processes; the host's exit does not establish their exit.
            sys.path.insert(0, str(root/'services'))
            from platform_support import require_same_user
            for name in ('prompts.sock', 'dual-memory.sock'):
                path = work/'shared-run'/name
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
                    peer.settimeout(2)
                    try: peer.connect(str(path))
                    except (FileNotFoundError, ConnectionRefusedError): continue
                    require_same_user(peer)
                    pid = struct.unpack('i', peer.getsockopt(0, 2, 4))[0]
                assert pid > 1 and pid != os.getpid()
                try: os.kill(pid, signal.SIGTERM)
                except ProcessLookupError: continue
                def stopped():
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as check:
                        check.settimeout(.2)
                        try: check.connect(str(path)); return False
                        except (FileNotFoundError, ConnectionRefusedError): return True
                wait_for(stopped, 10)
            report['fixtureSharedServicesStopped'] = True
        finally:
            server.shutdown(); server.server_close()
            # Retain private synthetic state/logs for diagnosis; no .app copy,
            # login job, credential from the owner or public artifact is created.
            report['privateFixtureDirectory'] = str(work)
            (args.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
            print(json.dumps(report), flush=True)


if __name__ == '__main__': main()
