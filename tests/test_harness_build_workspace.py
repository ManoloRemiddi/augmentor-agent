# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Disposable owned fixtures; never create an app copy or change an owner service."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if sys.platform == 'linux':
    spec = importlib.util.spec_from_file_location('authored_build_workspace', ROOT / 'scripts/harness-build-workspace.py')
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)


@unittest.skipUnless(sys.platform == 'linux', 'MX local build storage helper')
class BuildWorkspaceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='authored-build-storage-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.root = self.base / 'scratch'
        env = patch.dict(os.environ, {'HOME': str(self.base), 'XDG_DATA_HOME': str(self.base / 'data'), 'XDG_CONFIG_HOME': str(self.base / 'config')})
        env.start()
        self.addCleanup(env.stop)

    def test_success_and_failure_remove_their_own_scratch_and_keep_external_logs(self):
        receipt = self.base / 'kept-report.json'
        with build.workspace(self.root, 0) as path:
            (path / 'application').mkdir()
            (path / 'application/synthetic-build').write_text('AUTHORED')
            receipt.write_text(json.dumps({'result': 'kept'}))
        self.assertFalse(path.exists())
        with self.assertRaisesRegex(RuntimeError, 'authored failure'):
            with build.workspace(self.root, 0) as next_path:
                raise RuntimeError('authored failure')
        self.assertFalse(next_path.exists())
        self.assertEqual(json.loads(receipt.read_text()), {'result': 'kept'})
        self.assertEqual([p.name for p in self.root.iterdir()], ['.lock'])

    def test_concurrent_build_is_refused_before_allocating_another_copy(self):
        with build.workspace(self.root, 0):
            with self.assertRaisesRegex(ValueError, 'Another build'):
                with build.workspace(self.root, 0):
                    self.fail('A second workspace was admitted')

    def test_previous_unknown_workspace_is_preserved_and_blocks_another(self):
        self.root.mkdir(mode=0o700)
        previous = self.root / 'build-unexamined'
        previous.mkdir()
        (previous / 'keep').write_text('KEEP')
        with self.assertRaisesRegex(ValueError, 'previous build'):
            with build.workspace(self.root, 0):
                self.fail('An unreaped build was ignored')
        self.assertEqual((previous / 'keep').read_text(), 'KEEP')

    def test_alias_or_broad_storage_permissions_are_refused(self):
        target = self.base / 'real'
        target.mkdir(mode=0o700)
        alias = self.base / 'alias'
        alias.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'aliases'):
            with build.workspace(alias, 0):
                pass
        target.chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'private owned'):
            with build.workspace(target, 0):
                pass

    def test_free_space_reserve_refuses_allocation(self):
        with patch.object(build.shutil, 'disk_usage', return_value=type('Usage', (), {'free': 1})()):
            with self.assertRaisesRegex(ValueError, 'free-space reserve'):
                with build.workspace(self.root, 1024):
                    pass
        self.assertEqual([p.name for p in self.root.iterdir()], ['.lock'])

    def test_actual_live_process_keeps_its_workspace_and_blocks_new_work(self):
        child = None
        try:
            with self.assertRaisesRegex(ValueError, 'still referenced'):
                with build.workspace(self.root, 0) as path:
                    child = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(20)'], cwd=path)
            self.assertTrue(path.is_dir())
            with self.assertRaisesRegex(ValueError, 'previous build'):
                with build.workspace(self.root, 0):
                    pass
        finally:
            if child:
                child.terminate()
                child.wait(timeout=5)

    def test_selected_or_rollback_reference_prevents_cleanup(self):
        selection = self.base / 'data/augmentor/desktop.previous.json'
        selection.parent.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, 'registered review'):
            with build.workspace(self.root, 0) as path:
                selection.write_text(json.dumps({'root': str(path)}))
        self.assertTrue(path.is_dir())

    def test_real_command_uses_scratch_and_exit_status_without_retaining_a_copy(self):
        code = 'import os;from pathlib import Path;p=Path(os.environ["AUGMENTOR_BUILD_WORKSPACE"]);(p/"built").write_text("AUTHORED")'
        self.assertEqual(build.run([sys.executable, '-B', '-c', code], self.root, 0), 0)
        self.assertEqual(build.run([sys.executable, '-B', '-c', 'raise SystemExit(7)'], self.root, 0), 7)
        self.assertEqual([p.name for p in self.root.iterdir()], ['.lock'])

    def test_low_space_during_a_real_owned_command_stops_it_and_cleans_scratch(self):
        free = iter([1024, 0])
        def usage(_path):
            return type('Usage', (), {'free': next(free, 0)})()
        with patch.object(build.shutil, 'disk_usage', side_effect=usage):
            result = build.run([sys.executable, '-B', '-c', 'import time;time.sleep(20)'], self.root, 512)
        self.assertEqual(result, 75)
        self.assertEqual([p.name for p in self.root.iterdir()], ['.lock'])


if __name__ == '__main__':
    unittest.main()
