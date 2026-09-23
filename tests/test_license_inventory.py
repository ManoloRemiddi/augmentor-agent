# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/third-party-notices.py'
spec = importlib.util.spec_from_file_location('license_inventory', SCRIPT)
licensing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(licensing)


class LicenseInventoryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.package = self.root / 'node_modules/example'
        self.package.mkdir(parents=True)
        self.catalog = self.root / 'licenses'; self.catalog.mkdir()
        self.meta = {'name': 'example', 'version': '1.0.0', 'license': 'MIT'}
        self.write()
        (self.package / 'LICENSE').write_text('Fixture license text')
        (self.catalog / 'catalog.json').write_text('{"sources": {}, "overrides": {}}')

    def write(self):
        (self.package / 'package.json').write_text(json.dumps(self.meta))
        (self.root / 'package-lock.json').write_text(json.dumps({'packages': {'node_modules/example': self.meta}}))

    def test_preserves_notice_bytes_and_rejects_installed_version_drift(self):
        content = b'Copyright notice with non-ASCII: \xc2\xa9\n'
        (self.package / 'NOTICE').write_bytes(content)
        report, texts = licensing.inventory(self.root, self.catalog)
        self.assertEqual(report['components'][0]['name'], 'example')
        self.assertIn(content, texts.values())
        (self.package / 'package.json').write_text(json.dumps({**self.meta, 'version': '2.0.0'}))
        with self.assertRaisesRegex(ValueError, 'differs from lock'):
            licensing.inventory(self.root, self.catalog)

    def test_unknown_and_development_packages_cannot_hide_in_distribution(self):
        nested = self.package / 'node_modules/surprise'; nested.mkdir(parents=True)
        (nested / 'package.json').write_text(json.dumps(self.meta))
        with self.assertRaisesRegex(ValueError, 'not in the lock'):
            licensing.inventory(self.root, self.catalog)
        (nested / 'package.json').unlink()
        self.meta['dev'] = True; self.write()
        with self.assertRaisesRegex(ValueError, 'development package'):
            licensing.inventory(self.root, self.catalog)

    def test_missing_text_or_unreviewed_license_blocks_packaging(self):
        (self.package / 'LICENSE').unlink()
        with self.assertRaisesRegex(ValueError, 'missing reviewed license'):
            licensing.inventory(self.root, self.catalog)
        self.meta['license'] = 'GPL-3.0-only'; self.write()
        with self.assertRaisesRegex(ValueError, 'unreviewed license'):
            licensing.inventory(self.root, self.catalog)

    def test_license_choice_retains_notice_and_requires_exact_expression_and_version(self):
        self.meta['license'] = '(AFL-2.1 OR BSD-3-Clause)'; self.write()
        catalog = {'sources': {}, 'overrides': {}, 'choices': {
            'example@1.0.0': {'expression': self.meta['license'], 'selected': 'BSD-3-Clause'}}}
        (self.catalog / 'catalog.json').write_text(json.dumps(catalog))
        report, texts = licensing.inventory(self.root, self.catalog)
        self.assertEqual(report['components'][0]['license'], 'BSD-3-Clause')
        self.assertEqual(report['components'][0]['declaredLicense'], self.meta['license'])
        self.assertIn(b'Fixture license text', texts.values())
        self.meta['license'] = 'AFL-2.1'; self.write()
        with self.assertRaisesRegex(ValueError, 'unreviewed license'):
            licensing.inventory(self.root, self.catalog)
        self.meta.update(license='(AFL-2.1 OR BSD-3-Clause)', version='2.0.0'); self.write()
        with self.assertRaisesRegex(ValueError, 'unreviewed license'):
            licensing.inventory(self.root, self.catalog)

    def test_reviewed_fallback_is_bound_to_version_and_content_hash(self):
        (self.package / 'LICENSE').unlink()
        content = b'Reviewed fixture license\n'
        (self.catalog / 'reviewed.txt').write_bytes(content)
        catalog = {'sources': {'fixture': {'file': 'reviewed.txt', 'url': 'https://example.invalid/pinned-license',
                                          'sha256': hashlib.sha256(content).hexdigest()}},
                   'overrides': {'example@1.0.0': 'fixture'}}
        (self.catalog / 'catalog.json').write_text(json.dumps(catalog))
        report, _ = licensing.inventory(self.root, self.catalog)
        self.assertEqual(len(report['components']), 1)
        (self.catalog / 'reviewed.txt').write_text('Changed after review')
        with self.assertRaisesRegex(ValueError, 'hash changed'):
            licensing.inventory(self.root, self.catalog)


if __name__ == '__main__':
    unittest.main()
