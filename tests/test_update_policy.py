# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Release selection refuses partial, incompatible and ambiguous update plans."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services'))
from updates.policy import SCHEMA, eligibility, installed_identity, select_release, validate_catalog, validate_release


class UpdatePolicyTests(unittest.TestCase):
    def setUp(self):
        self.current = {'version': '0.2.12', 'build': 1, 'channel': 'preview', 'target': 'macos-arm64',
                        'installType': 'macos-app', 'dataSchema': 1, 'readableDataSchemas': [1],
                        'protocols': {'product': 'augmentor/1'}, 'updaterVersion': 1}
        self.release = {k: v for k, v in self.current.items() if k != 'updaterVersion'}
        self.release.update(build=3, sourceCommit='a' * 40, minimumOS='14.0',
                            releaseUrl='https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.12-macos-preview.3',
                            artifacts=[{'role': 'bundle', 'bytes': 100, 'sha256': 'b' * 64,
                                        'targetPath': 'releases/download/v0.2.12-macos-preview.3/app.dmg'}])

    def test_same_product_version_new_preview_build_is_an_update(self):
        self.assertIsNone(eligibility(self.current, self.release, 'preview', os_version='14.0'))
        old = {**self.release, 'build': 2}
        selected = select_release({'schema': SCHEMA, 'releases': [old, self.release]}, self.current, 'preview', os_version='26.0')
        self.assertEqual(selected['build'], 3)
        self.assertIsNotNone(eligibility({**self.current, 'build': 3}, self.release, 'preview'))
        self.assertIsNotNone(eligibility({**self.current, 'build': 0, 'buildKnown': False}, self.release, 'preview'))

    def test_target_channel_method_revocation_os_schema_and_protocol_constraints(self):
        for patch in ({'target': 'macos-x64'}, {'channel': 'stable'}, {'revoked': True}, {'minimumUpdater': 2},
                      {'protocols': {'product': 'augmentor/2'}}, {'dataSchema': 2, 'readableDataSchemas': [1, 2]}):
            with self.subTest(patch=patch):
                self.assertIsNotNone(eligibility(self.current, {**self.release, **patch}, 'preview'))
        self.assertIsNotNone(eligibility(self.current, self.release, 'preview', os_version='13.6'))
        self.assertIsNotNone(eligibility({**self.current, 'installType': 'development'}, self.release, 'preview'))

    def test_ambiguous_identity_unsafe_paths_invalid_fields_and_incomplete_debian_set(self):
        with self.assertRaises(ValueError):
            validate_catalog({'schema': SCHEMA, 'releases': [self.release, self.release]})
        for mutate in (lambda r: r.update(build=True), lambda r: r.update(version='0.2.12+metadata'),
                       lambda r: r.update(releaseUrl='https://evil.invalid/releases/tag/v1'),
                       lambda r: r.update(command='run-anything'),
                       lambda r: r['artifacts'][0].update(targetPath='releases/download/../app.dmg'),
                       lambda r: r['artifacts'][0].update(bytes=2**40),
                       lambda r: r.update(target='linux-x64', installType='debian')):
            value = deepcopy(self.release); mutate(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_release(value)

    def test_installed_receipt_and_development_identity_remain_distinct(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root / 'release').mkdir()
            product = {key: self.current[key] for key in ('version', 'channel', 'protocols', 'dataSchema', 'readableDataSchemas')}
            (root / 'release/product.json').write_text(json.dumps(product))
            source = installed_identity(root, target='macos-arm64')
            self.assertEqual(source['installType'], 'development')
            self.assertFalse(source['automaticInstallQualified'])
            (root / 'release.json').write_text(json.dumps({**product, 'target': 'macos-arm64',
                'sourceCommit': 'a'*40, 'update': {'build': 3, 'releaseId': 'fixture', 'automaticInstallQualified': True}}))
            installed = installed_identity(root, target='macos-arm64')
            self.assertEqual(installed['installType'], 'macos-app')
            self.assertEqual(installed['build'], 3)
            self.assertTrue(installed['automaticInstallQualified'])

    def test_linux_kernel_and_distribution_floors_are_separate(self):
        current={**self.current,'target':'linux-x64','installType':'managed-linux'}
        release={**self.release,'target':'linux-x64','installType':'managed-linux','minimumOS':'6.1',
                 'distributions':{'debian':'13','ubuntu':'24.04'}}
        self.assertIsNone(eligibility(current,release,'preview',os_version='6.12.75',distribution=('debian','13')))
        self.assertIsNone(eligibility(current,release,'preview',os_version='6.8',distribution=('ubuntu','24.04')))
        for operating_system,distribution in [('6.0',('debian','13')),('6.12',('debian','12')),('6.12',('fedora','43')),('6.12',None)]:
            with self.subTest(distribution=distribution):
                self.assertIsNotNone(eligibility(current,release,'preview',os_version=operating_system,distribution=distribution))


if __name__ == '__main__':
    unittest.main()
