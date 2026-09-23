# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('macos_builder',Path(__file__).resolve().parents[1]/'scripts/package-macos.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)


class ApplicationInventoryTests(unittest.TestCase):
    def test_inventory_tracks_content_and_records_links_without_reading_targets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'apps').mkdir();(root/'python').mkdir()
            source=root/'apps/code.py';source.write_text('first')
            (root/'python/private-runtime-file').write_text('excluded')
            (root/'apps/runtime-link').symlink_to('../python',target_is_directory=True)
            first=builder.application_inventory(root)['files']
            self.assertEqual(first['apps/code.py']['sha256'],hashlib.sha256(b'first').hexdigest())
            self.assertEqual(first['apps/runtime-link'],{'symlink':'../python'})
            self.assertEqual(set(first),{'apps/code.py','apps/runtime-link'})
            source.write_text('second')
            self.assertNotEqual(first,builder.application_inventory(root)['files'])


if __name__=='__main__':unittest.main()
