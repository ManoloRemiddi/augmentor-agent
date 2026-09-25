# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import hashlib
import importlib.util
import json
import re
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('macos_builder',Path(__file__).resolve().parents[1]/'scripts/package-macos.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)


class ApplicationInventoryTests(unittest.TestCase):
    def test_hashed_wheel_lock_matches_packaged_environment(self):
        root=Path(__file__).resolve().parents[1]
        normalize=lambda name:name.lower().replace('_','-').replace('.','-')
        expected={normalize(k):v for k,v in json.loads((root/'release/macos.json').read_text())['pythonPackages'].items()}
        locked={}
        for line in (root/'release/macos-requirements.txt').read_text().splitlines():
            if not line.strip() or line.startswith('#'):continue
            match=re.fullmatch(r'([A-Za-z0-9_.-]+)==([^ ]+) --hash=sha256:[a-f0-9]{64}',line)
            self.assertIsNotNone(match,line)
            name,version=match.groups()
            self.assertNotIn(normalize(name),locked)
            locked[normalize(name)]=version
        self.assertEqual(locked,expected)

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
