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


if __name__ == '__main__':
    unittest.main()
