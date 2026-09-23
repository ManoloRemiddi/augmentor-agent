# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services'))
from dsh.branch import BranchError, branch, boundary


def events():
    return [{'seq':i,'type':kind,'data':{}} for i,kind in enumerate([
        'turn/start','user/message','assistant/message','turn/end',
        'turn/start','user/message','assistant/message','turn/end'])]


class DshBranchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.log=events();self.calls=[];self.running=False;self.preset='augmentor-linux';self.lose=False
    def call(self,method,p):
        self.calls.append((method,p))
        if method=='session.list':return {'items':[{'sessionId':'source','agentPreset':self.preset,'cwd':'/work','running':self.running}]}
        if method=='session.history':
            # Force real pagination rather than satisfying the entire history
            # with one convenient fixture page.
            rows=[e for e in self.log if e['seq']<p.get('beforeSeq',999)]
            return {'events':[{'event':copy.deepcopy(e)} for e in rows[-3:]],'hasMore':len(rows)>3}
        if method=='session.models':return {'current':{'provider':'local','model':'fixture','reasoningEffort':'low'}}
        if method=='session.fork':
            if self.lose:raise TimeoutError('lost acknowledgement')
            return {'sessionId':'child-from-dsh'}
        if method=='session.create':return {'sessionId':p['sessionId']}
        if method=='session.selectModel':return {}
        raise AssertionError(method)
    def run_branch(self,seq=2,mode='reply',target='new',surface='linux',exact=None):
        return branch(self.call,{'sessionId':'source','newSessionId':target,'messageSeq':seq,'mode':mode},surface=surface,endpoint='http://127.0.0.1:3080',state=self.tmp.name,exact_fork=exact)
    def test_exact_edit_passes_cursor_and_excludes_legacy_fork(self):
        for event in self.log[4:]:event['seq']+=1
        self.log.insert(4,{'seq':4,'type':'agent/inbox/spliced','data':{'items':[]}})
        requests=[]
        def exact(p):requests.append(p);return {'sessionId':'exact-child'}
        result=self.run_branch(6,'edit',exact=exact)
        self.assertEqual(result['sessionId'],'exact-child')
        self.assertEqual(requests,[{'surface':'linux','sessionId':'source','atSeq':3,'expectedCursor':8}])
        self.assertFalse(any(method in ('session.fork','session.create') for method,_ in self.calls))
        self.assertEqual(self.run_branch(6,'edit',exact=exact),result)
        self.assertEqual(len(requests),1)

    def test_exact_fork_lost_ack_is_not_replayed_under_another_identity(self):
        requests=[]
        def exact(p):requests.append(p);raise TimeoutError('Child created but acknowledgement lost')
        with self.assertRaisesRegex(BranchError,'not be replayed'):self.run_branch(exact=exact)
        for target in ('new','different'):
            with self.assertRaisesRegex(BranchError,'unknown'):self.run_branch(target=target,exact=exact)
        self.assertEqual(len(requests),1)

    def test_exact_fork_known_child_resumes_model_setup_without_recreating(self):
        requests=[]
        def exact(p):requests.append(p);return {'sessionId':'exact-child'}
        original=self.call
        def failed(method,p):
            if method=='session.selectModel':raise TimeoutError('Lost setup acknowledgement')
            return original(method,p)
        self.call=failed
        with self.assertRaises(TimeoutError):self.run_branch(exact=exact)
        self.call=original
        self.assertEqual(self.run_branch(exact=exact)['sessionId'],'exact-child')
        self.assertEqual(len(requests),1)
    def test_reply_uses_exact_closed_turn_and_preserves_source(self):
        original=copy.deepcopy(self.log);result=self.run_branch()
        self.assertEqual(result['sessionId'],'child-from-dsh')
        self.assertIn(('session.fork',{'sessionId':'source','atSeq':3}),self.calls)
        self.assertEqual(original,self.log);self.assertFalse(any(m=='session.prompt' for m,p in self.calls))
        count=len(self.calls);self.assertEqual(self.run_branch(),result);self.assertEqual(len(self.calls),count)
        self.assertEqual(result['selection']['reasoningEffort'],'low')
    def test_latest_edit_excludes_its_turn_and_first_edit_starts_clean(self):
        self.run_branch(5,'edit');self.assertIn(('session.fork',{'sessionId':'source','atSeq':3}),self.calls)
        self.log=self.log[:4];self.run_branch(1,'edit','first')
        self.assertIn(('session.create',{'sessionId':'first','cwd':'/work','agentPreset':'augmentor-linux'}),self.calls)
    def test_invalid_old_open_tool_or_steered_targets_never_mutate(self):
        for seq,mode in [(1,'edit'),(99,'reply'),(2,'wrong')]:
            with self.assertRaises(BranchError):self.run_branch(seq,mode)
        self.log[3]['type']='tool/result'
        with self.assertRaisesRegex(BranchError,'final reply'):self.run_branch(2)
        self.log=events()[:-1]
        with self.assertRaisesRegex(BranchError,'Stop'):self.run_branch(6)
        self.log=events();self.log[6]['type']='user/message'
        with self.assertRaisesRegex(BranchError,'steered'):self.run_branch(6,'edit')
        self.assertFalse(any(m in ('session.fork','session.create') for m,p in self.calls))
    def test_hidden_runtime_context_does_not_replace_latest_human_input(self):
        for event in self.log[6:]:event['seq']+=1
        self.log.insert(6,{'seq':6,'type':'user/message','data':{'source':{'kind':'plugin'},'content':[{'type':'text','text':'runtime context'}]}})
        self.run_branch(5,'edit')
        self.assertIn(('session.fork',{'sessionId':'source','atSeq':3}),self.calls)
    def test_spliced_input_before_next_turn_is_refused_before_fork(self):
        for event in self.log[4:]:event['seq']+=1
        self.log.insert(4,{'seq':4,'type':'agent/inbox/spliced','data':{'items':[]}})
        with self.assertRaisesRegex(BranchError,'cannot isolate'):
            self.run_branch(6,'edit')
        self.assertFalse(any(method in ('session.fork','session.create','session.selectModel') for method,_ in self.calls))

    def test_active_chat_and_cross_role_are_refused(self):
        self.running=True
        with self.assertRaisesRegex(BranchError,'Stop'):self.run_branch()
        self.running=False
        with self.assertRaisesRegex(BranchError,'role'):self.run_branch(surface='browser')
        self.preset='augmentor';self.assertEqual(self.run_branch(surface='browser')['agentPreset'],'augmentor')
    def test_lost_ack_is_journaled_and_not_replayed_even_with_new_client_id(self):
        self.lose=True
        with self.assertRaisesRegex(BranchError,'not be replayed'):self.run_branch()
        for target in ('new','another-new'):
            with self.assertRaisesRegex(BranchError,'unknown outcome|outcome is unknown'):self.run_branch(target=target)
        self.assertEqual(sum(m=='session.fork' for m,p in self.calls),1)
        for path in (Path(self.tmp.name)/'dsh-branches').glob('*.json'):
            self.assertEqual(path.stat().st_mode&0o777,0o600)
    def test_failed_child_setup_resumes_known_child_without_another_fork(self):
        original=self.call
        def failing(method,p):
            if method=='session.selectModel':raise TimeoutError('lost setup acknowledgement')
            return original(method,p)
        self.call=failing
        with self.assertRaises(TimeoutError):self.run_branch()
        self.call=original;self.assertEqual(self.run_branch()['sessionId'],'child-from-dsh')
        self.assertEqual(sum(m=='session.fork' for m,p in self.calls),1)
