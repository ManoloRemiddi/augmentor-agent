# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Drift/refusal boundaries; synthetic tests do not qualify a real distro."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('linux_system_qt', ROOT/'scripts/linux-system-qt.py')
stack = importlib.util.module_from_spec(spec); spec.loader.exec_module(stack)
spec = importlib.util.spec_from_file_location('system_qt_runtime', ROOT/'scripts/linux-python-runtime.py')
runtime = importlib.util.module_from_spec(spec); spec.loader.exec_module(runtime)


class SystemQtTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(); self.addCleanup(folder.cleanup)
        self.home = Path(folder.name)
        self.value = runtime.policy(ROOT/'release/arch20261001-python-voice.json')
        self.path = self.home/stack.MANIFEST
        self.expected = stack.manifest(self.value, ROOT/'release/system-qt/arch20261002-inventory.json')

    def manifest(self, value=None):
        data = json.dumps(self.expected if value is None else value).encode()
        self.path.write_bytes(data)
        self.value['systemQtStack'].update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        return self.path

    def test_both_published_candidates_bind_registered_stack_and_exclude_release_claims(self):
        for label, file in [('arch', 'arch20261001-python-voice.json'), ('leap', 'opensuse-leap16.0-python-voice.json')]:
            value = runtime.policy(ROOT/'release'/file)
            data = stack.manifest(value, ROOT/'release/system-qt'/(label+'20261002-inventory.json'))
            self.assertFalse(data['completeDependencyClosure'])
            self.assertFalse(data['wholeDistroSnapshotQualified'])
            self.assertFalse(data['dependencyMaintenanceQualified'])
            self.assertFalse(data['publicReleaseQualified'])
            self.assertIn(value['python'], data['members'])

    def test_missing_or_cross_target_contract_is_refused(self):
        for change in ('missing', 'target', 'manager', 'qt', 'file', 'size'):
            value = copy.deepcopy(self.value)
            if change == 'missing': value.pop('systemQtStack')
            elif change == 'target': value['target'] = 'opensuse-leap16.0-x86_64'
            else:
                field = {'manager':'packageManager', 'qt':'qtVersion', 'file':'file', 'size':'bytes'}[change]
                value['systemQtStack'][field] = 0 if change == 'size' else 'invalid'
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'exact distro'):
                stack.contract(value)
        vendor = runtime.policy(ROOT/'release/ubuntu24.04-python.json')
        vendor['systemQtStack'] = self.value['systemQtStack']
        with self.assertRaisesRegex(ValueError, 'cannot declare'): stack.contract(vendor)

    def test_changed_manifest_symlink_and_hardlink_refuse_before_package_queries(self):
        self.manifest()
        original = self.path.read_bytes()
        self.path.write_bytes(original[:-1]+b'x')
        with self.assertRaisesRegex(ValueError, 'checksum'): stack.manifest(self.value, self.path)
        self.path.write_bytes(original)
        os.link(self.path, self.home/'shared')
        with self.assertRaisesRegex(ValueError, 'size/type'): stack.manifest(self.value, self.path)
        (self.home/'shared').unlink()
        self.path.rename(self.home/'saved'); self.path.symlink_to(self.home/'saved')
        with self.assertRaisesRegex(ValueError, 'size/type'): stack.manifest(self.value, self.path)

    def test_manifest_cannot_redirect_to_outside_scope_or_claim_snapshot_qualification(self):
        for path in ('/tmp/QtCore.so', '/usr/lib/../outside', '/usr/lib//double', 'usr/lib/relative'):
            changed = copy.deepcopy(self.expected); changed['members'][path] = {'type':'file'}
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'Unsafe'):
                stack.manifest(self.value, self.manifest(changed))
        changed = copy.deepcopy(self.expected); changed['wholeDistroSnapshotQualified'] = True
        with self.assertRaisesRegex(ValueError, 'candidate contract'):
            stack.manifest(self.value, self.manifest(changed))

    def test_registered_version_drift_refuses_before_reading_or_executing_python(self):
        self.manifest()
        changed = dict(self.expected['packages'], python='3.14.8-1')
        with patch.object(stack, 'packages', return_value=changed), patch.object(stack, 'listed') as listed, patch.object(stack, 'member') as member:
            with self.assertRaisesRegex(ValueError, 'versions changed'): stack.verify(self.value, self.path)
        listed.assert_not_called(); member.assert_not_called()

    def test_changed_package_file_set_and_same_version_different_bytes_are_refused(self):
        self.manifest()
        paths = sorted(self.expected['members'])
        with patch.object(stack, 'packages', return_value=self.expected['packages']), patch.object(stack, 'listed', return_value=paths[:-1]), patch.object(stack, 'member') as member:
            with self.assertRaisesRegex(ValueError, 'inventory changed'): stack.verify(self.value, self.path)
        member.assert_not_called()
        records = lambda path: dict(self.expected['members'][str(path)], sha256='0'*64)
        with patch.object(stack, 'packages', return_value=self.expected['packages']), patch.object(stack, 'listed', return_value=paths), patch.object(stack, 'member', side_effect=records):
            with self.assertRaisesRegex(ValueError, 'member changed'): stack.verify(self.value, self.path)

    def test_a_concurrent_package_change_is_refused_after_the_file_walk(self):
        self.manifest()
        changed = dict(self.expected['packages'], python='3.14.8-1')
        with patch.object(stack, 'packages', side_effect=[self.expected['packages'], changed]), patch.object(stack, 'listed', return_value=sorted(self.expected['members'])), patch.object(stack, 'member', side_effect=lambda path:self.expected['members'][str(path)]):
            with self.assertRaisesRegex(ValueError, 'registration changed'): stack.verify(self.value, self.path)

    def test_loader_injection_is_refused_before_the_package_manager_runs(self):
        for name in ('LD_PRELOAD', 'LD_AUDIT', 'LD_LIBRARY_PATH'):
            with self.subTest(name=name), patch.dict(os.environ, {name:'/unreviewed'}), patch.object(stack.subprocess, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'loader override'): stack.packages(stack.ARCH)
                run.assert_not_called()

    def test_special_file_replacement_is_refused_without_a_blocking_open(self):
        for mode in (stat.S_IFIFO, stat.S_IFSOCK, stat.S_IFCHR, stat.S_IFDIR | 0o022):
            info = SimpleNamespace(st_uid=0, st_mode=mode | 0o644)
            with self.subTest(mode=mode), patch.object(stack.Path, 'lstat', return_value=info), patch.object(stack, 'regular') as read:
                with self.assertRaisesRegex(ValueError, 'type or permissions'): stack.member('/usr/lib/synthetic')
                read.assert_not_called()

    def test_system_verification_precedes_the_abi_python_exec(self):
        with patch.object(runtime.Path, 'read_text', return_value='ID=arch\n'), patch.object(runtime.platform, 'machine', return_value='x86_64'), patch.object(runtime, 'system_qt', return_value=stack), patch.object(stack, 'verify', side_effect=ValueError('stack drift')), patch.object(runtime.subprocess, 'check_output') as python:
            with self.assertRaisesRegex(ValueError, 'stack drift'): runtime.host(self.value, self.path)
            python.assert_not_called()

    def test_import_drift_is_refused_without_overwriting_the_prior_receipt(self):
        root = self.home/'runtime'; root.mkdir(mode=0o700)
        (root/'pyvenv.cfg').write_text('synthetic')
        files = runtime.inventory(root)
        imports = {'qtVersion':'6.11.2', 'systemVersions':{'numpy':'2.5.3'}}
        receipt = {'format':'augmentor-linux-python-runtime/1', 'root':str(root), 'python':str(root/'bin/python3'),
            'target':self.value['target'], 'profile':self.value['profile'], 'wheels':self.value['wheels'],
            'lockIdentity':runtime.identity(self.value), 'systemQtStack':self.value['systemQtStack'],
            'imports':imports, 'files':files, 'artifactSha256':hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()}
        path = root/runtime.RECEIPT; path.write_text(json.dumps(receipt)); before = path.read_bytes()
        with patch.object(runtime, 'host'), patch.object(runtime, 'probe', return_value=imports):
            self.assertEqual(runtime.verify(self.value, root), receipt)
        changed = copy.deepcopy(imports); changed['systemVersions']['numpy'] = '2.6.0'
        with patch.object(runtime, 'host'), patch.object(runtime, 'probe', return_value=changed):
            with self.assertRaisesRegex(ValueError, 'imports changed'): runtime.verify(self.value, root)
        self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__': unittest.main()
