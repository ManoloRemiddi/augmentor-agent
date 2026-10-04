# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'services'))
from platform_adapters.paths import link_directory, private_directory


class DependencyLinkTests(unittest.TestCase):
    def test_repeatable_link_and_cleanup_preserve_dependency(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = private_directory(Path(temporary)/'private')
            target = private_directory(root/'package café')
            (target/'module.js').write_text('export default 42;', encoding='utf-8')
            parent = private_directory(root/'profile')
            link = parent/'node_modules'
            link_directory(link, target)
            link_directory(link, target)
            self.assertEqual((link/'module.js').read_text(), 'export default 42;')
            shutil.rmtree(parent)
            self.assertEqual((target/'module.js').read_text(), 'export default 42;')

    def test_conflicting_link_is_not_repointed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = private_directory(Path(temporary)/'private')
            first = private_directory(root/'one'); second = private_directory(root/'two')
            link = root/'dependency'
            link_directory(link, first)
            with self.assertRaisesRegex(ValueError, 'preserved'):
                link_directory(link, second)
            self.assertEqual(link.resolve(), first.resolve())


if __name__ == '__main__':
    unittest.main()
