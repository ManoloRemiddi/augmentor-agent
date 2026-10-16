# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import copy,importlib.util,unittest,os,tempfile,hashlib,base64,json,sys,types,io,contextlib
from unittest.mock import patch
from pathlib import Path
spec=importlib.util.spec_from_file_location('dsh_project_export',Path(os.environ.get('AUGMENTOR_PI_TEST_ROOT',Path(__file__).resolve().parents[1]))/'scripts/export-dsh-project.py')
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
class MultiRemote(RemoteFixture):
    def __init__(self):
        super().__init__();self.workspace['sessionIds'].append('authored-second');self.cursors['authored-second']=1
    def call(self,method,p=None):
        value=super().call(method,p)
        if method=='session.list':value['items'].append({'sessionId':'authored-second','running':False})
        if method=='workspace.list':value['pinnedSessionIds']=['authored-second','authored-root']
        return value

class ExportTests(unittest.TestCase):
    def test_compact_export_preserves_every_field_when_indentation_alone_exceeds_bound(self):
        value=module.export_project(RemoteFixture(),'authored-project')
        compact=module.encode_export(value);pretty=(json.dumps(value,indent=2)+'\n').encode()
        self.assertLess(len(compact),len(pretty))
        with patch.object(module,'MAX_EXPORT_BYTES',len(pretty)-1):
            captured=module.export_project(RemoteFixture(),'authored-project')
            self.assertEqual(module.encode_export(captured),compact)
        self.assertEqual(json.loads(compact),value)
    def test_published_byte_bound_includes_unicode_escapes_and_final_newline(self):
        value={'authored':{'text':'Caffè 🌍\n  keep whitespace\t','unknown':{'nested':[None,True,1.25]}}}
        raw=module.encode_export(value)
        self.assertEqual(json.loads(raw),value);self.assertTrue(raw.endswith(b'\n'))
        with patch.object(module,'MAX_EXPORT_BYTES',len(raw)):
            self.assertEqual(module.encode_export(value),raw)
        with patch.object(module,'MAX_EXPORT_BYTES',len(raw)-1):
            with self.assertRaisesRegex(ValueError,'size bound'):module.encode_export(value)
    def test_cli_publishes_exact_bounded_bytes_and_never_overwrites_previous_export(self):
        self.addCleanup(os.umask,os.umask(0o077))
        with tempfile.TemporaryDirectory(prefix='augmentor-dsh-compact-export-') as folder:
            output=Path(folder)/'export.json';fake=types.ModuleType('dsh.remote');fake.Remote=lambda *args:RemoteFixture()
            argv=['export-dsh-project.py','--project','authored-project','--output',str(output)]
            with patch.dict(sys.modules,{'dsh.remote':fake}),patch.object(sys,'argv',argv):
                report=io.StringIO()
                with contextlib.redirect_stdout(report):module.main()
                raw=output.read_bytes();receipt=json.loads(report.getvalue())
                if os.name=='posix':self.assertEqual(output.stat().st_mode&0o077,0)
                self.assertEqual(raw,module.encode_export(module.export_project(RemoteFixture(),'authored-project')))
                self.assertEqual(receipt['bytes'],len(raw));self.assertEqual(receipt['sha256'],hashlib.sha256(raw).hexdigest())
                with self.assertRaisesRegex(ValueError,'never overwrite'):module.main()
                self.assertEqual(output.read_bytes(),raw);self.assertEqual(list(Path(folder).iterdir()),[output])
    def test_cli_refuses_oversized_archive_without_creating_output_or_temporary_files(self):
        self.addCleanup(os.umask,os.umask(0o077))
        with tempfile.TemporaryDirectory(prefix='augmentor-dsh-compact-refusal-') as folder:
            output=Path(folder)/'export.json';fake=types.ModuleType('dsh.remote');fake.Remote=lambda *args:RemoteFixture()
            with patch.dict(sys.modules,{'dsh.remote':fake}),patch.object(sys,'argv',['export-dsh-project.py','--project','authored-project','--output',str(output)]),patch.object(module,'MAX_EXPORT_BYTES',1):
                with self.assertRaisesRegex(ValueError,'size bound'):module.main()
            self.assertEqual(list(Path(folder).iterdir()),[])
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
    def test_rejects_unknown_project_and_missing_member(self):
        remote=RemoteFixture()
        with self.assertRaisesRegex(ValueError,'exact DSH'):module.export_project(remote,'unknown')
        remote.workspace['sessionIds'].append('second')
        with self.assertRaisesRegex(ValueError,'Finish'):module.export_project(remote,'authored-project')
    def test_captures_all_parents_and_preserves_pin_order(self):
        remote=MultiRemote();value=module.export_project(remote,'authored-project')
        self.assertEqual([s['opening']['header']['id'] for s in value['sessions']],remote.workspace['sessionIds'])
        self.assertEqual(value['pinnedSessionIds'],['authored-second','authored-root'])
        self.assertEqual(len(value['relatedSessions']),1)
        self.assertEqual(set(remote.calls),{'workspace.list','session.list','session/follow','session/page'})
    def test_duplicate_membership_is_refused_before_capture(self):
        remote=RemoteFixture();remote.workspace['sessionIds']*=2
        with self.assertRaisesRegex(ValueError,'distinct'):module.export_project(remote,'authored-project')
        self.assertNotIn('session/follow',remote.calls)
    def test_empty_project_is_exported_without_inventing_a_conversation(self):
        remote=RemoteFixture();remote.workspace['sessionIds']=[]
        value=module.export_project(remote,'authored-project')
        self.assertEqual(value['sessions'],[]);self.assertEqual(value['relatedSessions'],[])
        self.assertEqual(value['pinnedSessionIds'],[]);self.assertNotIn('session/follow',remote.calls)
    def test_rejects_second_parent_that_changes(self):
        class Changed(MultiRemote):
            def item(self,sock):
                value=super().item(sock)
                if value['header']['id']=='authored-second' and self.captures>3:value['cursor']+=1
                return value
        with self.assertRaisesRegex(ValueError,'Source changed'):module.export_project(Changed(),'authored-project')
    def test_rejects_changed_project_membership(self):
        class Changed(MultiRemote):
            def call(self,method,p=None):
                value=super().call(method,p)
                if method=='workspace.list' and self.calls.count(method)>1:value['items'][0]['title']='Changed title'
                return value
        with self.assertRaisesRegex(ValueError,'Workspace changed'):module.export_project(Changed(),'authored-project')
    def test_rejects_source_that_starts_after_history_capture(self):
        class Started(MultiRemote):
            def call(self,method,p=None):
                value=super().call(method,p)
                if method=='session.list' and self.calls.count(method)>1:value['items'][1]['running']=True
                return value
        with self.assertRaisesRegex(ValueError,'started'):module.export_project(Started(),'authored-project')
    def test_child_cannot_alias_another_parent(self):
        class Alias(RemoteFixture):
            def invoke(self,method,p):
                value=super().invoke(method,p)
                value['records'][0]['event']['data']['childId']='authored-root'
                return value
        with self.assertRaisesRegex(ValueError,'conflicting'):module.export_project(Alias(),'authored-project')
    def test_child_identity_cannot_silently_move_between_parents(self):
        class Conflict(MultiRemote):
            def invoke(self,method,p):
                if p['request']['address'].get('sessionId')=='authored-second':
                    self.calls.append(method)
                    return {'records':[{'type':'event','event':{'type':'subagent/catalog','seq':0,'data':{'childId':'authored-child','mode':'one-shot'}}}],'hasMore':False}
                return super().invoke(method,p)
        with self.assertRaisesRegex(ValueError,'conflicting'):module.export_project(Conflict(),'authored-project')
    def test_combined_parent_bytes_are_bounded_before_family_capture(self):
        class Payload(MultiRemote):
            def invoke(self,method,p):
                value=super().invoke(method,p)
                value['records'][0]['event']['data']['authoredPayload']='x'*400
                return value
        remote=Payload()
        with patch.object(module,'MAX_EXPORT_BYTES',1100):
            with self.assertRaisesRegex(ValueError,'size bound'):module.export_project(remote,'authored-project')
        self.assertEqual(remote.calls.count('session/page'),2)

@unittest.skipUnless(os.name=='posix','Descriptor-relative MX image export')
class ImageExportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='augmentor-dsh-image-export-');self.addCleanup(self.temp.cleanup);self.home=Path(self.temp.name)
        self.raw=b'Independently authored immutable stored bytes';self.sha=hashlib.sha256(self.raw).hexdigest();self.identity='sha256:'+self.sha
        self.path=self.home/'attachments/v1/objects'/self.sha[:2]/self.sha;self.path.parent.mkdir(parents=True);self.path.write_bytes(self.raw)
        self.part={'type':'image','attachment':{'attachmentId':self.identity,'bytes':len(self.raw)}}
    def remote(self):
        part=self.part
        class Images(RemoteFixture):
            def invoke(self,method,p):
                self.calls.append(method)
                return {'records':[{'type':'event','event':{'type':'user/message','seq':0,'data':{'content':[copy.deepcopy(part),copy.deepcopy(part)]}}}],'hasMore':False}
        return Images()
    def test_reads_only_exact_named_objects_once_and_preserves_bytes(self):
        value=module.export_project(self.remote(),'authored-project',self.home)
        self.assertEqual(len(value['attachments']),1);blob=value['attachments'][0]
        self.assertEqual(blob['attachmentId'],self.identity);self.assertEqual(base64.b64decode(blob['data']),self.raw)
        self.assertEqual(self.path.read_bytes(),self.raw)
    def test_missing_and_changed_image_abort_the_whole_export(self):
        self.path.unlink()
        with self.assertRaises(FileNotFoundError):module.export_project(self.remote(),'authored-project',self.home)
        self.path.write_bytes(b'X'*len(self.raw))
        with self.assertRaisesRegex(ValueError,'checksum'):module.export_project(self.remote(),'authored-project',self.home)
    def test_no_symlink_is_followed_for_object_or_parent(self):
        other=self.home/'private-unrelated';other.write_bytes(self.raw);self.path.unlink();self.path.symlink_to(other)
        with self.assertRaises(OSError):module.export_project(self.remote(),'authored-project',self.home)
        self.path.unlink();self.path.parent.rmdir();self.path.parent.symlink_to(self.home,target_is_directory=True)
        with self.assertRaises(OSError):module.export_project(self.remote(),'authored-project',self.home)
    def test_image_payload_is_charged_to_existing_whole_export_bound(self):
        with patch.object(module,'MAX_EXPORT_BYTES',500):
            with self.assertRaisesRegex(ValueError,'size bound'):module.export_project(self.remote(),'authored-project',self.home)
    def test_image_export_requires_explicit_store_and_rejects_path_ids(self):
        with self.assertRaisesRegex(ValueError,'explicit DSH home'):module.export_project(self.remote(),'authored-project')
        self.part['attachment']['attachmentId']='../../unrelated'
        with self.assertRaisesRegex(ValueError,'Invalid source image'):module.export_project(self.remote(),'authored-project',self.home)
    def test_source_cursor_is_rechecked_after_image_reads(self):
        remote=self.remote();original=module.image_bundle
        def capture(*args):
            value=original(*args);remote.cursors['authored-root']+=1;return value
        with patch.object(module,'image_bundle',capture):
            with self.assertRaisesRegex(ValueError,'source changed'):module.export_project(remote,'authored-project',self.home)
if __name__=='__main__':unittest.main()
