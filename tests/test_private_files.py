# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'services'))
from platform_adapters.paths import private_directory
from platform_adapters.private_files import atomic_json, descriptor, read_json


class PrivateFilesTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = private_directory(Path(temporary.name)/'owned')

    def test_private_unicode_record_can_be_replaced_and_read(self):
        path = self.root/'credentials.json'
        atomic_json(path, {'fixture': '秘密 è 🪟'})
        self.assertEqual(read_json(path), {'fixture': '秘密 è 🪟'})
        atomic_json(path, {'updated': True})
        self.assertEqual(read_json(path), {'updated': True})
        self.assertEqual(list(self.root.iterdir()), [path])

    def test_hard_link_is_refused_without_replacing_or_reading_target(self):
        path = self.root/'credentials.json'; alias = self.root/'alias.json'
        atomic_json(path, {'fixture': 'retained'}); os.link(path, alias)
        with self.assertRaises((OSError, ValueError)): read_json(alias)
        with self.assertRaises((OSError, ValueError)): atomic_json(alias, {'changed': True})
        self.assertIn('retained', path.read_text())
        self.assertEqual(set(self.root.iterdir()), {path, alias})

    def test_failed_serialization_leaves_existing_record_and_no_temp_file(self):
        path = self.root/'credentials.json'; atomic_json(path, {'retained': True})
        with self.assertRaises(TypeError): atomic_json(path, {'invalid': object()})
        self.assertEqual(read_json(path), {'retained': True})
        self.assertEqual(list(self.root.iterdir()), [path])

    def test_reading_missing_record_does_not_create_it(self):
        path = self.root/'missing.json'
        with self.assertRaises(OSError): read_json(path)
        self.assertFalse(path.exists())

    def test_exclusive_creation_preserves_existing_content(self):
        path = self.root/'credentials.json'; atomic_json(path, {'retained': True})
        with self.assertRaises(OSError): descriptor(path, writable=True, exclusive=True)
        self.assertEqual(read_json(path), {'retained': True})


if __name__ == '__main__': unittest.main()
