# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Finite synthetic source/utility evidence; no builds, package or daemon actions."""
import hashlib,importlib.util,io,json,tarfile,tempfile,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
def module(name):
 p=ROOT/'release'/name;s=importlib.util.spec_from_file_location(name.replace('-','_'),p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
build=module('probe-recipient-core-bindings-build.py');notices=module('collect-source-qt-notices.py')
class NoticeTexts(unittest.TestCase):
 def fixture(self,root,extra=()):
  archives=root/'archives';archives.mkdir();rows=[]
  for i in range(7):
   path=archives/('source'+str(i)+'.tar.xz')
   with tarfile.open(path,'w:xz') as tar:
    data=[('source/LICENSE',b'old notice'),('source/LICENSES/LGPL-3.0-only.txt',b'lgpl text'),('source/LICENSES/Qt-GPL-exception-1.0.txt',b'exception text'),('source/notes/readme.txt',b'unrelated')]+list(extra if i==0 else ())
    for name,raw in data:
     m=tarfile.TarInfo(name)
     if raw is None:m.type=tarfile.SYMTYPE;m.linkname='../LICENSE'
     else:m.size=len(raw)
     tar.addfile(m,None if raw is None else io.BytesIO(raw))
   rows.append({'name':'module'+str(i),'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
  policy=root/'policy.json';policy.write_text(json.dumps({'format':'augmentor-linux-source-runtime-acquisition/1','sources':rows}));return policy,archives
 def test_spdx_license_and_exception_included_exactly(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);p,a=self.fixture(root);d=notices.collect(p,a,root/'out')
   self.assertEqual(len(d['files']),21);self.assertEqual(d['skippedCandidates'],[])
   for row in d['files']:
    self.assertEqual(hashlib.sha256((root/'out'/row['outputPath']).read_bytes()).hexdigest(),row['sha256'])
   self.assertFalse(any('readme.txt' in row['archivePath'] for row in d['files']));self.assertFalse(d['licenseReviewComplete'])
 def test_unsafe_nonregular_and_oversized_texts_stay_skipped(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);p,a=self.fixture(root,[('source/../LICENSES/MIT.txt',b'unsafe'),('source/LICENSES/link.txt',None),('source/LICENSES/huge.txt',b'x'*(2*1024**2+1))]);d=notices.collect(p,a,root/'out')
   self.assertEqual(len(d['files']),21);self.assertEqual(len(d['skippedCandidates']),3)
 def test_duplicate_text_refuses(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);p,a=self.fixture(root,[('source/LICENSES/LGPL-3.0-only.txt',b'duplicate')])
   with self.assertRaises(RuntimeError):notices.collect(p,a,root/'out')
 def test_changed_archive_refuses_before_output(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);p,a=self.fixture(root);next(a.iterdir()).write_bytes(b'changed')
   with self.assertRaises(RuntimeError):notices.collect(p,a,root/'out')
   self.assertFalse((root/'out').exists())
 def test_collector_pin_updated_without_historical_manifest_adoption(self):
  with self.assertRaisesRegex(ValueError,'Changed pinned input'):
   build.checked(ROOT/'release','collect-source-qt-notices.py','38b58e8c29b658fa3b5fec8f8b177fc5027436531e4db44cb3fd7ca8f88cde1f')
  self.assertEqual(build.checked(ROOT/'release','collect-source-qt-notices.py',build.TOOLS['collect-source-qt-notices.py']),ROOT/'release/collect-source-qt-notices.py')
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'kit-manifest.json').write_text('unreviewed manifest')
   with self.assertRaisesRegex(ValueError,'Changed pinned input'):
    build.authenticate_kit(root)
class CompilerEvidence(unittest.TestCase):
 def fixture(self,root,utility=True):
  directory=root/'sources/pyside-setup-everywhere-src-6.8.2/build/normal/build/pyside-tools' if utility else root/'native';directory.mkdir(parents=True)
  source=root/'sources/pyside-setup-everywhere-src-6.8.2/sources/pyside-tools';source.mkdir(parents=True)
  for n in ('CMakeLists.txt','cmake/PySideToolsSetup.cmake','cmake/PySideToolsHelpers.cmake'):
   p=source/n;p.parent.mkdir(exist_ok=True);p.write_text('synthetic source')
  cache=directory/'CMakeCache.txt';cache.write_text('CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON\nCMAKE_GENERATOR:INTERNAL=Ninja\n'+('CMAKE_PROJECT_NAME:STATIC=pyside-tools\nCMAKE_HOME_DIRECTORY:INTERNAL='+str(source)+'\n' if utility else ''))
  (directory/'build.ninja').write_text('build all: phony\nbuild install: CUSTOM_COMMAND all\n');(directory/'CMakeFiles').mkdir();(directory/'CMakeFiles/rules.ninja').write_text('rule CUSTOM_COMMAND\n  command = cmake install\nrule RERUN_CMAKE\n  command = cmake\n');(directory/'.ninja_log').write_text('log');(directory/'install_manifest.txt').write_text('installed');(directory/'cmake_install.cmake').write_text('install')
  return cache,source
 def admit_synthetic_source(self,source):
  original=build.checked
  def checked(root,name,expected=None):
   # Tests inject only source-byte authentication; production still checks the
   # exact three retained upstream hashes. All cache/rule/log checks are real.
   return original(root,name,None if root==source else expected)
  return mock.patch.object(build,'checked',side_effect=checked)
 def test_install_only_zero_tus_with_explicit_absent_deps(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);p,s=self.fixture(root)
   with self.admit_synthetic_source(s):row=build.cache_verified(p,root)
   self.assertEqual(row['translationUnits'],0);self.assertIsNone(row['compileCommandsSha256']);self.assertEqual(row['evidenceKind'],'install-only-pyside-tools')
   before=build.retained_ninja_inputs(p.parent,True);self.assertIsNone(before['.ninja_deps']);self.assertEqual(before,build.retained_ninja_inputs(p.parent,True))
   (p.parent/'.ninja_log').write_text('changed');self.assertNotEqual(before,build.retained_ninja_inputs(p.parent,True))
 def test_wrong_source_bytes_refuse(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);p,_=self.fixture(root)
   with self.assertRaises(ValueError):build.cache_verified(p,root)
 def test_utility_native_rules_or_edges_refuse(self):
  for where,text in [('build.ninja','build x.o: CXX_COMPILER x.cpp\n'),('build.ninja','build x.so: CXX_SHARED_LIBRARY_LINKER x.o\n'),('CMakeFiles/rules.ninja','rule C_COMPILER\n command = cc\n'),('CMakeFiles/rules.ninja','rule UNREVIEWED\n command = tool\n')]:
   with self.subTest(where=where,text=text),tempfile.TemporaryDirectory() as folder:
    root=Path(folder);p,s=self.fixture(root);f=p.parent/where;f.write_text(f.read_text()+text)
    with self.admit_synthetic_source(s),self.assertRaises(ValueError):build.cache_verified(p,root)
 def test_wrong_root_source_identity_and_unexpected_evidence_refuse(self):
  for change in ('root','home','db','deps','db-symlink','deps-symlink'):
   with self.subTest(change=change),tempfile.TemporaryDirectory() as folder:
    root=Path(folder);p,s=self.fixture(root)
    if change=='home':p.write_text(p.read_text().replace(str(s),'/foreign/source'))
    if change=='db':(p.parent/'compile_commands.json').write_text('[]')
    if change=='deps':(p.parent/'.ninja_deps').write_bytes(b'unexpected')
    if change=='db-symlink':(p.parent/'compile_commands.json').symlink_to('missing')
    if change=='deps-symlink':(p.parent/'.ninja_deps').symlink_to('missing')
    with self.admit_synthetic_source(s),self.assertRaises(ValueError):build.cache_verified(p,root/'foreign' if change=='root' else root)
 def test_ordinary_missing_empty_and_malformed_db_refuse(self):
  for content in (None,'[]','[{}]'):
   with self.subTest(content=content),tempfile.TemporaryDirectory() as folder:
    root=Path(folder);p,_=self.fixture(root,False)
    if content is not None:(p.parent/'compile_commands.json').write_text(content)
    with self.assertRaises((FileNotFoundError,ValueError)):build.cache_verified(p,root)
 def test_ordinary_db_and_deps_remain_required(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);p,_=self.fixture(root,False);(p.parent/'compile_commands.json').write_text('[{"directory":"/build","file":"x.cpp","command":"c++ x.cpp"}]')
   self.assertEqual(build.cache_verified(p,root)['translationUnits'],1)
   with self.assertRaises(FileNotFoundError):build.retained_ninja_inputs(p.parent)
   (p.parent/'.ninja_deps').write_bytes(b'deps');self.assertIsNotNone(build.retained_ninja_inputs(p.parent)['.ninja_deps'])
 def test_only_utility_deps_can_be_absent(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);p,_=self.fixture(root);(p.parent/'.ninja_log').unlink()
   with self.assertRaises(FileNotFoundError):build.retained_ninja_inputs(p.parent,True)
if __name__=='__main__':unittest.main()
