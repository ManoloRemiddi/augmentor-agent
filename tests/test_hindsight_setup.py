# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise installer parsing, saved choices and refusal without a real Docker daemon."""
from contextlib import redirect_stdout
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import threading
import unittest
from unittest.mock import patch


class HindsightSetupTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('hindsight_setup_choice_fixture', root / 'scripts/setup-hindsight.py')
        self.setup = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.setup)
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.data = Path(self.temporary.name)
        self.requests, self.commands = [], []
        requests = self.requests
        class Engine(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_GET(self):
                requests.append(self.path)
                values = {'/openapi.json': {'info': {'version': '0.10.0'}},
                          '/health': {'status': 'healthy'},
                          '/ext/augmentor/policy': {'protocol': 'augmentor-memory-processing/1', 'workerEnabled': False, 'reconcileSeconds': 0, 'llmRetries': 0}}
                value = values.get(self.path)
                self.send_response(200 if value else 404); self.end_headers()
                self.wfile.write(json.dumps(value).encode())
        self.engine = ThreadingHTTPServer(('127.0.0.1', 0), Engine)
        self.addCleanup(self.engine.server_close); self.addCleanup(self.engine.shutdown)
        threading.Thread(target=self.engine.serve_forever, daemon=True).start()
        self.port = self.engine.server_port
        self.gateway = 18441 if self.port != 18441 else 18443
        digest = hashlib.sha256((root / 'services/memory/hindsight_extension.py').read_bytes()).hexdigest()
        self.artifact = self.data / 'memory-engine' / digest
        self.artifact.mkdir(parents=True)
        (self.artifact / 'augmentor_memory.py').write_bytes((root / 'services/memory/hindsight_extension.py').read_bytes())
        self.previous = {'endpoint': f'http://127.0.0.1:{self.port}', 'gatewayKey': 'synthetic-' + 'k' * 40, 'modelKey': 'local'}
        self.argv = ['setup-hindsight.py', '--model-url', 'http://127.0.0.1:1/v1', '--model', 'synthetic-explicit-model',
                     '--port', str(self.port), '--gateway-port', str(self.gateway), '--name', 'synthetic-controlled', '--volume', 'synthetic-data']

    def run_setup(self, *, engine_mode='default', legacy_environment=False, options=()):
        expected = self.setup.environment('synthetic-explicit-model', self.port, self.gateway, llama_cpp_thinking=engine_mode)
        if legacy_environment:
            expected = {k: v for k, v in expected.items() if not k.endswith('_LLM_EXTRA_BODY')}
        container = {'Id': 'authored-existing-id', 'Config': {'Image': self.setup.IMAGE, 'Env': [k + '=' + v for k, v in expected.items()] + ['HINDSIGHT_API_HTTP_KEY=' + self.previous['gatewayKey']]},
                     'HostConfig': {'RestartPolicy': {'Name': 'unless-stopped'}},
                     'State': {'Running': True}, 'Mounts': [{'Type': 'bind', 'Source': str(self.artifact), 'Destination': '/augmentor', 'RW': False},
                                                           {'Type': 'volume', 'Name': 'synthetic-data', 'Destination': '/home/hindsight/.pg0', 'RW': True}]}
        def docker(command, **_):
            self.commands.append(command)
            if command == ['docker', 'inspect', 'synthetic-controlled']:
                return SimpleNamespace(returncode=0, stdout=json.dumps([container]))
            if command == ['docker', 'start', 'synthetic-controlled']:
                return SimpleNamespace(returncode=0, stdout='')
            raise AssertionError('Unexpected Docker mutation: ' + repr(command))
        with patch.dict(os.environ, {'AUGMENTOR_SHARED_DATA': str(self.data)}), patch('sys.argv', [*self.argv, *options]), \
                patch.object(self.setup.subprocess, 'run', side_effect=docker), redirect_stdout(io.StringIO()):
            self.setup.main()

    def write_previous(self):
        path = self.data / 'hindsight.json'
        path.write_text(json.dumps(self.previous) + '\n'); path.chmod(0o600)
        return path

    def test_omitted_option_preserves_saved_memory_only_choice(self):
        self.previous['llamaCppThinking'] = 'off'; path = self.write_previous()
        self.run_setup(engine_mode='off')
        saved = json.loads(path.read_text())
        self.assertEqual(saved['llamaCppThinking'], 'off')
        self.assertEqual(saved['gatewayKey'], self.previous['gatewayKey'])
        self.assertEqual(saved['modelUrl'], 'http://127.0.0.1:1/v1')
        self.assertTrue(self.commands)
        self.assertTrue(all(c == ['docker', 'inspect', 'synthetic-controlled'] for c in self.commands))
        self.assertEqual(self.requests, ['/openapi.json', '/health', '/ext/augmentor/policy'])

    def test_explicit_mode_change_refuses_running_engine_without_rewriting_configuration(self):
        self.previous['llamaCppThinking'] = 'off'; path = self.write_previous(); before = path.read_bytes()
        with self.assertRaisesRegex(SystemExit, 'Existing engine differs'):
            self.run_setup(engine_mode='off', options=['--llama-cpp-thinking', 'default'])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.commands, [['docker', 'inspect', 'synthetic-controlled']])
        self.assertEqual(self.requests, [])

    def test_legacy_default_engine_has_no_implicit_thinking_change(self):
        path = self.write_previous()
        self.run_setup(legacy_environment=True)
        self.assertEqual(json.loads(path.read_text())['llamaCppThinking'], 'default')
        self.assertTrue(all(c == ['docker', 'inspect', 'synthetic-controlled'] for c in self.commands))
        self.assertEqual(len(self.requests), 3)

    def test_invalid_saved_choice_refuses_before_engine_or_configuration_changes(self):
        self.previous['llamaCppThinking'] = 'unexpected'; path = self.write_previous(); before = path.read_bytes()
        with self.assertRaisesRegex(SystemExit, 'Saved memory thinking mode is invalid'):
            self.run_setup()
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.commands, [])
        self.assertEqual(self.requests, [])


if __name__ == '__main__': unittest.main()
