# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest,tempfile,os,json,hashlib,sys,types,io,contextlib
from pathlib import Path
from unittest.mock import patch
import test_dsh_project_export as legacy
module=legacy.module
RemoteFixture=legacy.RemoteFixture
bundle_module=sys.modules['dsh_project_bundle']
@unittest.skipUnless(sys.platform.startswith('linux'),'Linux atomic bundle publication')
class BundleTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='augmentor-dsh-bundle-');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
 def remote(self):
  remote=RemoteFixture();remote.cursors={'authored-root':0,'authored-child':0};return remote
 def test_complete_capture_has_checked_segments_openings_and_no_inline_image_body(self):
  stage=self.root/'stage';stage.mkdir(mode=0o700);writer=module.ProjectBundle(stage);value=module.export_project(self.remote(),'authored-project',bundle=writer);manifest,raw=writer.finish(value)
  self.assertEqual(manifest['schema'],'augmentor-dsh-project-export/2');self.assertEqual(len(manifest['sessions']),1);self.assertEqual(len(manifest['relatedSessions']),1)
  for descriptor,original in zip(manifest['sessions']+manifest['relatedSessions'],value['sessions']+value['relatedSessions']):
   opening=json.loads((writer.objects/descriptor['opening']['sha256']).read_bytes());self.assertEqual(opening,original['opening']);records=[]
   for segment in descriptor['segments']:
    payload=(writer.objects/segment['sha256']).read_bytes();self.assertEqual(hashlib.sha256(payload).hexdigest(),segment['sha256']);self.assertEqual(len(payload),segment['bytes']);rows=json.loads(payload);self.assertEqual(len(rows),segment['count']);self.assertEqual(rows[0]['event']['seq'],segment['firstSeq']);records+=rows
   self.assertEqual(records,original['records'])
  self.assertEqual(json.loads(raw),manifest);self.assertEqual((stage/'project.json').stat().st_mode&0o077,0)
 def test_segment_boundaries_and_single_large_record_preserve_exact_values(self):
  stage=self.root/'stage';stage.mkdir();writer=module.ProjectBundle(stage);rows=[{'type':'event','event':{'seq':i,'type':'authored/data','data':{'text':'keep\n spaces 🌍'*i}}} for i in range(8)]
  with patch.object(bundle_module,'SEGMENT_RECORDS',2),patch.object(bundle_module,'SEGMENT_BYTES',500):descriptor=writer.session({'address':{},'opening':{},'records':rows})
  self.assertGreaterEqual(len(descriptor['segments']),4);self.assertEqual([r for ref in descriptor['segments'] for r in json.loads((writer.objects/ref['sha256']).read_bytes())],rows)
 def test_oversized_object_total_and_object_count_are_refused_without_truncation(self):
  for key,limit,values in [('MAX_OBJECT_BYTES',4,[b'12345']),('MAX_BUNDLE_BYTES',4,[b'123',b'45']),('MAX_OBJECTS',1,[b'a',b'b'])]:
   with self.subTest(key=key),tempfile.TemporaryDirectory(dir=self.root) as folder:
    writer=module.ProjectBundle(folder)
    with patch.object(bundle_module,key,limit),self.assertRaises(ValueError):
     for raw in values:writer.put(raw)
    self.assertFalse((Path(folder)/'project.json').exists())
 def test_duplicate_objects_share_disk_bytes_but_charge_each_expanded_reference(self):
  writer=module.ProjectBundle(self.root);one=writer.put(b'authored');two=writer.put(b'authored');self.assertEqual(one,two);self.assertEqual(len(list(writer.objects.iterdir())),1);self.assertEqual(writer.total,16)
 def test_atomic_publication_never_replaces_an_empty_raced_directory_or_link(self):
  for kind in ['directory','file','link']:
   with self.subTest(kind=kind):
    stage=self.root/('stage-'+kind);stage.mkdir();(stage/'project.json').write_text('authored');destination=self.root/('destination-'+kind)
    if kind=='directory':destination.mkdir()
    elif kind=='file':destination.write_text('previous')
    else:destination.symlink_to(self.root/'absent')
    with self.assertRaises(FileExistsError):bundle_module.publish(stage,destination)
    self.assertEqual((stage/'project.json').read_text(),'authored')
    if kind=='directory':self.assertEqual(list(destination.iterdir()),[])
    elif kind=='file':self.assertEqual(destination.read_text(),'previous')
    else:self.assertTrue(destination.is_symlink())
 def test_actual_cli_success_and_changed_source_cleanup(self):
  self.addCleanup(os.umask,os.umask(0o077))
  for changed in [False,True]:
   with self.subTest(changed=changed):
    remote=self.remote();remote.change=changed;fake=types.ModuleType('dsh.remote');fake.Remote=lambda *args:remote;output=self.root/('changed' if changed else 'complete')
    with patch.dict(sys.modules,{'dsh.remote':fake}),patch.object(sys,'argv',['export-dsh-project.py','--project','authored-project','--output',str(output),'--bundle']):
     if changed:
      with self.assertRaisesRegex(ValueError,'Source changed'):module.main()
      self.assertFalse(output.exists());self.assertFalse(any(p.name.startswith('.changed.') for p in self.root.iterdir()))
     else:
      capture=io.StringIO()
      with contextlib.redirect_stdout(capture):module.main()
      receipt=json.loads(capture.getvalue());raw=(output/'project.json').read_bytes();self.assertEqual(receipt['sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(receipt['manifestBytes'],len(raw));self.assertTrue((output/'objects').is_dir())
 def test_stored_image_bytes_are_external_and_verified_without_base64_expansion(self):
  fixture=legacy.ImageExportTests();fixture.setUp();self.addCleanup(fixture.doCleanups);stage=self.root/'images';stage.mkdir();writer=module.ProjectBundle(stage);remote=fixture.remote();remote.cursors['authored-root']=0
  value=module.export_project(remote,'authored-project',fixture.home,writer);manifest,raw=writer.finish(value);ref=manifest['attachments'][0];self.assertEqual(set(ref),{'attachmentId','bytes','sha256'});self.assertEqual((writer.objects/ref['sha256']).read_bytes(),fixture.raw);self.assertEqual(fixture.path.read_bytes(),fixture.raw);self.assertNotIn('data',ref)
if __name__=='__main__':unittest.main()
