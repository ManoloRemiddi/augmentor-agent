# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual owned files/links/backups; synthetic immutable preset generators only."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from updates.linux_registration import RegistrationPlan,generated,HEADER,PRESETS,document
from updates.linux_managed import ManagedPlan,load_deployment
from updates.linux_coordinator import LinuxCoordinator
from lifecycle.posix_startup import Startup
from lifecycle.update_journal import UpdateJournal
from platform_adapters.private_files import atomic_json,read_json,replace_file


@unittest.skipUnless(sys.platform=='linux','Actual Linux private ownership, links and durable migration.')
class RegistrationTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='augmentor-owned-registration-');self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name);self.home=self.base/'home';self.home.mkdir(mode=0o700)
        self.source=self.base/'source';self.target=self.base/'target'
        for root,label in ((self.source,'before'),(self.target,'after')):
            root.mkdir(mode=0o700)
            for path in ('services/dsh','apps/browser/plugin/dist','dsh/node_modules/@deepseek-ai/dsh-tools',
                    'dsh/node_modules/@deepseek-ai/schemastery','node_modules/ws'):
                (root/path).mkdir(parents=True)
            (root/'services/dsh/setup.py').write_text('from pathlib import Path\nROOT=Path(__file__).resolve().parents[2]\n'
                'def personal_agent_entries():\n return [{"id":"persona","config":{"prefix":'+repr(label)+'}},'
                '{"id":"augmentor-memory","name":str(ROOT/"adapters/dsh-memory/index.mjs")}]\n')
            (root/'apps/browser/plugin/dist/index.js').write_bytes(('Inert browser '+label).encode())
            (root/'apps/browser/plugin/package.json').write_text(json.dumps({'fixture':label}))
        self.profile=self.home/'profiles/web';self.owned=self.profile/'augmentor-product'
        self.browser=self.owned/'browser'
        (self.browser/'dist').mkdir(parents=True)
        (self.browser/'node_modules/@deepseek-ai').mkdir(parents=True)
        self.owned.chmod(0o700)
        files={}
        for relative in ('browser/dist/index.js','browser/package.json'):
            path=self.owned/relative;raw=(self.source/('apps/browser/plugin/'+relative.removeprefix('browser/'))).read_bytes()
            path.write_bytes(raw);files[relative]=hashlib.sha256(raw).hexdigest()
        self.patch_rows=[{'id':'augmentor-product','name':str(self.source/'adapters/dsh-product/index.mjs')},
            {'id':'augmentor-product-browser','name':str(self.browser/'dist/index.js'),
             'config':{'agentPreset':PRESETS[1],'chatDir':str(self.source/'private-chat-choice'),'deleteAfterDays':0}},
            {'id':'augmentor-product-prompts','name':str(self.source/'adapters/dsh-prompt-library/lib/index.js')}]
        self.entry='- insert: '+json.dumps(self.patch_rows)
        self.other='- insert: [{"id":"unrelated","name":"fixture-other-plugin"}]\n'
        (self.profile/'cordis.patch.yml').write_text('# Preserve this host comment.\n'+self.other+self.entry+'\n')
        presets={}
        for name in PRESETS:
            directory=self.home/'.agent-presets'/name;directory.mkdir(parents=True,mode=0o700)
            meta={'name':'Augmentor '+('Linux' if name==PRESETS[0] else 'Browser'),'description':'Augmentor product integration 1.0.0'}
            (directory/'preset.yml').write_text(HEADER+json.dumps(meta)+'\n')
            (directory/'agent.cordis.yml').write_text(HEADER+json.dumps(generated(self.source),indent=2)+'\n')
            presets[name]={file:hashlib.sha256((directory/file).read_bytes()).hexdigest() for file in ('preset.yml','agent.cordis.yml')}
        self.ownership={'version':'1.0.0','files':files,'presets':presets,'patchEntry':self.entry}
        atomic_json(self.owned/'ownership.json',self.ownership)
        (self.profile/'node_modules').symlink_to(self.source/'dsh/node_modules',target_is_directory=True)
        for name in ('dsh-tools','schemastery'):
            (self.browser/('node_modules/@deepseek-ai/'+name)).symlink_to(self.source/('dsh/node_modules/@deepseek-ai/'+name),target_is_directory=True)
        (self.browser/'node_modules/ws').symlink_to(self.source/'node_modules/ws',target_is_directory=True)
        self.sentinels={'settings.yaml':b'fixture model choice and context',
            'augmentor-product-token':b'fixture identity must survive','conversation.json':b'fixture saved conversation',
            'voice.json':b'fixture GPU and speech choices'}
        for name,raw in self.sentinels.items():(self.home/name).write_bytes(raw)
        self.runtime=self.base/'runtime';self.transactions=self.base/'transactions'
        self.runtime.mkdir(mode=0o700);self.transactions.mkdir(mode=0o700)
        self.before={'version':'1.0.0','sourceCommit':'a'*40,'target':'linux-x64','channel':'preview',
            'sha256':'b'*64,'dataSchema':1,'readableDataSchemas':[1]}
        self.after={**self.before,'version':'2.0.0','sourceCommit':'c'*40,'sha256':'d'*64}

    def plan(self,*,bind=True):
        result=RegistrationPlan(self.home,self.source,self.target,'1.0.0','2.0.0')
        if bind:result.bind_artifacts(self.before,self.after)
        return result

    def intent(self,journal):
        for phase in ('preparing','prepared','drained','installer-ready','apply-intent'):journal.advance(phase)

    def sentinels_preserved(self):
        for name,raw in self.sentinels.items():self.assertEqual((self.home/name).read_bytes(),raw)

    def test_live_migration_updates_only_owned_code_and_keeps_models_tokens_chats_and_other_patch(self):
        plan=self.plan()
        self.assertEqual((self.profile/'cordis.patch.yml').read_text(),'# Preserve this host comment.\n'+self.other+self.entry+'\n')
        with UpdateJournal(self.transactions,self.before,self.after) as journal,Startup(
                self.runtime,maintenance=True,transactions=self.transactions) as gate:
            self.intent(journal);plan.apply(gate,journal)
            self.assertTrue(plan.verify_applied())
            updated=read_json(self.owned/'ownership.json');self.assertEqual(updated['version'],'2.0.0')
            rows=json.loads(updated['patchEntry'].removeprefix('- insert: '))
            self.assertEqual(rows[0]['name'],str(self.target/'adapters/dsh-product/index.mjs'))
            self.assertEqual(rows[1]['config'],self.patch_rows[1]['config'])
            self.assertIn(self.other,(self.profile/'cordis.patch.yml').read_text())
            for name in PRESETS:
                self.assertEqual(document((self.home/'.agent-presets'/name/'agent.cordis.yml').read_bytes()),generated(self.target))
            self.assertEqual(os.readlink(self.profile/'node_modules'),str(self.target/'dsh/node_modules'))
            self.assertEqual(os.readlink(self.browser/'node_modules/ws'),str(self.target/'node_modules/ws'))
            with self.assertRaisesRegex(ValueError,'cannot be retried'):plan.apply(gate,journal)
        self.sentinels_preserved()

    def test_edited_preset_or_browser_registration_refuses_before_any_mutation(self):
        path=self.home/'.agent-presets'/PRESETS[0]/'agent.cordis.yml';before=path.read_bytes()
        path.write_bytes(before+b'User edit.')
        with self.assertRaisesRegex(ValueError,'preset was edited'):self.plan()
        path.write_bytes(before)
        (self.browser/'dist/index.js').write_bytes(b'User browser change.')
        with self.assertRaisesRegex(ValueError,'browser integration was edited'):self.plan()
        self.assertFalse(any(self.transactions.iterdir()));self.sentinels_preserved()

    def test_custom_preset_cannot_be_hidden_by_changing_ownership_hash(self):
        path=self.home/'.agent-presets'/PRESETS[0]/'agent.cordis.yml'
        path.write_text(HEADER+json.dumps([{'id':'custom','name':'preserve-user-plugin'}])+'\n')
        owned=read_json(self.owned/'ownership.json')
        owned['presets'][PRESETS[0]]['agent.cordis.yml']=hashlib.sha256(path.read_bytes()).hexdigest()
        atomic_json(self.owned/'ownership.json',owned)
        with self.assertRaisesRegex(ValueError,'original immutable defaults'):self.plan()
        self.sentinels_preserved()

    def test_redirected_module_link_and_ambiguous_patch_refuse_before_apply(self):
        link=self.browser/'node_modules/ws';link.unlink();link.symlink_to(self.base/'unrelated')
        with self.assertRaisesRegex(ValueError,'module link differs'):self.plan()
        link.unlink();link.symlink_to(self.source/'node_modules/ws')
        with (self.profile/'cordis.patch.yml').open('a') as stream:stream.write('# Quoted '+self.entry+'\n')
        with self.assertRaisesRegex(ValueError,'composition entry changed'):self.plan()

    def test_changed_after_preflight_refuses_live_apply_and_keeps_pending(self):
        plan=self.plan();path=self.profile/'cordis.patch.yml'
        path.write_text(path.read_text()+'# Later user edit.\n')
        with UpdateJournal(self.transactions,self.before,self.after) as journal,Startup(
                self.runtime,maintenance=True,transactions=self.transactions) as gate:
            self.intent(journal)
            with self.assertRaisesRegex(ValueError,'changed after'):plan.apply(gate,journal)
            self.assertFalse(plan.begun);self.assertEqual(journal.record['phase'],'apply-intent')
        self.sentinels_preserved()

    def test_another_release_pair_cannot_authorize_registration_writes(self):
        plan=self.plan();other={**self.after,'sha256':'e'*64}
        with UpdateJournal(self.transactions,self.before,other) as journal,Startup(
                self.runtime,maintenance=True,transactions=self.transactions) as gate:
            self.intent(journal)
            with self.assertRaisesRegex(ValueError,'exact bound'):plan.apply(gate,journal)
            self.assertFalse(plan.begun);self.assertIsNone(plan.backup)
            self.assertEqual((self.profile/'cordis.patch.yml').read_text(),
                '# Preserve this host comment.\n'+self.other+self.entry+'\n')
        self.sentinels_preserved()

    def test_lost_namespace_ack_preserves_backups_and_never_retries_or_rolls_back(self):
        plan=self.plan();replace=replace_file
        def uncertain(source,target):
            replace(source,target)
            if Path(target)==plan.files[0]['path']:raise OSError('Synthetic post-replace flush failure.')
        with UpdateJournal(self.transactions,self.before,self.after) as journal,Startup(
                self.runtime,maintenance=True,transactions=self.transactions) as gate:
            self.intent(journal)
            with patch('updates.linux_registration.replace_file',side_effect=uncertain):
                with self.assertRaisesRegex(OSError,'post-replace'):plan.apply(gate,journal)
            self.assertTrue(plan.begun);self.assertFalse(plan.applied)
            self.assertTrue((plan.backup/'manifest.json').exists())
            self.assertEqual((plan.backup/'0.before').read_bytes(),plan.files[0]['before'])
            self.assertEqual(plan.files[0]['path'].read_bytes(),plan.files[0]['after'])
            with self.assertRaisesRegex(ValueError,'cannot be retried'):plan.apply(gate,journal)
        self.assertTrue((self.transactions/'active.json').exists());self.sentinels_preserved()

    def test_changed_backup_or_applied_profile_cannot_complete(self):
        plan=self.plan()
        with UpdateJournal(self.transactions,self.before,self.after) as journal,Startup(
                self.runtime,maintenance=True,transactions=self.transactions) as gate:
            self.intent(journal);plan.apply(gate,journal)
            (plan.backup/'0.before').write_bytes(b'Damaged original backup.')
            with self.assertRaisesRegex(ValueError,'backup changed'):plan.verify_applied()
            (plan.backup/'0.before').write_bytes(plan.files[0]['before'])
            plan.files[0]['path'].write_bytes(b'Later edited registration.')
            with self.assertRaisesRegex(ValueError,'changed after'):plan.verify_applied()
        self.sentinels_preserved()

    def test_version_change_composes_source_compatibility_registration_pointer_and_original_completion(self):
        data=self.base/'data';data.mkdir(mode=0o700);tool=load_deployment(data);tool.check=Mock()
        configs=[]
        for root,version,commit in ((self.source,'1.0.0','a'*40),(self.target,'2.0.0','c'*40)):
            (root/'apps/native/augmentor_linux').mkdir(parents=True)
            (root/'apps/native/augmentor_linux/window.py').write_text('--ensure-running')
            (root/'release').mkdir()
            product={'version':version,'channel':'preview','protocols':{'product':'augmentor/1'},
                'dataSchema':1,'readableDataSchemas':[1]}
            (root/'release/product.json').write_text(json.dumps(product))
            (root/'release.json').write_text(json.dumps({**product,'target':'linux-x64','sourceCommit':commit,
                'component':'desktop','update':{'build':1,'automaticInstallQualified':False}}))
            files=tool.inventory(root);digest=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
            config={'root':str(root),'python':sys.executable,'node':'/usr/bin/node','dshService':'fixture-owned.service',
                'dshHome':str(self.home),'dshEndpoint':'http://127.0.0.1:1','version':version,
                'releaseId':'fixture-'+version,'sourceRef':commit,'artifactSha256':digest}
            tool.atomic(root/'desktop-release.json',{'deployment':config,'files':files,'artifactSha256':digest})
            configs.append(config)
        atomic_json(data/'desktop.json',configs[0]);registration=self.plan(bind=False)
        with patch('updates.linux_managed.load_deployment',return_value=tool),patch(
                'updates.linux_completion.verify_health',return_value=True):
            with ManagedPlan(data,self.source,self.target,development=True,registration=registration) as plan:
                # The old live integration is checked with its original version;
                # the future target gets offline imports before any shutdown.
                self.assertEqual(tool.check.call_args_list[0].args[0],configs[0])
                self.assertEqual(tool.check.call_args_list[0].kwargs,{'connected':True})
                self.assertEqual(tool.check.call_args_list[1].args[0],configs[1])
                self.assertEqual(tool.check.call_args_list[1].kwargs,{'connected':False})
                result=LinuxCoordinator(plan,self.runtime,self.runtime/'shared',self.transactions).run(lambda stage:True)
                self.assertTrue(result['installationComplete']);self.assertTrue(registration.verify_applied())
                self.assertEqual(read_json(data/'desktop.json'),configs[1])
                self.assertEqual(read_json(data/'desktop.previous.json'),configs[0])
                self.assertEqual(read_json(Path(result['archive']))['phase'],'complete')
                self.assertFalse((self.transactions/'active.json').exists())
        self.sentinels_preserved()
