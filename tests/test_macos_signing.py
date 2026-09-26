# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Signing-policy rejection tests; Apple acceptance still requires real credentials."""
import importlib.util
import json
from pathlib import Path
import plistlib
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('macos_signing', ROOT/'scripts/macos-signing.py')
signing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(signing)


def macho(path, kind=2):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack('<IIIIIIII', 0xfeedfacf, 0x100000c, 0, kind, 0, 0, 0, 0))


def app_fixture(root):
    app = root/'Augmentor Agent Desktop.app'
    executable = app/'Contents/MacOS/Augmentor'
    macho(executable)
    (app/'Contents/Info.plist').write_bytes(plistlib.dumps({
        'CFBundleIdentifier': 'com.augmentor.Agent', 'CFBundleExecutable': 'Augmentor',
        'CFBundleShortVersionString': '0.2.12'}))
    return app


def framework_fixture(app):
    framework = app/'Contents/Resources/app/python/Qt/lib/QtCore.framework'
    version = framework/'Versions/A'
    macho(version/'QtCore', 6)
    (version/'Resources').mkdir()
    data = plistlib.dumps({'CFBundleExecutable': 'QtCore'})
    (version/'Resources/Info.plist').write_bytes(data)
    (framework/'Resources').mkdir()
    (framework/'Resources/Info.plist').write_bytes(data)
    return framework


class SigningPlanTests(unittest.TestCase):
    def test_inside_out_all_code_including_resources_without_library_entitlements(self):
        with tempfile.TemporaryDirectory() as folder:
            app = app_fixture(Path(folder))
            framework = framework_fixture(app)
            node = app/'Contents/Resources/app/node/bin/node'
            macho(node)
            macho(app/'Contents/Resources/app/extension.so', 8)
            (node.parent/'node-alias').symlink_to('node')
            before = signing.signing_plan(app)
            self.assertEqual(len(before['machOFiles']), 4)
            self.assertEqual(before['steps'][-1]['path'], '.')
            self.assertFalse(before['publicReleaseReady'])
            self.assertFalse((framework/'Versions/Current').exists())  # plan is read-only
            signing.normalize_frameworks(app)
            self.assertTrue((framework/'Versions/Current').is_symlink())
            self.assertTrue((framework/'Resources').is_symlink())
            self.assertEqual((framework/'QtCore').resolve(), (framework/'Versions/A/QtCore').resolve())
            plan = signing.signing_plan(app)
            self.assertEqual(plan, before)
            entitlements = [s for s in plan['steps'] if s['entitlements']]
            self.assertEqual(len(entitlements), 1)
            self.assertEqual(entitlements[0]['path'], node.relative_to(app).as_posix())
            self.assertEqual(entitlements[0]['entitlements'], {'com.apple.security.cs.allow-jit': True})
            # Normalization is repeatable, and cannot create a duplicate executable.
            signing.normalize_frameworks(app)
            self.assertEqual(signing.signing_plan(app), plan)

    def test_external_or_broken_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); app = app_fixture(root)
            external = root/'private'; external.write_text('private')
            link = app/'Contents/link'; link.symlink_to(external)
            with self.assertRaisesRegex(ValueError, 'escapes'):
                signing.signing_plan(app)
            external.unlink()
            with self.assertRaises(FileNotFoundError):
                signing.signing_plan(app)

    def test_modified_duplicate_resources_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            app = app_fixture(Path(folder)); framework = framework_fixture(app)
            extra = framework/'Resources/extra'; extra.write_text('keep this')
            with self.assertRaisesRegex(ValueError, 'resources differ'):
                signing.normalize_frameworks(app)
            self.assertEqual(extra.read_text(), 'keep this')
            self.assertFalse((framework/'Versions/Current').exists())

    def test_multiple_framework_versions_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            app = app_fixture(Path(folder)); framework = framework_fixture(app)
            (framework/'Versions/B').mkdir()
            with self.assertRaisesRegex(ValueError, 'single framework version'):
                signing.signing_plan(app)

    def test_all_universal_slices_must_be_valid_and_match(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'universal'
            thin = struct.pack('<IIIIIIII', 0xfeedfacf, 0x100000c, 0, 6, 0, 0, 0, 0)
            fat = struct.pack('>II', 0xcafebabe, 2)
            fat += struct.pack('>IIIII', 0x100000c, 0, 48, 32, 0)
            fat += struct.pack('>IIIII', 0x1000007, 0, 80, 32, 0)
            path.write_bytes(fat+thin+thin)
            self.assertEqual(signing.binary_type(path), 6)
            path.write_bytes(fat+thin+thin[:12]+struct.pack('<I', 2)+thin[16:])
            with self.assertRaisesRegex(ValueError, 'Inconsistent'):
                signing.binary_type(path)

    def test_ad_hoc_development_or_wrong_team_identity_is_rejected(self):
        fingerprint = 'A'*40; team = 'A1B2C3D4E5'
        with self.assertRaises(ValueError):
            signing.validate_identity('-', team)
        with patch.object(signing, 'capture') as command:
            command.return_value.stdout = f'  1) {fingerprint} "Apple Development: Test ({team})"\n'
            with self.assertRaises(ValueError):
                signing.validate_identity(fingerprint, team)
            command.return_value.stdout = f'  1) {fingerprint} "Developer ID Application: Test ({team})"\n'
            signing.validate_identity(fingerprint, team)
            with self.assertRaises(ValueError):
                signing.validate_identity(fingerprint, 'Z9Y8X7W6V5')

    def test_signing_does_not_modify_source_and_requires_new_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); app = app_fixture(root)
            out = root/'existing'; out.mkdir()
            with patch.object(signing.sys, 'platform', 'darwin'), patch.object(signing, 'run') as command:
                with self.assertRaisesRegex(ValueError, 'new output'):
                    signing.prepare(app, out, '-', 'A1B2C3D4E5', None)
                with self.assertRaisesRegex(ValueError, 'inside the source'):
                    signing.prepare(app, app/'output', '-', 'A1B2C3D4E5', None)
                command.assert_not_called()

    def test_notary_accepted_with_issues_still_blocks_candidate(self):
        with tempfile.TemporaryDirectory() as folder:
            evidence = Path(folder); identifier = '12345678-1234-1234-1234-123456789abc'
            def fake_run(*args, **kwargs):
                if args[2] == 'log':
                    Path(args[-1]).write_text(json.dumps({'status': 'Accepted', 'issues': [{'severity': 'warning'}]}))
                return subprocess.CompletedProcess(args, 0, json.dumps({'status': 'Accepted'}), '')
            with patch.object(signing, 'capture', return_value=subprocess.CompletedProcess([], 0, json.dumps({'id': identifier}), '')):
                with patch.object(signing, 'run', side_effect=fake_run):
                    with self.assertRaisesRegex(ValueError, 'issues'):
                        signing.notarize(evidence/'upload.zip', 'test-profile', evidence, 'app')
            self.assertEqual(json.loads((evidence/'app-submission.json').read_text())['id'], identifier)

    @unittest.skipUnless(sys.platform == 'darwin', 'requires actual Apple code-signing tools')
    def test_native_framework_normalization_and_recursive_signature(self):
        # A real compiled framework with wheel-style duplicated Resources.
        # Ad-hoc evidence validates layout/sealing, not Developer ID or notarization.
        with tempfile.TemporaryDirectory(suffix='.noindex') as folder:
            app = app_fixture(Path(folder)); framework = framework_fixture(app)
            source = Path(folder)/'fixture.c'; source.write_text('int fixture(void) { return 42; }\n')
            subprocess.run(['xcrun', 'clang', '-dynamiclib', str(source), '-o', str(framework/'Versions/A/QtCore')], check=True)
            signing.normalize_frameworks(app)
            subprocess.run(['codesign', '--force', '--sign', '-', str(framework)], check=True)
            subprocess.run(['codesign', '--verify', '--deep', '--strict', str(framework)], check=True)


if __name__ == '__main__':
    unittest.main()
