# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Authored profiles/SDK manifests; actual filesystem transaction, mocked network."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services'))
from dsh import setup
locate_cli=setup.cli_directory


@unittest.skipUnless(sys.platform=='linux','Modern setup is MX/Linux first')
class ModernSetupTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='authored-dsh-setup-',dir=os.environ.get('AUGMENTOR_BUILD_WORKSPACE'))
        self.addCleanup(temporary.cleanup);self.base=Path(temporary.name)
        self.home=self.base/'home';self.profile=self.home/'profiles/web';self.profile.mkdir(parents=True)
        self.composition=self.profile/'cordis.patch.yml'
        self.original='# Keep authored custom configuration exactly.\n- id: authored-custom\n  name: authored-custom\n  config:\n    off: off\n    expression: !!js "ctx.get(\'authored-only\')"\n'
        self.composition.write_text(self.original)
        self.configuration=self.base/'harnesses.json'
        self.cli=self.base/'cli';self.cli.mkdir();self.modules=self.cli/'node_modules'
        self.write_family(setup.MODERN_DSH)
        self.remote=Mock()
        self.remote.call.side_effect=lambda method,*args:{'catalogContract':setup.CATALOG_CONTRACT,'version':None} if method=='host.describe' else {'items':[]} if method=='session.list' else {'presets':[]}
        for item in [patch.object(setup,'cli_directory',return_value=self.cli),patch.object(setup,'remote_client',return_value=self.remote),patch.object(setup,'http',return_value={}),patch.object(setup,'configuration',return_value=self.configuration),patch.object(setup,'existing_prompt_plugin',return_value=None)]:
            item.start();self.addCleanup(item.stop)
        self.tool=setup.Setup()

    def write_family(self,family):
        (self.cli/'package.json').write_text(json.dumps({'name':'@deepseek-ai/dsh','version':family}))
        required={'dsh-base':family,'dsh-tools':family,'schemastery':'3.18.4' if family==setup.MODERN_DSH else '3.18.2'}
        if family==setup.MODERN_DSH:required.update({'cordis':'4.0.4','dsh-agent-preset':family,'dsh-agent-preset-registry':family})
        for name,version in required.items():
            directory=self.modules/'@deepseek-ai'/name;directory.mkdir(parents=True,exist_ok=True)
            (directory/'package.json').write_text(json.dumps({'name':'@deepseek-ai/'+name,'version':version}))

    def check(self):
        return self.tool.check({'endpoint':'http://127.0.0.1:3080','home':str(self.home)})['token']

    def install(self):
        return self.tool.install(self.check())

    def additions(self):
        line=next(line for line in self.composition.read_text().splitlines() if line.startswith('- insert: '))
        return json.loads(line[len('- insert: '):])

    def snapshot(self):
        return {str(p.relative_to(self.home)):p.read_bytes() for p in self.home.rglob('*') if p.is_file() and not p.is_symlink()}

    def test_modern_install_registers_both_presets_and_preserves_custom_text(self):
        before=self.composition.read_bytes();result=self.install();self.assertTrue(result['restartRequired'])
        self.assertTrue(self.composition.read_bytes().startswith(before))
        rows=self.additions();presets=[row for row in rows if row['id'].startswith('augmentor-preset-')]
        self.assertEqual({row['config']['id'] for row in presets},set(setup.PRESETS.values()))
        self.assertEqual(len(presets),2)
        for row in presets:
            self.assertEqual(row['name'],str(self.modules/'@deepseek-ai/dsh-agent-preset/lib/index.js'))
            entries=row['config']['plugins'];delegation=next(p for p in entries if p['id']=='delegation')['config']
            self.assertTrue(any(p['id']=='workflow-ptc' and p['name']=='@deepseek-ai/dsh-workflow-ptc' for p in delegation))
            self.assertFalse(any(p['id']=='workflow-worker-thread' for p in delegation))
            self.assertTrue(any(p['id']=='tool-ralph' and not p.get('disabled') for p in delegation))
            self.assertTrue({'augmentor-memory','augmentor-desktop','augmentor-execution'} <= {p['id'] for p in entries})
        token=(self.home/'augmentor-product-token').read_bytes();self.install();self.assertEqual((self.home/'augmentor-product-token').read_bytes(),token)
        self.assertEqual(self.composition.read_text().count('- insert: '),1)
        self.assertTrue(self.composition.read_bytes().startswith(before));self.assertFalse(self.configuration.exists())

    def test_owned_legacy_upgrade_adds_modern_declarations_without_rewriting_custom_rows(self):
        self.write_family(setup.LEGACY_DSH);self.install()
        self.assertFalse(any(p['id'].startswith('augmentor-preset-') for p in self.additions()))
        legacy=setup.personal_agent_entries();self.assertTrue(any(p['id']=='workflow-worker-thread' for p in next(p for p in legacy if p['id']=='delegation')['config']))
        token=(self.home/'augmentor-product-token').read_bytes();self.write_family(setup.MODERN_DSH);self.install()
        self.assertEqual(len([p for p in self.additions() if p['id'].startswith('augmentor-preset-')]),2)
        self.assertTrue(self.composition.read_text().startswith(self.original));self.assertEqual((self.home/'augmentor-product-token').read_bytes(),token)

    def test_mixed_or_changed_sdk_family_refuses_before_profile_writes(self):
        before=self.snapshot();token=self.check()
        (self.modules/'@deepseek-ai/schemastery/package.json').write_text('{"version":"3.18.2"}')
        with self.assertRaisesRegex(ValueError,'dependency family'):self.tool.install(token)
        self.assertEqual(self.snapshot(),before)
        with self.assertRaises(ValueError):self.check()

    def test_edited_peer_metadata_and_composition_remain_protected(self):
        self.install();package=self.profile/'augmentor-product/browser/package.json';original=package.read_bytes()
        value=json.loads(original);value['peerDependencies']['authored-edit']='KEEP';package.write_text(json.dumps(value))
        before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'files were edited'):self.install()
        self.assertEqual(self.snapshot(),before)
        package.write_bytes(original);self.composition.write_text(self.composition.read_text().replace('- insert: ','- insert:  ',1));before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'composition entry was edited'):self.install()
        self.assertEqual(self.snapshot(),before)

    def test_preserved_ownership_requires_deliberate_migration_not_standard_overwrite(self):
        self.install();path=self.profile/'augmentor-product/ownership.json';value=json.loads(path.read_text());value['schema']='augmentor-dsh-preserved-ownership/1';path.write_text(json.dumps(value));before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'preserved integration requires a reviewed migration'):self.install()
        self.assertEqual(self.snapshot(),before)

    def test_existing_prompt_library_is_not_duplicated(self):
        with patch.object(setup,'existing_prompt_plugin',return_value='authored-existing-library'):
            self.install()
        self.assertNotIn('augmentor-product-prompts',{row['id'] for row in self.additions()})
        self.assertEqual(len([r for r in self.additions() if r['id'].startswith('augmentor-preset-')]),2)

    def test_failure_restores_previous_owned_files_and_preset_bytes(self):
        self.install();before=self.snapshot();atomic=setup.atomic
        def fail(path,value):
            if Path(path).name=='ownership.json':raise OSError('Authored interrupted modern installation')
            return atomic(path,value)
        with patch.object(setup,'atomic',side_effect=fail):
            with self.assertRaisesRegex(OSError,'Authored interrupted'):self.install()
        after=self.snapshot()
        for name,value in before.items():self.assertEqual(after[name],value,name)
        self.assertEqual(self.composition.read_text().count('- insert: '),1)

    def test_explicit_modern_cli_and_missing_registry_are_checked_before_writes(self):
        binary=self.cli/'lib/bin.js';binary.parent.mkdir();binary.write_text('// Authored CLI identity only; never executed.\n')
        with patch.dict(os.environ,{'AUGMENTOR_DSH_CLI':str(binary)}):
            self.assertEqual(locate_cli(),self.cli.resolve())
            self.assertEqual(setup.cli_family(binary),setup.MODERN_DSH)
            self.assertEqual(setup.modules_directory(binary)[0],self.modules)
        before=self.snapshot();(self.modules/'@deepseek-ai/dsh-agent-preset-registry/package.json').unlink()
        with self.assertRaisesRegex(ValueError,'dependency family'):self.check()
        self.assertEqual(self.snapshot(),before)

    def test_modern_cli_is_not_implicitly_qualified_for_other_platforms(self):
        for platform in ['darwin','win32']:
            with self.subTest(platform=platform),patch.object(setup.sys,'platform',platform):
                with self.assertRaisesRegex(ValueError,'only on Linux'):setup.cli_family(self.cli)


if __name__=='__main__':unittest.main()
