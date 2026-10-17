# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Source-export failures must not silently alter source or publish misleading inputs."""
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('office_source_inputs',
    ROOT / 'release/office-rebuild/collect-source-inputs.py')
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux Office source export diagnostic')
class OfficeSourceInputTests(unittest.TestCase):
    def test_literal_version_expansion_and_font_pin(self):
        pins = source.external_pins('FIX_VERSION := 3\nFIX_SHA256SUM := ' + 'a' * 64 +
            '\nFIX_TARBALL := authored-$(FIX_VERSION).tar.xz\n' +
            'FONT_SHA256SUM := ' + 'b' * 64 + '\nFONT_TTF := authored.ttf\n')
        self.assertEqual(set(pins), {'authored-3.tar.xz', 'authored.ttf'})
        self.assertEqual(pins['authored-3.tar.xz']['sha256'], 'a' * 64)

    def test_shell_expansions_and_cycles_are_never_evaluated(self):
        with tempfile.TemporaryDirectory() as directory:
            sentinel = Path(directory) / 'must-not-exist'
            with self.assertRaises(ValueError):
                source.expand('$(shell touch ' + str(sentinel) + ')', {})
            self.assertFalse(sentinel.exists())
        with self.assertRaises(ValueError):
            source.expand('$(A)', {'A': '$(B)', 'B': '$(A)'})

    def test_duplicate_constants_missing_hash_and_unsafe_names_refuse(self):
        with self.assertRaises(ValueError):
            source.constants('A := first\nA := second\n')
        with self.assertRaises(KeyError):
            source.external_pins('FIX_TARBALL := authored.tar.gz\n')
        for name in ['../outside', '/outside', '$(UNKNOWN)', '..', 'bad name']:
            with self.subTest(name=name), self.assertRaises((ValueError, KeyError)):
                source.external_pins('FIX_SHA256SUM := ' + 'a' * 64 + '\nFIX_TARBALL := ' + name)

    def test_changed_source_and_existing_destination_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original, target = root / 'source', root / 'target'
            original.write_bytes(b'original authored bytes')
            target.write_bytes(b'existing output')
            sha = hashlib.sha256(original.read_bytes()).hexdigest()
            with self.assertRaises(FileExistsError):
                source.copy_checked(original, target, sha)
            self.assertEqual(target.read_bytes(), b'existing output')
            with self.assertRaises(ValueError):
                source.copy_checked(original, root / 'unpublished', '0' * 64)
            self.assertFalse((root / 'unpublished').exists())
            self.assertEqual(original.read_bytes(), b'original authored bytes')

    def test_copy_is_independent_and_links_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original, target = root / 'source', root / 'output/source'
            original.write_bytes(b'authored source')
            sha = hashlib.sha256(original.read_bytes()).hexdigest()
            source.copy_checked(original, target, sha)
            original.write_bytes(b'changed afterwards')
            self.assertEqual(target.read_bytes(), b'authored source')
            link = root / 'link'
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                source.regular(root, 'link')
            with self.assertRaises(ValueError):
                source.copy_checked(link, root / 'unpublished', sha)

    def test_parent_link_and_path_escape_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'source').mkdir()
            (root / 'source/item').write_bytes(b'authored')
            (root / 'outside').write_bytes(b'outside authored source')
            (root / 'linked').symlink_to(root / 'source', target_is_directory=True)
            with self.assertRaises(ValueError):
                source.regular(root, 'linked/item')
            with self.assertRaises(ValueError):
                source.regular(root / 'source', '../outside')

    def test_existing_output_refuses_before_inspecting_a_producer(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'outputs') as directory:
            root = Path(directory)
            (root / 'keep').write_bytes(b'authored existing output')
            with self.assertRaisesRegex(ValueError, 'new direct child'):
                source.collect(Path('/unavailable-cache'), 'no-producer', root)
            self.assertEqual((root / 'keep').read_bytes(), b'authored existing output')

    def test_archived_snapshot_excludes_generated_and_uncommitted_files(self):
        import gzip
        import tarfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / 'repo'
            repo.mkdir()
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            tracked = repo / 'authored.txt'
            tracked.write_bytes(b'committed authored source')
            (repo / '.gitattributes').write_text('schema/* export-ignore\n')
            (repo / 'schema').mkdir()
            (repo / 'schema/needed.xsd').write_bytes(b'committed schema required by build')
            subprocess.run(['git', 'add', '.'], cwd=repo, check=True)
            subprocess.run(['git', '-c', 'user.name=Authored fixture', '-c',
                'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false',
                'commit', '-qm', 'Authored source only'], cwd=repo, check=True)
            tracked.write_bytes(b'uncommitted source change')
            (repo / 'generated.o').write_bytes(b'not preferred source')
            target = root / 'source.tar.gz'
            record = source.archive_commit(repo, target)
            self.assertEqual(record['sha256'], hashlib.sha256(target.read_bytes()).hexdigest())
            with gzip.open(target, 'rb') as stream, tarfile.open(fileobj=stream, mode='r|') as archive:
                entries = []
                for item in archive:
                    if item.isfile():
                        entries.append(item.name)
                        expected = {'.gitattributes': b'schema/* export-ignore\n',
                                    'authored.txt': b'committed authored source',
                                    'schema/needed.xsd': b'committed schema required by build'}
                        self.assertEqual(archive.extractfile(item).read(), expected[item.name])
            self.assertEqual(set(entries), {'.gitattributes', 'authored.txt', 'schema/needed.xsd'})
            self.assertEqual(tracked.read_bytes(), b'uncommitted source change')


if __name__ == '__main__':
    unittest.main()
