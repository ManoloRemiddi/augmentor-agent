# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real supplier payload/export checks and the public redistribution boundary."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


debian = load('office_debian_packager', 'package-debian.py')
office = debian.office_engine


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux Office Wasm packaging is MX-first')
class OfficeEnginePackagingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='augmentor-office-notices café ')
        self.addCleanup(temporary.cleanup)
        self.app = Path(temporary.name) / 'app'
        for name in (office.ENGINE, office.ENTRY):
            shutil.copytree(ROOT / name, self.app / name,
                            ignore=shutil.ignore_patterns('node_modules'))
        shutil.copyfile(ROOT / 'package-lock.json', self.app / 'package-lock.json')

    def stage(self):
        return office.stage_engine(self.app)

    def test_actual_engine_exports_exact_notices_and_all_engine_build_sources(self):
        before = office.sha(self.app / office.ENGINE / 'assets/soffice.wasm')
        result = self.stage()
        self.assertEqual(before, result['sha256'])
        self.assertEqual(result['engineVersion'], '26.8.0.3')
        self.assertFalse(result['publicRedistributionQualified'])
        sources = list((self.app / 'licenses/office-engine/sources').rglob('*'))
        self.assertEqual(sum(path.is_file() for path in sources), 39)
        for notice in result['notices']:
            self.assertTrue((self.app / 'licenses' / notice).is_file(), notice)
        self.assertEqual(result, office.validate_bundle(self.app, require_public=False))

    def test_actual_debian_gate_refuses_public_packaging_after_private_identity_passes(self):
        self.stage()
        with self.assertRaisesRegex(ValueError, 'Office public source/rebuild qualification remains open'):
            debian.native_notices(self.app, {})
        self.assertFalse((self.app / 'licenses/native-components.json').exists())

    def test_changing_approval_labels_does_not_qualify_missing_corresponding_source(self):
        source = self.app.parent / 'source'
        pin = source / 'release/office-engine-linux-wasm.json'
        pin.parent.mkdir(parents=True)
        item = office.record()
        item['publicSourceRebuildGate'] = 'qualified'
        item['entryPackage']['preferredSourceGate'] = 'qualified'
        pin.write_text(json.dumps(item))
        office.stage_engine(self.app, source)
        with self.assertRaisesRegex(ValueError, 'public source/rebuild qualification remains open'):
            office.validate_bundle(self.app, source)

    def test_changed_binary_cannot_be_authorized_by_rehashing_local_export(self):
        self.stage()
        path = self.app / office.ENGINE / 'assets/soffice.wasm'
        with path.open('ab') as stream:
            stream.write(b'changed')
        build = self.app / 'licenses/office-engine/BUILD.json'
        item = json.loads(build.read_text())
        item['files']['assets/soffice.wasm'] = office.sha(path)
        build.write_text(json.dumps(item))
        with self.assertRaisesRegex(ValueError, 'changed: .*soffice.wasm'):
            office.validate_bundle(self.app, require_public=False)

    def test_missing_recipe_and_added_source_block_staging(self):
        path = self.app / office.ENGINE / 'sources/engine/wasm-source/build.mjs'
        original = path.read_bytes()
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'file inventory changed'):
            self.stage()
        path.write_bytes(original)
        added = path.parent / 'unreviewed.mjs'
        added.write_text('export {};\n')
        with self.assertRaisesRegex(ValueError, 'file inventory changed'):
            self.stage()

    def test_changed_engine_source_and_compiled_entry_are_not_accepted(self):
        for name in (office.ENGINE + '/sources/source-changes.patch', office.ENTRY + '/lib/index.js'):
            path = self.app / name
            original = path.read_bytes()
            path.write_bytes(original + b'changed')
            with self.assertRaisesRegex(ValueError, 'missing, linked or changed'):
                self.stage()
            path.write_bytes(original)

    def test_linked_package_parent_and_linked_export_are_refused(self):
        parent = self.app / 'node_modules/@deepseek-ai'
        saved = parent.with_name('saved-office')
        parent.rename(saved)
        parent.symlink_to(saved, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'linked or changed'):
            self.stage()
        parent.unlink()
        saved.rename(parent)
        self.stage()
        notice = self.app / 'licenses/office-engine/engine/LICENSE'
        original = self.app / office.ENGINE / 'licenses/LICENSE'
        notice.unlink()
        notice.symlink_to(original)
        with self.assertRaisesRegex(ValueError, 'linked or changed'):
            office.validate_bundle(self.app, require_public=False)

    def test_missing_notice_changed_export_and_extra_file_are_refused(self):
        self.stage()
        path = self.app / 'licenses/office-engine/kit-NOTICE'
        original = path.read_bytes()
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'missing, linked or changed'):
            office.validate_bundle(self.app, require_public=False)
        path.write_bytes(original + b'changed')
        with self.assertRaisesRegex(ValueError, 'missing, linked or changed'):
            office.validate_bundle(self.app, require_public=False)
        path.write_bytes(original)
        (path.parent / 'unknown.txt').write_text('unreviewed')
        with self.assertRaisesRegex(ValueError, 'export inventory changed'):
            office.validate_bundle(self.app, require_public=False)

    def test_different_locked_tarball_and_relabelled_component_are_refused(self):
        path = self.app / 'package-lock.json'
        original = path.read_bytes()
        lock = json.loads(original)
        lock['packages'][office.ENGINE]['integrity'] = 'unreviewed'
        path.write_text(json.dumps(lock))
        with self.assertRaisesRegex(ValueError, 'reviewed lock'):
            self.stage()
        path.write_bytes(original)
        self.stage()
        component = self.app / 'licenses/office-engine/native-component.json'
        item = json.loads(component.read_text())
        item['publicRedistributionQualified'] = True
        component.write_text(json.dumps(item))
        with self.assertRaisesRegex(ValueError, 'component inventory differs'):
            office.validate_bundle(self.app, require_public=False)


if __name__ == '__main__':
    unittest.main()
