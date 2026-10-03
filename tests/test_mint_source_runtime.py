# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Explicit Mint contract/refusal tests; no VM, native execution or install claims."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


runtime=load('linux-python-runtime')
distribution=load('linux_distribution')
debian=load('package-debian')
setup=load('setup-complete')
POLICY=ROOT/'release/linuxmint22.3-python-source-qt-voice.json'


class MintContractTests(unittest.TestCase):
    def setUp(self):
        self.value=runtime.policy(POLICY)

    def test_distinct_identity_preserves_exact_noble_built_inputs(self):
        noble=runtime.policy(ROOT/'release/ubuntu24.04-python-source-qt-voice.json')
        self.assertEqual(self.value['wheels'],noble['wheels'])
        self.assertEqual(self.value['sourceQt'],noble['sourceQt'])
        self.assertEqual(runtime.identity(noble),'2976a17cdfaee164cb01a7ce5f6e16afd5688403c48cc275cf2e7d68b1ad1c01')
        self.assertEqual(runtime.identity(self.value),'1288cb482b8db727b8cdf349a97cbcd4473a44fe6945862a1ac141d4a8b86c9a')
        changed=copy.deepcopy(self.value);changed['sourceQt']['manifestSha256']='0'*64
        self.assertNotEqual(runtime.identity(changed),runtime.identity(self.value))

    def test_only_exact_mint_host_is_selected(self):
        self.assertEqual(distribution.host_target({'ID':'linuxmint','VERSION_ID':'22.3','ID_LIKE':'ubuntu debian'},'x86_64'),distribution.MINT)
        for version in ('22','22.0','22.1','22.2','23'):
            with self.subTest(version=version),self.assertRaises(ValueError):
                distribution.host_target({'ID':'linuxmint','VERSION_ID':version},'x86_64')
        with self.assertRaises(ValueError):distribution.host_target({'ID':'linuxmint','VERSION_ID':'22.3'},'aarch64')

    def test_source_runtime_host_refuses_cross_target_before_python(self):
        noble=runtime.policy(ROOT/'release/ubuntu24.04-python-source-qt-voice.json')
        for value,release in ((self.value,'ID=ubuntu\nVERSION_ID=24.04\n'),
                              (self.value,'ID=linuxmint\nVERSION_ID=22.2\n'),
                              (noble,'ID=linuxmint\nVERSION_ID=22.3\n')):
            with patch.object(runtime.Path,'read_text',return_value=release),patch.object(runtime.subprocess,'check_output') as python:
                with self.assertRaisesRegex(ValueError,'runtime policy requires'):runtime.host(value)
                python.assert_not_called()

    def test_mint_contract_requires_source_payload_and_false_review_gates(self):
        contract=runtime.contract(self.value,runtime.digest(POLICY))
        self.assertEqual(distribution.python_runtime_contract({'pythonRuntime':contract},distribution.MINT),contract)
        for key,wrong in (('profile',runtime.SOURCE_PROFILE),('target',distribution.NOBLE),
                          ('pythonAbi',[3,13]),('sourceQt',{}),('licenseReviewComplete',True),
                          ('embeddedSourceCoverageComplete',True)):
            bad={**contract,key:wrong}
            with self.subTest(key=key),self.assertRaises(ValueError):
                distribution.python_runtime_contract({'pythonRuntime':bad},distribution.MINT)
        with self.assertRaises(ValueError):distribution.python_runtime_contract({},distribution.MINT)

    def test_mint_policy_cannot_substitute_vendor_wheel_or_claim_qualification(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'policy.json'
            for key,wrong in (('qualified',True),('licenseReviewComplete',True),('embeddedSourceCoverageComplete',True),
                              ('profile','mint222-cp312-x86_64-source-qt-voice'),('target',distribution.NOBLE)):
                bad=copy.deepcopy(self.value);bad[key]=wrong;path.write_text(json.dumps(bad))
                with self.subTest(key=key),self.assertRaises(ValueError):runtime.policy(path)
            bad=copy.deepcopy(self.value);bad['wheels'][0]['name']='PySide6-Essentials';path.write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError,'complete reviewed'):runtime.policy(path)

    def test_mint_requires_source_recipe_before_build_or_legacy_pip(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(debian.subprocess,'run') as run:
            out=Path(folder)/'out'
            with self.assertRaisesRegex(ValueError,'explicit source Qt'):debian.build(out,distribution.MINT)
            with self.assertRaisesRegex(ValueError,'seven-wheel'):debian.build(out,distribution.MINT,source_qt=True)
            with self.assertRaisesRegex(ValueError,'required Python runtime policy'):
                setup.prepare_python(Path(folder),Path(folder)/'data',distribution.MINT)
            run.assert_not_called();self.assertFalse(out.exists())
        deps,_=debian.dependencies(distribution.MINT,'0.2.13',source_qt=True)
        for name in ('python3.12-venv','libicu74','python3-gst-1.0','gir1.2-gst-plugins-base-1.0','gir1.2-secret-1'):
            self.assertIn(name,deps.split(', '))
        self.assertNotIn('python3-pyside6',deps);self.assertNotIn('python3-keyring',deps)

    def hook(self,component):
        return (ROOT/'release/debian-maintainer.py').read_text().replace('@COMPONENT@',component).replace('@HOOK@','preinst').replace('@VERSION@','0.2.13').replace('@TARGET@',distribution.MINT)

    def test_both_preinst_components_refuse_other_hosts_before_writes(self):
        for component in ('runtime','desktop'):
            source=self.hook(component)
            for release,machine in (('ID=ubuntu\nVERSION_ID=24.04\n','x86_64'),
                                    ('ID=linuxmint\nVERSION_ID=22.2\n','x86_64'),
                                    ('ID=linuxmint\nVERSION_ID=22.3\n','aarch64')):
                with self.subTest(component=component,release=release,machine=machine),\
                        patch.object(Path,'read_text',return_value=release),patch.object(Path,'mkdir') as mkdir,\
                        patch('platform.machine',return_value=machine),patch('sys.argv',['preinst','install']):
                    with self.assertRaisesRegex(SystemExit,'requires Linux Mint 22.3'):
                        exec(compile(source,'mint-preinst','exec'),{})
                    mkdir.assert_not_called()

    def test_same_version_desktop_refuses_cross_target_runtime_before_lease(self):
        source=self.hook('desktop')
        def read(path,*args,**kwargs):
            return 'ID=linuxmint\nVERSION_ID=22.3\n' if str(path)=='/etc/os-release' else json.dumps({'version':'0.2.13','target':distribution.NOBLE})
        with patch.object(Path,'read_text',read),patch.object(Path,'mkdir'),patch.object(Path,'is_symlink',return_value=False),\
                patch.object(Path,'is_dir',return_value=True),patch.object(Path,'is_file',return_value=True),\
                patch.object(Path,'stat',return_value=SimpleNamespace(st_uid=0,st_mode=0o755)),\
                patch('platform.machine',return_value='x86_64'),patch('sys.argv',['preinst','install']),patch.object(os,'open') as opened:
            with self.assertRaisesRegex(SystemExit,'matching Augmentor runtime'):
                exec(compile(source,'mint-desktop-preinst','exec'),{})
            opened.assert_not_called()

    def test_source_input_verification_occurs_before_runtime_creation(self):
        with patch.object(runtime,'verify_wheels'),patch.object(runtime,'source_qt') as qt,patch.object(runtime,'host') as host:
            qt.return_value.inputs.side_effect=ValueError('native input changed')
            with tempfile.TemporaryDirectory() as folder:
                store=Path(folder)/'store'
                with self.assertRaisesRegex(ValueError,'native input changed'):
                    runtime.prepare(self.value,Path(folder),store)
                self.assertFalse(store.exists())
            host.assert_not_called();qt.return_value.inputs.assert_called_once()

    def test_builder_cannot_stamp_mint_target_on_a_noble_policy(self):
        noble=runtime.policy(ROOT/'release/ubuntu24.04-python-source-qt-voice.json')
        with patch.object(debian.importlib.util,'spec_from_file_location'),\
                patch.object(debian.importlib.util,'module_from_spec') as module,\
                patch.object(debian.subprocess,'run') as run:
            tool=module.return_value
            tool.runtime.policy.return_value=noble
            with tempfile.TemporaryDirectory() as folder:
                out=Path(folder)/'out'
                with self.assertRaisesRegex(ValueError,'differs from the package target'):
                    debian.build(out,distribution.MINT,Path(folder),source_qt=True)
                self.assertFalse(out.exists())
            tool.runtime.verify_wheels.assert_not_called();run.assert_not_called()

    def test_mint_environment_selects_only_reviewed_native_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            app=Path(folder)/'app';app.mkdir();(app/'linux-python-runtime.json').write_bytes(POLICY.read_bytes())
            python=str(Path(folder)/'runtime/bin/python3')
            with patch.object(runtime,'resolve',return_value=python):
                env=runtime.environment(app,python,{'DISPLAY':':17','QT_PLUGIN_PATH':'/foreign','QT_QPA_PLATFORMTHEME':'foreign'})
                self.assertEqual(env['DISPLAY'],':17')
                self.assertEqual(env['QT_PLUGIN_PATH'],str(Path(folder)/'runtime/qt/plugins'))
                self.assertEqual(env['QML_IMPORT_PATH'],str(Path(folder)/'runtime/qt/qml'))
                self.assertNotIn('QT_QPA_PLATFORMTHEME',env)
                with self.assertRaisesRegex(ValueError,'preload/audit'):
                    runtime.environment(app,python,{'LD_AUDIT':'/foreign'})

    def test_mint_inventory_keeps_source_payload_and_skips_vendor_icu73_claim(self):
        inventory=load('linux-wheel-inventory')
        pins={row['name']:row for row in json.loads((ROOT/'release/native-sources.json').read_text())['sources']}
        with tempfile.TemporaryDirectory() as folder:
            app=Path(folder)
            for name,directory,record in [('pyside-setup','pyside-6.8.2.1','provenance.json')]+[
                    (name,name+'-6.8.2','collection.json') for name in
                    ('qtbase','qtsvg','qtimageformats','qtdeclarative','qttools','qtquicktimeline','qtwayland')]:
                base=app/'licenses'/directory;base.mkdir(parents=True)
                (base/record).write_text(json.dumps({'commit':pins[name]['commit'],'files':[]}))
            with patch.object(inventory,'inventory',return_value=({},{})),patch.object(inventory.runtime,'source_qt') as qt:
                qt.return_value.inputs.return_value={'synthetic':True}
                report=inventory.stage(self.value,app,app)
                self.assertEqual(report['sourceQt']['contract'],self.value['sourceQt'])
                self.assertIn(distribution.MINT,report['sourceQt']['systemIcu'])
                self.assertFalse(report['sourceQt']['compiledContentNoticeMappingComplete'])
                self.assertNotIn('icu4c',{row['component'] for row in report['supplementaryNoticeCollections']})


if __name__=='__main__':unittest.main()
