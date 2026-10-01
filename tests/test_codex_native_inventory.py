# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('codex_inventory',Path(__file__).resolve().parents[1]/'scripts/verify-codex-native.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class CodexInventoryTests(unittest.TestCase):
    def test_matching_payload_is_not_release_clearance_and_all_native_changes_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'package.json').write_text(json.dumps({'name':'@openai/codex','version':'fixture'}))
            data=b'\x7fELFfixture';binary=root/'codex';binary.write_bytes(data)
            record={'version':'fixture','files':[{'path':'codex','sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}]}
            self.assertFalse(module.verify(root,record)['releaseApproval'])
            extra=root/'extra';extra.write_bytes(b'\x00asmfixture')
            with self.assertRaisesRegex(ValueError,'Unreviewed'):module.verify(root,record)
            extra.unlink();binary.write_bytes(data+b'changed')
            with self.assertRaisesRegex(ValueError,'differs'):module.verify(root,record)
            binary.unlink()
            with self.assertRaisesRegex(ValueError,'missing'):module.verify(root,record)
            binary.symlink_to('/dev/null')
            with self.assertRaisesRegex(ValueError,'symlink'):module.verify(root,record)


if __name__=='__main__':unittest.main()
