# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stage = load('stage_production', 'stage-production.py')
debian = load('package_debian', 'package-debian.py')


class CodexPackagingTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.target = Path(directory.name)
        (self.target / 'node_modules').mkdir()
        for name in ('package.json', 'package-lock.json'):
            (self.target / name).write_bytes((ROOT / name).read_bytes())

    def test_prerequisite_matches_the_locked_source_and_is_not_bundled(self):
        stage.codex_prerequisite(self.target)
        record = json.loads((self.target / 'distribution-prerequisites.json').read_text())[0]
        self.assertEqual(record['version'], '0.159.2')
        self.assertFalse(record['bundled'])

    def test_any_nested_codex_supplier_package_still_blocks_staging(self):
        for name in ('@openai/codex', '@openai/codex-linux-x64', '@openai/codex-darwin-arm64'):
            with self.subTest(name=name):
                package = self.target / 'node_modules/other/node_modules' / name
                package.mkdir(parents=True)
                metadata = package / 'package.json'
                metadata.write_text(json.dumps({'name': name, 'version': '0.159.2'}))
                with self.assertRaisesRegex(ValueError, 'must not be bundled'):
                    stage.codex_prerequisite(self.target)
                metadata.unlink()

    def test_a_production_dependency_cannot_silently_reenable_redistribution(self):
        path = self.target / 'package.json'
        package = json.loads(path.read_text()); package['dependencies']['@openai/codex'] = '0.159.2'
        path.write_text(json.dumps(package))
        with self.assertRaisesRegex(ValueError, 'review packaging'):
            stage.codex_prerequisite(self.target)

    def test_unknown_native_binary_still_blocks_the_debian_installer(self):
        binary = self.target / 'node_modules/unreviewed/tool'
        binary.parent.mkdir(parents=True); binary.write_bytes(b'\x7fELFunknown')
        with self.assertRaisesRegex(ValueError, 'Unreviewed native executable'):
            debian.native_notices(self.target, {})
