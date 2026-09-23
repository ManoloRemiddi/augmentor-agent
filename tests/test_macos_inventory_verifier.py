# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec=importlib.util.spec_from_file_location('inventory_verifier',Path(__file__).resolve().parents[1]/'scripts/verify-macos-application-inventory.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class InventoryVerifierTests(unittest.TestCase):
    def fixture(self,root,content=b'original',name='apps/code.py'):
        data=json.dumps({'schema':'augmentor-application-inventory/1','files':{
            name:{'sha256':hashlib.sha256(b'original').hexdigest(),'bytes':8}}}).encode()
        path=root/'candidate.zip';prefix='Augmentor Agent Browser Companion.app/Contents/Resources/app/'
        with zipfile.ZipFile(path,'w') as archive:
            archive.writestr(prefix+'application-inventory.json',data)
            archive.writestr(prefix+name,content)
        report={'component':'companion','version':'fixture','artifact':path.name,
                'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,
                'applicationInventorySha256':hashlib.sha256(data).hexdigest()}
        (root/'artifacts.json').write_text(json.dumps(report))

    def test_valid_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);self.fixture(root)
            self.assertEqual(module.verify(root)['verifiedEntries'],1)

    def test_changed_file_fails_even_with_updated_archive_checksum(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);self.fixture(root,b'modified')
            with self.assertRaisesRegex(ValueError,'content mismatch'):module.verify(root)

    def test_parent_path_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);self.fixture(root,name='../outside')
            with self.assertRaisesRegex(ValueError,'Invalid inventory path'):module.verify(root)


if __name__=='__main__':unittest.main()
