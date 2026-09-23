# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import concurrent.futures
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch
from augmentor_linux.prompt_client import PromptClient
from augmentor_linux.pi_client import ContractError

class SharedPromptTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.env=patch.dict(os.environ,{'AUGMENTOR_SHARED_STATE':str(root/'state'),'AUGMENTOR_SHARED_DATA':str(root/'data')})
        self.env.start();self.addCleanup(self.env.stop)
        self.client=PromptClient();self.pid=self.client.call('host.describe')['pid'];self.addCleanup(self.stop)
    def stop(self):
        try:os.kill(self.pid,signal.SIGTERM)
        except ProcessLookupError:return
        end=time.monotonic()+3
        while Path(self.client.base).exists() and time.monotonic()<end:time.sleep(.02)
    def create(self):return self.client.call('prompts.save',{'name':'rewrite','content':'Rewrite "[clipboard]". Café 😀'})['prompts'][0]
    def test_python_and_node_share_library_without_any_harness(self):
        row=self.create()
        raw=subprocess.check_output(['node','--input-type=module','-e',"import {promptCall} from './dist/prompt-library/src/client.js'; console.log(JSON.stringify(await promptCall('prompts.list')));"],text=True)
        self.assertEqual(json.loads(raw)['prompts'],[row])
    def test_rename_preserves_id_and_stale_save_delete_do_not_overwrite(self):
        row=self.create();other=PromptClient()
        updated=other.call('prompts.save',{'id':row['id'],'name':'plain','content':'Changed','expectedRevision':row['revision']})['prompts'][0]
        self.assertEqual(updated['id'],row['id'])
        for method in ('prompts.save','prompts.delete'):
            with self.assertRaisesRegex(ContractError,'changed'):self.client.call(method,{'id':row['id'],'name':'plain','content':'Lost draft','expectedRevision':row['revision']})
        self.assertEqual(self.client.call('prompts.list')['prompts'],[updated])
    def test_concurrent_creates_and_updates_have_one_winner(self):
        def save(_):
            try:return PromptClient().call('prompts.save',{'name':'same','content':'data'})
            except ContractError:return None
        with concurrent.futures.ThreadPoolExecutor(8) as pool:results=list(pool.map(save,range(8)))
        self.assertEqual(sum(r is not None for r in results),1)
        self.assertEqual(len(self.client.call('prompts.list')['prompts']),1)
    def test_import_deduplicates_preserves_collisions_and_never_resurrects_deleted_rows(self):
        row=self.create();before=row['content']
        params={'source':'dsh','prompts':[{'id':'old','name':'rewrite','content':before},{'id':'different','name':'rewrite','content':'Different text'}]}
        imported=self.client.call('prompts.import',params)
        self.assertEqual(len(imported['prompts']),2)
        self.assertEqual({p['content'] for p in imported['prompts']},{before,'Different text'})
        self.assertEqual(self.client.call('prompts.import',params),imported)
        self.client.call('prompts.delete',{'id':row['id'],'expectedRevision':row['revision']})
        self.assertEqual(len(self.client.call('prompts.import',params)['prompts']),1)
    def test_notification_reconnect_and_restart_keep_committed_data(self):
        revision=self.client.call('prompts.list')['revision']
        with concurrent.futures.ThreadPoolExecutor(1) as pool:
            pending=pool.submit(PromptClient().call,'prompts.watch',{'afterRevision':revision,'timeout':3})
            row=self.create();self.assertEqual(pending.result(timeout=4)['prompts'],[row])
        self.stop();self.pid=self.client.call('host.describe')['pid']
        self.assertEqual(self.client.call('prompts.list')['prompts'],[row])
    def test_request_deduplication_is_content_checked_and_protocol_is_private(self):
        p={'name':'once','content':'only once'}
        one=self.client.call('prompts.save',p,request_id='same-request')
        self.assertEqual(self.client.call('prompts.save',p,request_id='same-request'),one)
        with self.assertRaisesRegex(ContractError,'Request ID'):self.client.call('prompts.save',dict(p,content='changed'),request_id='same-request')
        self.assertEqual(os.stat(self.client.base).st_mode&0o777,0o700)
        with self.assertRaises(ContractError):self.client.call('prompts.save',{'name':'../escape','content':'bad'})
    def test_improvement_is_separate_revisioned_and_persistent(self):
        initial=self.client.call('prompts.list')['improvement']
        self.assertIn('Preserve the intent',initial['content']);self.assertNotIn('[clipboard]',initial['content']);self.assertNotIn('PROMPT:',initial['content'])
        saved=self.client.call('prompts.improvement.save',{'content':'Keep the language. Be concise.','expectedRevision':initial['revision']})
        self.assertEqual(saved['prompts'],[])
        with self.assertRaisesRegex(ContractError,'changed elsewhere'):
            self.client.call('prompts.improvement.save',{'content':'Stale change','expectedRevision':initial['revision']})
        row=self.client.call('prompts.save',{'name':'prompt','content':'Unrelated reusable prompt'})['prompts'][0]
        self.client.call('prompts.delete',{'id':row['id'],'expectedRevision':row['revision']})
        self.stop();self.pid=self.client.call('host.describe')['pid']
        self.assertEqual(self.client.call('prompts.list')['improvement'],saved['improvement'])
        restored=self.client.call('prompts.improvement.save',{'content':initial['defaultContent'],'expectedRevision':saved['improvement']['revision']})
        self.assertEqual(restored['improvement']['content'],initial['defaultContent'])
