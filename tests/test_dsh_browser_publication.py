# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Authored extension code, real SQLite/review binding and real child exits."""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from unittest.mock import patch

from test_dsh_review_publication import ReviewPublicationFixture
from dsh import browser_code_publication as browser
from dsh import client_publication as publication
from dsh import preservation_transaction as tx
from dsh import cold_backup as archives
from dsh import shared_data_adoption as data


class BrowserPublicationFixture(ReviewPublicationFixture):
    def setUp(self):
        super().setUp()
        self.code=self.deployment/'browser/0.2.11'
        self.incoming_code=self.incoming/'apps/browser/extension'
        self.browser_stage=self.base/'browser-recovery'
        manifest={'manifest_version':3,'key':'AUTHORED_INDEPENDENT_KEY','name':'Authored Browser',
                  'version':'0.2.11','permissions':['nativeMessaging','storage'],'host_permissions':['http://127.0.0.1/*']}
        self.write(self.code/'manifest.json',manifest)
        self.write(self.code/'old.js',b'// AUTHORED ORIGINAL CODE KEEP\n');(self.code/'old.js').chmod(0o664)
        self.code.chmod(0o755)
        self.write(self.incoming_code/'manifest.json',dict(manifest,version='0.2.13'))
        self.write(self.incoming_code/'app.mjs',b'// AUTHORED INCOMING CODE\n');(self.incoming_code/'app.mjs').chmod(0o664)
        self.write(self.incoming_code/'icons/authored.svg',b'<svg><!-- AUTHORED --></svg>\n')
        self.write(self.incoming_code/'labels/café-😀.txt',b'AUTHORED UNICODE FILENAME\n')
        self.restage()
        self.code_before=browser.image(self.code)

    def restage(self):
        value=json.loads((self.incoming/'desktop-release.json').read_text());value['files']=tx.deployment.inventory(self.incoming)
        value['artifactSha256']=tx.preserve.sha(json.dumps(value['files'],sort_keys=True).encode());self.artifact=value['artifactSha256']
        self.write(self.incoming/'desktop-release.json',value)
        self.stage_number=getattr(self,'stage_number',0)+1;self.output=self.base/('browser-config-stage-'+str(self.stage_number));self.stage_sha=self.stage()['planSha256']

    def capture(self,guard,include_code=True):
        extra=[{'id':'source-history','path':str(self.source)},
               {'id':'other-selection','path':str(self.other),'members':['desktop.json','desktop.previous.json']},
               {'id':'registry','path':str(self.registry),'members':['reviews.json']}]
        for i,pair in enumerate(getattr(self,'extra_sources',[])):extra.append({'id':'legacy-extra-'+str(i),'path':pair['data']})
        if include_code:extra.append({'id':'browser-code','path':str(self.code)})
        result=archives.capture(self.archive,guard.configuration,extra)
        return {'root':str(self.archive),'sha256':result['backupSha256']}

    def prepare_browser(self,guard,backup):
        result=browser.prepare(self.code,self.incoming,self.artifact,self.browser_stage,backup,guard.configuration)
        self.browser_sha=result['browserCodeSha256'];return {'root':str(self.browser_stage),'sha256':self.browser_sha}

    def prepared(self,guard,*,include_code=True):
        backup=self.capture(guard,include_code)
        self.data_sha=data.prepare([self.other_pair,*getattr(self,'extra_sources',[])],self.adoption,backup,guard.configuration,map_default_person=True)['sharedAdoptionSha256']
        ref=self.prepare_browser(guard,backup)
        config=tx.prepare(self.output,self.stage_sha,self.backup,self.artifact,guard.configuration,cold_backup=backup)
        return publication.prepare(self.backup,config['transactionSha256'],self.publication,guard,self.bootstrap,
            shared_adoption={'root':str(self.adoption),'sha256':self.data_sha},browser_code=ref,
            reviews={'revision':9,'names':['main','pilot']})['publicationSha256']

    def assert_code_original(self):
        self.assertEqual(browser.image(self.code),self.code_before);self.assert_registered_original()

    def assert_code_incoming(self):
        self.assertEqual(json.loads((self.code/'manifest.json').read_text())['version'],'0.2.13')
        self.assertFalse((self.code/'old.js').exists());self.assertEqual((self.code/'app.mjs').read_bytes(),b'// AUTHORED INCOMING CODE\n')
        self.assertEqual((self.code/'app.mjs').stat().st_mode&0o777,0o644)
        self.assertEqual(self.code.stat().st_mode&0o777,0o755)
        self.assertEqual(browser.image(self.browser_stage/'extension'),self.code_before)

    def child(self,digest,action):
        code='''import json,os,sys
from pathlib import Path
from contextlib import contextmanager
from types import SimpleNamespace
sys.path.insert(0,sys.argv[1]);from dsh import client_publication as p
from dsh import preservation_transaction as tx
from dsh import browser_code_publication as b
home,deploy,other,registry,journal=map(Path,sys.argv[2:7]);pairs=json.loads(sys.argv[7]);digest=sys.argv[8];action=sys.argv[9]
@contextmanager
def fake(directory,digest,guard,*args):
 tx.inspect(directory,digest,guard)
 yield SimpleNamespace(preflight=lambda:{'productVersion':'0.2.13','homeIdentityMatches':True},native_adapter_preflight=lambda _:{'candidateNativeAdapterMatched':True}),None
p.probes.backend_probe=fake
with p.maintenance(home,deploy,pairs,[other],review_registry=registry) as guard:
 if action=='finalize':
  p.apply(journal,digest,guard,os.environ,home)
  original=Path.unlink
  def unlink(path,*args,**kwargs):
   original(path,*args,**kwargs)
   if path==deploy/tx.shared.PRESERVATION_FENCE:os._exit(86)
  Path.unlink=unlink
  p.finalize(journal,digest,guard,os.environ,home)
 else:
  original=b.exchange
  def die(*args):original(*args);os._exit(83)
  b.exchange=die
  if action=='apply':p.apply(journal,digest,guard,os.environ,home)
  else:p.rollback(journal,digest,guard)
'''
        return subprocess.run([sys.executable,'-I','-B','-c',code,str(tx.ROOT/'services'),str(self.home),str(self.deployment),str(self.other),str(self.registry),str(self.publication),json.dumps([self.pair,self.other_pair]),digest,action],capture_output=True,text=True)


class BrowserPublicationTests(BrowserPublicationFixture):
    def test_one_cut_publishes_code_data_reviews_and_selectors_then_reverses_exactly(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard);self.assert_code_original();self.apply(digest,guard)
            self.assert_code_incoming();self.assert_registry_rebound();self.assert_merged()
            result=publication.rollback(self.publication,digest,guard);self.assertTrue(result['browserCodeRestored'])
        self.assert_code_original()

    def test_preparation_is_offline_keeps_original_code_and_normalizes_only_incoming_write_modes(self):
        with self.full_guard() as guard:
            backup=self.capture(guard)
            with patch.object(publication.review,'Owner',side_effect=AssertionError('No owner during code preparation')):
                self.prepare_browser(guard,backup)
            self.assert_code_original();self.assertEqual((self.browser_stage/'extension/app.mjs').stat().st_mode&0o777,0o644)
            self.assertEqual((self.code/'old.js').stat().st_mode&0o777,0o664)
            with self.assertRaisesRegex(ValueError,'matching client publication|matching publication'):
                browser.commit(self.browser_stage,self.browser_sha,guard.configuration)

    def test_whole_original_code_coverage_is_required(self):
        with self.full_guard() as guard:
            backup=self.capture(guard,include_code=False)
            with self.assertRaisesRegex(ValueError,'complete existing Browser code'):self.prepare_browser(guard,backup)
            self.assertFalse(self.browser_stage.exists());self.assert_code_original()

    def test_a_prepared_publication_cannot_authorize_standalone_code_mutation(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard)
            for fn in (browser.commit,browser.rollback,browser.release):
                with self.subTest(fn=fn.__name__),self.assertRaises(ValueError):fn(self.browser_stage,self.browser_sha,guard.configuration)
            with publication.configuration_owner(self.publication,digest,json.loads((self.publication/'publication.json').read_text()),guard):
                with self.assertRaisesRegex(ValueError,'durable intent'):browser.commit(self.browser_stage,self.browser_sha,guard.configuration)
            self.assert_code_original();publication.rollback(self.publication,digest,guard)

    def test_unknown_code_edit_before_apply_is_preserved_before_data_or_config_changes(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard);path=self.code/'old.js';raw=path.read_bytes();path.write_bytes(b'AUTHORED FOREIGN EDIT KEEP')
            with self.assertRaisesRegex(ValueError,'code or its recovery slot changed'):self.apply(digest,guard)
            self.assertEqual(path.read_bytes(),b'AUTHORED FOREIGN EDIT KEEP');self.assert_original()
            path.write_bytes(raw);publication.rollback(self.publication,digest,guard)
        self.assert_code_original()

    def test_unknown_recovery_slot_edit_blocks_reverse_without_losing_new_code(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard);self.apply(digest,guard);path=self.browser_stage/'extension/old.js';raw=path.read_bytes();path.write_bytes(b'AUTHORED FOREIGN SLOT KEEP')
            with self.assertRaisesRegex(ValueError,'code or its recovery slot changed'):publication.rollback(self.publication,digest,guard)
            self.assertEqual(path.read_bytes(),b'AUTHORED FOREIGN SLOT KEEP');self.assertEqual((self.code/'app.mjs').read_bytes(),b'// AUTHORED INCOMING CODE\n')
            path.write_bytes(raw);publication.rollback(self.publication,digest,guard)
        self.assert_code_original()

    def test_replacement_with_identical_bytes_has_a_foreign_identity_and_is_preserved(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard);kept=self.code.with_name('kept-original');self.code.rename(kept);shutil.copytree(kept,self.code)
            with self.assertRaisesRegex(ValueError,'code or its recovery slot changed'):self.apply(digest,guard)
            self.assertTrue((kept/'old.js').is_file());shutil.rmtree(self.code);kept.rename(self.code)
            publication.rollback(self.publication,digest,guard)
        self.assert_code_original()

    def test_identity_change_is_not_a_browser_update(self):
        path=self.incoming_code/'manifest.json';value=json.loads(path.read_text());value['key']='AUTHORED OTHER ID';self.write(path,value);self.restage()
        with self.full_guard() as guard:
            with self.assertRaisesRegex(ValueError,'identity or incoming product'):self.prepare_browser(guard,self.capture(guard))
        self.assert_code_original()

    def test_permission_expansion_is_refused_before_staging(self):
        path=self.incoming_code/'manifest.json';value=json.loads(path.read_text());value['permissions'].append('debugger');self.write(path,value);self.restage()
        with self.full_guard() as guard:
            with self.assertRaisesRegex(ValueError,'permission changes'):self.prepare_browser(guard,self.capture(guard))
        self.assertFalse(self.browser_stage.exists());self.assert_code_original()

    def test_browser_product_version_must_match_the_same_immutable_candidate(self):
        path=self.incoming_code/'manifest.json';value=json.loads(path.read_text());value['version']='0.2.12';self.write(path,value);self.restage()
        with self.full_guard() as guard:
            with self.assertRaisesRegex(ValueError,'incoming product version'):self.prepare_browser(guard,self.capture(guard))
        self.assert_code_original()

    def test_links_and_code_bounds_refuse_without_copying_user_data(self):
        with self.full_guard() as guard:
            backup=self.capture(guard)
            with patch.object(browser,'MAX_BYTES',1),self.assertRaisesRegex(ValueError,'byte bound'):self.prepare_browser(guard,backup)
            path=self.code/'outside-link';path.symlink_to(self.base/'owner-setting.txt')
            with self.assertRaisesRegex(ValueError,'cannot contain links'):self.prepare_browser(guard,backup)
            self.assertTrue(path.is_symlink());path.unlink()
        self.assertFalse(self.browser_stage.exists());self.assert_code_original()

    def test_low_space_refuses_before_any_browser_copy(self):
        with self.full_guard() as guard:
            backup=self.capture(guard)
            with patch.object(archives,'reserve',side_effect=ValueError('AUTHORED 64 GiB reserve')):
                with self.assertRaisesRegex(ValueError,'64 GiB'):self.prepare_browser(guard,backup)
        self.assertFalse(self.browser_stage.exists());self.assert_code_original()

    def test_real_death_after_forward_exchange_resumes_without_another_exchange(self):
        with self.full_guard() as guard:digest=self.prepared(guard)
        result=self.child(digest,'apply');self.assertEqual(result.returncode,83,result.stderr)
        with self.full_guard() as guard:
            with patch.object(browser,'exchange',side_effect=AssertionError('The code already moved')):self.apply(digest,guard)
            self.assert_code_incoming();self.assert_registry_rebound();publication.rollback(self.publication,digest,guard)
        self.assert_code_original()

    def test_real_death_after_reverse_exchange_restores_exact_original_inode_and_modes(self):
        with self.full_guard() as guard:digest=self.prepared(guard);self.apply(digest,guard)
        result=self.child(digest,'rollback');self.assertEqual(result.returncode,83,result.stderr)
        with self.full_guard() as guard:
            with patch.object(browser,'exchange',side_effect=AssertionError('Original code already returned')):publication.rollback(self.publication,digest,guard)
        self.assert_code_original()

    def test_final_fence_death_preserves_new_work_and_finishes_without_replaying_code_or_data(self):
        with self.full_guard() as guard:digest=self.prepared(guard)
        result=self.child(digest,'finalize');self.assertEqual(result.returncode,86,result.stderr)
        with sqlite3.connect(self.deployment/'prompts.sqlite3') as db:
            db.execute("UPDATE prompts SET content='AUTHORED NEW ORDINARY WORK' WHERE name='source-only'")
        storage=self.deployment/'browser-profile/saved-chat.json';self.write(storage,{'authoredNewChat':'KEEP'})
        with self.full_guard() as guard:
            with patch.object(publication,'apply',side_effect=AssertionError('No replay after reopening')):
                result=publication.finalize(self.publication,digest,guard,os.environ,self.base)
            self.assertTrue(result['clientPublicationComplete']);self.assertFalse(result['ownerContinuationVerified'])
            with self.assertRaisesRegex(ValueError,'fresh reviewed cold reverse'):publication.rollback(self.publication,digest,guard)
            self.assertEqual(browser.inspect(self.browser_stage,self.browser_sha,guard.configuration)[1]['phase'],'released')
        self.assert_code_incoming();self.assertEqual(json.loads(storage.read_text()),{'authoredNewChat':'KEEP'})
        with sqlite3.connect(self.deployment/'prompts.sqlite3') as db:self.assertEqual(db.execute("SELECT content FROM prompts WHERE name='source-only'").fetchone()[0],'AUTHORED NEW ORDINARY WORK')

    def test_changed_archive_and_old_publication_schema_cannot_apply(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard);path=self.archive/'data.tar';raw=path.read_bytes();path.write_bytes(raw+b'AUTHORED CHANGED ARCHIVE')
            with self.assertRaisesRegex(ValueError,'Cold backup contents changed'):self.apply(digest,guard)
            path.write_bytes(raw);pub=self.publication/'publication.json';before=pub.read_bytes();value=json.loads(before);value['schema']='augmentor-dsh-client-publication/3';self.write(pub,value)
            with self.assertRaisesRegex(ValueError,'exact declared deployment guards'):self.apply(tx.preserve.sha(pub.read_bytes()),guard)
            pub.write_bytes(before);publication.rollback(self.publication,digest,guard)
        self.assert_code_original()

    def test_replaced_parent_is_refused_without_touching_either_directory(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard);parent=self.code.parent;kept=parent.with_name('browser-parent-kept');parent.rename(kept);shutil.copytree(kept,parent)
            with self.assertRaisesRegex(ValueError,'parent changed'):self.apply(digest,guard)
            self.assertTrue((kept/self.code.name/'old.js').is_file());shutil.rmtree(parent);kept.rename(parent)
            publication.rollback(self.publication,digest,guard)
        self.assert_code_original()

    def test_missing_preparation_ownership_marker_recovers_without_applying_code(self):
        original=tx.atomic
        def interrupted(path,*args,**kwargs):
            if path==self.browser_stage/'client-publication.json':raise OSError('AUTHORED BROWSER OWNERSHIP GAP')
            return original(path,*args,**kwargs)
        with self.full_guard() as guard:
            with patch.object(tx,'atomic',interrupted),self.assertRaisesRegex(OSError,'OWNERSHIP GAP'):self.prepared(guard)
        digest=tx.preserve.sha((self.publication/'publication.json').read_bytes())
        with self.full_guard() as guard:publication.rollback(self.publication,digest,guard)
        self.assert_code_original()

    def test_finalizing_gap_before_browser_release_finishes_forward_without_reapply(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard);self.apply(digest,guard)
            with patch.object(browser,'release',side_effect=OSError('AUTHORED BROWSER RELEASE GAP')):
                with self.assertRaisesRegex(OSError,'RELEASE GAP'):publication.finalize(self.publication,digest,guard,os.environ,self.base)
        with self.full_guard() as guard:
            with patch.object(publication,'apply',side_effect=AssertionError('No reapply during finalizing')):
                self.assertTrue(publication.finalize(self.publication,digest,guard,os.environ,self.base)['clientPublicationComplete'])
        self.assert_code_incoming()

    def test_released_code_edit_is_preserved_and_never_rolled_back(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard);self.apply(digest,guard);publication.finalize(self.publication,digest,guard,os.environ,self.base)
        path=self.code/'app.mjs';path.write_bytes(b'AUTHORED NEW USER CODE KEEP')
        with self.full_guard() as guard:
            for method in (publication.apply,publication.rollback):
                with self.subTest(method=method.__name__),self.assertRaisesRegex(ValueError,'code or its recovery slot changed'):
                    if method==publication.apply:method(self.publication,digest,guard,os.environ,self.base)
                    else:method(self.publication,digest,guard)
        self.assertEqual(path.read_bytes(),b'AUTHORED NEW USER CODE KEEP')

    def test_browser_and_reviews_share_one_cut_with_the_legacy_partial_third_source(self):
        legacy={'state':str(self.base/'legacy-state'),'data':str(self.base/'legacy-data')}
        for p in legacy.values():Path(p).mkdir(mode=0o700)
        source=Path(legacy['data'])/'dual-memory.sqlite3';self.write(source,(self.source/'dual-memory.sqlite3').read_bytes());before=source.read_bytes();self.extra_sources=[legacy]
        with publication.maintenance(self.home,self.deployment,[self.pair,self.other_pair,legacy],[self.other],partial_pairs=[legacy],review_registry=self.registry) as guard:
            digest=self.prepared(guard);self.apply(digest,guard);self.assert_code_incoming();self.assert_registry_rebound()
            self.assertFalse((Path(legacy['data'])/'prompts.sqlite3').exists());self.assertFalse((Path(legacy['data'])/'memory.sqlite3').exists());self.assertEqual(source.read_bytes(),before)
            publication.rollback(self.publication,digest,guard)
        self.assert_code_original();self.assertEqual(source.read_bytes(),before)

    def test_declared_browser_code_cannot_be_omitted_from_matching_client_publication(self):
        with self.full_guard() as guard:
            backup=self.capture(guard)
            self.data_sha=data.prepare(self.other_pair,self.adoption,backup,guard.configuration,map_default_person=True)['sharedAdoptionSha256']
            config=tx.prepare(self.output,self.stage_sha,self.backup,self.artifact,guard.configuration,cold_backup=backup)
            with self.assertRaisesRegex(ValueError,'declared archived Browser code folder'):
                publication.prepare(self.backup,config['transactionSha256'],self.publication,guard,self.bootstrap,
                    shared_adoption={'root':str(self.adoption),'sha256':self.data_sha},reviews={'revision':9,'names':['main','pilot']})
            self.assertFalse(self.publication.exists());self.assert_code_original()
            tx.rollback(self.backup,config['transactionSha256'],guard.configuration)

    def test_real_target_cannot_put_its_recovery_in_a_disposable_workspace(self):
        scratch=self.base/'disposable';scratch.mkdir(mode=0o700);self.browser_stage=scratch/'browser-stage'
        with self.full_guard() as guard:
            backup=self.capture(guard)
            with patch.dict(os.environ,{'AUGMENTOR_BUILD_WORKSPACE':str(scratch)}):
                with self.assertRaisesRegex(ValueError,'outside disposable build scratch'):self.prepare_browser(guard,backup)
        self.assertFalse(self.browser_stage.exists());self.assert_code_original()
