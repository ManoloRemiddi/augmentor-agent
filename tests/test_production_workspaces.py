# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Authored workspace packaging and supplier-inventory boundaries."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'services'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stage = load('production_workspace_stage', ROOT / 'scripts/stage-production.py')
notices = load('production_workspace_notices', ROOT / 'scripts/third-party-notices.py')


class ProductionWorkspacesTest(unittest.TestCase):
    def test_workspace_manifest_stages_exact_dependencies_without_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'source'
            target = Path(directory) / 'stage'
            workspace = root / 'apps/ui'
            workspace.mkdir(parents=True)
            (root / 'package.json').write_text(json.dumps({'workspaces': ['apps/ui']}))
            metadata = json.dumps({'name': 'authored-ui', 'private': True,
                                   'dependencies': {'authored-fixture': '1.0.0'}})
            (workspace / 'package.json').write_text(metadata)
            (workspace / 'private-unselected.txt').write_text('Never copy implicit workspace source.')
            stage.stage_workspace_manifests(target, root)
            self.assertEqual((target / 'apps/ui/package.json').read_text(), metadata)
            self.assertFalse((target / 'apps/ui/private-unselected.txt').exists())
            for value in ['../outside', '/outside', 'apps/*', '.', '']:
                (root / 'package.json').write_text(json.dumps({'workspaces': [value]}))
                with self.assertRaises((ValueError, FileNotFoundError)):
                    stage.stage_workspace_manifests(target, root)

    def test_own_workspace_is_excluded_but_its_supplier_dependency_is_audited(self):
        with tempfile.TemporaryDirectory() as directory:
            tree = Path(directory)
            workspace = tree / 'apps/ui'
            dependency = tree / 'node_modules/authored-fixture'
            workspace.mkdir(parents=True)
            dependency.mkdir(parents=True)
            (workspace / 'package.json').write_text(json.dumps({'name': 'authored-ui', 'private': True}))
            (tree / 'node_modules/authored-ui').symlink_to('../apps/ui', target_is_directory=True)
            meta = {'name': 'authored-fixture', 'version': '1.0.0', 'license': 'MIT'}
            (dependency / 'package.json').write_text(json.dumps(meta))
            (dependency / 'LICENSE').write_text('Independently authored test notice.')
            (tree / 'package.json').write_text(json.dumps({'workspaces': ['apps/ui']}))
            lock = {'apps/ui': {'name': 'authored-ui'},
                    'node_modules/authored-ui': {'link': True, 'resolved': 'apps/ui'},
                    'node_modules/authored-fixture': meta}
            (tree / 'package-lock.json').write_text(json.dumps({'packages': lock}))
            catalog = ROOT / 'licenses'
            report, texts = notices.inventory(tree, catalog)
            self.assertEqual([row['name'] for row in report['components']], ['authored-fixture'])
            self.assertEqual(len(texts), 1)
            (tree / 'package.json').write_text(json.dumps({'workspaces': []}))
            with self.assertRaisesRegex(ValueError, 'unverified workspace link'):
                notices.inventory(tree, catalog)


if __name__ == '__main__':
    unittest.main()
