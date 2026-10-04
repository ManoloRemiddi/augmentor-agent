# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('coordinated', Path(__file__).resolve().parents[1]/'release/prove-published-linux-coordinated-version.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class AdmissionTests(unittest.TestCase):
    def binding(self, mode='upgrade'):
        version = '0.2.13' if mode == 'upgrade' else '0.2.12'
        return {'format': 'augmentor-published-coordinated-binding/1', 'mode': mode, 'proofSha256': 'proof', 'createdAt': 100,
                'baselineRunSha256': module.BASELINE_RUN_SHA, 'baselineEndingAuditSha256': module.BASELINE_ENDING_SHA,
                'nativeAuditSha256': 'a'*64, 'upgradeRunSha256': 'b'*64,
                'packageTransaction': {'phase': 'pass', 'exitCode': 0, 'pending': None, 'unknownOutcome': False,
                    'versions': {'augmentor-runtime': version, 'augmentor-desktop': version},
                    'addedDependencies': sorted(module.NEW_DEPENDENCIES) if mode=='upgrade' else [],
                    'removedPackages': [], 'unrelatedPackageChanges': False, 'receiptSha256': 'c'*64},
                'nativeAudit': {'status': 'pass', 'version': version, 'source': module.SOURCES[version], 'pending': None,
                                'unknownOutcome': False, 'leasesIdle': True, 'processesAbsent': True, 'socketAbsent': True, 'portsIdle': True}}

    def test_exact_known_baseline_and_phase(self):
        self.assertEqual(module.binding_identity(self.binding(), 'upgrade', 'proof', 120), '0.2.13')
        self.assertEqual(module.binding_identity(self.binding('rollback'), 'rollback', 'proof', 120), '0.2.12')

    def test_stale_foreign_missing_or_unknown_binding_refuses(self):
        cases = [{'createdAt': -1000}, {'createdAt': 121}, {'proofSha256': 'wrong'}, {'mode': 'rollback'},
                 {'baselineRunSha256': '0'*64}, {'baselineEndingAuditSha256': '0'*64}, {'nativeAuditSha256': ''}]
        for change in cases:
            with self.subTest(change=change), self.assertRaises(ValueError):
                module.binding_identity({**self.binding(), **change}, 'upgrade', 'proof', 120)
        for change in [{'unknownOutcome': True}, {'pending': 'APT'}, {'version': '0.2.12'}, {'source': 'other'},
                       {'leasesIdle': False}, {'processesAbsent': False}, {'portsIdle': False}, {'socketAbsent': False}]:
            binding = self.binding(); binding['nativeAudit'].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                module.binding_identity(binding, 'upgrade', 'proof', 120)

    def test_rollback_requires_exact_prior_upgrade_identity(self):
        binding = self.binding('rollback'); binding.pop('upgradeRunSha256')
        with self.assertRaises(ValueError): module.binding_identity(binding, 'rollback', 'proof', 120)

    def test_package_transaction_unknown_nonzero_or_extra_package_refuses(self):
        for change in [{'phase':'pending'},{'exitCode':1},{'unknownOutcome':True},{'pending':'APT'},
                       {'receiptSha256':''},{'unrelatedPackageChanges':True},{'removedPackages':['foreign']},
                       {'versions':{'augmentor-runtime':'0.2.12','augmentor-desktop':'0.2.13'}},
                       {'addedDependencies':sorted(module.NEW_DEPENDENCIES)+['foreign']}, {'addedDependencies':[]}]:
            binding=self.binding();binding['packageTransaction'].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):module.binding_identity(binding,'upgrade','proof',120)

    def test_known_prior_does_not_adopt_unknown_pending_or_failed(self):
        good = {'phase': 'pass', 'unknownOutcome': False, 'pendingRequest': None, 'pendingLifecycle': None, 'pendingDeployment': None}
        module.known_pass(good)
        for key, value in [('phase', 'failed-do-not-resume'), ('unknownOutcome', True), ('pendingRequest', 'request'),
                           ('pendingLifecycle', 'stop'), ('pendingDeployment', 'activate'), ('pendingAction', 'install')]:
            with self.subTest(key=key), self.assertRaises(ValueError): module.known_pass({**good, key: value})

    def test_registered_native_cohort_refuses_mixed_version_or_changed_bytes(self):
        good = lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout='0.2.13' if _args[0][0]=='dpkg-query' else '', stderr='')
        module.native_audit('0.2.13', good)
        for result in [SimpleNamespace(returncode=1, stdout='', stderr=''), SimpleNamespace(returncode=0, stdout='changed', stderr='')]:
            invoke = Mock(return_value=result)
            with self.subTest(result=result), self.assertRaises(ValueError): module.native_audit('0.2.13', invoke)


class MutationAndSettingsTests(unittest.TestCase):
    def test_install_intent_is_durable_before_normal_api(self):
        with tempfile.TemporaryDirectory() as name:
            folder=Path(name); saved=[]; record={'pendingAction': None}
            base=SimpleNamespace(atomic=lambda _path, value: saved.append(copy.deepcopy(value)))
            def invoke():
                self.assertEqual(saved[-1]['pendingAction'], 'normal-setup-install')
                return {'installed': True}
            self.assertEqual(module.action(base, folder, record, 'normal-setup-install', invoke), {'installed': True})
            self.assertIsNone(saved[-1]['pendingAction'])
            with self.assertRaises(ValueError): module.action(base, folder, record, 'normal-setup-install', invoke)

    def test_unknown_normal_install_remains_pending_and_is_never_replayed(self):
        record={'pendingAction': None}; base=SimpleNamespace(atomic=Mock()); invoke=Mock(side_effect=TimeoutError('unknown'))
        with self.assertRaises(TimeoutError): module.action(base, Path('/synthetic'), record, 'normal-setup-install', invoke)
        self.assertEqual(record['pendingAction'], 'normal-setup-install')
        with self.assertRaises(ValueError): module.action(base, Path('/synthetic'), record, 'normal-setup-save', invoke)
        invoke.assert_called_once()

    def test_save_version_only_and_preserves_managed_and_other_settings(self):
        before={'dsh': {'version': '0.2.12', 'endpoint': 'loopback', 'home': 'fixture', 'managed': {'service': 'fixture'}}, 'unrelated': {'x': 1}}
        after=copy.deepcopy(before); after['dsh']['version']='0.2.13'; module.saved_transition(before, after, '0.2.13')
        for key, value in [('managed', None), ('endpoint', 'other'), ('home', 'other')]:
            changed=copy.deepcopy(after); changed['dsh'][key]=value
            with self.subTest(key=key), self.assertRaises(ValueError): module.saved_transition(before, changed, '0.2.13')
        changed=copy.deepcopy(after); changed['unrelated']['x']=2
        with self.assertRaises(ValueError): module.saved_transition(before, changed, '0.2.13')

    def test_only_two_intended_setting_files_may_change(self):
        before={module.HARNESS:'old', module.SELECTOR:'old', 'provider':'exact', 'installation':'exact'}
        module.preserve_settings(before, {**before,module.HARNESS:'new',module.SELECTOR:'new'})
        with self.assertRaises(ValueError): module.preserve_settings(before, {**before,'provider':'changed'})
        with self.assertRaises(ValueError): module.preserve_settings(before, {k:v for k,v in before.items() if k!='installation'})

    def test_save_refuses_foreign_format_normalization_and_preserves_exact_layout(self):
        document={'unrelated':{'keep':'exact'},'dsh':{'endpoint':'fixture','version':'0.2.12','managed':{'service':'fixture'}}}
        original=(json.dumps(document,indent=2)+'\n').encode();expected=copy.deepcopy(document);expected['dsh']['version']='0.2.13'
        self.assertEqual(module.saved_bytes(original,'0.2.13'),(json.dumps(expected,indent=2)+'\n').encode())
        with self.assertRaises(ValueError):module.saved_bytes(json.dumps(document).encode(),'0.2.13')

    def test_staged_candidate_cannot_change_endpoint_python_or_service(self):
        prior={'root':'/old','node':'/old/node/bin/node','version':'0.2.12','sourceRef':module.SOURCES['0.2.12'],
               'artifactSha256':'old','releaseId':'old','python':'/known/python','dshEndpoint':'loopback','dshHome':'fixture','dshService':'known'}
        root=Path('/new');chosen={**prior,'root':str(root),'node':str(root/'node/bin/node'),'version':'0.2.13',
                                  'sourceRef':module.SOURCES['0.2.13'],'artifactSha256':'new','releaseId':'new'}
        module.candidate_identity(chosen,prior,root,'0.2.13')
        for key in ['python','dshEndpoint','dshHome','dshService','root','node','sourceRef']:
            with self.subTest(key=key),self.assertRaises(ValueError):module.candidate_identity({**chosen,key:'foreign'},prior,root,'0.2.13')


class RealProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); self.home=self.root/'dsh-home'
        self.profile=self.home/'profiles/web'; self.target=self.profile/'augmentor-product'; self.presets=self.home/'.agent-presets'; self.app=self.root/'native'
        self.profile.mkdir(parents=True); self.presets.mkdir(); self.app.mkdir()
        (self.profile/'foreign.yml').write_text('foreign exact\n')
        (self.presets/'foreign').mkdir(); (self.presets/'foreign/preset.yml').write_text('foreign preset\n')
        self.generate('0.2.12', '- insert: [{"id":"old-product","name":"old"}]')
        self.before=module.integration_snapshot(self.home, '0.2.12')

    def tearDown(self): self.temp.cleanup()

    def generate(self, version, entry):
        plugin=self.target/'browser'; (plugin/'dist').mkdir(parents=True)
        source=self.app/'apps/browser/plugin'; (source/'dist').mkdir(parents=True,exist_ok=True)
        for path, text in [('dist/index.js','plugin '+version),('package.json','{"version":"'+version+'"}')]:
            (source/path).write_text(text); shutil.copy2(source/path, plugin/path)
        owned={'version':version,'files':{},'presets':{},'patchEntry':entry}
        for path in ['browser/dist/index.js','browser/package.json']:
            owned['files'][path]=hashlib.sha256((self.target/path).read_bytes()).hexdigest()
        for name in module.PRESETS:
            (self.presets/name).mkdir(exist_ok=True); owned['presets'][name]={}
            for filename in ['preset.yml','agent.cordis.yml']:
                file=self.presets/name/filename; file.write_text(filename+' '+version+'\n')
                owned['presets'][name][filename]=hashlib.sha256(file.read_bytes()).hexdigest()
        (self.target/'ownership.json').write_text(json.dumps(owned))
        (self.profile/'cordis.patch.yml').write_text('foreign expression\n'+entry+'\n')

    def upgrade(self):
        backup=self.profile/('augmentor-product.before-'+'a'*32); self.target.rename(backup)
        for name in module.PRESETS:
            (backup/'presets'/name).mkdir(parents=True)
            for filename in ['preset.yml','agent.cordis.yml']:
                (backup/'presets'/name/filename).write_text((self.presets/name/filename).read_text())
        shutil.copy2(self.profile/'cordis.patch.yml',self.profile/('cordis.patch.yml.before-augmentor-'+'b'*32))
        entry='- insert: '+json.dumps([{'id':'augmentor-product','name':str(self.app/'adapters/dsh-product/index.mjs')}])
        self.generate('0.2.13', entry)
        return backup

    def test_normal_backup_and_foreign_content_preserved(self):
        self.upgrade(); after=module.integration_snapshot(self.home,'0.2.13',self.app)
        module.integration_preserved(self.before,after)

    def test_foreign_expression_and_file_edits_refuse(self):
        self.upgrade()
        (self.profile/'foreign.yml').write_text('changed')
        with self.assertRaises(ValueError):module.integration_preserved(self.before,module.integration_snapshot(self.home,'0.2.13',self.app))

    def test_foreign_preset_deletion_refuses(self):
        self.upgrade(); (self.presets/'foreign/preset.yml').unlink()
        with self.assertRaises(ValueError):module.integration_preserved(self.before,module.integration_snapshot(self.home,'0.2.13',self.app))

    def test_foreign_directory_permission_change_refuses(self):
        self.upgrade();(self.presets/'foreign').chmod(0o700)
        with self.assertRaises(ValueError):module.integration_preserved(self.before,module.integration_snapshot(self.home,'0.2.13',self.app))

    def test_old_owned_backup_tamper_refuses(self):
        backup=self.upgrade(); (backup/'browser/dist/index.js').write_text('lost old bytes')
        with self.assertRaises(ValueError):module.integration_preserved(self.before,module.integration_snapshot(self.home,'0.2.13',self.app))

    def test_new_unknown_backup_member_refuses(self):
        backup=self.upgrade(); (backup/'unexpected').write_text('unexpected')
        with self.assertRaises(ValueError):module.integration_preserved(self.before,module.integration_snapshot(self.home,'0.2.13',self.app))

    def test_self_consistent_owned_plugin_from_foreign_root_refuses(self):
        self.upgrade(); owned=json.loads((self.target/'ownership.json').read_text())
        (self.target/'browser/dist/index.js').write_text('foreign'); owned['files']['browser/dist/index.js']=hashlib.sha256(b'foreign').hexdigest()
        (self.target/'ownership.json').write_text(json.dumps(owned))
        with self.assertRaises(ValueError):module.integration_snapshot(self.home,'0.2.13',self.app)

    def test_duplicate_patch_or_edited_owned_preset_refuses_before_mutation(self):
        patch=self.profile/'cordis.patch.yml'; patch.write_text(patch.read_text()+self.before['owned']['patchEntry'])
        with self.assertRaises(ValueError):module.integration_snapshot(self.home,'0.2.12')

    def test_regular_hardlink_and_linked_snapshot_root_refuse(self):
        file=self.profile/'foreign.yml'; os.link(file,self.profile/'hardlink')
        with self.assertRaises(ValueError):module.tree(self.profile)
        alias=self.root/'alias'; alias.symlink_to(self.profile, target_is_directory=True)
        with self.assertRaises(ValueError):module.tree(alias)


if __name__=='__main__': unittest.main()
