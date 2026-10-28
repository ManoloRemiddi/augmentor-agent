# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import hashlib,importlib.util,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('legacy_assets',ROOT/'scripts/capture-dsh-legacy-assets.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

@unittest.skipUnless(sys.platform.startswith('linux'),'MX Linux asset capture helper')
class LegacyAssets(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name);self.home=self.base/'dsh';self.home.mkdir();self.stage=self.base/'stage';self.stage.mkdir();self.raw=b'Authored binary\x00\xff';self.row=self.store(self.raw,'file')
 def store(self,raw,kind):
  digest=hashlib.sha256(raw).hexdigest();path=self.home/'attachments/v1'/('file-objects' if kind=='file' else 'objects')/digest[:2]/digest;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);self.path=path;return {'kind':kind,'attachmentId':'sha256:'+digest,'bytes':len(raw)}
 def test_binary_exact_and_unrelated_store_never_scanned(self):
  (self.home/'attachments/v1/private-unrelated').write_bytes(b'not an asset')
  with patch.object(Path,'rglob',side_effect=AssertionError('No store scans')):value=module.capture(self.home,self.stage,[self.row])
  chunks=value['assets'][0]['chunks'];self.assertEqual(b''.join((self.stage/'objects'/r['sha256']).read_bytes() for r in chunks),self.raw);self.assertEqual(self.path.read_bytes(),self.raw);self.assertEqual(value['expandedBytes'],len(self.raw))
 def test_empty_file_has_no_zero_length_object(self):
  row=self.store(b'','file');value=module.capture(self.home,self.stage,[row]);self.assertEqual(value['assets'][0]['chunks'],[]);self.assertEqual(list((self.stage/'objects').iterdir()),[])
 def test_same_digest_in_both_source_namespaces_is_bound_per_kind(self):
  other=self.store(self.raw,'image');value=module.capture(self.home,self.stage,[self.row,other]);self.assertEqual(len(value['assets']),2);self.assertEqual(value['objects'],1);self.assertEqual(value['expandedBytes'],len(self.raw)*2)
 def test_all_requests_validate_before_any_source_read(self):
  for bad in [{'kind':'file','attachmentId':'../foreign','bytes':1},{**self.row,'bytes':True},{**self.row,'bytes':-1},{**self.row,'bytes':20*1024*1024+1},{**self.row,'extra':True},{**self.row,'kind':'other'}]:
   with self.subTest(bad=bad),patch.object(module.reader,'stored_attachment_bytes',side_effect=AssertionError('No early reads')):
    with self.assertRaises(ValueError):module.capture(self.home,self.stage,[self.row,bad])
  self.assertFalse((self.stage/'objects').exists())
 def test_duplicate_request_refuses_before_read(self):
  with patch.object(module.reader,'stored_attachment_bytes',side_effect=AssertionError('No early reads')):
   with self.assertRaises(ValueError):module.capture(self.home,self.stage,[self.row,self.row])
 def test_missing_object_refuses(self):
  self.path.unlink()
  with self.assertRaises(FileNotFoundError):module.capture(self.home,self.stage,[self.row])
 def test_changed_bytes_refuse(self):
  self.path.write_bytes(b'x'*len(self.raw))
  with self.assertRaisesRegex(ValueError,'checksum'):module.capture(self.home,self.stage,[self.row])
 def test_symlink_namespace_refuses(self):
  folder=self.home/'attachments/v1/file-objects';folder.rename(folder.with_name('saved'));folder.symlink_to(folder.with_name('saved'))
  with self.assertRaises(OSError):module.capture(self.home,self.stage,[self.row])
 def test_fifo_never_waits_for_writer(self):
  self.path.unlink();os.mkfifo(self.path)
  with self.assertRaisesRegex(ValueError,'file type'):module.capture(self.home,self.stage,[self.row])
