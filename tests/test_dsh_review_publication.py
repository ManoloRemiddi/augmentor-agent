# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Authored registered reviews: cold archive, common-store rebind and recovery."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from test_dsh_shared_data_adoption import SharedDataFixture
from dsh import client_publication as publication
from dsh import preservation_transaction as tx
from dsh import cold_backup as archives
from dsh import shared_data_adoption as data


class ReviewPublicationFixture(SharedDataFixture):
    def setUp(self):
        super().setUp()
        self.operator=self.base/'operator';self.operator.mkdir(mode=0o700)
        environment=patch.dict(os.environ,{'HOME':str(self.operator)})
        environment.start();self.addCleanup(environment.stop)
        self.registry=self.base/'registered-reviews';self.registry.mkdir(mode=0o700)
        self.binary=self.operator/'.local/bin/augmentor-harness-review';self.write(self.binary,b'# AUTHORED OWNED OLD OPENER\n');self.binary.chmod(0o700)
        self.entries={}
        for name in ('main','pilot','other'):
            base=self.base/'profiles'/name
            profile={key:str(base/key) for key in publication.review.PATH_KEYS}
            profile.update(sharedState=self.other_pair['state'],sharedData=self.other_pair['data'],socket=str(base/'state/owner.sock'),
                workspace=str(self.base),port=0,sessionId='authored-'+name,llamaCppProviders='authored-local-route',linuxTools=True)
            for key in publication.review.PATH_KEYS:
                if key!='socket':Path(profile[key]).mkdir(parents=True,mode=0o700,exist_ok=True)
            menu=str(self.base/(name+'.desktop'));self.write(Path(menu),('# AUTHORED '+name+' MENU KEEP\n').encode())
            self.entries[name]={'title':'Authored '+name,'deployment':{'root':str(self.old),'authoredOriginal':'KEEP'},'profile':profile,
                                'menuFiles':[menu],'authoredExtra':{'keep':True}}
        self.old={'schema':publication.review.SCHEMA,'revision':9,'entries':self.entries,
                  'ownedFiles':{str(self.binary):publication.review.digest(self.binary.read_bytes()),'/authored/icon.svg':'keep-hash'}}
        self.write(self.registry/'reviews.json',self.old)
        self.registry_before=publication.snapshot(self.registry/'reviews.json');self.binary_before=publication.snapshot(self.binary)
        # Public opener copied as a declared fixture input, never private code.
        self.write(self.incoming/'scripts/harness-review.py',(tx.ROOT/'scripts/harness-review.py').read_bytes())
        value=json.loads((self.incoming/'desktop-release.json').read_text());value['files']=tx.deployment.inventory(self.incoming)
        value['artifactSha256']=tx.preserve.sha(json.dumps(value['files'],sort_keys=True).encode());self.artifact=value['artifactSha256']
        self.write(self.incoming/'desktop-release.json',value)
        self.output=self.base/'registration-stage';self.stage_sha=self.stage()['planSha256']

    def full_guard(self):
        return publication.maintenance(self.home,self.deployment,[self.pair,self.other_pair],[self.other],review_registry=self.registry)

    def prepared(self,guard,*,archive_registry=True,with_data=True):
        extra=[{'id':'source-history','path':str(self.source)},{'id':'other-selection','path':str(self.other),'members':['desktop.json','desktop.previous.json']}]
        if archive_registry:extra.append({'id':'review-registry','path':str(self.registry),'members':['reviews.json']})
        result=archives.capture(self.archive,guard.configuration,extra);linked={'root':str(self.archive),'sha256':result['backupSha256']}
        self.data_sha=data.prepare(self.other_pair,self.adoption,linked,guard.configuration,map_default_person=True)['sharedAdoptionSha256']
        result=tx.prepare(self.output,self.stage_sha,self.backup,self.artifact,guard.configuration,cold_backup=linked)
        return publication.prepare(self.backup,result['transactionSha256'],self.publication,guard,self.bootstrap,
            shared_adoption={'root':str(self.adoption),'sha256':self.data_sha} if with_data else None,
            reviews={'revision':9,'names':['main','pilot']})['publicationSha256']

    def assert_registry_rebound(self):
        value=publication.review.registry_read(self.registry)
        self.assertEqual(value['revision'],10);self.assertEqual(value['entries']['other'],self.entries['other'])
        deployment=json.loads((self.incoming/'desktop-release.json').read_text())['deployment']
        for name in ('main','pilot'):
            entry=value['entries'][name];old=self.entries[name]
            self.assertEqual(entry['deployment'],deployment)
            self.assertEqual(entry['profile'],dict(old['profile'],sharedState=self.pair['state'],sharedData=self.pair['data']))
            self.assertEqual(entry['launchData'],str(self.deployment))
            for key in ('title','menuFiles','authoredExtra'):self.assertEqual(entry[key],old[key])
            env=publication.review.runtime_environment(publication.review.profile_record(entry['profile']),dict(deployment,node='/authored/node',python='/authored/python'))
            self.assertEqual(env['AUGMENTOR_SHARED_STATE'],self.pair['state']);self.assertEqual(env['AUGMENTOR_SHARED_DATA'],self.pair['data'])
        self.assertEqual(value['ownedFiles']['/authored/icon.svg'],'keep-hash')
        self.assertEqual(value['ownedFiles'][str(self.binary)],publication.review.digest(self.binary.read_bytes()))
        self.assertEqual(self.binary.read_bytes(),(self.incoming/'scripts/harness-review.py').read_bytes())

    def assert_registered_original(self):
        self.assertEqual(publication.snapshot(self.registry/'reviews.json'),self.registry_before)
        self.assertEqual(publication.snapshot(self.binary),self.binary_before)
        self.assert_original();self.mixed_root_preserved()


class ReviewPublicationTests(ReviewPublicationFixture):
    def registry_child(self,digest,action,index):
        code='''import json,os,sys
from pathlib import Path
from contextlib import contextmanager
from types import SimpleNamespace
sys.path.insert(0,sys.argv[1]);from dsh import client_publication as p
from dsh import preservation_transaction as tx
home,deploy,other,registry,journal,binary=map(Path,sys.argv[2:8]);pairs=json.loads(sys.argv[8]);digest=sys.argv[9];action=sys.argv[10];point=int(sys.argv[11]);count=0
@contextmanager
def fake(directory,digest,guard,*args):
 tx.inspect(directory,digest,guard)
 yield SimpleNamespace(preflight=lambda:{'productVersion':'0.2.13','homeIdentityMatches':True},native_adapter_preflight=lambda _:{'candidateNativeAdapterMatched':True}),None
p.probes.backend_probe=fake
original=p.write_image
def die(output,row,*args):
 global count
 path=Path(row['path']);before=p.snapshot(path);original(output,row,*args)
 if path in (registry/'reviews.json',binary) and p.snapshot(path)!=before:
  count+=1
  if count==point:os._exit(81)
p.write_image=die
with p.maintenance(home,deploy,pairs,[other],review_registry=registry) as guard:
 if action=='apply':p.apply(journal,digest,guard,os.environ,home)
 else:p.rollback(journal,digest,guard)
'''
        return subprocess.run([sys.executable,'-I','-B','-c',code,str(tx.ROOT/'services'),str(self.home),str(self.deployment),str(self.other),str(self.registry),str(self.publication),str(self.binary),json.dumps([self.pair,self.other_pair]),digest,action,str(index)],capture_output=True,text=True)

    def test_registered_profiles_follow_same_data_and_artifact_then_reverse_exactly(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard);self.assert_registered_original()
            self.apply(digest,guard);self.assert_registry_rebound();self.assert_merged()
            publication.rollback(self.publication,digest,guard)
        self.assert_registered_original()

    def test_registry_renderer_is_read_only_and_starts_no_owner(self):
        deployment=json.loads((self.incoming/'desktop-release.json').read_text())['deployment']
        with patch.object(publication.review,'Owner',side_effect=AssertionError('No owner during rendering')):
            result=publication.review.registry_plan(self.registry,deployment,self.pair,['main','pilot'],9,b'# AUTHORED NEW OPENER\n',self.deployment)
        self.assertEqual(result['revisionAfter'],10);self.assert_registered_original()
        self.assertEqual(result['previousPairs'],{'main':self.other_pair,'pilot':self.other_pair})

    def test_registry_must_be_in_archive_and_locked_by_this_publication(self):
        with self.full_guard() as guard:
            with self.assertRaisesRegex(ValueError,'exact review registry'):self.prepared(guard,archive_registry=False)
            tx.rollback(self.backup,tx.preserve.sha((self.backup/'transaction.json').read_bytes()),guard.configuration)
        self.assert_registered_original()

    def test_source_pair_binding_is_required_even_when_only_registry_changes(self):
        # The deployment itself already uses the canonical store; the review
        # profile still needs the old shared source included in adoption.
        self.write(self.other/'desktop.json',{'root':str(self.old),'sharedProfile':self.pair})
        self.before_files[self.other/'desktop.json']=publication.snapshot(self.other/'desktop.json')
        with self.full_guard() as guard:
            with self.assertRaisesRegex(ValueError,'every review previous shared pair'):self.prepared(guard,with_data=False)
            tx.rollback(self.backup,tx.preserve.sha((self.backup/'transaction.json').read_bytes()),guard.configuration)
        self.assert_registered_original()

    def test_unowned_or_edited_opener_is_never_adopted(self):
        self.binary.write_bytes(b'AUTHORED FOREIGN OPENER KEEP')
        with self.full_guard() as guard:
            with self.assertRaisesRegex(ValueError,'edited or is unowned'):self.prepared(guard)
            self.assertEqual(self.binary.read_bytes(),b'AUTHORED FOREIGN OPENER KEEP')
            self.binary.write_bytes(self.binary_before[0]);tx.rollback(self.backup,tx.preserve.sha((self.backup/'transaction.json').read_bytes()),guard.configuration)
        self.assert_registered_original()

    def test_registry_edit_after_prepare_is_kept_without_any_data_application(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard);path=self.registry/'reviews.json';original=path.read_bytes();path.write_bytes(original+b'\n ')
            with self.assertRaisesRegex(ValueError,'was edited'):self.apply(digest,guard)
            self.assertEqual(path.read_bytes(),original+b'\n ');self.assert_original()
            path.write_bytes(original);publication.rollback(self.publication,digest,guard)
        self.assert_registered_original()

    def test_recovery_requires_the_same_registry_lock(self):
        with self.full_guard() as guard:digest=self.prepared(guard)
        with publication.maintenance(self.home,self.deployment,[self.pair,self.other_pair],[self.other]) as guard:
            with self.assertRaisesRegex(ValueError,'exact bound review registry lock'):self.apply(digest,guard)
        with self.full_guard() as guard:publication.rollback(self.publication,digest,guard)
        self.assert_registered_original()

    def test_existing_registry_reader_excludes_the_cold_publisher(self):
        # Real flock contention, accelerated only for the authored wait bound.
        with publication.review.registry_lock(self.registry),patch.object(publication.review.time,'monotonic',side_effect=[0,1,11]):
            with self.assertRaisesRegex(ValueError,'registration is busy'):
                with self.full_guard():pass
        self.assert_registered_original()

    def test_forward_death_after_each_registry_or_opener_write_resumes_and_reverses(self):
        for index in (1,2):
            with self.subTest(write=index):
                self.adoption=self.base/('registry-data-'+str(index));self.publication=self.base/('registry-clients-'+str(index));self.archive=self.base/('registry-cold-'+str(index));self.backup=self.base/('registry-config-'+str(index))
                with self.full_guard() as guard:digest=self.prepared(guard)
                result=self.registry_child(digest,'apply',index);self.assertEqual(result.returncode,81,result.stderr)
                with self.full_guard() as guard:
                    self.apply(digest,guard);self.assert_registry_rebound();self.assert_merged();publication.rollback(self.publication,digest,guard)
                self.assert_registered_original()

    def test_reverse_death_after_each_registry_or_opener_write_preserves_originals(self):
        for index in (1,2):
            with self.subTest(write=index):
                self.adoption=self.base/('reverse-registry-data-'+str(index));self.publication=self.base/('reverse-registry-clients-'+str(index));self.archive=self.base/('reverse-registry-cold-'+str(index));self.backup=self.base/('reverse-registry-config-'+str(index))
                with self.full_guard() as guard:digest=self.prepared(guard);self.apply(digest,guard)
                result=self.registry_child(digest,'rollback',index);self.assertEqual(result.returncode,81,result.stderr)
                with self.full_guard() as guard:publication.rollback(self.publication,digest,guard)
                self.assert_registered_original()

    def test_finalized_registration_is_complete_without_claiming_owner_continuation(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard);self.apply(digest,guard)
            result=publication.finalize(self.publication,digest,guard,os.environ,self.base)
            self.assertTrue(result['clientPublicationComplete']);self.assertFalse(result['ordinaryClientsStarted']);self.assertFalse(result['ownerContinuationVerified'])
            self.assert_registry_rebound();self.assert_merged()

    def test_stale_revision_unknown_or_duplicate_reviews_fail_without_mutation(self):
        deployment=json.loads((self.incoming/'desktop-release.json').read_text())['deployment']
        for names,revision in [(['main'],8),(['missing'],9),(['main','main'],9),([],9),([[1]],9)]:
            with self.subTest(names=names,revision=revision),self.assertRaises(ValueError):
                publication.review.registry_plan(self.registry,deployment,self.pair,names,revision,b'# AUTHORED OPENER\n',self.deployment)
        self.assert_registered_original()
