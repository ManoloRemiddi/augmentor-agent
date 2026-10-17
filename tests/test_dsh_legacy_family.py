# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util,json,os,socket,subprocess,sys,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import dsh_legacy_family as family
class FamilyGraph(unittest.TestCase):
 def row(self,sid,parent=None,origin=None):
  return {'header':{'id':sid,**({'parentSession':parent} if parent else {}),**({'origin':origin} if origin else {})}}
 def test_all_nested_children_and_no_user_fork_borrowing(self):
  rows=[self.row('root'),self.row('child','root','subagent'),self.row('grand','child','subagent'),self.row('fork','root'),self.row('foreign','other','subagent')]
  self.assertEqual([r['header']['id'] for r in family.family_rows(rows,['root'])],['root','child','grand'])
 def test_missing_root(self):
  with self.assertRaises(ValueError):family.family_rows([],['root'])
 def test_duplicate_root(self):
  with self.assertRaises(ValueError):family.family_rows([self.row('root')],['root','root'])
 def test_duplicate_index_identity(self):
  with self.assertRaises(ValueError):family.family_rows([self.row('root'),self.row('root')],['root'])
 def test_untyped_root(self):
  with self.assertRaises(ValueError):family.family_rows([self.row('root')],[{}])
 def test_subagent_root_refused(self):
  with self.assertRaises(ValueError):family.family_rows([self.row('root','other','subagent')],['root'])
 def test_family_bound(self):
  with self.assertRaises(ValueError):family.family_rows([self.row('root')]+[self.row(str(i),'root','subagent') for i in range(33)],['root'])
 def test_nanoseconds_losslessly_serialized(self):
  class Info:st_dev=1;st_ino=2;st_size=3;st_mtime_ns=1790000000000000001;st_ctime_ns=1790000000000000002
  value=family.identity(Info());self.assertEqual(json.loads(json.dumps(value))['mtime_ns'],'1790000000000000001');self.assertEqual(value['size'],3)
@unittest.skipUnless(sys.platform.startswith('linux'),'Linux source-family capture adapter')
class FamilyCapture(unittest.TestCase):
 def log(self,home,sid,parent=None,version=0,physical=0):
  directory=home/'sessions'/'project'/sid;directory.mkdir(parents=True,exist_ok=True);header={'type':'session','version':version,'id':sid,'createdAt':1,'delegationDepth':int(parent is not None),'cwd':str(home/'project'),**({'parentSession':parent,'origin':'subagent'} if parent else {})}
  raw=(json.dumps(header)+'\n'+json.dumps({'type':'session/end-seed','seq':0,'time':1,'data':{}})+'\n').encode();path=directory/('session'+('.v'+str(physical) if physical else '')+'.jsonl.zstd');run=subprocess.run(['zstd','-q','-c'],input=raw,capture_output=True,check=True);path.write_bytes(run.stdout);return path
 def setup(self,temp):
  home=Path(temp)/'dsh';(home/'project').mkdir(parents=True);a=self.log(home,'root');b=self.log(home,'child','root');workspace={'workspaceId':'authored','path':str(home/'project'),'title':'Authored','sessionIds':['root']};return home,a,b,workspace
 def test_missing_decoder_refuses_before_source_read_or_output(self):
  with tempfile.TemporaryDirectory() as temp:
   home,a,b,w=self.setup(temp);before=[a.read_bytes(),b.read_bytes()];out=Path(temp)/'snapshot';empty=Path(temp)/'empty-path';empty.mkdir()
   with patch.dict(os.environ,{'PATH':str(empty)}),patch.object(family,'index_sources',side_effect=AssertionError('Source must not be read')):
    with self.assertRaisesRegex(ValueError,'requires zstd.*Install the zstd system package'):
     family.freeze_family(home,w,out,lambda:self.fail('Workspace callback must not run'),{'archivedSessionIds':[],'pinnedSessionIds':[]})
   self.assertFalse(out.exists());self.assertFalse(list(Path(temp).glob('.dsh-source-family-*')));self.assertEqual(before,[a.read_bytes(),b.read_bytes()])
 def test_cli_missing_decoder_stops_before_contacting_dsh(self):
  with tempfile.TemporaryDirectory() as temp:
   home,a,b,w=self.setup(temp);before=[a.read_bytes(),b.read_bytes()];out=Path(temp)/'snapshot';empty=Path(temp)/'empty-path';empty.mkdir()
   with socket.socket() as listener:
    listener.bind(('127.0.0.1',0));listener.listen();listener.setblocking(False)
    base='http://127.0.0.1:'+str(listener.getsockname()[1])
    run=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/capture-dsh-legacy-family.py'),'--project','root','--output',str(out),'--dsh-home',str(home),'--base',base],env={**os.environ,'PATH':str(empty)},capture_output=True,text=True,timeout=10)
    with self.assertRaises(BlockingIOError):listener.accept()
   self.assertEqual(run.returncode,2);self.assertIn('requires zstd',run.stderr);self.assertIn('Install the zstd system package',run.stderr);self.assertNotIn('Traceback',run.stderr);self.assertEqual(run.stdout,'');self.assertFalse(out.exists());self.assertFalse(list(Path(temp).glob('.dsh-source-family-*')));self.assertEqual(before,[a.read_bytes(),b.read_bytes()])
 def test_whole_family_and_original_bytes_preserved(self):
  with tempfile.TemporaryDirectory() as temp:
   home,a,b,w=self.setup(temp);before=[a.read_bytes(),b.read_bytes()];out=Path(temp)/'snapshot';calls=[];result=family.freeze_family(home,w,out,lambda:calls.append(True),{'archivedSessionIds':[],'pinnedSessionIds':['root']});self.assertEqual(result['descendants'],1);manifest=json.loads((out/'family.json').read_bytes());self.assertEqual(manifest['organization']['pinnedSessionIds'],['root']);self.assertEqual(len(manifest['nodes']),2);self.assertEqual(before,[a.read_bytes(),b.read_bytes()]);self.assertEqual(calls,[True]);self.assertFalse(list(Path(temp).glob('.dsh-source-family-*')))
 def test_callback_failure_has_no_published_destination(self):
  with tempfile.TemporaryDirectory() as temp:
   home,a,b,w=self.setup(temp)
   def changed():raise ValueError('Authored workspace changed')
   with self.assertRaises(ValueError):family.freeze_family(home,w,Path(temp)/'out',changed,{'archivedSessionIds':[],'pinnedSessionIds':[]})
   self.assertFalse((Path(temp)/'out').exists());self.assertFalse(list(Path(temp).glob('.dsh-source-family-*')))
 def test_source_change_during_metadata_revalidation_refuses(self):
  with tempfile.TemporaryDirectory() as temp:
   home,a,b,w=self.setup(temp)
   def changed():a.write_bytes(a.read_bytes()+b'changed')
   with self.assertRaises(ValueError):family.freeze_family(home,w,Path(temp)/'out',changed,{'archivedSessionIds':[],'pinnedSessionIds':[]})
   self.assertFalse((Path(temp)/'out').exists())
 def test_existing_destination_preserved(self):
  with tempfile.TemporaryDirectory() as temp:
   home,a,b,w=self.setup(temp);out=Path(temp)/'out';out.mkdir();(out/'keep').write_bytes(b'keep')
   with self.assertRaises(ValueError):family.freeze_family(home,w,out,lambda:None,{'archivedSessionIds':[],'pinnedSessionIds':[]})
   self.assertEqual((out/'keep').read_bytes(),b'keep')
 def test_opposite_encoding_refused(self):
  with tempfile.TemporaryDirectory() as temp:
   home,a,b,w=self.setup(temp);(a.parent/'session.jsonl').write_bytes(b'keep')
   with self.assertRaises(ValueError):family.index_sources(home/'sessions')
 def test_future_generation_is_not_downgraded(self):
  with tempfile.TemporaryDirectory() as temp:
   home,a,b,w=self.setup(temp);(a.parent/'session.v5.jsonl.zstd').write_bytes(b'future')
   with self.assertRaises(ValueError):family.index_sources(home/'sessions')
 def test_filename_header_version_mismatch(self):
  with tempfile.TemporaryDirectory() as temp:
   home=Path(temp);self.log(home,'root',version=0,physical=4)
   with self.assertRaises(ValueError):family.index_sources(home/'sessions')
 def test_symlink_canonical_source_refused(self):
  with tempfile.TemporaryDirectory() as temp:
   home,a,b,w=self.setup(temp);a.unlink();a.symlink_to(b)
   with self.assertRaises(OSError):family.index_sources(home/'sessions')
 def test_fifo_canonical_source_never_blocks(self):
  with tempfile.TemporaryDirectory() as temp:
   home,a,b,w=self.setup(temp);a.unlink();os.mkfifo(a)
   with self.assertRaises(ValueError):family.index_sources(home/'sessions')
 def test_organization_foreign_id_refused(self):
  with tempfile.TemporaryDirectory() as temp:
   home,a,b,w=self.setup(temp)
   with self.assertRaises(ValueError):family.freeze_family(home,w,Path(temp)/'out',lambda:None,{'archivedSessionIds':['other'],'pinnedSessionIds':[]})
   self.assertFalse((Path(temp)/'out').exists())

 def test_output_inside_dsh_home_refused(self):
  with tempfile.TemporaryDirectory() as temp:
   home,a,b,w=self.setup(temp);before=[a.read_bytes(),b.read_bytes()]
   with self.assertRaisesRegex(ValueError,'outside the original DSH home'):family.freeze_family(home,w,home/'out',lambda:None,{'archivedSessionIds':[],'pinnedSessionIds':[]})
   self.assertFalse((home/'out').exists());self.assertEqual(before,[a.read_bytes(),b.read_bytes()])
 def test_raced_destination_preserved(self):
  with tempfile.TemporaryDirectory() as temp:
   home,a,b,w=self.setup(temp);out=Path(temp)/'out'
   def raced():out.mkdir();(out/'keep').write_bytes(b'keep')
   with self.assertRaises(OSError):family.freeze_family(home,w,out,raced,{'archivedSessionIds':[],'pinnedSessionIds':[]})
   self.assertEqual((out/'keep').read_bytes(),b'keep');self.assertFalse(list(Path(temp).glob('.dsh-source-family-*')))
