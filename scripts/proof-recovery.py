#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real stopped-runtime recovery using isolated Pi state and a credential-free DSH profile."""
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root/'apps/native'), str(root/'services')]
from augmentor_linux.pi_client import PiClient
from augmentor_linux.adapters.dsh import DshAdapter
from dsh.setup import modules_directory
from recovery import recover, recover_saved_session

with tempfile.TemporaryDirectory(prefix='augmentor-recovery-proof-') as folder:
    work = Path(folder)
    os.environ.update(AUGMENTOR_PI_STATE=str(work/'pi-state'), AUGMENTOR_PI_CONFIG=str(work/'pi-config'),
        AUGMENTOR_SHARED_CONFIG=str(work/'shared-config'), XDG_STATE_HOME=str(work/'state'),
        AUGMENTOR_PI_NODE=shutil.which('node'), PI_OFFLINE='1', DSH_TELEMETRY_MODE='DISABLED')
    os.environ.pop('AUGMENTOR_PI_NO_AUTOSTART', None)
    pi = PiClient()
    try:
        recover(pi, 'pi', lambda _: None)
        assert pi.call('host.describe')
        print('Pi: stopped runtime started; health, history and catalog verified.', flush=True)
    finally:
        try: pi.call('host.shutdown')
        except Exception: pass
    home = work/'dsh'; profile = home/'profiles/web'; profile.mkdir(parents=True)
    modules, _ = modules_directory(Path(shutil.which('dsh')).resolve())
    (profile/'node_modules').symlink_to(modules, target_is_directory=True)
    (profile/'package.json').write_text(json.dumps({'name':'recovery-proof','private':True,'type':'module',
        'dsh':{'profile':{'bundles':['@deepseek-ai/dsh-base','@deepseek-ai/dsh-web-app']}}}))
    (profile/'cordis.yml').write_text('[]\n')
    (profile/'cordis.patch.yml').write_text('- id: session-title-llm\n  disabled: true\n')
    (home/'settings.yaml').write_text('llm-pi-ai:\n  providers: {}\n')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0)); port = probe.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    config = work/'shared-config'; config.mkdir()
    (config/'harnesses.json').write_text(json.dumps({'dsh':{'home':str(home),'endpoint':base}}))
    class FixtureAdapter(DshAdapter):
        def call(self, method, payload=None):
            assert method not in ('session.prompt','session.cancel')
            log = work/'state/augmentor-recovery/dsh-startup.log'
            if log.exists():
                tokens = re.findall(r'token=([A-Za-z0-9_-]+)', log.read_text())
                if tokens: self.remote.token = tokens[-1]
            return super().call(method, payload)
    client = FixtureAdapter(base=base, home=home)
    client.product = False  # The isolated base profile deliberately has no product plugin.
    children = []
    original = subprocess.Popen
    def launch(*args, **kwargs):
        child = original(*args, **kwargs); children.append(child); return child
    try:
        with patch('recovery.subprocess.Popen', side_effect=launch):
            recover(client, 'dsh', lambda _: None)
            assert len(children) == 1
            children[-1].terminate(); children[-1].wait(timeout=15)
            recover(client, 'dsh', lambda _: None)
            assert len(children) == 2
        print('DSH: stopped profile started, then terminated and recovered again; real history/catalog checks passed.', flush=True)
        legacy = home/'sessions/--tmp-augmentor-recovery-fixture--/legacy-proof/session.v3.jsonl.zstd'
        legacy.parent.mkdir(parents=True)
        records = [{'type':'session','version':3,'id':'legacy-proof','cwd':'/tmp/augmentor-recovery-fixture','createdAt':int(time.time()*1000),'isSeeded':False,'delegationDepth':0},
                   {'type':'turn/start','seq':0,'time':1,'data':{'turn':1}},
                   {'type':'user/message','seq':1,'time':2,'surfaceOp':'append','data':{'id':'fixture-message','role':'user','content':[{'type':'text','text':'Synthetic history only; no inference.'}],'source':{'kind':'user'}}},
                   {'type':'adaptive-reasoning/decision','seq':2,'time':3,'data':{'version':2,'turn':1,'step':1}},
                   {'type':'turn/end','seq':3,'time':4,'data':{'turn':1,'reason':{'kind':'completed'}}}]
        compress = "process.stdout.write(require('node:zlib').zstdCompressSync(require('node:fs').readFileSync(0)))"
        legacy.write_bytes(b''.join(subprocess.run(['node','-e',compress],input=(json.dumps(row)+'\n').encode(),capture_output=True,check=True).stdout for row in records))
        try: client.call('session.history',{'sessionId':'legacy-proof','maxMessages':1})
        except Exception as error: assert 'unknown to this harness' in str(error), str(error)
        else: raise AssertionError('The fixture did not reproduce the cold-read failure')
        recover_saved_session(client,'legacy-proof',lambda _:None)
        assert client.call('session.history',{'sessionId':'legacy-proof','maxMessages':1})['sessionId']=='legacy-proof'
        print('DSH: real refused legacy history repaired and reopened through recovery while the server stayed running.',flush=True)
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate(); child.wait(timeout=15)
