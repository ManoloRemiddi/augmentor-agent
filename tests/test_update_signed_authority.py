# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual signed HTTP metadata/downloads joined to live Python authority.

Only the installation identity/qualified flags are synthetic. Production helper
configuration/HTTPS requirements are unchanged; the fixture uses the library's
existing explicit loopback fetcher. No inert installer bytes are executed.
"""
import base64
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import unittest

import test_update_installation as fixtures

ROOT=Path(__file__).resolve().parents[1]
NODE=ROOT/'outputs/payload/node/node.exe' if os.name=='nt' else Path(shutil.which('node') or '/unavailable-node')
AVAILABLE=NODE.is_file() and (ROOT/'node_modules/tuf-js/package.json').is_file()


@unittest.skipUnless(AVAILABLE,'Requires the locked Node/TUF dependencies, after npm ci.')
class SignedAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.InstallationAuthorityTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        payload=self.fixture.file.read_bytes();self.fixture.file.unlink()
        environment={key:value for key,value in os.environ.items() if not key.upper().startswith('NODE_')}
        self.child=subprocess.Popen([str(NODE),str(ROOT/'tests/helpers/update-signed-authority.mjs')],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=environment)
        self.addCleanup(self.close)
        self.replies=queue.Queue()
        def receive():
            while line:=self.child.stdout.readline(2*1024**2+1):self.replies.put(line)
            self.replies.put(None)
        self.reader=threading.Thread(target=receive,daemon=True);self.reader.start()
        result=self.command('seed',fixtureOnly=True,cache=str(self.fixture.updates/'repository'),
            release=self.fixture.release,payload=base64.b64encode(payload).decode('ascii'))
        self.assertTrue(result['authenticated']);self.assertEqual(result['catalog']['releases'],[self.fixture.release])
        self.assertEqual(result['downloads'],self.fixture.state['downloads'])
        if os.name=='nt':
            from platform_adapters.windows_identity import protect_inherited_download
            protect_inherited_download(self.fixture.file)
        self.assertEqual(self.fixture.file.read_bytes(),payload)
        self.fixture.state['candidate']=result['catalog']['releases'][0]
        self.fixture.state['downloads']=result['downloads'];self.fixture.save()

    def command(self,operation,**params):
        self.child.stdin.write(json.dumps({'operation':operation,**params}).encode()+b'\n');self.child.stdin.flush()
        try:raw=self.replies.get(timeout=10)
        except queue.Empty:raise TimeoutError('The private signed fixture did not reply.') from None
        if raw is None:raise RuntimeError('The private signed fixture exited.')
        if len(raw)>2*1024**2 or not raw.endswith(b'\n'):raise ValueError('Invalid fixture response.')
        result=json.loads(raw)
        if result.get('ok') is not True:raise ValueError(result.get('error','Publisher verification failed.'))
        return result

    def close(self):
        try:
            if self.child.poll() is None:self.command('quit')
        finally:
            try:self.child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.child.terminate();self.child.wait(timeout=5)  # Only this private fixture, never an app.
            for stream in (self.child.stdin,self.child.stdout,self.child.stderr):stream.close()
            self.reader.join(timeout=2)

    def refresh(self):return self.command('refresh')

    def test_signed_download_enters_live_authority_but_fresh_withdrawal_refuses_installation(self):
        with self.fixture.authority(repository=self.refresh) as authority:
            self.assertTrue(authority.check('prepared'))
            self.command('withdraw')
            with self.assertRaisesRegex(ValueError,'removed, withdrawn or changed'):
                authority.check('installer-ready')
        requests=self.command('requests')['requests']
        artifact='/'+self.fixture.release['artifacts'][0]['targetPath']
        self.assertEqual(requests.count(artifact),1)
        self.assertGreaterEqual(requests.count('/metadata/timestamp.json'),4)
        self.assertFalse((self.fixture.updates/'active.json').exists())

    def test_damaged_publisher_signature_cannot_reuse_cached_installation_authority(self):
        with self.fixture.authority(repository=self.refresh) as authority:
            self.command('damage-signature')
            with self.assertRaises(ValueError):authority.check('prepared')
        self.assertEqual(self.fixture.state['candidate'],self.fixture.release)
        self.assertFalse((self.fixture.updates/'active.json').exists())


if __name__=='__main__':unittest.main()
