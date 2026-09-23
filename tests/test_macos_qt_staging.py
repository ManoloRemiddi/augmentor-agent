# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('qt_staging',Path(__file__).resolve().parents[1]/'scripts/stage-macos-qt.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class QtStagingTest(unittest.TestCase):
    def test_unexpected_dependency_refuses_before_removal(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);file=root/'optional.dylib';file.write_bytes(b'fixture')
            policy={'reason':'fixture','plugins':[{'path':file.name,'missingQtFrameworks':['expected']}]}
            with patch.object(module,'missing_frameworks',return_value=['different']):
                with self.assertRaises(ValueError):module.stage(root,policy)
            self.assertTrue(file.exists())

    def test_exact_policy_preserves_other_plugins_and_records_removal(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bad=root/'optional.dylib';good=root/'cocoa.dylib'
            bad.write_bytes(b'optional');good.write_bytes(b'required')
            policy={'reason':'fixture','plugins':[{'path':bad.name,'missingQtFrameworks':['absent']}]}
            with patch.object(module,'missing_frameworks',side_effect=lambda root,file:['absent'] if file==bad else []):
                report=module.stage(root,policy)
            self.assertFalse(bad.exists());self.assertEqual(good.read_bytes(),b'required')
            self.assertEqual(report['removed'][0]['path'],bad.name)
            self.assertEqual(len(report['removed'][0]['sha256']),64)

if __name__=='__main__':unittest.main()
