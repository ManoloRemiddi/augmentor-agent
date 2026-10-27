# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""The private build alias is omitted without following or weakening links."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))
spec = importlib.util.spec_from_file_location('windows_workspace_stage', ROOT/'scripts/stage-windows-application.py')
stage = importlib.util.module_from_spec(spec); spec.loader.exec_module(stage)
from lifecycle.payload_integrity import _scan


class WindowsWorkspaceAliasTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()/'stage'; self.root.mkdir()
        self.workspace = self.root/'apps/harness'; self.workspace.mkdir(parents=True)
        self.alias = self.root/'node_modules/augmentor-harness-dsh-gui'; self.alias.parent.mkdir()
        self.package = {'workspaces': ['apps/harness']}
        self.lock = {'packages': {'apps/harness': {'name': 'augmentor-harness-dsh-gui'},
            'node_modules/augmentor-harness-dsh-gui': {'link': True, 'resolved': 'apps/harness'}}}
        self.metadata = {'name': 'augmentor-harness-dsh-gui', 'private': True}
        self.write()
        nested = self.workspace/'node_modules/authored-dependency'; nested.mkdir(parents=True)
        (nested/'index.js').write_bytes(b'Independent retained dependency fixture.\n')
        self.link(self.alias, self.workspace)

    def write(self):
        for path, value in [(self.root/'package.json', self.package),
                            (self.root/'package-lock.json', self.lock),
                            (self.workspace/'package.json', self.metadata)]:
            path.write_text(json.dumps(value))

    def link(self, alias, target):
        if os.name == 'nt':
            import _winapi
            _winapi.CreateJunction(str(target), str(alias))
        else:
            alias.symlink_to(target, target_is_directory=True)

    def unlink(self):
        if os.name == 'nt': os.rmdir(self.alias)
        else: self.alias.unlink()

    def test_native_junction_or_symlink_removes_only_alias_and_preserves_nested_dependencies(self):
        before = stage.workspace_snapshot(self.workspace)
        with self.assertRaisesRegex(ValueError, 'reparse/link.*augmentor-harness-dsh-gui'):
            _scan(self.root)
        result = stage.remove_build_workspace_alias(self.root)
        self.assertEqual(result['path'], 'node_modules/augmentor-harness-dsh-gui')
        self.assertFalse(os.path.lexists(self.alias))
        self.assertEqual(stage.workspace_snapshot(self.workspace), before)
        _scan(self.root)

    def test_retargeted_alias_is_refused_without_changing_either_target(self):
        other = self.root/'other'; other.mkdir(); (other/'kept.txt').write_text('Independent fixture.')
        self.unlink(); self.link(self.alias, other)
        with self.assertRaises(ValueError): stage.remove_build_workspace_alias(self.root)
        self.assertTrue(os.path.lexists(self.alias)); self.assertEqual((other/'kept.txt').read_text(), 'Independent fixture.')

    def test_extra_link_is_refused_before_removing_the_expected_alias(self):
        extra = self.alias.parent/'authored-extra'; self.link(extra, self.workspace)
        with self.assertRaises(ValueError): stage.remove_build_workspace_alias(self.root)
        self.assertTrue(os.path.lexists(self.alias)); self.assertTrue(os.path.lexists(extra))

    def test_changed_workspace_contract_is_refused(self):
        for key in ['main', 'exports', 'bin']:
            self.metadata[key] = 'authored-runtime-entry'; self.write()
            with self.assertRaises(ValueError): stage.remove_build_workspace_alias(self.root)
            self.assertTrue(os.path.lexists(self.alias)); self.metadata.pop(key)
        self.metadata['private'] = False; self.write()
        with self.assertRaises(ValueError): stage.remove_build_workspace_alias(self.root)

    def test_undeclared_link_and_real_directory_are_not_removed(self):
        self.lock['packages']['node_modules/authored-extra'] = {'link': True, 'resolved': 'apps/harness'}
        self.write()
        with self.assertRaises(ValueError): stage.remove_build_workspace_alias(self.root)
        self.lock['packages'].pop('node_modules/authored-extra'); self.write(); self.unlink(); self.alias.mkdir()
        with self.assertRaises(ValueError): stage.remove_build_workspace_alias(self.root)
        self.assertTrue(self.alias.is_dir())


if __name__ == '__main__': unittest.main()
