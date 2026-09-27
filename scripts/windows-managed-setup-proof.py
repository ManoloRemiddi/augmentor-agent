#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual isolated Windows DSH setup/chat/restart using a deterministic model.

Never selects an installed user's profile, modifies login entries, or uses a real
provider secret. This does not claim live-provider or interactive desktop proof.
"""
import argparse
import http.server
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'win32': parser.error('Requires the native Windows runtime.')
    root = args.root.resolve(); args.out.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(root/'services'), str(root/'apps/native')]
    from platform_adapters.paths import private_directory
    from dsh import managed, setup
    import windows_supervisor as owner
    work = private_directory(Path(tempfile.mkdtemp(prefix='augmentor-windows-setup-')).resolve()/'private')
    for name in ('config', 'data', 'state', 'run', 'workspace'): private_directory(work/name)
    os.environ.update(XDG_CONFIG_HOME=str(work/'config'), XDG_DATA_HOME=str(work/'data'),
        XDG_STATE_HOME=str(work/'state'), XDG_RUNTIME_DIR=str(work/'run'),
        AUGMENTOR_SHARED_CONFIG=str(private_directory(work/'config/shared')),
        AUGMENTOR_SHARED_STATE=str(private_directory(work/'run/shared')),
        AUGMENTOR_SHARED_DATA=str(private_directory(work/'data/shared')),
        AUGMENTOR_DSH_WORKSPACE_ROOT=str(work/'workspace'),
        AUGMENTOR_DSH_CLI=str(root/'dsh/node_modules/@deepseek-ai/dsh/lib/bin.js'),
        AUGMENTOR_PYTHON=str(root/'python/python.exe'), AUGMENTOR_PI_NODE=str(root/'node/node.exe'),
        AUGMENTOR_PWSH=str(root/'powershell/pwsh.exe'), PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
    os.environ['PATH'] = os.pathsep.join([str(root/'node'), str(root/'python'), str(root/'powershell'), os.environ.get('PATH', os.defpath)])
    calls = []
    model_waiting, release_model = threading.Event(), threading.Event()
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
                latest = next((item for item in reversed(body.get('messages', [])) if item.get('role') == 'user'), {})
                if 'LEASE_HOLD_FIXTURE' in json.dumps(latest):
                    self.wfile.write(b'data: {"choices":[{"index":0,"delta":{"role":"assistant","content":"Waiting"},"finish_reason":null}]}\n\n')
                    self.wfile.flush(); model_waiting.set()
                    release_model.wait(30)
                    return
                for delta, finish in [({'role': 'assistant', 'content': 'Windows managed setup verified.'}, None), ({}, 'stop')]:
                    event = {'id': 'fixture', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'fixture',
                             'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
                    self.wfile.write(('data: '+json.dumps(event)+'\n\n').encode()); self.wfile.flush()
                self.wfile.write(b'data: [DONE]\n\n')
            else:
                self.wfile.write(json.dumps({'id': 'fixture', 'object': 'chat.completion', 'created': 1, 'model': 'fixture',
                    'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'OK'}, 'finish_reason': 'stop'}]}).encode())
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Model)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    state = owner.managed_directory(); agent = owner.ManagedAgent(root, state)
    report = {'passed': False, 'scope': 'Native bundled DSH and supervisor; deterministic model, isolated state, no installed-user data.'}
    def wait_for(check, seconds=60):
        until = time.monotonic()+seconds
        while time.monotonic() < until:
            try:
                result = check()
                if result: return result
            except (OSError, RuntimeError, ValueError): pass
            time.sleep(.2)
        raise AssertionError('The isolated Windows setup proof timed out.')
    # Retain the exact process handle for the owned crash/restart test.
    supervisor = subprocess.Popen([str(root/'python/python.exe'), '-I', '-Xutf8', '-B',
        str(root/'services/windows_supervisor.py')], stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        wait_for(lambda: owner.request('status', root=root))
        result = managed.provision(root, state, {'url': f'http://127.0.0.1:{server.server_port}/v1',
            'model': 'fixture', 'apiKey': 'fixture-only-key', 'context': 32768},
            agent=agent, manager_type='windows-supervisor')
        assert result['saved'] and agent.loaded()
        report['startupCheck'] = managed.private_json(state/'startup-check.json')
        from augmentor_linux.adapters.dsh import DshAdapter
        adapter = DshAdapter(); adapter.call('host.describe'); assert adapter.product
        session = 'windows-setup-'+uuid.uuid4().hex
        adapter.call('session.create', {'sessionId': session, 'agentPreset': 'augmentor-linux-product', 'cwd': str(work/'workspace')})
        adapter.call('session.selectModel', {'sessionId': session, 'provider': 'augmentor-model', 'model': 'fixture'})
        before = len(calls)
        adapter.call('session.prompt', {'sessionId': session, 'mode': 'queue',
            'content': [{'type': 'text', 'text': 'Reply to the isolated Windows setup fixture.'}]})
        wait_for(lambda: len(calls)>before and not next(row for row in adapter.call('session.list')['items'] if row['sessionId']==session)['running'])
        assert 'Windows managed setup verified.' in json.dumps(adapter.call('session.history', {'sessionId': session}))
        # This is the actual DSH writer, not two copies of our adapter. While
        # its model request is active, repair must fail to acquire its lease.
        from dsh.session_lease import session_write_lease
        directories = {path.parent for path in (state/'home/sessions').glob('*/'+session+'/session*.jsonl*')}
        assert len(directories) == 1, 'The actual session artifact directory is ambiguous.'
        lock_path = directories.pop()/'session.lock'
        adapter.call('session.prompt', {'sessionId': session, 'mode': 'queue',
            'content': [{'type': 'text', 'text': 'LEASE_HOLD_FIXTURE'}]})
        assert model_waiting.wait(20), 'The deterministic model did not receive the cancellable turn.'
        contended = False
        try:
            with session_write_lease(lock_path): pass
        except BlockingIOError: contended = True
        assert contended, 'Recovery lease failed to exclude the actual DSH history writer.'
        adapter.call('session.cancel', {'sessionId': session})
        wait_for(lambda: not next(row for row in adapter.call('session.list')['items'] if row['sessionId']==session)['running'])
        release_model.set()
        report.update(actualHarnessLeaseContention=True, stopCancelledTurn=True)
        with_error = False
        try: agent.stop_failed_setup()
        except ValueError: with_error = True
        assert with_error and agent.loaded(), 'Published runtime must refuse failed-setup cleanup'
        supervisor.kill(); supervisor.wait(timeout=10)
        wait_for(lambda: not agent.loaded())
        def released_history():
            with session_write_lease(lock_path): return True
        wait_for(released_history)
        agent.start(); wait_for(lambda: adapter.call('host.describe'))
        assert 'Windows managed setup verified.' in json.dumps(adapter.call('session.history', {'sessionId': session}))
        report.update(passed=True, setup=True, conversation=True, crashRestartPreservedHistory=True,
                      selectedRuntimeProtected=True, providerRequests=len(calls))
    except BaseException:
        report['fixtureDiagnostics'] = {}
        for path in (state/'setup-dsh.log', state/'runtime.log', state/'startup-check.json', owner.owner_directory()/'supervisor.log'):
            if path.is_file():
                excerpt = path.read_text(encoding='utf-8', errors='replace')[-12000:]
                excerpt = re.sub(r'token=[A-Za-z0-9_-]+', 'token=[redacted]', excerpt)
                report['fixtureDiagnostics'][path.name] = excerpt.replace('fixture-only-key', '[redacted]')
        raise
    finally:
        try:
            # This is a disposable synthetic connection, never the user's config.
            setup.configuration().unlink(missing_ok=True)
            if agent.owned(): agent.stop_failed_setup()
            try: owner.request('exit-if-empty', root=root)
            except FileNotFoundError: pass
        finally:
            if supervisor.poll() is None: supervisor.kill()
            supervisor.wait(timeout=10)
            release_model.set()
            server.shutdown(); server.server_close()
            report['privateFixtureDirectory'] = str(work)
            (args.out/'managed-setup.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
            print(json.dumps(report), flush=True)


if __name__ == '__main__': main()
