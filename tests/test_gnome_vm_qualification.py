# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Qualification must not adopt another artifact, target or interpreter."""
import importlib.util
import json
import sys
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

spec=importlib.util.spec_from_file_location('vm_qualification',Path(__file__).resolve().parents[1]/'release/gnome-vm-qualification.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
SOURCE='a'*40
TOKEN='d'*64


@unittest.skipUnless(sys.platform.startswith('linux'),'Owned GNOME qualification uses Linux guest paths and file guards.')
class ProofJournalTests(unittest.TestCase):
    def test_guest_restore_rejects_stale_same_source_before_session_or_native_settings_access(self):
        spec=importlib.util.spec_from_file_location('guest_shortcut_proof',Path(__file__).resolve().parents[1]/'release/noble-gnome-shortcut-session.py')
        guest=importlib.util.module_from_spec(spec);spec.loader.exec_module(guest)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'journal.json';saved={'source':SOURCE,'proofToken':TOKEN}
            module.create_journal(path,saved,SOURCE,TOKEN);before=path.read_bytes()
            argv=['guest-proof','restore','--target','fedora44','--source',SOURCE,'--proof-token','e'*64]
            contract={'root':'/usr/lib/augmentor','selection':{},'python':sys.executable}
            loader=SimpleNamespace(exec_module=Mock())
            with patch.object(guest,'STATE',path),patch.object(sys,'argv',argv),\
                 patch.object(module,'verified_profile',return_value=contract),\
                 patch.object(guest.importlib.util,'spec_from_file_location',return_value=SimpleNamespace(loader=loader)),\
                 patch.object(guest.importlib.util,'module_from_spec',return_value=module),\
                 patch.object(guest,'command',side_effect=AssertionError('No session/native access permitted')) as session:
                with self.assertRaisesRegex(ValueError,'another run'):guest.main()
                session.assert_not_called()
            self.assertEqual(path.read_bytes(),before)

    def test_stale_same_source_other_run_refuses_read_write_and_new_adoption(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'journal.json';saved={'source':SOURCE,'proofToken':TOKEN,'registeredAfter':['foreign']}
            module.create_journal(path,saved,SOURCE,TOKEN);before=path.read_bytes()
            with self.assertRaisesRegex(ValueError,'already exists'):module.require_new_journal(path)
            with self.assertRaisesRegex(ValueError,'another run'):module.read_journal(path,SOURCE,'e'*64)
            replacement={**saved,'proofToken':'e'*64,'registeredAfter':[]}
            with self.assertRaisesRegex(ValueError,'another run'):module.write_journal(path,replacement,SOURCE,'e'*64)
            with self.assertRaises(FileExistsError):module.create_journal(path,replacement,SOURCE,'e'*64)
            self.assertEqual(path.read_bytes(),before)

    def test_other_source_refuses_even_with_the_current_token(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'journal.json';saved={'source':SOURCE,'proofToken':TOKEN}
            module.create_journal(path,saved,SOURCE,TOKEN);before=path.read_bytes()
            with self.assertRaisesRegex(ValueError,'another run or source'):module.read_journal(path,'b'*40,TOKEN)
            with self.assertRaisesRegex(ValueError,'another run or source'):
                module.write_journal(path,{**saved,'source':'b'*40},'b'*40,TOKEN)
            self.assertEqual(path.read_bytes(),before)

    def test_interrupted_exact_run_can_read_and_update_its_retained_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'journal.json';saved={'source':SOURCE,'proofToken':TOKEN,'registeredAfter':[]}
            module.create_journal(path,saved,SOURCE,TOKEN)
            # A new process with the retained receipt can recover the same run.
            recovered=module.read_journal(path,SOURCE,TOKEN)
            recovered['registeredAfter']=['owned-main','owned-secondary','foreign']
            module.write_journal(path,recovered,SOURCE,TOKEN)
            self.assertEqual(module.read_journal(path,SOURCE,TOKEN),recovered)
            self.assertEqual(path.stat().st_mode&0o777,0o600)

    def test_missing_token_legacy_journal_and_symlinks_are_not_adopted(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'journal.json';path.write_text(json.dumps({'source':SOURCE}));path.chmod(0o600)
            with self.assertRaisesRegex(ValueError,'another run'):module.read_journal(path,SOURCE,TOKEN)
            link=Path(directory)/'link.json';link.symlink_to(path)
            with self.assertRaises(OSError):module.read_journal(link,SOURCE,TOKEN)
            with self.assertRaisesRegex(ValueError,'already exists'):module.require_new_journal(link)
            with self.assertRaisesRegex(ValueError,'one-run proof token'):module.proof_identity(SOURCE,'short')


@unittest.skipUnless(sys.platform.startswith('linux'),'Owned GNOME qualification uses Linux guest paths and file guards.')
class SelectedArtifactTests(unittest.TestCase):
    def test_guest_profile_requires_exact_owner_marker_os_and_security_before_selection(self):
        for target in module.PROFILES:
            profile=module.PROFILES[target]
            def read(path):
                if str(path)=='/etc/augmentor-test-vm':return profile['marker']
                if str(path)=='/etc/os-release':return 'ID='+profile['os'][0]+'\nVERSION_ID="'+profile['os'][1]+'"\n'
                if str(path)=='/sys/module/apparmor/parameters/enabled':return 'Y\n'
                raise AssertionError(str(path))
            answers={'hostname':profile['hostname'],'systemd-detect-virt':'qemu',
                     'getenforce':'Enforcing','systemctl':'active','dpkg':''}
            with self.subTest(target=target),patch.object(module.os,'geteuid',return_value=1000),\
                 patch.dict(module.os.environ,{'USER':'augmentor-proof'},clear=True),\
                 patch.object(Path,'read_text',read),\
                 patch.object(module,'output',side_effect=lambda argv:answers[argv[0]]),\
                 patch.object(module.subprocess,'run') as rpm,\
                 patch.object(module,'verify_selection',return_value={'verified':True}) as selected:
                self.assertEqual(module.verified_profile(target,SOURCE),{'verified':True})
                selected.assert_called_once_with(Path.home()/'.local/share/augmentor',target,SOURCE)
                if target=='fedora44':rpm.assert_called_once_with(['rpm','-V','augmentor-agent'],check=True,timeout=30)

    def test_foreign_user_or_loader_override_refuses_before_selected_code(self):
        with patch.object(module.os,'geteuid',return_value=0),patch.object(module,'verify_selection') as selected:
            with self.assertRaisesRegex(ValueError,'marked ordinary-user'):module.verified_profile('fedora44',SOURCE)
            selected.assert_not_called()
        profile=module.PROFILES['fedora44']
        with patch.object(module.os,'geteuid',return_value=1000),\
             patch.dict(module.os.environ,{'USER':'augmentor-proof','LD_PRELOAD':'foreign.so'},clear=True),\
             patch.object(Path,'read_text',return_value=profile['marker']),\
             patch.object(module,'output',side_effect=[profile['hostname'],'qemu']),\
             patch.object(module,'verify_selection') as selected:
            with self.assertRaisesRegex(ValueError,'loader overrides'):module.verified_profile('fedora44',SOURCE)
            selected.assert_not_called()

    def fixture(self, directory, target):
        data=Path(directory)/'augmentor';root=data/'releases'/'owned';root.mkdir(parents=True)
        selection={'root':str(root),'python':'/usr/bin/python3' if target=='fedora44' else str(data/'python-runtimes/selected/bin/python3'),
                   'sourceRef':SOURCE,'artifactSha256':'b'*64}
        (data/'desktop.json').write_text(json.dumps(selection))
        release={'source':{'commit':SOURCE,'dirty':False},'target':module.PROFILES[target]['target']}
        (root/'release.json').write_text(json.dumps(release))
        deployment=SimpleNamespace(verify=Mock(return_value={'artifactSha256':'b'*64}))
        runtime=SimpleNamespace(resolve=Mock(return_value=selection['python']))
        return data,root,selection,deployment,runtime

    def test_both_targets_use_the_verified_selected_root_not_a_cached_python_file(self):
        for target in module.PROFILES:
            with self.subTest(target=target),tempfile.TemporaryDirectory() as directory:
                data,root,selection,deployment,runtime=self.fixture(directory,target)
                (data/'selected-python.txt').write_text('/wrong/old/python')
                with patch.object(module,'load',side_effect=lambda p,n:deployment if n.endswith('deployment') else runtime):
                    result=module.verify_selection(data,target,SOURCE)
                self.assertEqual(result['python'],selection['python']);self.assertEqual(result['root'],str(root))
                self.assertTrue(result['managedInventoryVerified']);deployment.verify.assert_called_once_with(root)

    def test_source_target_artifact_hash_and_runtime_mismatch_refuse(self):
        for corruption in ('source','target','hash','runtime'):
            with self.subTest(corruption=corruption),tempfile.TemporaryDirectory() as directory:
                data,root,selection,deployment,runtime=self.fixture(directory,'ubuntu24')
                release=json.loads((root/'release.json').read_text())
                if corruption=='source':release['source']['dirty']=True
                if corruption=='target':release['target']='fedora44-x86_64'
                if corruption=='hash':deployment.verify.return_value={'artifactSha256':'c'*64}
                if corruption=='runtime':runtime.resolve.return_value='/old/python'
                (root/'release.json').write_text(json.dumps(release))
                with patch.object(module,'load',side_effect=lambda p,n:deployment if n.endswith('deployment') else runtime),self.assertRaises(ValueError):
                    module.verify_selection(data,'ubuntu24',SOURCE)

    def test_fedora_refuses_managed_interpreter_and_foreign_runtime_policy(self):
        for policy in (False,True):
            with tempfile.TemporaryDirectory() as directory:
                data,root,selection,deployment,runtime=self.fixture(directory,'fedora44')
                if policy:(root/'linux-python-runtime.json').write_text('{}')
                else:
                    selection['python']='/usr/bin/python3.12';(data/'desktop.json').write_text(json.dumps(selection))
                with patch.object(module,'load',return_value=deployment),self.assertRaisesRegex(ValueError,'native system'):
                    module.verify_selection(data,'fedora44',SOURCE)

    def test_relative_and_escaped_managed_roots_refuse_before_installed_code(self):
        for value in ('relative/root','/tmp/foreign-release'):
            with tempfile.TemporaryDirectory() as directory:
                data,root,selection,deployment,runtime=self.fixture(directory,'ubuntu24')
                selection['root']=value;(data/'desktop.json').write_text(json.dumps(selection))
                with patch.object(module,'load') as load,self.assertRaises(ValueError):
                    module.verify_selection(data,'ubuntu24',SOURCE)
                load.assert_not_called()
