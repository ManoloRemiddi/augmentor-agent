# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('nested_notices', Path(__file__).parents[1] / 'scripts/third-party-notices.py')
notices = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notices)


class NestedPackageNotices(unittest.TestCase):
    def fixture(self, root):
        tree = root / 'tree'
        package = tree / 'node_modules/authored-fixture'
        catalog = root / 'catalog'
        (package / 'licenses').mkdir(parents=True)
        catalog.mkdir()
        meta = {'name': 'authored-fixture', 'version': '1.0.0', 'license': 'MPL-2.0'}
        (package / 'package.json').write_text(json.dumps(meta))
        (tree / 'package.json').write_text('{}')
        (tree / 'package-lock.json').write_text(json.dumps({'packages': {'node_modules/authored-fixture': meta}}))
        texts = {'licenses/LICENSE': b'Independent synthetic licence fixture.', 'licenses/NOTICE': b'Independent synthetic notice fixture.'}
        for name, content in texts.items():
            (package / name).write_bytes(content)
        reviewed = {'sources': {}, 'overrides': {}, 'additionalLicenses': {'authored-fixture@1.0.0': 'MPL-2.0'},
                    'nestedPackageTexts': {'authored-fixture@1.0.0': {name: {'role': 'license' if name.endswith('LICENSE') else 'notice', 'sha256': hashlib.sha256(content).hexdigest()} for name, content in texts.items()}}}
        return tree, package, catalog, reviewed, texts

    def test_exact_version_review_collects_nested_text_without_globally_permitting_mpl(self):
        with tempfile.TemporaryDirectory() as directory:
            tree, package, catalog, reviewed, texts = self.fixture(Path(directory))
            (catalog / 'catalog.json').write_text(json.dumps(reviewed))
            report, collected = notices.inventory(tree, catalog)
            self.assertEqual(report['components'][0]['license'], 'MPL-2.0')
            self.assertEqual({row['path'] for row in report['components'][0]['notices']}, {'node_modules/authored-fixture/' + name for name in texts})
            self.assertEqual(set(collected.values()), set(texts.values()))
            reviewed['additionalLicenses'] = {}
            (catalog / 'catalog.json').write_text(json.dumps(reviewed))
            with self.assertRaisesRegex(ValueError, 'unreviewed license MPL-2.0'):
                notices.inventory(tree, catalog)

    def test_changed_nested_body_is_rejected_even_at_same_version(self):
        with tempfile.TemporaryDirectory() as directory:
            tree, package, catalog, reviewed, texts = self.fixture(Path(directory))
            (catalog / 'catalog.json').write_text(json.dumps(reviewed))
            (package / 'licenses/NOTICE').write_bytes(b'Changed independent fixture body.')
            with self.assertRaisesRegex(ValueError, 'changed reviewed nested text'):
                notices.inventory(tree, catalog)

    def test_outside_paths_and_links_do_not_expand_notice_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            tree, package, catalog, reviewed, texts = self.fixture(Path(directory))
            outside = Path(directory) / 'outside'
            outside.write_bytes(b'Independent outside fixture.')
            for name in ['../outside', str(outside)]:
                reviewed['nestedPackageTexts']['authored-fixture@1.0.0'][name] = {'role': 'notice', 'sha256': hashlib.sha256(outside.read_bytes()).hexdigest()}
            (package / 'licenses/NOTICE').unlink()
            (package / 'licenses/NOTICE').symlink_to(outside)
            (catalog / 'catalog.json').write_text(json.dumps(reviewed))
            with self.assertRaisesRegex(ValueError, 'changed reviewed nested text'):
                notices.inventory(tree, catalog)


if __name__ == '__main__':
    unittest.main()
