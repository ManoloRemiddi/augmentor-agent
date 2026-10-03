# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Synthetic admission refusals; no native install or product upgrade evidence."""
import importlib.util
from pathlib import Path
import json
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('upgrade_preparation', Path(__file__).parents[1]/'release/prepare-published-linux-upgrade-fixture.py')
proof = importlib.util.module_from_spec(spec); spec.loader.exec_module(proof)


class Admission(unittest.TestCase):
    def test_foreign_account_refuses_without_native_query(self):
        with patch.object(proof.os, 'getuid', return_value=1234), patch.object(proof.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'dedicated ordinary'): proof.admit()
            run.assert_not_called()

    def test_symlink_input_refuses(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'real').write_text('synthetic'); (root/'link').symlink_to(root/'real')
            with self.assertRaisesRegex(ValueError, 'ordinary immutable'): proof.root_file(root/'link')

    def test_atomic_record_cannot_reuse_uncommitted_temporary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'run.json'; proof.atomic(path, {'phase': 'pending'})
            (Path(directory)/'run.json.new').write_text('uncertain')
            with self.assertRaises(FileExistsError): proof.atomic(path, {'phase': 'success'})
            self.assertEqual(json.loads(path.read_text()), {'phase': 'pending'})

    def fixture_admission(self, home, bundle, app):
        bundle.mkdir(); app.mkdir(); home.chmod(0o700)
        (bundle/'setup.py').write_text('synthetic only')
        manifest = {'sourceCommit': proof.SOURCE, 'target': 'debian13-amd64', 'version': '0.2.12', 'sha256': {}}
        (bundle/'bundle.json').write_text(json.dumps(manifest))
        (app/'release.json').write_text(json.dumps({'source': {'commit': proof.SOURCE, 'dirty': False}, 'target': 'debian13-amd64', 'version': '0.2.12'}))
        return manifest

    def test_prior_state_refuses_before_any_installer(self):
        # Inject only native/root admission facts; actual state-file existence and
        # exclusive journal creation are exercised on a real temporary filesystem.
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory); bundle = home/'bundle'; app = home/'app'; self.fixture_admission(home, bundle, app)
            prior = home/'.local/share/augmentor'; prior.mkdir(parents=True)
            real_read = Path.read_text
            real_stat = Path.lstat
            def lstat(path, *args, **kwargs):
                value = real_stat(path, *args, **kwargs)
                if path == home:
                    values = list(value); values[4] = 1000; return os.stat_result(values)
                return value
            def read(path, *args, **kwargs):
                return proof.MARKER if str(path) == '/etc/augmentor-test-container' else real_read(path, *args, **kwargs)
            with patch.object(proof, 'HOME', home), patch.object(proof, 'BUNDLE', bundle), patch.object(proof, 'APP', app), \
                 patch.object(proof.Path, 'home', return_value=home), patch.object(proof, 'root_file'), \
                 patch.object(proof, 'digest', side_effect=lambda path: proof.MANIFEST_SHA if path.name == 'bundle.json' else proof.SETUP_SHA), \
                 patch.object(proof.os, 'getuid', return_value=1000), patch.object(proof.Path, 'read_text', read), \
                 patch.object(proof.Path, 'lstat', lstat), \
                 patch.object(proof.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as run:
                with self.assertRaisesRegex(ValueError, 'Prior product state'): proof.prepare()
                self.assertEqual(run.call_count, 2)
            self.assertFalse((home/'.local/state/published-product-upgrade150').exists())


if __name__ == '__main__': unittest.main()
