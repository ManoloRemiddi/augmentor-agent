# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('codex_sources',Path(__file__).resolve().parents[1]/'scripts/collect-codex-sources.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class CodexSourceTests(unittest.TestCase):
    def test_lockfile_pins_registry_archives_and_git_commits_without_resolution(self):
        with tempfile.TemporaryDirectory() as directory:
            lock=Path(directory)/'Cargo.lock'
            lock.write_text('''version = 4
[[package]]
name = "fixture"
version = "1.2.3"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "'''+('a'*64)+'''"
[[package]]
name = "fork"
version = "0.1.0"
source = "git+https://github.com/example/fork.git?rev='''+('b'*40)+'#'+('b'*40)+'''"
''')
            rows=module.inputs(lock)
            self.assertEqual(rows[0]['sha256'],'a'*64)
            self.assertEqual(rows[1]['url'],'https://codeload.github.com/example/fork/tar.gz/'+'b'*40)
            lock.write_text(lock.read_text().replace('crates.io-index','different-index'))
            with self.assertRaisesRegex(ValueError,'registry'):module.inputs(lock)

    def test_notices_keep_attribution_and_cached_sources_must_match_the_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);archive=root/'fixture.crate'
            with tarfile.open(archive,'w:gz') as target:
                for name,content in [('fixture-1/LICENSE','Copyright fixture'),('fixture-1/Cargo.toml','[package]\nname="fixture"\nversion="1"\nlicense="MIT"\n'),('fixture-1/LICENSES/MIT.txt','Nested license attribution'),('fixture-1/src/main.rs','unneeded code')]:
                    content=content.encode();member=tarfile.TarInfo(name);member.size=len(content);target.addfile(member,io.BytesIO(content))
            row={'file':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
            self.assertEqual(module.fetch(row,root)['sha256'],row['sha256'])
            record=module.notices(row,root,root/'notices')
            self.assertEqual(record['license'],'MIT');self.assertFalse(record['needsNoticeReview'])
            self.assertEqual(len(record['files']),3)
            archive.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'checksum mismatch'):module.fetch(row,root)

    def test_archive_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with tarfile.open(root/'bad.tar','w') as target:
                member=tarfile.TarInfo('../LICENSE');member.size=1;target.addfile(member,io.BytesIO(b'x'))
            with self.assertRaisesRegex(ValueError,'Unsafe'):module.notices({'file':'bad.tar'},root,root/'notices')
            self.assertFalse((root/'LICENSE').exists())


if __name__=='__main__':unittest.main()
