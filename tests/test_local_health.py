# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Shared offline health renders the real UI without starting a conversation."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from augmentor_linux.local_health import render_preview


class LocalHealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication(['local-health-test'])

    def test_real_render_never_starts_controller_or_process_or_writes_preferences(self):
        if sys.platform == 'win32':
            self.assertEqual(self.app.platformName(),'windows',
                'Windows font health must run with the native QPA font backend.')
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            saved=root/'appearance.json';saved.write_text('{"ui_scale":140,"harness":"pi"}')
            original=saved.read_bytes()
            with patch.dict(os.environ,{'AUGMENTOR_PI_CONFIG':str(root)}), \
                    patch('augmentor_linux.window.Controller',side_effect=AssertionError('No conversation during health.')), \
                    patch('subprocess.Popen',side_effect=AssertionError('No service during health.')):
                result=render_preview(platform=self.app.platformName())
            self.assertTrue(result['rendered']);self.assertTrue(result['fontCoverage'])
            self.assertGreater(result['width'],0);self.assertGreater(result['height'],0)
            self.assertEqual(saved.read_bytes(),original)
            self.assertEqual(list(root.iterdir()),[saved])

    def test_wrong_platform_does_not_report_success(self):
        with self.assertRaisesRegex(RuntimeError,'native Qt'):
            render_preview(platform='unavailable-health-platform')


if __name__=='__main__':unittest.main()
