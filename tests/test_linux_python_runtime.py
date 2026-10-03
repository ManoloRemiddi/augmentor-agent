# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('linux_python_runtime', ROOT/'scripts/linux-python-runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.home = Path(self.folder.name)
        self.value = runtime.policy(ROOT/'release/ubuntu24.04-python.json')

    def test_new_profiles_require_their_own_target_abi_and_complete_modules(self):
        for file in ('opensuse-leap16.0-python-voice.json','arch20261001-python-voice.json'):
            value=runtime.policy(ROOT/'release'/file)
            self.assertNotIn('pyside6-essentials',{runtime.normalized(row['name']) for row in value['wheels']})
            for key,wrong in (('target','ubuntu24.04-amd64'),('pythonAbi',[3,12]),('python','/usr/bin/python3.12')):
                changed=copy.deepcopy(value);changed[key]=wrong
                path=self.home/'invalid.json';path.write_text(json.dumps(changed))
                with self.subTest(file=file,key=key),self.assertRaisesRegex(ValueError,'Unsupported'):runtime.policy(path)
            changed=copy.deepcopy(value);changed['wheels'].pop();path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'complete reviewed wheel set'):runtime.policy(path)

    def test_new_host_profiles_refuse_a_derivative_or_wrong_release_before_python(self):
        for file,os_release in (('opensuse-leap16.0-python-voice.json','ID=opensuse-tumbleweed\nVERSION_ID=20261001\n'),
                                ('arch20261001-python-voice.json','ID=manjaro\n')):
            value=runtime.policy(ROOT/'release'/file)
            with patch.object(runtime.Path,'read_text',return_value=os_release),patch.object(runtime.subprocess,'check_output') as python:
                with self.assertRaisesRegex(ValueError,'runtime policy requires'):runtime.host(value)
                python.assert_not_called()

    def receipt(self):
        root = self.home/'runtime'
        root.mkdir(mode=0o700)
        (root/'pyvenv.cfg').write_text('include-system-site-packages = true\n')
        files = runtime.inventory(root)
        receipt = {'format': 'augmentor-linux-python-runtime/1', 'root': str(root),
                   'python': str(root/'bin/python3'), 'target': self.value['target'],
                   'profile': self.value['profile'], 'wheels': self.value['wheels'],
                   'lockIdentity': runtime.identity(self.value), 'files': files,
                   'artifactSha256': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()}
        (root/runtime.RECEIPT).write_text(json.dumps(receipt))
        return root, receipt

    def test_bad_wheel_cannot_create_runtime_store_or_execute_python(self):
        wheelhouse = self.home/'wheels'
        wheelhouse.mkdir()
        (wheelhouse/self.value['wheels'][0]['file']).write_bytes(b'corrupt wheel')
        with patch.object(runtime, 'host') as host, patch.object(runtime.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'checksum/size'):
                runtime.prepare(self.value, wheelhouse, self.home/'store')
        host.assert_not_called()
        run.assert_not_called()
        self.assertFalse((self.home/'store').exists())

    def test_symlinked_wheel_is_refused_even_with_matching_content(self):
        row = self.value['wheels'][0]
        payload = self.home/'payload'
        payload.write_bytes(b'fixture')
        row.update(bytes=7, sha256=runtime.digest(payload))
        wheels = self.home/'wheels'
        wheels.mkdir()
        (wheels/row['file']).symlink_to(payload)
        with self.assertRaisesRegex(ValueError, 'checksum/size'):
            runtime.verify_wheels(self.value, wheels)

    def test_abi_mismatch_is_refused_before_environment_creation(self):
        with patch.object(runtime.Path, 'read_text', return_value='ID=ubuntu\nVERSION_ID="24.04"\n'), \
                patch.object(runtime.platform, 'machine', return_value='x86_64'), \
                patch.object(runtime.subprocess, 'check_output', return_value='[3,13]'):
            with self.assertRaisesRegex(ValueError, 'ABI differs'):
                runtime.host(self.value)

    def test_changed_file_is_refused_before_running_its_interpreter(self):
        root, _ = self.receipt()
        (root/'pyvenv.cfg').write_text('changed')
        with patch.object(runtime, 'probe') as probe:
            with self.assertRaisesRegex(ValueError, 'files changed'):
                runtime.verify(self.value, root)
        probe.assert_not_called()

    def test_receipt_cannot_move_to_another_path(self):
        root, _ = self.receipt()
        moved = self.home/'moved'
        root.rename(moved)
        with patch.object(runtime, 'probe') as probe:
            with self.assertRaisesRegex(ValueError, 'path or wheel contract'):
                runtime.verify(self.value, moved)
        probe.assert_not_called()

    def test_symlinked_receipt_is_refused(self):
        root, _ = self.receipt()
        saved = self.home/'receipt'
        (root/runtime.RECEIPT).rename(saved)
        (root/runtime.RECEIPT).symlink_to(saved)
        with self.assertRaisesRegex(ValueError, 'receipt identity'):
            runtime.verify(self.value, root)

    def test_artifact_digest_is_checked(self):
        root, receipt = self.receipt()
        receipt['artifactSha256'] = '0'*64
        (root/runtime.RECEIPT).write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, 'files changed'):
            runtime.verify(self.value, root)

    def test_partial_prior_environment_is_preserved_and_not_repaired(self):
        store = self.home/'store'
        store.mkdir(mode=0o700)
        root = store/(self.value['profile']+'-'+runtime.identity(self.value)[:16])
        root.mkdir(mode=0o700)
        sentinel = root/'retained'
        sentinel.write_text('previous attempt')
        with patch.object(runtime, 'verify_wheels'), patch.object(runtime, 'host'), \
                patch.object(runtime.os, 'geteuid', return_value=1001), \
                patch.object(runtime.subprocess, 'run') as run:
            with self.assertRaises(FileNotFoundError):
                runtime.prepare(self.value, self.home/'wheels', store)
        run.assert_not_called()
        self.assertEqual(sentinel.read_text(), 'previous attempt')

    def test_runtime_identity_changes_for_wheel_changes_not_research_metadata(self):
        other = copy.deepcopy(self.value)
        other['wheels'][0]['metadataSha256'] = '1'*64
        self.assertEqual(runtime.identity(other), runtime.identity(self.value))
        other['wheels'][0]['sha256'] = '1'*64
        self.assertNotEqual(runtime.identity(other), runtime.identity(self.value))

    def test_declared_artifact_cannot_fall_back_to_another_interpreter(self):
        app=self.home/'app';app.mkdir()
        (app/runtime.POLICY_FILE).write_text(json.dumps(self.value))
        with patch.object(runtime,'verify') as verify:
            with self.assertRaisesRegex(ValueError,'does not match'):
                runtime.resolve(app,'/usr/bin/python3')
        verify.assert_not_called()

    def test_artifact_selects_its_own_profile_instead_of_prior_selection(self):
        app=self.home/'app';app.mkdir()
        (app/runtime.POLICY_FILE).write_text(json.dumps(self.value))
        with patch.dict(runtime.os.environ,{'XDG_DATA_HOME':str(self.home/'data')}),patch.object(runtime,'verify') as verify:
            chosen=runtime.resolve(app)
        expected=self.home/'data/augmentor/python-runtimes'/(self.value['profile']+'-'+runtime.identity(self.value)[:16])
        self.assertEqual(chosen,str(expected/'bin/python3'))
        verify.assert_called_once_with(self.value,expected)

    def test_broken_policy_symlink_cannot_be_treated_as_absent(self):
        (self.home/runtime.POLICY_FILE).symlink_to(self.home/'missing')
        with self.assertRaisesRegex(ValueError,'regular artifact'):
            runtime.resolve(self.home)


if __name__ == '__main__':
    unittest.main()
