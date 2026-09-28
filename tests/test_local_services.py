# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise the real shared prompt daemon across separate OS processes."""
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))
sys.path.insert(0, str(ROOT/'apps/native'))
from augmentor_linux.prompt_client import PromptClient
from platform_adapters.paths import private_directory
from platform_adapters.transport import LocalSocket


class LocalServiceTests(unittest.TestCase):
    def test_concurrent_start_private_unicode_save_and_durable_restart(self):
        with tempfile.TemporaryDirectory(prefix='augmentor services café ') as temporary:
            root = private_directory(Path(temporary)/'private')
            state, data = private_directory(root/'state'), private_directory(root/'data')
            env = {**os.environ, 'AUGMENTOR_SHARED_STATE': str(state), 'AUGMENTOR_SHARED_DATA': str(data),
                   'XDG_CONFIG_HOME': str(private_directory(root/'config')),
                   'XDG_RUNTIME_DIR': str(private_directory(root/'run'))}
            children = []
            with (root/'fixture.log').open('w', encoding='utf-8') as log:
                def start():
                    child = subprocess.Popen([sys.executable, '-Xutf8', '-B', str(ROOT/'services/prompt-library/service.py')],
                        stdin=subprocess.DEVNULL, stdout=log, stderr=log, env=env,
                        **({'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform=='win32' else {}))
                    children.append(child)
                    return child

                def ready():
                    deadline = time.monotonic()+10
                    while time.monotonic() < deadline:
                        with LocalSocket() as connection:
                            connection.settimeout(.5)
                            try:
                                connection.connect(state/'prompts.sock')
                                return
                            except (FileNotFoundError, ConnectionRefusedError):
                                if all(c.poll() is not None for c in children):
                                    break
                                time.sleep(.05)
                    raise AssertionError('Shared service did not start: '+(root/'fixture.log').read_text(encoding='utf-8'))

                try:
                    start(); start(); ready()
                    with patch.dict(os.environ, env):
                        client = PromptClient()
                        owner = client.call('host.describe')['pid']
                        for child in children:
                            if child.pid != owner:
                                self.assertEqual(child.wait(timeout=5), 0)
                        value = 'Keep café, 日本語 and draft text intact.'
                        saved = client.call('prompts.save', {'name': 'portable', 'content': value}, 'fixture-save')
                        repeated = client.call('prompts.save', {'name': 'portable', 'content': value}, 'fixture-save')
                        self.assertEqual(saved, repeated)
                        self.assertEqual(len(saved['prompts']), 1)
                        self.assertEqual(saved['prompts'][0]['content'], value)
                        node = os.environ.get('AUGMENTOR_PI_NODE') or shutil.which('node')
                        if not node or not (ROOT/'dist/prompt-library/src/client.js').is_file():
                            raise AssertionError('Build the shared Node client before this integration test.')
                        javascript = '''
                            import {pathToFileURL} from 'node:url';
                            const {promptCall}=await import(pathToFileURL(process.argv[1]));
                            const result=await promptCall('prompts.save',{name:'from-node',content:'Node café 日本語'},'node-fixture');
                            console.log(JSON.stringify(result));
                        '''
                        result = subprocess.run([node, '--input-type=module', '-e', javascript,
                            str(ROOT/'dist/prompt-library/src/client.js')], capture_output=True, text=True,
                            encoding='utf-8', timeout=15, check=True,
                            env={**env, 'AUGMENTOR_PYTHON': sys.executable})
                        saved = json.loads(result.stdout)
                        self.assertEqual(len(saved['prompts']), 2)
                        self.assertEqual(next(p for p in saved['prompts'] if p['name']=='from-node')['content'], 'Node café 日本語')
                        self.assertEqual(client.call('prompts.list'), saved)
                        running = next(c for c in children if c.pid == owner)
                        running.terminate(); running.wait(timeout=10)
                        next_child = start(); ready()
                        self.assertEqual(client.call('host.describe')['pid'], next_child.pid)
                        self.assertEqual(client.call('prompts.list'), saved)
                finally:
                    for child in children:
                        if child.poll() is None:
                            child.terminate()
                        try:
                            child.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            child.kill(); child.wait(timeout=5)


@unittest.skipUnless(sys.platform == 'win32', 'requires the actual Windows component owner')
class WindowsClientOwnershipTests(unittest.TestCase):
    def test_python_and_node_start_owned_companions_and_restore_prompts(self):
        import win32api, win32con, win32event
        import windows_supervisor as supervisor
        node = os.environ.get('AUGMENTOR_PI_NODE') or shutil.which('node')
        self.assertTrue(node and (ROOT/'dist/prompt-library/src/client.js').is_file(),
                        'Build the shared Node client before this integration test.')
        with tempfile.TemporaryDirectory(prefix='augmentor owner café ') as temporary:
            root = private_directory(Path(temporary)/'private')
            env = {**os.environ, **{key: str(private_directory(root/name)) for key, name in (
                ('XDG_CONFIG_HOME', 'config'), ('XDG_RUNTIME_DIR', 'run'),
                ('XDG_DATA_HOME', 'data'), ('XDG_STATE_HOME', 'state'),
                ('AUGMENTOR_SHARED_STATE', 'shared'), ('AUGMENTOR_SHARED_DATA', 'shared-data'))},
                'AUGMENTOR_PYTHON': sys.executable}
            process = subprocess.Popen([sys.executable, '-I', '-Xutf8', '-B',
                str(ROOT/'services/windows_supervisor.py')], env=env, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
            handles = []
            endpoint = Path(env['XDG_RUNTIME_DIR'])/'supervisor'

            def node_call(method, params=None):
                javascript = '''
                    import {pathToFileURL} from 'node:url';
                    const {promptCall}=await import(pathToFileURL(process.argv[1]));
                    console.log(JSON.stringify(await promptCall(process.argv[2],JSON.parse(process.argv[3]))));
                '''
                result = subprocess.run([node, '--input-type=module', '-e', javascript,
                    str(ROOT/'dist/prompt-library/src/client.js'), method, json.dumps(params or {})],
                    capture_output=True, text=True, encoding='utf-8', timeout=50, check=True, env=env)
                return json.loads(result.stdout)

            def handle(pid):
                value = win32api.OpenProcess(win32con.SYNCHRONIZE | win32con.PROCESS_TERMINATE, False, pid)
                handles.append(value)
                return value

            try:
                deadline = time.monotonic()+20
                while True:
                    try: supervisor.request('status', owner=endpoint); break
                    except FileNotFoundError:
                        if time.monotonic()>deadline: self.fail('The fixture owner did not become ready.')
                        time.sleep(.1)
                with patch.dict(os.environ, env):
                    client = PromptClient()
                    prompts = client.call('host.describe')  # Python cold start.
                    prompt_process = handle(prompts['pid'])
                    memory = node_call('memory.dual.describe')  # Node cold start.
                    handle(memory['pid'])
                    status = supervisor.request('status', owner=endpoint)
                    self.assertTrue(all(item['running'] for item in status['companions'].values()))
                    saved = node_call('prompts.save', {'name': 'owned', 'content': 'Preserve café 日本語'})
                    self.assertEqual(client.call('prompts.list'), saved)
                    # A deliberate service fault must not lose committed data or
                    # cause the replacement to escape background ownership.
                    win32api.TerminateProcess(prompt_process, 1)
                    self.assertEqual(win32event.WaitForSingleObject(prompt_process, 5000), win32event.WAIT_OBJECT_0)
                    old_helper = status['companions']['prompts']['ownerProcessPid']
                    deadline = time.monotonic()+10
                    while supervisor.request('status', owner=endpoint)['companions']['prompts']['running']:
                        if time.monotonic()>deadline: self.fail('The owner did not reap the failed service.')
                        time.sleep(.1)
                    self.assertEqual(node_call('prompts.list'), saved)  # Node cold restart.
                    replacement = client.call('host.describe')
                    handle(replacement['pid'])
                    status = supervisor.request('status', owner=endpoint)
                    self.assertTrue(status['companions']['prompts']['running'])
                    self.assertNotEqual(status['companions']['prompts']['ownerProcessPid'], old_helper)
                    self.assertEqual(node_call('memory.dual.describe')['pid'], memory['pid'])
            finally:
                if process.poll() is None: process.kill()
                _out, errors = process.communicate(timeout=10)
                for item in handles:
                    try:
                        self.assertEqual(win32event.WaitForSingleObject(item, 5000), win32event.WAIT_OBJECT_0)
                    finally: item.Close()
                if errors: print(errors.decode('utf-8', errors='replace'))


if __name__ == '__main__':
    unittest.main()
