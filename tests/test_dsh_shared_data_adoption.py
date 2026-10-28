# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real authored SQLite, mixed-root preservation and component crash recovery."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from unittest.mock import patch

from test_dsh_client_publication import ClientPublicationFixture
from dsh import preservation_transaction as tx
from dsh import cold_backup as archives
from dsh import client_publication as publication
from dsh import shared_data_adoption as data


@contextmanager
def connection(*args,**kwargs):
    db=sqlite3.connect(*args,**kwargs)
    try:
        with db:yield db
    finally:db.close()


class SharedDataFixture(ClientPublicationFixture):
    def setUp(self):
        super().setUp()
        base=self.base/'stores';base.mkdir(mode=0o700)
        run=subprocess.run([sys.executable,'-I','-B',str(tx.ROOT/'tests/fixtures/shared-profile-data.py'),str(tx.ROOT),str(base),'target-processed'],capture_output=True,text=True,check=True)
        pairs=json.loads(run.stdout);self.pair={k:pairs['target'][k] for k in ('state','data')};self.other_pair={k:pairs['source'][k] for k in ('state','data')}
        self.deployment=Path(self.pair['data']);self.source=Path(self.other_pair['data'])
        self.write(self.deployment/'desktop.json',{'root':str(self.old),'sharedProfile':self.pair})
        self.write(self.deployment/'releases/kept-app/app.bin',b'AUTHORED INSTALLED APP DO NOT MOVE\n')
        self.write(self.deployment/'owner-setting.txt',b'AUTHORED MIXED ROOT SETTING KEEP\n')
        self.write(self.deployment/'hindsight-installation.json',{'authoredExistingInstallation':'KEEP'})
        self.write(self.other/'desktop.json',{'root':str(self.old),'sharedProfile':self.other_pair})
        self.helper=self.deployment/'desktop-launch.py';self.write(self.helper,b'# AUTHORED OLD STABLE HELPER\n')
        self.bootstrap[-1]=(self.helper,b'# AUTHORED NEW STABLE HELPER\n',0o600)
        # This nested source history must survive the real common-store merge.
        self.write(self.source/'shared-imports/older-cut/data/receipt-é-😀.txt',b'AUTHORED EARLIER IMPORT\n')
        self.write(self.source/'shared-imports/older-cut/receipt.json',{'authoredEarlierReceipt':'KEEP'})
        with connection(self.source/'memory.sqlite3') as db:
            db.execute('INSERT INTO operations VALUES (?,?,?,?,?,?,?,?,?,?,?)',('source-operation','old-request','authored-digest','http://127.0.0.1:9','authored-bank','relationship','old-document','Authored original manual operation.','{}','completed',1))
        self.before_files={p:publication.snapshot(p) for p in [self.existing,self.new,self.helper,
            self.deployment/'desktop.json',self.deployment/'desktop.previous.json',self.other/'desktop.json',self.other/'desktop.previous.json']}
        self.stores={p:p.read_bytes() for pair in (self.pair,self.other_pair) for name in (*data.DATABASES,*data.OPTIONAL) if (p:=Path(pair['data'])/name).exists()}
        self.source_before=data.inventory(self.source)
        self.root_identity=(self.deployment.stat().st_dev,self.deployment.stat().st_ino)
        self.adoption=self.base/'data-adoption'

    def prepared(self,guard,*,archive_other=True):
        extra=[{'id':'source-history','path':str(self.source)}]
        for i,pair in enumerate(getattr(self,'extra_sources',[])):extra.append({'id':'source-extra-'+str(i),'path':pair['data']})
        for i,path in enumerate(getattr(self,'extra_deployments',[])):extra.append({'id':'selection-extra-'+str(i),'path':str(path),'members':['desktop.json']})
        if (self.deployment/'shared-imports').exists():extra.append({'id':'target-import-history','path':str(self.deployment/'shared-imports')})
        if archive_other:extra.append({'id':'other-selection','path':str(self.other),'members':['desktop.json','desktop.previous.json']})
        backup=archives.capture(self.archive,guard.configuration,extra);self.linked={'root':str(self.archive),'sha256':backup['backupSha256']}
        self.data_sha=data.prepare([self.other_pair,*getattr(self,'extra_sources',[])],self.adoption,self.linked,guard.configuration,map_default_person=True)['sharedAdoptionSha256']
        config=tx.prepare(self.output,self.stage_sha,self.backup,self.artifact,guard.configuration,cold_backup=self.linked)
        return publication.prepare(self.backup,config['transactionSha256'],self.publication,guard,self.bootstrap,
            shared_adoption={'root':str(self.adoption),'sha256':self.data_sha})['publicationSha256']

    def full_guard(self):
        return publication.maintenance(self.home,self.deployment,[self.pair,self.other_pair,*getattr(self,'extra_sources',[])],[self.other,*getattr(self,'extra_deployments',[])],partial_pairs=getattr(self,'partial_pairs',[]))

    def mixed_root_preserved(self):
        self.assertEqual((self.deployment.stat().st_dev,self.deployment.stat().st_ino),self.root_identity)
        self.assertEqual((self.deployment/'releases/kept-app/app.bin').read_bytes(),b'AUTHORED INSTALLED APP DO NOT MOVE\n')
        self.assertEqual((self.deployment/'owner-setting.txt').read_bytes(),b'AUTHORED MIXED ROOT SETTING KEEP\n')
        self.assertEqual(data.inventory(self.source),self.source_before)

    def assert_merged(self):
        self.mixed_root_preserved()
        with connection((self.deployment/'prompts.sqlite3').as_uri()+'?mode=ro&immutable=1',uri=True) as db:
            prompts=list(db.execute('SELECT name,content FROM prompts'))
            self.assertEqual(len(prompts),4);self.assertTrue(any(p[0]=='source-only' for p in prompts));self.assertFalse(any(p[0]=='deleted-old' for p in prompts))
        with connection((self.deployment/'dual-memory.sqlite3').as_uri()+'?mode=ro&immutable=1',uri=True) as db:
            self.assertEqual(db.execute('SELECT enabled,person FROM settings').fetchone(),(0,'target-person'))
            self.assertEqual(db.execute('SELECT paused FROM memory_processing').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0],3)
            self.assertEqual(db.execute('SELECT count(*) FROM memory_eligible WHERE job IS NULL').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM memory_windows').fetchone()[0],0)
            self.assertEqual(db.execute("SELECT count(*) FROM sessions WHERE person!='target-person'").fetchone()[0],0)
            self.assertEqual(db.execute("SELECT status FROM memory_jobs WHERE id='authored-job'").fetchone()[0],'pending')
        with connection((self.deployment/'memory.sqlite3').as_uri()+'?mode=ro&immutable=1',uri=True) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM operations').fetchone()[0],1)
        cut=self.deployment/'shared-imports'/self.source_before['sha256']
        self.assertEqual(data.inventory(cut/'data'),self.source_before)
        receipt=json.loads((cut/'receipt.json').read_text());self.assertFalse(receipt['engineCopiedOrCalled']);self.assertFalse(receipt['modelWorkSubmitted'])
        self.assertEqual(receipt['memory']['unassignedEligibilityArchived'],1)
        for name in data.OPTIONAL:self.assertEqual((self.deployment/name).read_bytes(),self.stores[self.deployment/name])

    def crash(self,digest,action,index):
        code='''import os,sys,json
from pathlib import Path
from contextlib import contextmanager
from types import SimpleNamespace
sys.path.insert(0,sys.argv[1]);from dsh import client_publication as p
from dsh import preservation_transaction as tx
from dsh import shared_data_adoption as data
home,deploy,other,journal=map(Path,sys.argv[2:6]);pairs=json.loads(sys.argv[6]);digest=sys.argv[7];action=sys.argv[8];point=int(sys.argv[9]);extra=list(map(Path,json.loads(sys.argv[10])));partial=json.loads(sys.argv[11]);count=0
@contextmanager
def fake(directory,digest,guard,*args):
 tx.inspect(directory,digest,guard)
 yield SimpleNamespace(preflight=lambda:{'productVersion':'0.2.13','homeIdentityMatches':True},native_adapter_preflight=lambda _:{'candidateNativeAdapterMatched':True}),None
p.probes.backend_probe=fake
original=data.rename
def die(*args):
 global count
 original(*args);count+=1
 if count==point:os._exit(79)
data.rename=die
with p.maintenance(home,deploy,pairs,[other,*extra],partial_pairs=partial) as guard:
 if action=='apply':p.apply(journal,digest,guard,os.environ,home)
 else:p.rollback(journal,digest,guard)
'''
        return subprocess.run([sys.executable,'-I','-B','-c',code,str(tx.ROOT/'services'),str(self.home),str(self.deployment),str(self.other),str(self.publication),json.dumps([self.pair,self.other_pair,*getattr(self,'extra_sources',[])]),digest,action,str(index),json.dumps(list(map(str,getattr(self,'extra_deployments',[])))),json.dumps(getattr(self,'partial_pairs',[]))],capture_output=True,text=True)


class SharedDataAdoptionTests(SharedDataFixture):
    def test_review_and_legacy_native_sources_merge_together_with_partial_archive_recovery(self):
        base=self.base/'another-stores';base.mkdir(mode=0o700)
        run=subprocess.run([sys.executable,'-I','-B',str(tx.ROOT/'tests/fixtures/shared-profile-data.py'),str(tx.ROOT),str(base),'plain'],capture_output=True,text=True,check=True)
        pair={k:json.loads(run.stdout)['source'][k] for k in ('state','data')};source=Path(pair['data'])
        # Match the actual older Native preview: only automatic memory was
        # initialized. Do not manufacture empty prompts/manual DBs in its data.
        for name in ('prompts.sqlite3','memory.sqlite3'):(source/name).unlink()
        memory=data.merger.DualMemory(source/'dual-memory.sqlite3')
        memory.call('memory.dual.append',{'session':'pi:source-chat','events':[{'id':'native-preview-extra','role':'user','mode':'text','content':'Authored separate Native preview capture.','status':'complete'}]})
        second_before=data.inventory(source);self.extra_sources=[pair];self.partial_pairs=[pair]
        third=self.base/'legacy-preview-deployment';self.write(third/'desktop.json',{'root':str(self.old),'sharedProfile':pair});self.extra_deployments=[third]
        self.before_files[third/'desktop.json']=publication.snapshot(third/'desktop.json');self.before_files[third/'desktop.previous.json']=None
        self.stores[source/'dual-memory.sqlite3']=(source/'dual-memory.sqlite3').read_bytes()
        history=self.deployment/'shared-imports/older-target';self.write(history/'keep.txt',b'AUTHORED EXISTING IMPORT KEEP');history.parent.chmod(0o700)
        old_history=data.inventory(history.parent)
        with self.full_guard() as guard:digest=self.prepared(guard)
        result=self.crash(digest,'apply',4);self.assertEqual(result.returncode,79,result.stderr)
        with self.full_guard() as guard:self.apply(digest,guard)
        with connection(self.deployment/'prompts.sqlite3') as db:self.assertEqual(db.execute('SELECT count(*) FROM prompts').fetchone()[0],4)
        with connection(self.deployment/'dual-memory.sqlite3') as db:self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0],4)
        for before in (self.source_before,second_before):
            self.assertEqual(data.inventory(self.deployment/'shared-imports'/before['sha256']/'data'),before)
        receipt=json.loads((self.deployment/'shared-imports'/second_before['sha256']/'receipt.json').read_text())
        self.assertTrue(receipt['prompts']['sourceComponentAbsent']);self.assertTrue(receipt['manualMemory']['sourceComponentAbsent'])
        self.assertEqual(json.loads((third/'desktop.json').read_text())['sharedProfile'],self.pair)
        result=self.crash(digest,'rollback',4);self.assertEqual(result.returncode,79,result.stderr)
        with self.full_guard() as guard:publication.rollback(self.publication,digest,guard)
        self.assertEqual(data.inventory(history.parent),old_history);self.assertEqual(data.inventory(source),second_before)
        self.assert_original();self.mixed_root_preserved()

    def test_partial_sources_are_explicit_and_cannot_weaken_the_primary_store(self):
        with self.assertRaisesRegex(ValueError,'secondary source pairs'):
            with publication.maintenance(self.home,self.deployment,[self.pair,self.other_pair],[self.other],partial_pairs=[self.pair]):pass
        path=self.source/'prompts.sqlite3';before=path.read_bytes();path.unlink()
        try:
            with self.assertRaises(FileNotFoundError):
                with self.full_guard():pass
            with publication.maintenance(self.home,self.deployment,[self.pair,self.other_pair],[self.other],partial_pairs=[self.other_pair]) as guard:
                backup=archives.capture(self.archive,guard.configuration,[{'id':'partial-source','path':str(self.source)}])
                self.assertTrue(archives.verify_for_guard(self.archive,backup['backupSha256'],guard.configuration)['matchesCurrentCoveredData'])
                path.write_bytes(before);path.chmod(0o600)
                with self.assertRaisesRegex(ValueError,'no longer matches'):archives.verify_for_guard(self.archive,backup['backupSha256'],guard.configuration)
        finally:
            if not path.exists():path.write_bytes(before);path.chmod(0o600)
        self.assert_original()

    def test_real_merge_keeps_mixed_root_authority_history_and_exact_reverse(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard)
            self.assert_original();self.mixed_root_preserved()
            self.apply(digest,guard);self.assert_merged()
            self.assertTrue(all(p.exists() for p in publication.fences(guard)))
            self.assertEqual(json.loads((self.other/'desktop.json').read_text())['sharedProfile'],self.pair)
            result=publication.rollback(self.publication,digest,guard);self.assertTrue(result['dataRestored'])
            self.assertFalse((self.deployment/'shared-imports').exists())
        self.assert_original();self.mixed_root_preserved()

    def test_every_forward_component_and_archive_death_can_resume_then_reverse(self):
        for index in range(1,5):
            with self.subTest(exchange=index):
                self.adoption=self.base/('adoption-'+str(index));self.publication=self.base/('clients-'+str(index));self.archive=self.base/('archive-'+str(index));self.backup=self.base/('configuration-'+str(index))
                with self.full_guard() as guard:digest=self.prepared(guard)
                result=self.crash(digest,'apply',index);self.assertEqual(result.returncode,79,result.stderr)
                with self.full_guard() as guard:
                    self.apply(digest,guard);self.assert_merged();publication.rollback(self.publication,digest,guard)
                self.assert_original();self.mixed_root_preserved()

    def test_every_reverse_component_and_archive_death_can_finish(self):
        for index in range(1,5):
            with self.subTest(exchange=index):
                self.adoption=self.base/('reverse-adoption-'+str(index));self.publication=self.base/('reverse-clients-'+str(index));self.archive=self.base/('reverse-archive-'+str(index));self.backup=self.base/('reverse-configuration-'+str(index))
                with self.full_guard() as guard:digest=self.prepared(guard);self.apply(digest,guard)
                result=self.crash(digest,'rollback',index);self.assertEqual(result.returncode,79,result.stderr)
                with self.full_guard() as guard:publication.rollback(self.publication,digest,guard)
                self.assert_original();self.mixed_root_preserved()

    def test_foreign_database_recovery_or_source_edit_is_never_overwritten(self):
        for kind in ('database','slot','source'):
            with self.subTest(kind=kind):
                self.adoption=self.base/('foreign-adoption-'+kind);self.publication=self.base/('foreign-clients-'+kind);self.archive=self.base/('foreign-archive-'+kind);self.backup=self.base/('foreign-config-'+kind)
                with self.full_guard() as guard:
                    digest=self.prepared(guard)
                    path={'database':self.deployment/'prompts.sqlite3','slot':self.adoption/'images/prompts.sqlite3','source':self.source/'prompts.sqlite3'}[kind]
                    old=path.read_bytes();path.write_bytes(old+b'AUTHORED NEW WORK KEEP')
                    state={p:p.read_bytes() for p in self.stores}
                    with self.assertRaisesRegex(ValueError,'edited|source changed'):
                        self.apply(digest,guard)
                    self.assertEqual(path.read_bytes(),old+b'AUTHORED NEW WORK KEEP');self.assertEqual(state,{p:p.read_bytes() for p in self.stores})
                    path.write_bytes(old);publication.rollback(self.publication,digest,guard)
                self.assert_original()

    def test_existing_archive_parent_is_preserved_through_forward_and_reverse(self):
        earlier=self.deployment/'shared-imports/older-target/data';self.write(earlier/'historical.txt',b'AUTHORED TARGET HISTORY KEEP')
        (self.deployment/'shared-imports').chmod(0o700)
        original=data.inventory(earlier.parent.parent)
        with self.full_guard() as guard:
            digest=self.prepared(guard);self.apply(digest,guard);self.assert_merged()
            publication.rollback(self.publication,digest,guard)
        self.assertEqual(data.inventory(earlier.parent.parent),original);self.assert_original()

    def test_finalizing_recovery_preserves_new_ordinary_work_and_forbids_old_reverse(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard);self.apply(digest,guard);self.assert_merged()
            with patch.object(publication,'remove_fences',side_effect=OSError('AUTHORED death after data release')):
                with self.assertRaisesRegex(OSError,'data release'):publication.finalize(self.publication,digest,guard,os.environ,self.base)
        with connection(self.deployment/'prompts.sqlite3') as db:
            db.execute("UPDATE prompts SET content='AUTHORED NEW ORDINARY USER WORK' WHERE name='source-only'")
        with self.full_guard() as guard:
            with patch.object(publication,'apply',side_effect=AssertionError('Must not replay old publication')):
                result=publication.finalize(self.publication,digest,guard,os.environ,self.base)
            self.assertTrue(result['clientPublicationComplete']);self.assertFalse(result['ownerContinuationVerified'])
            with self.assertRaisesRegex(ValueError,'fresh reviewed cold reverse'):publication.rollback(self.publication,digest,guard)
        with connection(self.deployment/'prompts.sqlite3') as db:
            self.assertEqual(db.execute("SELECT content FROM prompts WHERE name='source-only'").fetchone()[0],'AUTHORED NEW ORDINARY USER WORK')
        self.mixed_root_preserved()

    def test_unbound_data_api_cannot_mutate_or_release_the_canonical_store(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard)
            for method in (data.commit,data.rollback,data.release):
                with self.assertRaisesRegex(ValueError,'bound client publication'):method(self.adoption,self.data_sha,guard.configuration)
            self.assert_original();publication.rollback(self.publication,digest,guard)

    def test_runtime_inventory_identity_agrees_for_unicode_and_nested_history(self):
        node=shutil.which('node');self.assertIsNotNone(node)
        folder=self.base/'inventory';folder.mkdir(mode=0o700)
        for name in ('é😀','\ue000','🟣','a\nline'):
            self.write(folder/name,('Authored '+name).encode())
        code="import{stateInventory}from './dist/runtime/src/profile-transaction.js';console.log(JSON.stringify(stateInventory(process.argv[1])))"
        result=json.loads(subprocess.check_output([node,'--input-type=module','-e',code,str(folder)],cwd=tx.ROOT,text=True))
        self.assertEqual(data.inventory(folder),result)

    def test_missing_full_source_archive_cannot_prepare_adoption(self):
        with self.full_guard() as guard:
            backup=archives.capture(self.archive,guard.configuration,[])
            with self.assertRaisesRegex(ValueError,'complete dedicated shared source'):
                data.prepare(self.other_pair,self.adoption,{'root':str(self.archive),'sha256':backup['backupSha256']},guard.configuration,map_default_person=True)
            self.assertFalse(self.adoption.exists());self.assert_original()

    def test_switching_a_deployment_without_its_data_receipt_refuses(self):
        with self.full_guard() as guard:
            backup=archives.capture(self.archive,guard.configuration,[{'id':'source','path':str(self.source)},{'id':'other','path':str(self.other),'members':['desktop.json','desktop.previous.json']}])
            config=tx.prepare(self.output,self.stage_sha,self.backup,self.artifact,guard.configuration,cold_backup={'root':str(self.archive),'sha256':backup['backupSha256']})
            with self.assertRaisesRegex(ValueError,'source shared-data adoption'):
                publication.prepare(self.backup,config['transactionSha256'],self.publication,guard,self.bootstrap)
            self.assertFalse(self.publication.exists());tx.rollback(self.backup,config['transactionSha256'],guard.configuration)
        self.assert_original()

    def test_legacy_deployment_requires_its_explicit_previous_pair(self):
        self.write(self.other/'desktop.json',{'root':str(self.old)})
        self.before_files[self.other/'desktop.json']=publication.snapshot(self.other/'desktop.json')
        with self.full_guard() as guard:
            with self.assertRaisesRegex(ValueError,'actual existing shared pair'):self.prepared(guard)
            config_sha=tx.preserve.sha((self.backup/'transaction.json').read_bytes())
            digest=publication.prepare(self.backup,config_sha,self.publication,guard,self.bootstrap,
                shared_adoption={'root':str(self.adoption),'sha256':self.data_sha},previous_pairs={str(self.other):self.other_pair})['publicationSha256']
            self.apply(digest,guard);self.assert_merged();publication.rollback(self.publication,digest,guard)
        self.assert_original()

    def test_preparation_ownership_gap_can_reverse_without_changing_data(self):
        original=tx.atomic
        def interrupted(path,*args,**kwargs):
            if path==self.adoption/'client-publication.json':raise OSError('AUTHORED DATA OWNERSHIP GAP')
            return original(path,*args,**kwargs)
        with self.full_guard() as guard:
            with patch.object(tx,'atomic',interrupted):
                with self.assertRaisesRegex(OSError,'OWNERSHIP GAP'):self.prepared(guard)
        digest=tx.preserve.sha((self.publication/'publication.json').read_bytes())
        with self.full_guard() as guard:publication.rollback(self.publication,digest,guard)
        self.assert_original();self.mixed_root_preserved()

    def test_foreign_archive_or_engine_configuration_is_preserved(self):
        for kind in ('archive','engine'):
            with self.subTest(kind=kind):
                self.adoption=self.base/('history-adoption-'+kind);self.publication=self.base/('history-clients-'+kind);self.archive=self.base/('history-archive-'+kind);self.backup=self.base/('history-config-'+kind)
                with self.full_guard() as guard:
                    digest=self.prepared(guard);self.apply(digest,guard)
                    path=self.deployment/'hindsight.json' if kind=='engine' else self.deployment/'shared-imports'/self.source_before['sha256']/'receipt.json'
                    original=path.read_bytes();path.write_bytes(original+b'\nAUTHORED FOREIGN EDIT KEEP')
                    db_before={name:(self.deployment/name).read_bytes() for name in data.DATABASES}
                    with self.assertRaisesRegex(ValueError,'configuration changed|archive publication differs'):
                        publication.rollback(self.publication,digest,guard)
                    self.assertEqual(path.read_bytes(),original+b'\nAUTHORED FOREIGN EDIT KEEP')
                    self.assertEqual(db_before,{name:(self.deployment/name).read_bytes() for name in data.DATABASES})
                    path.write_bytes(original);publication.rollback(self.publication,digest,guard)
                self.assert_original()

    def test_cached_cold_archive_verification_detects_a_later_edit(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard);path=self.archive/'data.tar';before=path.read_bytes()
            path.write_bytes(before+b'AUTHORED CHANGED ARCHIVE')
            with self.assertRaisesRegex(ValueError,'Cold backup contents changed'):data.inspect(self.adoption,self.data_sha,guard.configuration)
            self.assert_original();path.write_bytes(before);publication.rollback(self.publication,digest,guard)

    def test_reserve_refusal_happens_before_creating_merge_images(self):
        with self.full_guard() as guard:
            backup=archives.capture(self.archive,guard.configuration,[{'id':'source','path':str(self.source)}])
            with patch.object(archives,'reserve',side_effect=ValueError('AUTHORED 64 GiB reserve refusal')):
                with self.assertRaisesRegex(ValueError,'64 GiB'):
                    data.prepare(self.other_pair,self.adoption,{'root':str(self.archive),'sha256':backup['backupSha256']},guard.configuration,map_default_person=True)
            self.assertFalse(self.adoption.exists());self.assert_original()

    def test_death_before_data_release_can_finish_without_reapplying(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard);self.apply(digest,guard)
            original=tx.atomic
            def interrupted(path,raw,*args,**kwargs):
                if path==self.adoption/'status.json' and json.loads(raw)['phase']=='released':raise OSError('AUTHORED RELEASE GAP')
                return original(path,raw,*args,**kwargs)
            with patch.object(tx,'atomic',interrupted):
                with self.assertRaisesRegex(OSError,'RELEASE GAP'):publication.finalize(self.publication,digest,guard,os.environ,self.base)
        with self.full_guard() as guard:
            with patch.object(publication,'apply',side_effect=AssertionError('Do not replay')):
                self.assertTrue(publication.finalize(self.publication,digest,guard,os.environ,self.base)['clientPublicationComplete'])
        self.assert_merged()

    def finish_after_marker_death(self,index):
        with self.full_guard() as guard:digest=self.prepared(guard)
        result=self.child(digest,'finalize',index);self.assertEqual(result.returncode,76,result.stderr)
        with connection(self.deployment/'prompts.sqlite3') as db:
            db.execute("UPDATE prompts SET content='AUTHORED POST-REOPEN WORK' WHERE name='source-only'")
        with self.full_guard() as guard:
            with patch.object(publication,'apply',side_effect=AssertionError('Do not replay after reopening')):
                publication.finalize(self.publication,digest,guard,os.environ,self.base)
        with connection(self.deployment/'prompts.sqlite3') as db:
            self.assertEqual(db.execute("SELECT content FROM prompts WHERE name='source-only'").fetchone()[0],'AUTHORED POST-REOPEN WORK')
        self.mixed_root_preserved()

    def test_data_survives_death_after_home_fence_removal_and_new_work(self):self.finish_after_marker_death(1)
    def test_data_survives_death_after_secondary_fence_removal_and_new_work(self):self.finish_after_marker_death(2)
    def test_data_survives_death_after_primary_fence_removal_and_new_work(self):self.finish_after_marker_death(3)
