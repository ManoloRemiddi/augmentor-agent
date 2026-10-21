# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util,io,os,tarfile,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('legacy_fetch',ROOT/'scripts/fetch-dsh-legacy-format-source.py');fetcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(fetcher)
class PublicFormatSourceFetch(unittest.TestCase):
 def archive(self,root,name,data=b'authored invalid source',symbolic=False):
  path=root/'public.tar.gz'
  with tarfile.open(path,'w:gz') as tar:
   row=tarfile.TarInfo(name)
   if symbolic:row.type=tarfile.SYMTYPE;row.linkname=str(root/'must-stay.txt');tar.addfile(row)
   else:row.size=len(data);tar.addfile(row,io.BytesIO(data))
  return path
 def refused(self,name,data=b'authored invalid source',symbolic=False):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);sentinel=root/'must-stay.txt';sentinel.write_bytes(b'keep');archive=self.archive(root,name,data,symbolic);destination=root/'new';original=archive.read_bytes()
   with self.assertRaises(ValueError):fetcher.fetch(destination,archive)
   self.assertFalse(destination.exists());self.assertEqual(sentinel.read_bytes(),b'keep');self.assertEqual(archive.read_bytes(),original);self.assertFalse(list(root.glob('.dsh-format-source-*')))
 def test_checksum_refusal(self):self.refused('public-root/LICENSE')
 def test_incomplete_archive(self):self.refused('public-root/unknown.txt')
 def test_traversal_ignored_and_incomplete(self):self.refused('public-root/../must-stay.txt')
 def test_expected_source_symlink_refused(self):self.refused('public-root/LICENSE',symbolic=True)
 def test_existing_destination_preserved(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);destination=root/'old';destination.mkdir();sentinel=destination/'keep';sentinel.write_bytes(b'keep')
   with self.assertRaises(ValueError):fetcher.fetch(destination,root/'missing-archive')
   self.assertEqual(sentinel.read_bytes(),b'keep')
 @unittest.skipUnless(os.name=='posix','POSIX symlink preservation adapter')
 def test_destination_symlink_preserved(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);target=root/'target';target.mkdir();destination=root/'link';destination.symlink_to(target)
   with self.assertRaises(ValueError):fetcher.fetch(destination,root/'missing')
   self.assertTrue(destination.is_symlink());self.assertTrue(target.is_dir())
 def test_unbounded_read_refused(self):
  with self.assertRaises(ValueError):fetcher.Bounded(io.BytesIO(b'keep')).read()
 def test_compressed_byte_bound(self):
  bounded=fetcher.Bounded(io.BytesIO(b'x'));bounded.total=fetcher.MAX_ARCHIVE_BYTES
  with self.assertRaises(ValueError):bounded.read(1)
if __name__=='__main__':unittest.main()
