# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import base64,copy,hashlib,importlib.util,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_dsh_project_export import module,RemoteFixture

@unittest.skipUnless(os.name=='posix','MX descriptor-relative source file export')
class FileExportTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='augmentor-dsh-file-export-');self.addCleanup(self.temp.cleanup);self.home=Path(self.temp.name)
  self.raw=b'Authored complete document\x00\xff\n';self.identity='sha256:'+hashlib.sha256(self.raw).hexdigest();self.part={'type':'file','attachment':{'attachmentId':self.identity,'bytes':len(self.raw),'name':'authored.bin'}};self.store(self.raw)
 def store(self,raw):
  self.raw=raw;self.identity='sha256:'+hashlib.sha256(raw).hexdigest();self.part['attachment'].update(attachmentId=self.identity,bytes=len(raw));self.path=self.home/'attachments/v1/file-objects'/self.identity[7:9]/self.identity[7:];self.path.parent.mkdir(parents=True,exist_ok=True);self.path.write_bytes(raw)
 def remote(self):
  part=self.part
  class Files(RemoteFixture):
   def invoke(self,m,p):
    self.calls.append(m);return {'records':[{'type':'event','event':{'type':'user/message','seq':0,'data':{'content':[copy.deepcopy(part),copy.deepcopy(part)]}}}],'hasMore':False}
  return Files()
 def test_exact_binary_bytes_and_names_are_preserved_without_store_scan(self):
  value=module.export_project(self.remote(),'authored-project',self.home);self.assertEqual(len(value['files']),1);self.assertEqual(base64.b64decode(value['files'][0]['data']),self.raw);self.assertEqual(value['sessions'][0]['records'][0]['event']['data']['content'][0],self.part);self.assertNotIn('attachments',value)
 def test_twenty_mib_file_is_segmented_without_raising_object_ceiling(self):
  self.store(bytes(range(256))*(20*1024*1024//256));stage=self.home/'bundle';stage.mkdir(mode=0o700);bundle=module.ProjectBundle(stage);value=module.export_project(self.remote(),'authored-project',self.home,bundle);manifest,raw=bundle.finish(value);row=manifest['files'][0]
  self.assertEqual([p['bytes'] for p in row['chunks']],[8*1024*1024,8*1024*1024,4*1024*1024]);self.assertEqual(b''.join((stage/'objects'/r['sha256']).read_bytes() for r in row['chunks']),self.raw);self.assertLess(len(raw),4096);self.assertEqual(json.loads(raw)['files'],value['files'])
 def test_empty_file_is_preserved_without_an_invalid_zero_length_object(self):
  self.store(b'');stage=self.home/'bundle';stage.mkdir(mode=0o700);bundle=module.ProjectBundle(stage);value=module.export_project(self.remote(),'authored-project',self.home,bundle);self.assertEqual(value['files'][0],{'attachmentId':self.identity,'bytes':0,'chunks':[]})
 def test_missing_and_changed_files_refuse_the_complete_export(self):
  self.path.unlink()
  with self.assertRaises(FileNotFoundError):module.export_project(self.remote(),'authored-project',self.home)
  self.path.write_bytes(b'x'*len(self.raw))
  with self.assertRaisesRegex(ValueError,'checksum'):module.export_project(self.remote(),'authored-project',self.home)
 def test_symlink_and_fifo_objects_are_not_read(self):
  self.path.unlink();self.path.symlink_to(self.home/'unrelated')
  with self.assertRaises(OSError):module.export_project(self.remote(),'authored-project',self.home)
  self.path.unlink();os.mkfifo(self.path,0o600)
  with self.assertRaisesRegex(ValueError,'file type'):module.export_project(self.remote(),'authored-project',self.home)
 def test_explicit_home_path_ids_sizes_and_aggregate_bounds(self):
  with self.assertRaisesRegex(ValueError,'explicit DSH home'):module.export_project(self.remote(),'authored-project')
  with patch.object(module,'MAX_EXPORT_BYTES',300):
   with self.assertRaisesRegex(ValueError,'size bound'):module.export_project(self.remote(),'authored-project',self.home)
  for bad in [-1,20*1024*1024+1,True]:
   self.part['attachment']['bytes']=bad
   with self.assertRaisesRegex(ValueError,'Invalid source file'):module.export_project(self.remote(),'authored-project',self.home)
  self.part['attachment'].update(bytes=len(self.raw),attachmentId='../../unrelated')
  with self.assertRaisesRegex(ValueError,'Invalid source file'):module.export_project(self.remote(),'authored-project',self.home)
 def test_source_cut_is_rechecked_after_file_capture(self):
  remote=self.remote();original=module.file_bundle
  def changed(*args):
   value=original(*args);remote.cursors['authored-root']+=1;return value
  with patch.object(module,'file_bundle',changed):
   with self.assertRaisesRegex(ValueError,'source changed'):module.export_project(remote,'authored-project',self.home)
 def test_file_object_count_refuses_before_any_source_object_read(self):
  parts=[{'type':'file','attachment':{'attachmentId':'sha256:'+format(i,'064x'),'bytes':1,'name':'authored.bin'}} for i in range(10001)]
  rows=[{'records':[{'event':{'type':'user/message','data':{'content':parts}}}]}]
  with patch.object(module,'stored_attachment_bytes',side_effect=AssertionError('No source read expected')):
   with self.assertRaisesRegex(ValueError,'Too many'):module.file_bundle(rows,self.home,lambda value:None)
