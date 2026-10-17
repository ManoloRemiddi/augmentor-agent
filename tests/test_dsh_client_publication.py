# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Authored multi-deployment cuts, real leases/CAS and abrupt-process recovery.

Backend/Native health replies are synthetic here. The separate backend-probe
suite qualifies its real namespace/transport/adapter boundary.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from test_dsh_preservation_transaction import PreservationTransactionFixture
from dsh import preservation_transaction as tx
from dsh import cold_backup as archives
from dsh import client_publication as publication


@contextmanager
def synthetic_backend(directory,digest,guard,environment,cwd):
    # The real fixed boundary also requires the original selection cut.
    tx.inspect(directory,digest,guard)
    yield SimpleNamespace(
        preflight=lambda:{'productVersion':'0.2.13','homeIdentityMatches':True,'modelRequests':0},
        native_adapter_preflight=lambda _: {'candidateNativeAdapterMatched':True,'modelRequests':0}),None


class ClientPublicationFixture(PreservationTransactionFixture):
    def setUp(self):
        super().setUp()
        if os.environ.get('GITHUB_ACTIONS')=='true':
            # Hosted runner capacity is not an owner-data qualification. Only
            # tiny authored fixtures use simulated space; local MX uses the
            # real reserve (including the outer managed workspace lease).
            space=patch.object(archives.shutil,'disk_usage',return_value=SimpleNamespace(free=128*archives.GIB))
            space.start();self.addCleanup(space.stop)
        self.other=self.base/'other-deployment'
        self.other_pair={'state':str(self.base/'other-state'),'data':str(self.base/'other-data')}
        for name in self.other_pair.values():Path(name).mkdir(mode=0o700)
        for name in tx.shared.DATABASES:self.write(Path(self.other_pair['data'])/name,b'AUTHORED OTHER STORE\n')
        self.write(self.other/'desktop.json',{'root':str(self.old),'sharedProfile':self.other_pair,'dshService':'authored-keep','dshEndpoint':'http://127.0.0.1:19001','dshHome':str(self.home)})
        self.write(self.other/'desktop.previous.json',{'authoredOlderRollback':'KEEP'})
        self.bin=self.base/'launchers';self.bin.mkdir(mode=0o700)
        self.existing=self.bin/'agent';self.write(self.existing,b'#!/bin/sh\n# AUTHORED BEFORE\n');self.existing.chmod(0o755)
        self.new=self.bin/'new-managed-host'
        self.helper=self.deployment/'desktop-launch.py';self.write(self.helper,b'# AUTHORED OLD HELPER\n')
        self.bootstrap=[(self.existing,b'#!/bin/sh\n# AUTHORED AFTER\n',0o755),
                        (self.new,b'#!/bin/sh\n# AUTHORED NEW\n',0o700),
                        (self.helper,b'# AUTHORED MATCHING HELPER\n',0o600)]
        self.publication=self.base/'client-journal';self.archive=self.base/'cold-archive'
        self.before_files={p:publication.snapshot(p) for p in [self.existing,self.new,self.helper,
            self.deployment/'desktop.json',self.deployment/'desktop.previous.json',self.other/'desktop.json',self.other/'desktop.previous.json']}
        self.stores={p:p.read_bytes() for pair in (self.pair,self.other_pair) for p in Path(pair['data']).iterdir()}
        backend=patch.object(publication.probes,'backend_probe',synthetic_backend)
        backend.start();self.addCleanup(backend.stop)

    def full_guard(self):return publication.maintenance(self.home,self.deployment,[self.pair,self.other_pair],[self.other])

    def prepared(self,guard,*,archive_other=True):
        extra=[{'id':'other-selection','path':str(self.other),'members':['desktop.json','desktop.previous.json']}] if archive_other else []
        backup=archives.capture(self.archive,guard.configuration,extra)
        linked={'root':str(self.archive),'sha256':backup['backupSha256']}
        config=tx.prepare(self.output,self.stage_sha,self.backup,self.artifact,guard.configuration,cold_backup=linked)
        return publication.prepare(self.backup,config['transactionSha256'],self.publication,guard,self.bootstrap)['publicationSha256']

    def apply(self,digest,guard):return publication.apply(self.publication,digest,guard,os.environ,self.base)

    def assert_original(self):
        for path,before in self.before_files.items():self.assertEqual(publication.snapshot(path),before,str(path))
        self.assert_before()
        for path,raw in self.stores.items():self.assertEqual(path.read_bytes(),raw)

    def child(self,digest,action,index):
        code='''import json,os,sys
from pathlib import Path
from contextlib import contextmanager
from types import SimpleNamespace
sys.path.insert(0,sys.argv[1]);from dsh import client_publication as p
from dsh import preservation_transaction as tx
home,data,other,out=map(Path,sys.argv[2:6]);pairs=json.loads(sys.argv[6]);digest=sys.argv[7];action=sys.argv[8];point=int(sys.argv[9]);count=0
@contextmanager
def fake(directory,digest,guard,*args):
 tx.inspect(directory,digest,guard)
 yield SimpleNamespace(preflight=lambda:{'productVersion':'0.2.13','homeIdentityMatches':True},native_adapter_preflight=lambda _:{'candidateNativeAdapterMatched':True}),None
p.probes.backend_probe=fake
with p.maintenance(home,data,pairs,[other]) as guard:
 if action=='finalize':
  p.apply(out,digest,guard,os.environ,home)
  original=Path.unlink;paths=set(p.fences(guard))
  def unlink(path,*args,**kwargs):
   global count
   original(path,*args,**kwargs)
   if path in paths:
    count+=1
    if count==point:os._exit(76)
  Path.unlink=unlink
  p.finalize(out,digest,guard,os.environ,home)
 else:
  original=p.write_image
  def write(output,row,*args):
   global count
   before=p.snapshot(Path(row['path']));original(output,row,*args)
   if before!=p.snapshot(Path(row['path'])):
    count+=1
    if count==point:os._exit(76)
  p.write_image=write
  if action=='apply':p.apply(out,digest,guard,os.environ,home)
  else:p.rollback(out,digest,guard)
'''
        return subprocess.run([sys.executable,'-I','-B','-c',code,str(tx.ROOT/'services'),str(self.home),str(self.deployment),str(self.other),str(self.publication),json.dumps([self.pair,self.other_pair]),digest,action,str(index)],capture_output=True,text=True)


class ClientPublicationTests(ClientPublicationFixture):
    def test_reviewed_home_launcher_helper_can_be_updated_and_reversed(self):
        home_helper=self.deployment/'home-launch.py'
        self.write(home_helper,b'# AUTHORED EXISTING HOME HELPER\n')
        before=publication.snapshot(home_helper)
        self.bootstrap.append((home_helper,b'# AUTHORED MATCHING HOME HELPER\n',0o600))
        with self.full_guard() as guard:
            digest=self.prepared(guard)
            self.apply(digest,guard)
            self.assertEqual(home_helper.read_bytes(),b'# AUTHORED MATCHING HOME HELPER\n')
            publication.rollback(self.publication,digest,guard)
        self.assertEqual(publication.snapshot(home_helper),before)
        self.assert_original()

    def test_apply_selects_one_matching_artifact_keeps_all_fences_then_exact_reverse(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard)
            configuration_sha=tx.preserve.sha((self.backup/'transaction.json').read_bytes())
            proposed=publication.prospective_selections(self.backup,configuration_sha,guard)
            result=self.apply(digest,guard)
            self.assertTrue(result['matchingClientsSelected']);self.assertFalse(result['activationComplete'])
            for root in guard.deployments:
                selected=json.loads((Path(root)/'desktop.json').read_bytes())
                self.assertEqual(selected['root'],str(self.incoming));self.assertEqual(selected['sharedProfile'],self.pair)
                self.assertEqual(selected,proposed[root])
            selected=json.loads((self.other/'desktop.json').read_bytes())
            self.assertEqual(selected['dshService'],'authored-keep');self.assertEqual(selected['dshEndpoint'],'http://127.0.0.1:19001')
            self.assertTrue(all(p.exists() for p in publication.fences(guard)))
        with self.assertRaisesRegex(ValueError,'requires recovery'):
            with tx.shared.launch_lease(self.other):pass
        with self.full_guard() as guard:
            self.assertTrue(publication.rollback(self.publication,digest,guard)['clientConfigurationRestored'])
            self.assertFalse(any(p.exists() for p in publication.fences(guard)))
        self.assert_original()

    def test_original_configuration_guard_still_refuses_an_unrelated_pointer_edit(self):
        with self.full_guard() as guard:
            self.prepared(guard)
            self.write(self.deployment/'desktop.json',{'root':'/authored/foreign'})
            with self.assertRaisesRegex(ValueError,'selection changed'):
                tx.require(guard.configuration,self.home)

    def test_a_linked_configuration_cannot_be_mutated_through_the_configuration_only_api(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard)
            configuration_sha=tx.preserve.sha((self.backup/'transaction.json').read_bytes())
            for action in (tx.commit,tx.rollback):
                with self.assertRaisesRegex(ValueError,'bound client publication'):
                    action(self.backup,configuration_sha,guard.configuration)
            self.assert_before()
            self.apply(digest,guard);publication.rollback(self.publication,digest,guard)
        self.assert_original()

    def test_every_selector_must_be_in_the_bound_cold_archive(self):
        with self.full_guard() as guard:
            with self.assertRaisesRegex(ValueError,'cold archive does not contain'):
                self.prepared(guard,archive_other=False)
        self.assertFalse(self.publication.exists());self.assert_original()

    def test_configuration_without_current_cold_binding_cannot_publish_clients(self):
        with self.full_guard() as guard:
            digest=tx.prepare(self.output,self.stage_sha,self.backup,self.artifact,guard.configuration)['transactionSha256']
            with self.assertRaisesRegex(ValueError,'current verified cold archive'):
                publication.prepare(self.backup,digest,self.publication,guard,self.bootstrap)
        self.assertFalse(self.publication.exists())

    def test_an_existing_managed_reader_on_any_declared_deployment_blocks_the_cut(self):
        with tx.shared.launch_lease(self.other):
            with self.assertRaisesRegex(ValueError,'existing managed client'):
                with self.full_guard():pass
        self.assert_original()

    def test_foreign_bootstrap_edit_is_preserved_without_changing_configuration_or_selectors(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard)
            self.existing.write_bytes(b'AUTHORED CONCURRENT EDIT')
            with self.assertRaisesRegex(ValueError,'edited'):
                self.apply(digest,guard)
        self.assertEqual(self.existing.read_bytes(),b'AUTHORED CONCURRENT EDIT');self.assert_before()
        self.assertEqual(publication.snapshot(self.deployment/'desktop.json'),self.before_files[self.deployment/'desktop.json'])

    def test_corrupt_recovery_image_or_archive_cannot_authorize_publication(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard)
            image=self.publication/'after/0';raw=image.read_bytes();image.write_bytes(b'AUTHORED TAMPER')
            with self.assertRaisesRegex(ValueError,'image changed'):self.apply(digest,guard)
            image.write_bytes(raw)
            with (self.archive/'data.tar').open('ab') as stream:stream.write(b'AUTHORED TAMPER')
            with self.assertRaisesRegex(ValueError,'backup contents changed'):self.apply(digest,guard)
        self.assert_original()

    def test_mismatched_backend_keeps_clients_fenced_and_can_reverse(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard)
            @contextmanager
            def wrong(*_):
                yield SimpleNamespace(preflight=lambda:{'productVersion':'0.2.11','homeIdentityMatches':True},native_adapter_preflight=lambda _:{'candidateNativeAdapterMatched':True}),None
            with patch.object(publication.probes,'backend_probe',wrong):
                with self.assertRaisesRegex(ValueError,'did not match'):self.apply(digest,guard)
            self.assertTrue(all(p.exists() for p in publication.fences(guard)))
            publication.rollback(self.publication,digest,guard)
        self.assert_original()

    def test_finalization_rechecks_on_new_guard_and_does_not_claim_owner_acceptance(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard);self.apply(digest,guard)
        with self.full_guard() as guard:
            result=publication.finalize(self.publication,digest,guard,os.environ,self.base)
            self.assertTrue(result['clientPublicationComplete']);self.assertFalse(result['activationComplete'])
            self.assertFalse(result['ordinaryClientsStarted']);self.assertFalse(result['ownerContinuationVerified'])
            self.assertFalse(any(p.exists() for p in publication.fences(guard)))
            with self.assertRaisesRegex(ValueError,'fresh reviewed cold reverse'):
                publication.rollback(self.publication,digest,guard)
        for path,raw in self.stores.items():self.assertEqual(path.read_bytes(),raw)

    def test_process_death_after_each_bootstrap_or_pointer_write_can_resume_and_reverse(self):
        for point in range(1,8):
            with self.subTest(point=point):
                self.publication=self.base/('client-forward-'+str(point))
                self.archive=self.base/('archive-forward-'+str(point));self.backup=self.base/('config-forward-'+str(point))
                with self.full_guard() as guard:digest=self.prepared(guard)
                result=self.child(digest,'apply',point);self.assertEqual(result.returncode,76,result.stderr)
                with self.full_guard() as guard:
                    self.apply(digest,guard);publication.rollback(self.publication,digest,guard)
                self.assert_original()

    def test_process_death_after_each_reverse_write_preserves_exact_originals(self):
        for point in range(1,8):
            with self.subTest(point=point):
                self.publication=self.base/('client-reverse-'+str(point))
                self.archive=self.base/('archive-reverse-'+str(point));self.backup=self.base/('config-reverse-'+str(point))
                with self.full_guard() as guard:digest=self.prepared(guard);self.apply(digest,guard)
                result=self.child(digest,'rollback',point);self.assertEqual(result.returncode,76,result.stderr)
                with self.full_guard() as guard:publication.rollback(self.publication,digest,guard)
                self.assert_original()

    def finalize_crash(self,point):
        # Independent fixture per marker: finalization intentionally does not
        # permit replaying an old reverse after ordinary startup might reopen.
        with self.full_guard() as guard:digest=self.prepared(guard)
        result=self.child(digest,'finalize',point)
        self.assertEqual(result.returncode,76,result.stderr)
        with self.full_guard() as guard:
            result=publication.finalize(self.publication,digest,guard,os.environ,self.base)
            self.assertTrue(result['clientPublicationComplete']);self.assertFalse(any(p.exists() for p in publication.fences(guard)))

    def test_process_death_after_home_marker_removal_can_finish(self):self.finalize_crash(1)
    def test_process_death_after_secondary_marker_removal_can_finish(self):self.finalize_crash(2)
    def test_process_death_after_primary_marker_removal_can_finish(self):self.finalize_crash(3)

    def test_missing_secondary_fence_after_interrupted_preparation_can_be_completed(self):
        original=tx.atomic
        def interrupted(path,*args,**kwargs):
            if path==self.other/tx.shared.PRESERVATION_FENCE:raise OSError('AUTHORED INTERRUPTED PREPARATION')
            return original(path,*args,**kwargs)
        with self.full_guard() as guard:
            with patch.object(tx,'atomic',interrupted):
                with self.assertRaisesRegex(OSError,'INTERRUPTED'):self.prepared(guard)
        digest=tx.preserve.sha((self.publication/'publication.json').read_bytes())
        with self.full_guard() as guard:
            self.apply(digest,guard);publication.rollback(self.publication,digest,guard)
        self.assert_original()

    def test_preparation_death_before_configuration_ownership_can_reverse_without_guessing(self):
        original=tx.atomic
        def interrupted(path,*args,**kwargs):
            if path==self.backup/'client-publication.json':raise OSError('AUTHORED OWNERSHIP GAP')
            return original(path,*args,**kwargs)
        with self.full_guard() as guard:
            with patch.object(tx,'atomic',interrupted):
                with self.assertRaisesRegex(OSError,'OWNERSHIP GAP'):self.prepared(guard)
        digest=tx.preserve.sha((self.publication/'publication.json').read_bytes())
        with self.full_guard() as guard:publication.rollback(self.publication,digest,guard)
        self.assert_original()

    def test_foreign_fence_created_during_finalization_is_kept_with_primary_still_blocked(self):
        original=Path.unlink;foreign=self.other/tx.shared.PRESERVATION_FENCE
        def replace(path,*args,**kwargs):
            original(path,*args,**kwargs)
            if path==self.home/tx.gate.FENCE:tx.atomic(foreign,tx.encoded({'authoredForeign':'KEEP'}))
        with self.full_guard() as guard:
            digest=self.prepared(guard);self.apply(digest,guard)
            with patch.object(Path,'unlink',replace):
                with self.assertRaisesRegex(ValueError,'startup fence changed'):
                    publication.finalize(self.publication,digest,guard,os.environ,self.base)
            self.assertEqual(json.loads(foreign.read_bytes()),{'authoredForeign':'KEEP'})
            self.assertTrue((self.deployment/tx.shared.PRESERVATION_FENCE).exists())

    def test_reviewed_bootstrap_cannot_replace_a_shared_database_or_application_source(self):
        with self.full_guard() as guard:
            backup=archives.capture(self.archive,guard.configuration,[{'id':'other-selection','path':str(self.other),'members':['desktop.json','desktop.previous.json']}])
            digest=tx.prepare(self.output,self.stage_sha,self.backup,self.artifact,guard.configuration,cold_backup={'root':str(self.archive),'sha256':backup['backupSha256']})['transactionSha256']
            for target in [Path(self.pair['data'])/'prompts.sqlite3',self.incoming/'release/product.json']:
                with self.subTest(target=target.name),self.assertRaisesRegex(ValueError,'cannot replace'):
                    publication.prepare(self.backup,digest,self.publication,guard,[(target,b'AUTHORED INVALID BOOTSTRAP',0o600)])
        self.assertFalse(self.publication.exists());self.assert_original()

    def test_client_images_respect_the_real_reserve_without_starting_publication(self):
        with self.full_guard() as guard:
            backup=archives.capture(self.archive,guard.configuration,[{'id':'other-selection','path':str(self.other),'members':['desktop.json','desktop.previous.json']}])
            digest=tx.prepare(self.output,self.stage_sha,self.backup,self.artifact,guard.configuration,cold_backup={'root':str(self.archive),'sha256':backup['backupSha256']})['transactionSha256']
            with patch.object(archives.shutil,'disk_usage',return_value=SimpleNamespace(free=archives.RESERVE)):
                with self.assertRaisesRegex(ValueError,'64 GiB'):
                    publication.prepare(self.backup,digest,self.publication,guard,self.bootstrap)
        self.assertFalse(self.publication.exists());self.assert_original()

    def test_archive_removed_after_apply_cannot_reopen_startup(self):
        with self.full_guard() as guard:
            digest=self.prepared(guard);self.apply(digest,guard)
            (self.archive/'data.tar').unlink()
            with self.assertRaises(FileNotFoundError):
                publication.finalize(self.publication,digest,guard,os.environ,self.base)
            self.assertTrue(all(p.exists() for p in publication.fences(guard)))

    def test_supplier_edited_during_preflight_is_not_selected_and_can_reverse(self):
        @contextmanager
        def edited(*args):
            with synthetic_backend(*args) as handle:yield handle
            (self.incoming/'apps/browser/plugin/dist/index.js').write_bytes(b'AUTHORED UNEXPECTED SUPPLIER EDIT')
        with self.full_guard() as guard:
            digest=self.prepared(guard)
            with patch.object(publication.probes,'backend_probe',edited):
                with self.assertRaisesRegex(ValueError,'Release files changed'):self.apply(digest,guard)
            self.assertEqual(publication.snapshot(self.deployment/'desktop.json'),self.before_files[self.deployment/'desktop.json'])
            publication.rollback(self.publication,digest,guard)
        self.assert_original()

