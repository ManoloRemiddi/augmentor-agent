# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('stage_dsh', ROOT/'scripts/stage-dsh.py')
stager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stager)
patch_spec = importlib.util.spec_from_file_location('windows_dsh_preparation', ROOT/'scripts/prepare-windows-dsh.py')
preparation = importlib.util.module_from_spec(patch_spec); patch_spec.loader.exec_module(preparation)


class DshPayloadStagingTests(unittest.TestCase):
    def test_windows_dependency_drift_leaves_every_source_untouched(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            first = target/'first.js'; first.write_bytes(b'original')
            second = target/'second.js'; second.write_bytes(b'changed upstream')
            patches = [dict(path='first.js', sha256=hashlib.sha256(b'original').hexdigest(), old='original', new='fixed'),
                       dict(path='second.js', sha256='0'*64, old='old', new='new')]
            with patch.object(preparation, 'PATCHES', patches):
                with self.assertRaisesRegex(ValueError, 'changed Windows terminal source'):
                    preparation.prepare(target, platform='win32')
            self.assertEqual(first.read_bytes(), b'original')
            self.assertEqual(second.read_bytes(), b'changed upstream')
            self.assertEqual(preparation.prepare(target, platform='darwin'), [])

    def test_changed_preparation_never_executes(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            script = target/stager.PREPARE_SCRIPT
            script.parent.mkdir(parents=True)
            script.write_text('process.exit(0)')
            with patch.object(stager.subprocess, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'preparation changed'):
                    stager.prepare(target, 'node')
                run.assert_not_called()

    def fixture(self, root, installed='0.1.5-rc.1', locked='0.1.5-rc.1'):
        path = root/'node_modules/@deepseek-ai/dsh'
        path.mkdir(parents=True)
        (path/'package.json').write_text(json.dumps({'name':'@deepseek-ai/dsh', 'version':installed}))
        (root/'package-lock.json').write_text(json.dumps({'packages':{
            'node_modules/@deepseek-ai/dsh':{'version':locked, 'integrity':'fixture'}}}))

    def test_dependency_drift_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.fixture(target, installed='0.1.5-rc.2')
            with self.assertRaisesRegex(ValueError, 'differs from production lock'):
                stager.inventory(target)

    def test_mixed_suite_is_refused_even_if_lock_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.fixture(target, installed='0.1.5-rc.2', locked='0.1.5-rc.2')
            with self.assertRaisesRegex(ValueError, 'Mixed DSH suite'):
                stager.inventory(target)


if __name__ == '__main__':
    unittest.main()
