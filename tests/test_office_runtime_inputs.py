# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Independently authored source/link fixtures; no owner data or model calls."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('office_runtime_inputs',
    ROOT / 'release/office-rebuild/collect-runtime-inputs.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux runtime-source diagnostic')
class OfficeRuntimeInputsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def source_fixture(self, *, duplicate=False, unsafe=False, missing=False):
        installed = self.root / 'installed'
        installed.mkdir()
        rows = {'LICENSE': b'Authored original notice', 'AUTHORS': b'Authored contributors',
                'emcc.py': b'# authored compiler driver', 'system/lib/runtime.c': b'authored runtime source',
                'src/lib.js': b'authored js source', 'tools/build.py': b'authored tool source',
                'third_party/item/source.c': b'authored third party'}
        for name, raw in rows.items():
            path = installed / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        (installed / 'emscripten-version.txt').write_text('"1.0.0"\n')
        (installed / 'emscripten-revision.txt').write_text('a' * 40 + '\n')
        archive_path = self.root / 'source.tar.gz'
        with tarfile.open(archive_path, 'w:gz') as archive:
            archive_rows = {**rows, 'emscripten-version.txt': b'1.0.0-git\n'}
            if missing:
                archive_rows.pop('system/lib/runtime.c')
            for name, raw in archive_rows.items():
                item = tarfile.TarInfo('emscripten-' + 'a' * 40 + '/' + name)
                item.size = len(raw)
                archive.addfile(item, io.BytesIO(raw))
                if duplicate and name == 'LICENSE':
                    archive.addfile(item, io.BytesIO(raw))
            if unsafe:
                item = tarfile.TarInfo('../outside')
                item.size = 1
                archive.addfile(item, io.BytesIO(b'x'))
        pin = {'emscriptenRevision': 'a' * 40, 'sourceArchive': {
                   'bytes': archive_path.stat().st_size, 'sha256': runtime.inputs.digest(archive_path)},
               'installedSourceGroups': ['system', 'src', 'tools', 'third_party'],
               'installedRootSources': ['LICENSE', 'AUTHORS', 'emcc.py'],
               'installedPreferredSourceFiles': len(rows),
               'publicVersionSource': {'bytes': '1.0.0-git\n',
                   'sha256': hashlib.sha256(b'1.0.0-git\n').hexdigest()}}
        return installed, archive_path, pin

    def test_source_matches_with_explicit_release_overlay_and_no_extraction(self):
        installed, archive, pin = self.source_fixture()
        result = runtime.match_source(archive, installed, pin)
        self.assertEqual(len(result), 7)
        self.assertNotIn('emscripten-version.txt', result)
        self.assertEqual((installed / 'emscripten-version.txt').read_text(), '"1.0.0"\n')
        self.assertEqual(set(path.name for path in self.root.iterdir()), {'installed', 'source.tar.gz'})

    def test_changed_installed_body_cannot_be_hidden_by_a_version_label(self):
        installed, archive, pin = self.source_fixture()
        (installed / 'system/lib/runtime.c').write_bytes(b'changed runtime body')
        with self.assertRaisesRegex(ValueError, 'differs from public source'):
            runtime.match_source(archive, installed, pin)

    def test_extra_root_file_and_wrong_public_version_refuse(self):
        installed, archive, pin = self.source_fixture()
        (installed / 'unexpected.py').write_bytes(b'authored unreviewed tool')
        with self.assertRaisesRegex(ValueError, 'root source inventory'):
            runtime.match_source(archive, installed, pin)
        (installed / 'unexpected.py').unlink()
        pin['publicVersionSource']['bytes'] = 'wrong-version\n'
        with self.assertRaisesRegex(ValueError, 'version source changed'):
            runtime.match_source(archive, installed, pin)

    def test_archive_hash_and_installed_links_refuse(self):
        installed, archive, pin = self.source_fixture()
        original = archive.read_bytes()
        archive.write_bytes(original + b'changed')
        with self.assertRaisesRegex(ValueError, 'reviewed source'):
            runtime.match_source(archive, installed, pin)
        archive.write_bytes(original)
        target = installed / 'src/lib.js'
        target.unlink()
        target.symlink_to(installed / 'emcc.py')
        with self.assertRaisesRegex(ValueError, 'Linked installed'):
            runtime.match_source(archive, installed, pin)

    def test_duplicate_source_refuses(self):
        installed, archive, pin = self.source_fixture(duplicate=True)
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            runtime.match_source(archive, installed, pin)

    def test_missing_public_source_refuses(self):
        installed, archive, pin = self.source_fixture(missing=True)
        with self.assertRaisesRegex(ValueError, 'absent from the public archive'):
            runtime.match_source(archive, installed, pin)

    def test_archive_traversal_refuses_without_writing(self):
        installed, archive, pin = self.source_fixture(unsafe=True)
        with self.assertRaisesRegex(ValueError, 'Unsafe public source'):
            runtime.match_source(archive, installed, pin)
        self.assertFalse((self.root / 'outside').exists())

    def link_fixture(self):
        directory = self.root / 'emsdk/upstream/emscripten/cache/sysroot/lib/wasm32-emscripten/thinlto'
        directory.mkdir(parents=True)
        (directory / 'libauthored.a').write_bytes(b'authored library input; never executable')
        (directory / 'crtbegin.o').write_bytes(b'authored object input; never executable')
        debug = self.root / 'thin-build-debug'
        debug.mkdir()
        response = debug / 'fixture.rsp.utf-8'
        response.write_text('-o /office/build-thin/instdir/program/soffice.wasm -lauthored ' +
            '/office/emsdk/upstream/emscripten/cache/sysroot/lib/wasm32-emscripten/thinlto/crtbegin.o')
        pin = {'finalOutput': '/office/build-thin/instdir/program/soffice.wasm',
               'finalLinkResponseSha256': runtime.inputs.digest(response),
               'systemLibraries': {'libauthored.a': runtime.inputs.digest(directory / 'libauthored.a')},
               'explicitSystemObjects': {'crtbegin.o': runtime.inputs.digest(directory / 'crtbegin.o')}}
        return directory, response, pin

    def test_exact_final_response_and_library_object_bytes_required(self):
        directory, response, pin = self.link_fixture()
        selected, libraries = runtime.link_inputs(self.root, pin)
        self.assertEqual(selected, response)
        self.assertEqual(set(libraries), {'libauthored.a'})
        (directory / 'libauthored.a').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'system-library inputs changed'):
            runtime.link_inputs(self.root, pin)

    def test_duplicate_link_response_and_wrong_output_refuse(self):
        directory, response, pin = self.link_fixture()
        duplicate = response.with_name('duplicate.rsp.utf-8')
        duplicate.write_bytes(response.read_bytes())
        with self.assertRaisesRegex(ValueError, 'unavailable or ambiguous'):
            runtime.link_inputs(self.root, pin)
        duplicate.unlink()
        pin['finalOutput'] = '/different-output.wasm'
        with self.assertRaisesRegex(ValueError, 'another output'):
            runtime.link_inputs(self.root, pin)

    def test_submodule_scope_refuses_new_inputs_and_language_changes(self):
        build = self.root / 'build-thin'
        build.mkdir()
        (build / 'config_host.mk').write_text('export BUILD_TYPE=LibO EMSCRIPTEN\nexport WITH_MYSPELL_DICTS=\n')
        languages = build / 'config_host_lang.mk'
        languages.write_text('WITH_LANG=\nWITH_LANG_LIST=en-US\n')
        for name in ['dictionaries', 'helpcontent2', 'translations']:
            (self.root / 'core' / name).mkdir(parents=True)
        result = runtime.submodule_scope(self.root)
        self.assertEqual(len(result['emptySubmodules']), 3)
        (self.root / 'core/dictionaries/new').write_bytes(b'authored additional source')
        with self.assertRaisesRegex(ValueError, 'unqualified inputs'):
            runtime.submodule_scope(self.root)
        (self.root / 'core/dictionaries/new').unlink()
        languages.write_text('WITH_LANG=fr\nWITH_LANG_LIST=en-US fr\n')
        with self.assertRaisesRegex(ValueError, 'submodule use differs'):
            runtime.submodule_scope(self.root)


if __name__ == '__main__':
    unittest.main()
