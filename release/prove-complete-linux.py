#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fresh-user complete-bundle qualification in a disposable Linux container.

Uses a deterministic localhost model with real installed DSH/plugins/adapters.
Offscreen rendering and adapter turns do not qualify a graphical browser/session.
"""
import argparse
import http.server
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time


def run(command, **kwargs):
    return subprocess.run([str(v) for v in command], check=True, text=True, **kwargs)


def user_proof(bundle):
    assert os.geteuid() != 0
    requests = []
    class Model(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()
            for delta, reason in (({'role': 'assistant', 'content': 'LINUX DISTRO FIXTURE VERIFIED'}, None), ({}, 'stop')):
                value = {'id': 'qualification', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'fixture',
                         'choices': [{'index': 0, 'delta': delta, 'finish_reason': reason}]}
                self.wfile.write(('data: '+json.dumps(value)+'\n\n').encode())
            self.wfile.write(b'data: [DONE]\n\n')
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Model)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with socket.socket() as available:
        available.bind(('127.0.0.1', 0))
        port = available.getsockname()[1]
    home = Path.home()
    data = home/'.local/share/augmentor'
    config = home/'.config'
    state = home/'.local/state/augmentor-install'
    app = Path('/usr/lib/augmentor')
    node = app/'node/bin/node'
    os.environ.update(AUGMENTOR_FIXTURE_KEY='qualification-fixture', QT_QPA_PLATFORM='offscreen',
                      XDG_RUNTIME_DIR=str(home/'runtime'), PATH=str(node.parent)+':'+os.environ['PATH'])
    Path(os.environ['XDG_RUNTIME_DIR']).mkdir(mode=0o700)
    command = ['/usr/bin/python3', bundle/'setup.py', '--bundle', bundle, '--skip-packages', '--no-services',
               '--non-interactive', '--model-url', f'http://127.0.0.1:{server.server_port}/v1', '--model', 'fixture',
               '--api-key-env', 'AUGMENTOR_FIXTURE_KEY', '--port', str(port)]
    process = None
    log = (home/'qualification-dsh.log').open('w')
    try:
        run(command)
        manifest = json.loads((bundle/'bundle.json').read_text())
        receipt = json.loads((state/'installation.json').read_text())
        assert receipt['status'] == 'installed' and receipt['target'] == manifest['target']
        assert (state/'model.env').stat().st_mode & 0o077 == 0
        saved = config/'augmentor/harnesses.json'
        assert json.loads(saved.read_text())['dsh']['version'] == manifest['version']
        assert (config/'autostart/com.augmentor.Agent.desktop').is_file()
        assert (home/'.local/share/applications/com.augmentor.Agent.secondary.desktop').is_file()
        assert (data/'browser'/manifest['version']/'voice.mjs').is_file()
        assert (config/'chromium/NativeMessagingHosts/com.augmentor.agent.json').is_file()
        dsh_home = data/'dsh-home'
        for plugin in ('dsh-resonant-voice', 'dsh-adaptive-reasoning', 'dsh-model-picker-augmented'):
            assert (dsh_home/'profiles/web/node_modules'/plugin/'package.json').is_file()
        python = data/'python/bin/python'
        run([python, '-m', 'augmentor_linux', '--preview', '--screenshot', home/'desktop.png'],
            env={**os.environ, 'PYTHONPATH': str(app/'apps/native')})
        assert (home/'desktop.png').stat().st_size > 10000
        first = saved.read_bytes()
        run(command)
        assert saved.read_bytes() == first
        sys.path.insert(0, str(app/'apps/native'))
        from augmentor_linux.adapters.dsh import DshAdapter
        cli = data/'dsh-runtime/node_modules/.bin/dsh'
        env = {**os.environ, 'DSH_HOME': str(dsh_home), 'DSH_TELEMETRY_MODE': 'DISABLED',
               'AUGMENTOR_MODEL_API_KEY': 'qualification-fixture'}

        def stop():
            nonlocal process
            if process is not None and process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=15)
            process = None

        def start():
            nonlocal process
            process = subprocess.Popen([str(node), str(cli.resolve()), 'web', '--no-open', '--host', '127.0.0.1', '--port', str(port)],
                                       env=env, stdout=log, stderr=log, start_new_session=True)
            deadline = time.monotonic()+60
            while time.monotonic() < deadline:
                assert process.poll() is None, 'DSH stopped; inspect qualification-dsh.log'
                try:
                    adapter = DshAdapter()
                    adapter.call('host.describe')
                    assert adapter.product
                    return adapter
                except (OSError, ValueError, RuntimeError):
                    time.sleep(.2)
            raise AssertionError('Installed DSH did not become ready')

        adapter = start()
        histories = {}
        for role in ('linux', 'browser'):
            session = 'qualification-'+role
            adapter.call('session.create', {'sessionId': session, 'agentPreset': 'augmentor-'+role+'-product', 'cwd': str(home)})
            adapter.call('session.selectModel', {'sessionId': session, 'provider': 'augmentor-model', 'model': 'fixture'})
            adapter.call('session.prompt', {'sessionId': session, 'mode': 'queue',
                         'content': [{'type': 'text', 'text': 'Reply to the '+role+' qualification fixture.'}]})
            deadline = time.monotonic()+60
            while time.monotonic() < deadline:
                histories[session] = adapter.call('session.history', {'sessionId': session})
                row = next(v for v in adapter.call('session.list')['items'] if v['sessionId'] == session)
                if not row['running'] and 'LINUX DISTRO FIXTURE VERIFIED' in json.dumps(histories[session]):
                    break
                time.sleep(.1)
            else:
                raise AssertionError('Installed '+role+' role did not complete a fixture model turn')
        count = len(requests)
        stop()
        adapter = start()
        for session, history in histories.items():
            assert adapter.call('session.history', {'sessionId': session}) == history
        assert len(requests) == count, 'Restart replayed a model request'
        stop()
        report = {'target': manifest['target'], 'sourceCommit': manifest['sourceCommit'], 'bundle': manifest['artifactId'],
                  'ordinaryUserSetup': True, 'realInstalledDshAndPlugins': True, 'offscreenNativeRender': True,
                  'secondWindowEntry': True, 'nativeHostRegistered': True, 'repeatPreservesSettings': True,
                  'linuxAndBrowserRoleFixtureTurns': True, 'restartPreservesHistoryWithoutReplay': True,
                  'modelRequests': count, 'realDesktopSessionTested': False, 'graphicalBrowserTested': False,
                  'physicalVoiceTested': False, 'memoryEngineTested': False}
        (home/'complete-proof.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report))
    finally:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=15)
        server.shutdown()
        server.server_close()
        log.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--out', type=Path, default=Path('/tmp/complete-linux-proof.json'))
    p.add_argument('--user-phase', action='store_true', help=argparse.SUPPRESS)
    a = p.parse_args()
    if not any(Path(marker).exists() for marker in ('/.dockerenv', '/run/.containerenv')):
        raise SystemExit('This proof requires a disposable Docker/Podman container.')
    bundle = a.bundle.resolve()
    if a.user_phase:
        user_proof(bundle)
        return
    assert os.geteuid() == 0
    plan = json.loads(subprocess.check_output(['/usr/bin/python3', str(bundle/'setup.py'), '--bundle', str(bundle), '--plan'], text=True))
    command = plan['system']['command']
    assert command[:2] in (['sudo', 'apt'], ['sudo', 'dnf'])
    if command[1] == 'apt':
        run(['apt-get', 'update', '-qq'])
        run(['apt-get', 'install', '-y', '--no-install-recommends', 'passwd', 'util-linux'])
    else:
        run(['dnf', 'install', '-y', 'shadow-utils', 'util-linux'])
    # The actual installer runs as a fresh ordinary user below; root performs
    # only the exact package plan, avoiding a sudo dependency in minimal images.
    run(command[1:])
    run(['useradd', '-m', '-s', '/bin/sh', 'augmentor-complete-proof'])
    run(['runuser', '-u', 'augmentor-complete-proof', '--', '/usr/bin/python3', Path(__file__).resolve(), '--bundle', bundle, '--user-phase'])
    report = json.loads(Path('/home/augmentor-complete-proof/complete-proof.json').read_text())
    report['systemPlan'] = plan['system']
    a.out.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
