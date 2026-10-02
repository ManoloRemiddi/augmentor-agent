# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Wrong input identities must refuse before a prepared package is exposed."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('system_qt_packaging', ROOT/'scripts/package-system-qt.py')
packaging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packaging)


class SystemQtPackages(unittest.TestCase):
    def test_foreign_runtime_dirty_source_or_wrong_package_pair_refuses_before_extraction(self):
        source = {'commit': 'a'*40, 'dirty': False}
        original = {'version': '0.2.13', 'target': 'debian13-amd64', 'source': source,
                    'artifacts': [{'file': 'augmentor-runtime_0.2.13_amd64.deb'},
                                  {'file': 'augmentor-desktop_0.2.13_amd64.deb'}]}
        bad = [{**original, 'target': 'ubuntu24.04-amd64'},
               {**original, 'pythonRuntime': {'profile': 'foreign'}},
               {**original, 'source': {**source, 'dirty': True}},
               {**original, 'source': {**source, 'commit': 'unverified'}},
               {**original, 'artifacts': original['artifacts'][:1]},
               {**original, 'artifacts': [original['artifacts'][0]]*2}]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for manifest in bad:
                with self.subTest(manifest=manifest):
                    (root/'artifacts.json').write_text(json.dumps(manifest))
                    with patch.object(packaging.subprocess, 'run') as run, self.assertRaises(ValueError):
                        packaging.prepare(root, root, root/'new-result', 'opensuse-leap16.0-x86_64')
                    run.assert_not_called()
                    self.assertFalse((root/'new-result').exists())

    def test_corrupt_checked_package_preserves_existing_output_and_refuses_new_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            names = ['augmentor-runtime_0.2.13_amd64.deb', 'augmentor-desktop_0.2.13_amd64.deb']
            for name in names:
                (root/name).write_bytes(b'corrupted input')
            (root/'artifacts.json').write_text(json.dumps({'version': '0.2.13',
                'target': 'debian13-amd64', 'source': {'commit': 'a'*40, 'dirty': False},
                'artifacts': [{'file': n, 'sha256': 'b'*64, 'bytes': 15} for n in names]}))
            existing = root/'existing'; existing.mkdir()
            (existing/'sentinel').write_bytes(b'preserve')
            for out in (existing, root/'new'):
                with self.subTest(out=out), patch.object(packaging.subprocess, 'run') as run, self.assertRaises(ValueError):
                    packaging.prepare(root, root, out, 'arch20261001-x86_64')
                run.assert_not_called()
            self.assertEqual((existing/'sentinel').read_bytes(), b'preserve')
            self.assertFalse((root/'new').exists())

    def test_embedded_removal_guard_is_standalone_and_rpm_macro_safe(self):
        package = {'name': 'augmentor-agent', 'versionRelease': '0.2.13-1.leap16', 'architecture': 'x86_64'}
        for phase, expanded in packaging.leap_scriptlets(package).items():
            with self.subTest(phase=phase):
                source = expanded.replace('%%', '%')
                compile(source, '<'+phase+'>', 'exec')
                self.assertIn("APP=Path('/usr/lib/augmentor')", source)
                self.assertIn("STATE=Path('/var/lib/augmentor-package-maintenance')", source)
                self.assertIn('%{NAME}', source)
                self.assertNotIn('sys.path', source)
        self.assertIn("sys.argv[1]=='0'", packaging.leap_scriptlets(package)['postuntrans'])


if __name__ == '__main__':
    unittest.main()
