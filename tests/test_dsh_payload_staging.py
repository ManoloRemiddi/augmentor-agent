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


class DshPayloadStagingTests(unittest.TestCase):
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
