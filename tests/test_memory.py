# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services'))
from memory.provider import Memory,MemoryError,validate


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.calls=[];self.fail=False;self.pending={}
        def request(c,method,path,body=None):
            self.calls.append((c,method,path,body))
            if self.fail:raise MemoryError('Test outage')
            if path=='/health':return {'status':'healthy'}
            if path=='/openapi.json':return {'info':{'version':'0.9.2'}}
            if path.endswith('/memories/recall'):return {'results':[{'id':'fact','text':'Stored fact','type':'world'}]}
            if path.endswith('/memories'):
                self.pending[body['operation_id']]=body
                return {'success':True,'operation_id':body['operation_id']}
            if '/operations/' in path:return {'status':'completed'}
            if '/documents' in path:return {'items':[],'total':0}
            raise AssertionError(path)
        self.request=request;self.store=Memory(Path(self.tmp.name)/'memory.sqlite3',request)
        self.fields={'endpoint':'http://127.0.0.1:8888','apiKey':'','userBank':'user-bank','projectBank':'project-bank','activeScope':'user'}
    def call(self,method,p=None,id='request'):return self.store.call('memory.'+method,p or {},id)
    def connect(self,patch=None):
        token=self.call('check',{**self.fields,**(patch or {})})['token']
        return self.call('configure',{'token':token})
    def test_off_by_default_and_connection_check_does_not_save(self):
        self.assertFalse(self.call('describe')['enabled']);self.assertFalse(self.call('agentRecall',{'query':'anything'})['enabled']);self.assertEqual(self.calls,[])
        token=self.call('check',self.fields)['token'];self.assertFalse(self.call('describe')['enabled'])
        self.call('configure',{'token':token});self.assertTrue(self.call('describe')['enabled'])
        with self.assertRaises(MemoryError):self.call('configure',{'token':token})
    def test_scopes_are_separate_and_model_cannot_supply_scope_or_bank(self):
        self.connect();self.call('agentRecall',{'query':'facts'})
        self.assertIn('/banks/user-bank/',self.calls[-1][2])
        self.connect({'activeScope':'project'});self.call('agentRecall',{'query':'facts'})
        self.assertIn('/banks/project-bank/',self.calls[-1][2])
        count=len(self.calls)
        for extra in ({'scope':'user'},{'bank_id':'other'}):
            with self.assertRaises(MemoryError):self.call('agentRecall',{'query':'facts',**extra})
        self.assertEqual(len(self.calls),count)
    def test_retention_is_explicit_async_durable_and_not_replayed(self):
        self.connect();result=self.call('retain',{'content':'Preference π','scope':'user','provenance':{'surface':'linux','harness':'pi'}},id='save-1')
        self.assertEqual(result['status'],'pending');before=len(self.calls)
        self.assertEqual(self.call('retain',{'content':'Preference π','scope':'user','provenance':{'surface':'linux','harness':'pi'}},id='save-1'),result)
        self.assertEqual(len(self.calls),before)
        self.store=Memory(self.store.path,self.request)
        self.assertEqual(self.call('operation',{'id':result['id']})['status'],'completed')
        with self.assertRaises(MemoryError):self.call('operation',{'scope':'project','id':result['id']})
        self.assertEqual(self.pending[result['id']]['items'][0]['metadata']['harness'],'pi')
        self.assertEqual(self.store.path.stat().st_mode&0o777,0o600)
    def test_outage_never_blocks_chat_and_unknown_write_is_not_repeated(self):
        self.connect();self.fail=True
        self.assertTrue(self.call('agentRecall',{'query':'facts'})['unavailable'])
        result=self.call('retain',{'content':'An explicitly retained fact'},id='lost');self.assertEqual(result['status'],'unknown')
        before=len(self.calls);self.assertEqual(self.call('retain',{'content':'An explicitly retained fact'},id='lost'),result);self.assertEqual(len(self.calls),before)
    def test_disable_blocks_new_retention_and_recall_but_keeps_data_controls(self):
        self.connect();self.call('disable');before=len(self.calls)
        self.assertFalse(self.call('agentRecall',{'query':'facts'})['enabled'])
        with self.assertRaises(MemoryError):self.call('retain',{'content':'should not be sent'})
        self.assertEqual(len(self.calls),before);self.call('documents')
    def test_pending_retention_cannot_be_deleted_until_reconciled(self):
        self.connect();record=self.call('retain',{'content':'Fact'})
        with self.assertRaisesRegex(MemoryError,'pending'):self.call('delete',{'id':record['document']})
        self.call('operation',{'id':record['id']});self.call('delete',{'id':record['document']})
        self.assertEqual(self.call('operation',{'id':record['id']})['status'],'deleted')
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT content FROM operations').fetchone()[0],'')
    def test_remote_key_and_destination_validation_and_secret_redaction(self):
        for patch in ({'endpoint':'http://remote.example'},{'endpoint':'https://remote.example'}, {'endpoint':'https://user:pass@remote.example','apiKey':'key'}, {'projectBank':'user-bank'}, {'activeScope':'elsewhere'}):
            with self.assertRaises(MemoryError):validate({**self.fields,**patch})
        self.connect({'endpoint':'https://memory.example','apiKey':'private-token'})
        self.assertNotIn('private-token',json.dumps(self.call('describe')))
        before=len(self.calls)
        with self.assertRaisesRegex(MemoryError,'API key'):self.call('check',{**self.fields,'endpoint':'https://other.example'})
        self.assertEqual(len(self.calls),before)
    def test_stale_check_cannot_restore_memory_after_disable(self):
        token=self.call('check',self.fields)['token'];self.call('disable')
        with self.assertRaises(MemoryError):self.call('configure',{'token':token})
