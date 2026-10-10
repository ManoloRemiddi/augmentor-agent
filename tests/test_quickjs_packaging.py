# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Distribution failure contracts and actual Node resolution of codemode assets."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


engine = load('quickjs_packaging', 'quickjs_engine.py')
builder = load('quickjs_source_export', 'build-quickjs.py')


class QuickJSPackagingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='augmentor-qjs-test café ')
        self.addCleanup(temporary.cleanup); self.directory = Path(temporary.name)
        self.root = self.directory / 'source'; self.app = self.directory / 'app'
        shutil.copytree(ROOT / 'release/quickjs', self.root / 'release/quickjs')
        shutil.copytree(ROOT / 'vendor/quickjs-engine', self.root / 'vendor/quickjs-engine')

    def package(self, nested=False):
        def write(path, value):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value))
        write(self.app / 'node_modules/@earendil-works/pi-coding-agent/package.json',
              {'name': '@earendil-works/pi-coding-agent', 'version': '1.1.0'})
        codemode = self.app / 'node_modules/@earendil-works/pi-codemode'
        write(codemode / 'package.json', {'name': '@earendil-works/pi-codemode', 'version': '1.1.0',
              'exports': {'.': {'import': './dist/index.js'}}})
        (codemode / 'dist').mkdir(); (codemode / 'dist/index.js').write_text('export {};\n')
        package = (codemode / 'node_modules' if nested else self.app / 'node_modules') / 'quickjs-wasi'
        write(package / 'package.json', {'name': 'quickjs-wasi', 'version': '3.6.2',
              'exports': {'./package.json': './package.json', './quickjs.wasm': './quickjs.wasm'}})
        upstream = ROOT / 'node_modules/quickjs-wasi'
        for name in ['quickjs.wasm', *engine.reviewed(self.root)[1]['excludedAssets']]:
            target = package / name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(upstream / name, target)
        return package

    def test_normal_stage_preserves_sources_and_rejects_packaged_tampering(self):
        package = self.package(); excluded = []
        result = engine.stage_engine(self.app, excluded, self.root)
        self.assertEqual(engine.sha(package / 'quickjs.wasm'), result['wasmSha256'])
        self.assertNotEqual(result['wasmSha256'], result['originalWasmSha256'])
        self.assertEqual(len(excluded), 5)
        self.assertFalse(list((package / 'extensions').glob('*/*.so')))
        item = engine.validate_bundle(self.app, self.root)
        self.assertEqual(item['path'], 'node_modules/quickjs-wasi/quickjs.wasm')
        for notice in item['notices']:
            self.assertTrue((self.app / 'licenses' / notice).is_file(), notice)
        # A rehashed local bundle record cannot authorize a changed executable.
        wasm = package / 'quickjs.wasm'; wasm.write_bytes(wasm.read_bytes() + b'tamper')
        with self.assertRaisesRegex(ValueError, 'changed: quickjs.wasm'):
            engine.validate_bundle(self.app, self.root)
        record = self.app / 'licenses/quickjs/BUILD.json'
        data = json.loads(record.read_text()); data['files']['quickjs.wasm'] = engine.sha(wasm)
        record.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'changed: BUILD.json'):
            engine.validate_bundle(self.app, self.root)

    def test_missing_static_notice_blocks_packaging_and_a_rehashed_vendor_record(self):
        notice = self.root / 'vendor/quickjs-engine/third-party/musl-COPYRIGHT.txt'
        notice.unlink()
        record = self.root / 'vendor/quickjs-engine/BUILD.json'
        data = json.loads(record.read_text()); del data['files']['third-party/musl-COPYRIGHT.txt']
        record.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            engine.reviewed(self.root)

    def test_changed_sources_and_linked_notices_are_refused(self):
        path = self.root / 'vendor/quickjs-engine/sources/wasi-libc.tar.gz'
        original = path.read_bytes(); path.write_bytes(original + b'changed source')
        with self.assertRaisesRegex(ValueError, 'sources/wasi-libc'):
            engine.reviewed(self.root)
        path.write_bytes(original)
        notice = self.root / 'vendor/quickjs-engine/third-party/quickjs-ng-MIT.txt'
        copy = self.directory / 'outside-notice'; shutil.copyfile(notice, copy)
        notice.unlink()
        try:
            notice.symlink_to(copy)
        except OSError:
            self.skipTest('OS does not grant symbolic-link creation')
        with self.assertRaisesRegex(ValueError, 'Linked QuickJS vendor'):
            engine.reviewed(self.root)

    def test_codemode_resolution_uses_its_nested_engine_and_import_condition(self):
        package = self.package(nested=True)
        unrelated = self.app / 'node_modules/quickjs-wasi'; unrelated.mkdir()
        (unrelated / 'package.json').write_text(json.dumps({'name': 'quickjs-wasi', 'version': 'unreviewed'}))
        engine.stage_engine(self.app, [], self.root)
        self.assertEqual(engine.validate_bundle(self.app, self.root)['path'], package.relative_to(self.app).as_posix() + '/quickjs.wasm')

    def test_changed_npm_engine_or_optional_inventory_stops_before_override(self):
        package = self.package(); original = (package / 'quickjs.wasm').read_bytes()
        (package / 'quickjs.wasm').write_bytes(original + b'unknown upstream')
        with self.assertRaisesRegex(ValueError, 'Published QuickJS engine differs'):
            engine.stage_engine(self.app, [], self.root)
        (package / 'quickjs.wasm').write_bytes(original)
        # Refuse a linked executable before substitution can write its target.
        outside = self.directory / 'outside-engine'; outside.write_bytes(original)
        (package / 'quickjs.wasm').unlink()
        try:
            (package / 'quickjs.wasm').symlink_to(outside)
        except OSError:
            pass  # Windows may withhold symlink privilege; other checks still run.
        else:
            with self.assertRaisesRegex(ValueError, 'escaped production dependencies'):
                engine.stage_engine(self.app, [], self.root)
            self.assertEqual(outside.read_bytes(), original)
            (package / 'quickjs.wasm').unlink()
        (package / 'quickjs.wasm').write_bytes(original)
        extension = package / 'extensions/crypto/crypto.so'; extension_bytes = extension.read_bytes()
        outside = self.directory / 'outside-extension'; outside.write_bytes(extension_bytes); extension.unlink()
        try:
            extension.symlink_to(outside)
        except OSError:
            pass
        else:
            with self.assertRaisesRegex(ValueError, 'Linked QuickJS staging'):
                engine.stage_engine(self.app, [], self.root)
            self.assertEqual(outside.read_bytes(), extension_bytes)
            self.assertEqual((package / 'quickjs.wasm').read_bytes(), original)
            extension.unlink()
        extension.write_bytes(extension_bytes)
        extra = package / 'extensions/foreign/foreign.so'; extra.parent.mkdir()
        extra.write_bytes(b'\x00asmunknown')
        with self.assertRaisesRegex(ValueError, 'optional extension inventory changed'):
            engine.stage_engine(self.app, [], self.root)
        self.assertEqual((package / 'quickjs.wasm').read_bytes(), original)

    def test_missing_bundle_notice_and_foreign_binary_still_block_distribution(self):
        package = self.package(); engine.stage_engine(self.app, [], self.root)
        notice = self.app / 'licenses/quickjs/third-party/compiler-rt-LICENSE.txt'
        content = notice.read_bytes(); notice.unlink()
        with self.assertRaisesRegex(ValueError, 'compiler-rt-LICENSE'):
            engine.validate_bundle(self.app, self.root)
        notice.write_bytes(content)
        wasm = package / 'quickjs.wasm'; content = wasm.read_bytes(); wasm.unlink()
        with self.assertRaises(subprocess.CalledProcessError):
            engine.validate_bundle(self.app, self.root)
        wasm.write_bytes(content)
        binary = package / 'foreign-helper.bin'; binary.write_bytes(b'MZunknown helper')
        with self.assertRaisesRegex(ValueError, 'Unreviewed native asset'):
            engine.validate_bundle(self.app, self.root)
        binary.unlink()
        outside = self.directory / 'empty-notices'; outside.mkdir()
        link = self.app / 'licenses/quickjs/foreign-notices'
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            pass
        else:
            with self.assertRaisesRegex(ValueError, 'Linked QuickJS source/notice'):
                engine.validate_bundle(self.app, self.root)

    def test_package_version_change_and_artifact_path_escape_are_refused(self):
        package = self.package(); metadata = package / 'package.json'
        data = json.loads(metadata.read_text()); data['version'] = '3.6.3'; metadata.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'identity changed'):
            engine.stage_engine(self.app, [], self.root)
        with self.assertRaisesRegex(ValueError, 'Unsafe QuickJS artifact path'):
            engine.verified_file(self.root, '../outside', 'irrelevant')

    def test_source_export_excludes_untracked_files_and_checks_git_blob_identity(self):
        source = self.directory / 'llvm-fixture'; source.mkdir()
        (source / 'LICENSE.TXT').write_text('Independently authored source fixture\n')
        (source / 'compiler-rt/lib/builtins').mkdir(parents=True)
        (source / 'compiler-rt/lib/builtins/test.c').write_text('int fixture(void) { return 1; }\n')
        git = lambda *args: subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()
        git('init', '-q'); git('config', 'core.autocrlf', 'false'); git('add', '.')
        git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'Synthetic source')
        commit = git('rev-parse', 'HEAD'); (source / 'private-untracked.txt').write_text('must stay out')
        archive = self.directory / 'source.tar.gz'
        builder.export_llvm(source, commit, ['LICENSE.TXT', 'compiler-rt/lib/builtins'], archive)
        import tarfile
        with tarfile.open(archive) as bundle:
            self.assertEqual(bundle.getnames(), ['LICENSE.TXT', 'compiler-rt/lib/builtins/test.c'])
        (source / 'compiler-rt/lib/builtins/test.c').write_text('changed source')
        with self.assertRaisesRegex(ValueError, 'differs from pinned Git blob'):
            builder.export_llvm(source, commit, ['LICENSE.TXT', 'compiler-rt/lib/builtins'], archive)


if __name__ == '__main__':
    unittest.main()
