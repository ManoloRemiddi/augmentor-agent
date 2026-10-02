# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import hashlib
import importlib.util
import io
import json
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

    def test_explicit_inline_notice_is_retained_and_missing_or_changed_bytes_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);content=b'// Copyright fixture\n// Permission is hereby granted\npub fn example() {}\n'
            with tarfile.open(root/'inline.tar','w') as target:
                member=tarfile.TarInfo('fixture/src/lib.rs');member.size=len(content);target.addfile(member,io.BytesIO(content))
            row={'file':'inline.tar'};notice={'sha256':hashlib.sha256(content).hexdigest(),'form':'inline-license'}
            record=module.notices(row,root,root/'notices',{'src/lib.rs':notice})
            self.assertEqual((root/'notices/inline.tar/fixture/src/lib.rs').read_bytes(),content)
            self.assertEqual(record['files'][0]['form'],'inline-license')
            with self.assertRaisesRegex(ValueError,'checksum mismatch'):
                module.notices(row,root,root/'bad',{'src/lib.rs':{'sha256':'a'*64}})
            with self.assertRaisesRegex(ValueError,'missing'):
                module.notices(row,root,root/'missing',{'missing.rs':notice})

    def test_monorepo_path_is_inferred_only_from_a_unique_versioned_manifest(self):
        manifest=b'[package]\nname="fixture"\nversion="1.2.3"\nlicense="MIT"\n'
        published={'Cargo.toml':manifest,'.cargo_vcs_info.json':json.dumps({'git':{'sha1':'a'*40}}).encode(),'src/lib.rs':b'pub fn example() {}'}
        upstream={'nested/Cargo.toml':manifest,'nested/src/lib.rs':published['src/lib.rs']}
        package={'source':'crates/fixture-1.2.3.crate','pathInVcs':None,'candidateNotices':[]}
        repo={'repository':'https://github.com/example/fixture','commit':'a'*40}
        record=module.supplement_identity(package,repo,published,upstream)
        self.assertEqual(record['resolvedPackagePath'],'nested')
        self.assertTrue(record['publishedVcsCommitMatches']);self.assertTrue(record['upstreamPackageVersionMatches'])
        self.assertTrue(record['allPublishedRustFilesMatch']);self.assertFalse(record['releaseApproval'])
        upstream['ambiguous/Cargo.toml']=manifest
        record=module.supplement_identity(package,repo,published,upstream)
        self.assertIsNone(record['resolvedPackagePath']);self.assertFalse(record['allPublishedRustFilesMatch'])

    def test_generated_changed_and_wrong_version_sources_remain_unresolved(self):
        published={'Cargo.toml':b'[package]\nname="fixture"\nversion="1"\n','src/lib.rs':b'original','src/generated.rs':b'generated'}
        upstream={'Cargo.toml':b'[package]\nname="fixture"\nversion="2"\n','src/lib.rs':b'changed'}
        record=module.supplement_identity({'source':'fixture.crate','pathInVcs':'','candidateNotices':[]},
                                         {'repository':'https://github.com/example/fixture','commit':'a'*40},published,upstream)
        self.assertFalse(record['publishedVcsCommitMatches']);self.assertFalse(record['upstreamPackageVersionMatches'])
        self.assertFalse(record['allPublishedRustFilesMatch']);self.assertTrue(record['needsApplicabilityReview'])
        self.assertFalse(record['releaseApproval'])
        self.assertEqual(len(record['rustFiles']),2)

    def test_source_identity_reader_rejects_duplicate_and_uncontained_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for names in (['fixture/src/lib.rs','fixture/src/lib.rs'],['fixture/src/lib.rs','other/src/lib.rs'],['../lib.rs']):
                with tarfile.open(root/'bad.tar','w') as target:
                    for name in names:
                        member=tarfile.TarInfo(name);member.size=1;target.addfile(member,io.BytesIO(b'x'))
                with self.assertRaises(ValueError):module.source_files(root/'bad.tar')

    def test_workspace_metadata_uses_the_nearest_enclosing_workspace(self):
        files={'Cargo.toml':b'[workspace.package]\nversion="wrong"\nlicense="wrong"\n',
               'nested/Cargo.toml':b'[workspace.package]\nversion="1"\nlicense="MIT"\n',
               'nested/fixture/Cargo.toml':b'[package]\nname="fixture"\nversion.workspace=true\nlicense.workspace=true\n'}
        metadata,path=module.package_metadata(files,'nested/fixture/Cargo.toml')
        self.assertEqual(path,'nested/Cargo.toml');self.assertEqual(metadata['version'],'1');self.assertEqual(metadata['license'],'MIT')


if __name__=='__main__':unittest.main()
