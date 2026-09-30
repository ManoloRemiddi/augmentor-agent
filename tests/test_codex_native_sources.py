# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('codex_native_sources', Path(__file__).resolve().parents[1]/'scripts/collect-codex-native-sources.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def archive(path, entries):
    with tarfile.open(path, 'w:gz') as target:
        for name, content, link in entries:
            member = tarfile.TarInfo(name)
            if link is not None:
                member.type = tarfile.SYMTYPE
                member.linkname = link
                target.addfile(member)
            else:
                member.size = len(content)
                target.addfile(member, io.BytesIO(content))


class NativeSourceTests(unittest.TestCase):
    def test_nested_notices_and_contained_aliases_preserve_original_bytes_without_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = b'Original upstream copyright and notice\n'
            archive(root/'fixture.tar.gz', [('fixture/COPYING', b'', 'LICENSES/LGPL.txt'), ('fixture/LICENSES/LGPL.txt', content, None)])
            record = module.native_notices({'name': 'fixture', 'version': '1', 'file': 'fixture.tar.gz', 'root': 'fixture'}, root, root/'notices')
            self.assertEqual((root/'notices/fixture/fixture/LICENSES/LGPL.txt').read_bytes(), content)
            self.assertFalse((root/'notices/fixture/fixture/COPYING').exists())
            self.assertTrue(record['aliases'][0]['targetNoticeRetained'])
            self.assertFalse(record['releaseApproval'])

    def test_rootless_gitiles_sources_and_unresolved_aliases_are_recorded_separately(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive(root/'fixture.tar.gz', [('LICENSE.TXT', b'Original', None), ('COPYING', b'', 'other-text.txt')])
            record = module.native_notices({'name': 'fixture', 'version': '1', 'file': 'fixture.tar.gz', 'root': '.'}, root, root/'notices')
            self.assertEqual(len(record['files']), 1)
            self.assertFalse(record['aliases'][0]['targetNoticeRetained'])
            self.assertTrue(record['needsApplicabilityReview'])

    def test_escape_duplicate_and_wrong_source_roots_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = {'name': 'fixture', 'version': '1', 'file': 'fixture.tar.gz', 'root': 'fixture'}
            cases = [[('../LICENSE', b'x', None)], [('fixture/COPYING', b'', '../outside')],
                     [('fixture/COPYING', b'', '/outside')], [('fixture/LICENSE', b'x', None), ('fixture/LICENSE', b'y', None)],
                     [('different/LICENSE', b'x', None)]]
            for i, entries in enumerate(cases):
                archive(root/'fixture.tar.gz', entries)
                with self.subTest(entries=entries), self.assertRaises(ValueError):
                    module.native_notices(row, root, root/str(i))


if __name__ == '__main__':
    unittest.main()
