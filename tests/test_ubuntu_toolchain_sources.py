# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Small refusal fixtures; real signed source acquisition is recorded separately."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('source_acquisition', Path(__file__).resolve().parents[1] / 'release/acquire-ubuntu-toolchain-sources.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def row(data=b'synthetic upstream source object'):
    return {'path': 'pool/main/s/synthetic/synthetic_1.orig.tar.xz', 'size': len(data),
        'sha256': hashlib.sha256(data).hexdigest(), 'urls': ['https://archive.ubuntu.com/ubuntu/synthetic']}


class SourceObjectTests(unittest.TestCase):
    def test_unsafe_paths_refused(self):
        for value in (None, 4, '../escape', '/pool/main/s/synthetic/a', 'pool/main/s/synthetic/../a',
                      'pool//main/s/synthetic/a', 'pool/main/s/synthetic/./a', 'pool/main/s/synthetic/a?secret'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.checked_path(value)

    def test_valid_download_and_cached_recheck_without_network(self):
        data = b'synthetic upstream source object'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(module.urllib.request, 'urlopen', return_value=io.BytesIO(data)):
                result = module.acquire(row(data), root)
            self.assertFalse(result['reused'])
            target = root / row()['path']
            self.assertEqual(target.read_bytes(), data)
            self.assertEqual(target.stat().st_mode & 0o777, 0o444)
            with patch.object(module.urllib.request, 'urlopen', side_effect=AssertionError('Unexpected network')):
                self.assertTrue(module.acquire(row(data), root)['reused'])

    def test_corrupt_cached_object_refused_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); target = root / row()['path']
            target.parent.mkdir(parents=True); target.write_bytes(b'corrupt')
            with patch.object(module.urllib.request, 'urlopen', side_effect=AssertionError('Unexpected network')):
                with self.assertRaisesRegex(ValueError, 'Existing source object differs'):
                    module.acquire(row(), root)
            self.assertEqual(target.read_bytes(), b'corrupt')

    def test_symlink_directory_refused_before_download(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); outside = root / 'outside'; outside.mkdir()
            (root / 'pool').symlink_to(outside, target_is_directory=True)
            with patch.object(module.urllib.request, 'urlopen', side_effect=AssertionError('Unexpected network')):
                with self.assertRaisesRegex(ValueError, 'symlink refused'):
                    module.acquire(row(), root)
            self.assertEqual(list(outside.iterdir()), [])

    def test_bad_hash_and_oversize_downloads_preserve_partials(self):
        for data in (b'x' * row()['size'], b'x' * (row()['size'] + 1)):
            with self.subTest(data=len(data)), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with patch.object(module.urllib.request, 'urlopen', return_value=io.BytesIO(data)):
                    with self.assertRaisesRegex(RuntimeError, 'All approved URLs refused'):
                        module.acquire(row(), root)
                self.assertFalse((root / row()['path']).exists())
                self.assertEqual(len(list(root.rglob('*.partial'))), 1)

    def test_download_race_does_not_overwrite_destination(self):
        data = b'synthetic upstream source object'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); target = root / row()['path']
            def publish_other(*args):
                target.write_bytes(b'concurrent candidate')
                raise FileExistsError()
            with patch.object(module.urllib.request, 'urlopen', return_value=io.BytesIO(data)), patch.object(module.os, 'link', side_effect=publish_other):
                with self.assertRaises(RuntimeError):
                    module.acquire(row(), root)
            self.assertEqual(target.read_bytes(), b'concurrent candidate')
            self.assertEqual(len(list(root.rglob('*.partial'))), 1)

    def test_duplicate_checksum_rows_refused(self):
        line = row()['sha256'] + ' 32 synthetic_1.orig.tar.xz'
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            module.checksum_rows({'Directory': 'pool/main/s/synthetic', 'Checksums-Sha256': line + '\n' + line})

    def test_source_control_identity_and_checksum_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); dsc = root / 'pool/main/s/synthetic/synthetic_1.dsc'
            dsc.parent.mkdir(parents=True)
            source = {'Directory': 'pool/main/s/synthetic', 'Checksums-Sha256':
                '0' * 64 + ' 1 synthetic_1.dsc\n' + '1' * 64 + ' 2 synthetic_1.orig.tar.xz'}
            for text, message in (
                ('Source: other\nVersion: 1\nChecksums-Sha256:\n ' + '1' * 64 + ' 2 synthetic_1.orig.tar.xz\n', 'identity differs'),
                ('Source: synthetic\nVersion: 1\nChecksums-Sha256:\n ' + '2' * 64 + ' 2 synthetic_1.orig.tar.xz\n', 'checksum inventory differs')):
                dsc.write_text(text)
                with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                    module.dsc_crosscheck({('synthetic', '1'): source}, root)


if __name__ == '__main__':
    unittest.main()
