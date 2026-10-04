# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from augmentor_linux import managed_setup
from augmentor_linux.adapters import dsh


class WindowsManagedSetupTests(unittest.TestCase):
    def test_first_run_checks_the_windows_payload_and_selects_its_owner(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(sys, 'platform', 'win32'):
            root = Path(temporary)
            problem = managed_setup.runtime_problem(root)
            self.assertIn('bundled PowerShell', problem)
            self.assertIn('background runtime owner', problem)
            for name, _label in managed_setup.WINDOWS_RUNTIME_PAYLOAD:
                target = root/name; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('fixture', encoding='utf-8')
            self.assertEqual(managed_setup.runtime_problem(root), '')
            self.assertEqual(managed_setup.setup_script().name, 'setup-windows.py')
            self.assertEqual(managed_setup.owner_type(), 'windows-supervisor')

    def test_setup_never_adopts_an_external_or_other_platform_owner(self):
        with patch.object(sys, 'platform', 'win32'), patch.object(managed_setup, 'missing_runtime', return_value=[]):
            for saved, expected in (({}, True), ({'managed': {'type': 'windows-supervisor'}}, True),
                                    ({'endpoint': 'http://127.0.0.1:3080'}, False),
                                    ({'managed': {'type': 'launchd'}}, False)):
                with self.subTest(saved=saved), patch.object(dsh, 'current', return_value=saved):
                    self.assertEqual(managed_setup.available(), expected)
                    self.assertEqual(managed_setup.needed(), not bool(saved))


if __name__ == '__main__': unittest.main()
