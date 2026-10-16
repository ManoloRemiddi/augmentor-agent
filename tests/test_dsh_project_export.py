# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import copy,importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('dsh_project_export',Path(__file__).resolve().parents[1]/'scripts/export-dsh-project.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class RemoteFixture:
    def __init__(self):
        self.workspace={'workspaceId':'authored-project','path':'/authored/project','title':'Authored','sessionIds':['authored-root']}
        self.cursors={'authored-root':3,'authored-child':1};self.running=False;self.calls=[];self.change=False;self.captures=0
    def call(self,method,p=None):
        self.calls.append(method)
        if method=='workspace.list':return {'items':[copy.deepcopy(self.workspace)],'archivedSessionIds':[],'pinnedSessionIds':['authored-root']}
        if method=='session.list':return {'items':[{'sessionId':'authored-root','running':self.running}]}
        raise AssertionError('Unexpected mutation '+method)
    def stream(self,method,args):
        self.calls.append(method);assert method=='session/follow';self.address=args['request']['address'];return self
    def item(self,sock):
        sid=self.address.get('sessionId',self.address.get('childSessionId'));self.captures+=1
        return {'type':'snapshot','header':{'id':sid},'cursor':self.cursors[sid]+int(self.change and self.captures>1)}
    def close(self):pass
    def invoke(self,method,p):
        self.calls.append(method);assert method=='session/page';a=p['request']['address'];sid=a.get('sessionId',a.get('childSessionId'))
        if sid=='authored-root':rows=[{'type':'event','event':{'type':'subagent/catalog','seq':0,'data':{'childId':'authored-child','mode':'one-shot'}}}]
        else:rows=[{'type':'event','event':{'type':'turn/end','seq':0,'data':{}}}]
        return {'records':rows,'hasMore':False}
class ExportTests(unittest.TestCase):
    def test_captures_direct_family_and_membership_through_read_only_calls(self):
        remote=RemoteFixture();value=module.export_project(remote,'authored-project')
        self.assertEqual(len(value['sessions']),1);self.assertEqual(len(value['relatedSessions']),1)
        self.assertEqual(value['relatedSessions'][0]['address']['parentSessionId'],'authored-root')
        self.assertEqual(value['pinnedSessionIds'],['authored-root'])
        self.assertEqual(set(remote.calls),{'workspace.list','session.list','session/follow','session/page'})
    def test_rejects_running_source_before_history_capture(self):
        remote=RemoteFixture();remote.running=True
        with self.assertRaisesRegex(ValueError,'Finish'):module.export_project(remote,'authored-project')
        self.assertNotIn('session/follow',remote.calls)
    def test_rejects_source_that_changes_during_capture(self):
        remote=RemoteFixture();remote.change=True
        with self.assertRaisesRegex(ValueError,'Source changed'):module.export_project(remote,'authored-project')
    def test_rejects_unknown_project_and_bulk_membership(self):
        remote=RemoteFixture()
        with self.assertRaisesRegex(ValueError,'exact DSH'):module.export_project(remote,'unknown')
        remote.workspace['sessionIds'].append('second')
        with self.assertRaisesRegex(ValueError,'exactly one'):module.export_project(remote,'authored-project')
if __name__=='__main__':unittest.main()
