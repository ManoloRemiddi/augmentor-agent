# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('source_boundary', Path(__file__).parents[1] / 'scripts/check-private-source-boundary.py')
boundary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boundary)


class SourceBoundaryTests(unittest.TestCase):
    def test_deleted_archive_still_fails_when_history_retains_it(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            def git(*args):
                return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True)
            git('init'); git('config', 'user.name', 'Synthetic Test'); git('config', 'user.email', 'synthetic@example.invalid')
            path = root / 'vendor/testing/resonant-voice-service-0.1.17.tgz'
            path.parent.mkdir(parents=True); path.write_bytes(b'Synthetic banned-path test, no private source.')
            git('add', '.'); git('commit', '-m', 'Synthetic archive')
            with self.assertRaisesRegex(ValueError, 'tracked'):
                boundary.check(root)
            git('rm', str(path.relative_to(root))); git('commit', '-m', 'Delete file')
            with self.assertRaisesRegex(ValueError, 'history'):
                boundary.check(root)

    def test_clean_synthetic_fixture_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for args in [('init',), ('config', 'user.name', 'Synthetic Test'), ('config', 'user.email', 'synthetic@example.invalid')]:
                subprocess.run(['git', *args], cwd=root, check=True, capture_output=True)
            (root / 'fixture.mjs').write_text('export const transcript = "Synthetic test";\n')
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-m', 'Synthetic peer'], cwd=root, check=True, capture_output=True)
            boundary.check(root)
