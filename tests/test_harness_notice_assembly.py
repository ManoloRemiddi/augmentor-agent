# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real private filesystem publication boundaries; no supplier execution or owner data."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('harness_notice_assembly', ROOT / 'scripts/assemble-harness-notices.py')
assembly = importlib.util.module_from_spec(spec) if sys.platform == 'linux' else None
if assembly:
    spec.loader.exec_module(assembly)


@unittest.skipUnless(sys.platform == 'linux', 'Linux private preview assembly')
class HarnessNoticeAssemblyTest(unittest.TestCase):
    def fixture(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        app, baseline = root / 'app', root / 'baseline'
        def write(path, value):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value if isinstance(value, bytes) else value.encode())
        for tree in (app, baseline):
            write(tree / 'node/bin/node', b'\x7fELF AUTHORED NATIVE IDENTITY')
        write(baseline / 'licenses/node.txt', 'AUTHORED ORIGINAL NODE NOTICE')
        files = assembly.inventory.inventory(baseline)
        digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
        write(baseline / 'desktop-release.json', json.dumps({'files': files, 'artifactSha256': digest}))
        provenance = {}
        for name, key in (('dsh', None), ('dsh-context', 'dshContext'), ('dsh-metafolder', 'dshMetafolder'), ('augmentor-brand', 'augmentorBrand')):
            selected = {'license': 'MIT', 'fixture': name}
            write(app / 'apps/harness/vendor' / name / 'LICENSE', 'AUTHORED NOTICE ' + name)
            write(app / 'apps/harness/vendor' / name / 'SOURCE.json', json.dumps(selected))
            if key:
                provenance[key] = selected
        for name in ('dsh-web-search-free', 'keyless-search', 'dsh-keyless-fetch'):
            notices = ['LICENSE-dddmuc', 'LICENSE-shinjiyu'] if name == 'keyless-search' else ['LICENSE']
            bodies = {filename: 'AUTHORED SUPPLIER NOTICE ' + filename for filename in notices}
            bodies['original.txt'] = 'AUTHORED SELECTED SOURCE ' + name
            selected = {'fixture': name, 'files': [{'path': filename, 'sha256': hashlib.sha256(body.encode()).hexdigest()} for filename, body in bodies.items()]}
            for part in ('packages/runtime/vendor', 'dist/runtime/vendor'):
                for filename, body in bodies.items():
                    write(app / part / name / filename, body)
                write(app / part / name / 'SOURCE.json', json.dumps(selected))
        client = {'fixture': 'original-search-card', 'files': [{'path': 'LICENSE', 'sha256': hashlib.sha256(b'AUTHORED CLIENT NOTICE').hexdigest()}]}
        write(app / 'apps/harness/vendor/dsh-web-search-free/LICENSE', 'AUTHORED CLIENT NOTICE')
        write(app / 'apps/harness/vendor/dsh-web-search-free/SOURCE.json', json.dumps(client))
        provenance['dshFreeSearch'] = client
        write(app / 'dist/harness-web/SOURCE.json', json.dumps(provenance))
        write(app / 'dist/harness-web/THIRD-PARTY-NOTICES.txt', 'AUTHORED CURRENT GUI NOTICES')
        for name in ('dsh-attachment', 'dsh-file-reference', 'dsh-preview', 'dsh-model-discovery', 'dsh-office', 'dsh-plugin-wiki-tools', 'dsh-plugin-wiki-skills'):
            vendor = app / ('packages/runtime/vendor' if name == 'dsh-office' else 'dist/runtime/vendor') / name
            write(vendor / 'LICENSE', 'AUTHORED NOTICE ' + name)
            write(vendor / 'SOURCE.json', json.dumps({'fixture': name}))
        write(app / 'dist/runtime/vendor/dsh-plugin-wiki-skills/ORIGINAL_LICENSE', 'AUTHORED PRIOR SKILL NOTICE')
        return root, app, baseline

    def test_complete_closure_keeps_original_node_notice_and_current_gui_wiki_provenance(self):
        _, app, baseline = self.fixture()
        result = assembly.assemble(app, baseline)
        self.assertFalse(result['publicBinaryRedistributionQualified'])
        self.assertEqual((app / 'licenses/node.txt').read_bytes(), (baseline / 'licenses/node.txt').read_bytes())
        self.assertEqual((app / 'licenses/dsh-gui/SOURCE.json').read_bytes(), (app / 'dist/harness-web/SOURCE.json').read_bytes())
        self.assertEqual((app / 'licenses/dsh-plugin-wiki-skills/ORIGINAL_LICENSE').read_text(), 'AUTHORED PRIOR SKILL NOTICE')
        self.assertEqual(result['verifiedSearchSourceRecords'], 8)
        self.assertEqual((app / 'licenses/dsh-web-search-free/client/SOURCE.json').read_bytes(), (app / 'apps/harness/vendor/dsh-web-search-free/SOURCE.json').read_bytes())
        self.assertEqual((app / 'licenses/keyless-search/runtime/LICENSE-shinjiyu').read_text(), 'AUTHORED SUPPLIER NOTICE LICENSE-shinjiyu')

    def test_search_source_drift_missing_notice_and_stale_client_provenance_refuse_before_any_write(self):
        for fault in ('preferred', 'compiled', 'notice', 'client'):
            with self.subTest(fault=fault):
                _, app, baseline = self.fixture()
                if fault in ('preferred', 'compiled'):
                    part = 'packages' if fault == 'preferred' else 'dist'
                    (app / part / 'runtime/vendor/keyless-search/original.txt').write_text('UNATTESTED SOURCE')
                elif fault == 'notice':
                    (app / 'dist/runtime/vendor/keyless-search/LICENSE-shinjiyu').unlink()
                else:
                    provenance = json.loads((app / 'dist/harness-web/SOURCE.json').read_text())
                    provenance['dshFreeSearch'] = {'fixture': 'stale compiled card'}
                    (app / 'dist/harness-web/SOURCE.json').write_text(json.dumps(provenance))
                with self.assertRaises((ValueError, FileNotFoundError)):
                    assembly.assemble(app, baseline)
                self.assertFalse((app / 'licenses').exists())

    def test_search_selected_path_escape_and_link_preserve_outside_source_without_notice_writes(self):
        for fault in ('escape', 'link'):
            with self.subTest(fault=fault):
                root, app, baseline = self.fixture()
                outside = root / 'outside.txt'
                outside.write_text('AUTHORED OUTSIDE ORIGINAL')
                vendor = app / 'dist/runtime/vendor/keyless-search'
                if fault == 'link':
                    (vendor / 'original.txt').unlink()
                    (vendor / 'original.txt').symlink_to(outside)
                else:
                    selected = json.loads((vendor / 'SOURCE.json').read_text())
                    selected['files'].append({'path': '../outside.txt', 'sha256': '0' * 64})
                    for part in ('packages/runtime/vendor', 'dist/runtime/vendor'):
                        (app / part / 'keyless-search/SOURCE.json').write_text(json.dumps(selected))
                with self.assertRaisesRegex(ValueError, 'escapes'):
                    assembly.assemble(app, baseline)
                self.assertFalse((app / 'licenses').exists())
                self.assertEqual(outside.read_text(), 'AUTHORED OUTSIDE ORIGINAL')

    def test_native_drift_missing_input_and_tampered_baseline_refuse_before_any_notice_write(self):
        for fault in ('native', 'missing', 'baseline'):
            with self.subTest(fault=fault):
                _, app, baseline = self.fixture()
                if fault == 'native':
                    (app / 'node/bin/node').write_bytes(b'\x7fELF CHANGED')
                elif fault == 'missing':
                    (app / 'dist/runtime/vendor/dsh-plugin-wiki-tools/LICENSE').unlink()
                else:
                    (baseline / 'licenses/node.txt').write_text('UNATTESTED REPLACEMENT')
                with self.assertRaises((ValueError, FileNotFoundError)):
                    assembly.assemble(app, baseline)
                self.assertFalse((app / 'licenses').exists())

    def test_staged_release_and_linked_destination_preserve_both_originals(self):
        root, app, baseline = self.fixture()
        manifest = app / 'desktop-release.json'
        manifest.write_text('AUTHORED SEALED MARKER')
        with self.assertRaisesRegex(ValueError, 'staged release'):
            assembly.assemble(app, baseline)
        self.assertEqual(manifest.read_text(), 'AUTHORED SEALED MARKER')
        manifest.unlink()
        outside = root / 'outside'
        outside.mkdir()
        (outside / 'node.txt').write_text('AUTHORED OUTSIDE ORIGINAL')
        (app / 'licenses').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'escapes'):
            assembly.assemble(app, baseline)
        self.assertEqual((outside / 'node.txt').read_text(), 'AUTHORED OUTSIDE ORIGINAL')
