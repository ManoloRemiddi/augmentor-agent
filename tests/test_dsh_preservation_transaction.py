# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Authored four-file profiles; real gates, durable journal and process-death recovery."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from test_dsh_preservation import PreservationFixture
from dsh import preservation_transaction as tx


class PreservationTransactionTests(PreservationFixture):
    def setUp(self):
        super().setUp()
        # mkdir(parents=True) does not apply its mode to intermediate fixture
        # directories; make this authored maintenance profile private explicitly.
        for path in self.base.rglob('*'):
            if path.is_dir():path.chmod(0o700)
        self.pair={'state':str(self.base/'shared-state'),'data':str(self.base/'shared-data')}
        for name in self.pair.values():Path(name).mkdir(mode=0o700)
        for name in tx.shared.DATABASES:self.write(Path(self.pair['data'])/name,b'AUTHORED UNCHANGED SHARED COMPONENT\n')
        self.deployment=self.base/'deployment';self.write(self.deployment/'desktop.json',{'root':str(self.old),'sharedProfile':self.pair})
        self.backup=self.base/'transaction'
        files=tx.deployment.inventory(self.incoming);self.artifact=tx.preserve.sha(json.dumps(files,sort_keys=True).encode())
        self.write(self.incoming/'desktop-release.json',{'deployment':{'root':str(self.incoming),'version':'0.2.13'},'files':files,'artifactSha256':self.artifact})
        self.stage_sha=self.stage()['planSha256']
        self.before={str(p):p.read_bytes() for p in tx.destinations(self.home)}

    def guard(self):return tx.maintenance(self.home,self.deployment,[self.pair])
    def prepare(self,guard):return tx.prepare(self.output,self.stage_sha,self.backup,self.artifact,guard)['transactionSha256']
    def actual(self):return {str(p):p.read_bytes() for p in tx.destinations(self.home)}
    def assert_before(self):self.assertEqual(self.actual(),self.before)

    def test_apply_is_fenced_then_exact_reverse_preserves_modes_and_shared_bytes(self):
        modes={str(p):p.stat().st_mode&0o777 for p in tx.destinations(self.home)}
        data={p:p.read_bytes() for p in Path(self.pair['data']).iterdir()}
        with self.guard() as guard:
            digest=self.prepare(guard);self.assert_before()
            result=tx.commit(self.backup,digest,guard);self.assertTrue(result['configurationApplied']);self.assertFalse(result['activationComplete']);self.assertTrue(result['startupFenced'])
            for index,p in enumerate(tx.destinations(self.home)):
                self.assertEqual(p.read_bytes(),(self.backup/'after'/str(index)).read_bytes());self.assertEqual(p.stat().st_mode&0o777,modes[str(p)])
            self.assertTrue(tx.commit(self.backup,digest,guard)['startupFenced'])
        with self.assertRaisesRegex(ValueError,'requires recovery'):
            with tx.gate.lease(self.home):pass
        with self.guard() as guard:
            self.assertTrue(tx.rollback(self.backup,digest,guard)['configurationRestored']);self.assert_before()
            self.assertTrue(tx.rollback(self.backup,digest,guard)['configurationRestored'])
        with tx.gate.lease(self.home):pass
        self.assertEqual({p:p.read_bytes() for p in data},data)

    def test_real_process_death_after_a_replace_can_resume_or_reverse_without_rebuilding(self):
        code='''import json,os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]);from dsh import preservation_transaction as tx
home,data,backup=map(Path,sys.argv[2:5]);digest=sys.argv[5];pair=json.loads(sys.argv[6]);index=int(sys.argv[7]);original=tx.atomic;count=0
def die(path,*args,**kwargs):
 global count
 original(path,*args,**kwargs)
 if path in tx.destinations(home):
  count+=1
  if count==index:os._exit(77)
tx.atomic=die
with tx.maintenance(home,data,[pair]) as guard:tx.commit(backup,digest,guard)
'''
        for index in range(1,5):
            with self.subTest(replacedFiles=index):
                self.backup=self.base/('transaction-'+str(index))
                with self.guard() as guard:digest=self.prepare(guard)
                run=subprocess.run([sys.executable,'-I','-B','-c',code,str(tx.ROOT/'services'),str(self.home),str(self.deployment),str(self.backup),digest,json.dumps(self.pair),str(index)],capture_output=True,text=True)
                self.assertEqual(run.returncode,77,run.stderr);self.assertTrue((self.home/tx.gate.FENCE).exists());self.assertNotEqual(self.actual(),self.before)
                with self.guard() as guard:
                    self.assertTrue(tx.commit(self.backup,digest,guard)['configurationApplied']);tx.rollback(self.backup,digest,guard)
                self.assert_before()

    def test_real_reverse_process_death_after_each_replace_can_finish(self):
        code='''import json,os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]);from dsh import preservation_transaction as tx
home,data,backup=map(Path,sys.argv[2:5]);digest=sys.argv[5];pair=json.loads(sys.argv[6]);index=int(sys.argv[7]);original=tx.atomic;count=0
def die(path,*args,**kwargs):
 global count
 original(path,*args,**kwargs)
 if path in tx.destinations(home):
  count+=1
  if count==index:os._exit(78)
tx.atomic=die
with tx.maintenance(home,data,[pair]) as guard:tx.rollback(backup,digest,guard)
'''
        for index in range(1,5):
            with self.subTest(restoredFiles=index):
                self.backup=self.base/('reverse-'+str(index))
                with self.guard() as guard:digest=self.prepare(guard);tx.commit(self.backup,digest,guard)
                run=subprocess.run([sys.executable,'-I','-B','-c',code,str(tx.ROOT/'services'),str(self.home),str(self.deployment),str(self.backup),digest,json.dumps(self.pair),str(index)],capture_output=True,text=True)
                self.assertEqual(run.returncode,78,run.stderr);self.assertTrue((self.home/tx.gate.FENCE).exists())
                with self.guard() as guard:
                    with self.assertRaisesRegex(ValueError,'reversing transaction'):tx.commit(self.backup,digest,guard)
                    tx.rollback(self.backup,digest,guard)
                self.assert_before()

    def test_partial_failure_reverses_and_recovery_refuses_new_user_edits(self):
        with self.guard() as guard:
            digest=self.prepare(guard);original=tx.atomic
            def fail(path,*args,**kwargs):
                if path==tx.destinations(self.home)[1]:raise OSError('AUTHORED interrupted publication')
                return original(path,*args,**kwargs)
            with patch.object(tx,'atomic',side_effect=fail):
                with self.assertRaises(OSError):tx.commit(self.backup,digest,guard)
            victim=tx.destinations(self.home)[0];victim.write_bytes(b'AUTHORED NEW OWNER EDIT KEEP')
            observed=self.actual()
            with self.assertRaisesRegex(ValueError,'was edited'):tx.rollback(self.backup,digest,guard)
            self.assertEqual(self.actual(),observed)
            victim.write_bytes((self.backup/'after/0').read_bytes());tx.rollback(self.backup,digest,guard);self.assert_before()

    def test_reverse_death_after_status_before_fence_unlink_can_finish(self):
        with self.guard() as guard:
            digest=self.prepare(guard);tx.commit(self.backup,digest,guard);original=tx.atomic
            def fail(path,data,*args,**kwargs):
                original(path,data,*args,**kwargs)
                if path==self.backup/'status.json' and json.loads(data)['phase']=='reversed':raise OSError('AUTHORED power loss before fence removal')
            with patch.object(tx,'atomic',side_effect=fail):
                with self.assertRaises(OSError):tx.rollback(self.backup,digest,guard)
            self.assert_before();self.assertTrue((self.home/tx.gate.FENCE).exists())
            self.assertFalse(tx.rollback(self.backup,digest,guard)['startupFenced'])

    def test_no_cold_guard_or_changed_selection_and_shared_reader_refuse(self):
        with tx.gate.lease(self.home):
            with self.assertRaisesRegex(ValueError,'managed DSH host'):
                with self.guard():pass
        with tx.shared.launch_lease(self.deployment):
            with self.assertRaisesRegex(ValueError,'managed client'):
                with self.guard():pass
        with tx.shared.cold([self.pair]):
            with self.assertRaisesRegex(ValueError,'companion owners'):
                with self.guard():pass
        with self.guard() as guard:digest=self.prepare(guard)
        with self.assertRaisesRegex(ValueError,'cold maintenance'):tx.commit(self.backup,digest,guard)
        with self.guard() as guard:
            selection=self.deployment/'desktop.json';original=selection.read_bytes();selection.write_bytes(original+b' ')
            with self.assertRaisesRegex(ValueError,'selection changed'):tx.commit(self.backup,digest,guard)
            selection.write_bytes(original);tx.rollback(self.backup,digest,guard)
        self.assert_before()

    def test_changed_incoming_or_owner_input_refuses_apply_but_originals_can_reverse(self):
        with self.guard() as guard:
            digest=self.prepare(guard);self.write(self.home/'settings.yaml',b'AUTHORED SETTINGS CHANGED KEEP')
            with self.assertRaisesRegex(ValueError,'input changed'):tx.commit(self.backup,digest,guard)
            tx.rollback(self.backup,digest,guard);self.assert_before()
        self.assertEqual((self.home/'settings.yaml').read_bytes(),b'AUTHORED SETTINGS CHANGED KEEP')
        self.output=self.base/'review-again';self.backup=self.base/'transaction-again';self.stage_sha=self.stage()['planSha256']
        with self.guard() as guard:
            digest=self.prepare(guard);self.write(self.incoming/'adapters/dsh-product/index.mjs',b'AUTHORED DAMAGED CANDIDATE')
            with self.assertRaisesRegex(ValueError,'files changed'):tx.commit(self.backup,digest,guard)
            tx.rollback(self.backup,digest,guard);self.assert_before()

    def test_corrupt_backups_foreign_fence_and_wrong_plan_refuse_without_replacement(self):
        with self.guard() as guard:
            digest=self.prepare(guard);raw=(self.backup/'before/0').read_bytes();(self.backup/'before/0').write_bytes(b'CORRUPTED')
            with self.assertRaisesRegex(ValueError,'Recovery copy changed'):tx.rollback(self.backup,digest,guard)
            self.assert_before();(self.backup/'before/0').write_bytes(raw)
            fence=self.home/tx.gate.FENCE;original=fence.read_bytes();fence.write_bytes(b'{"foreign":true}')
            with self.assertRaisesRegex(ValueError,'fence changed'):tx.commit(self.backup,digest,guard)
            self.assert_before();fence.write_bytes(original)
            with self.assertRaisesRegex(ValueError,'identity changed'):tx.commit(self.backup,'0'*64,guard)
            tx.rollback(self.backup,digest,guard)

    def test_retained_library_alias_changes_stop_a_prepared_transaction(self):
        supplier,alias=self.legacy_bundle()
        files=tx.deployment.inventory(self.incoming);self.artifact=tx.preserve.sha(json.dumps(files,sort_keys=True).encode())
        self.write(self.incoming/'desktop-release.json',{'deployment':{'root':str(self.incoming),'version':'0.2.13'},'files':files,'artifactSha256':self.artifact})
        self.output=self.base/'review-library';self.stage_sha=self.stage()['planSha256']
        with self.guard() as guard:
            digest=self.prepare(guard);alias.unlink();alias.symlink_to(self.incoming,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'package alias changed'):tx.commit(self.backup,digest,guard)
            self.assert_before();tx.rollback(self.backup,digest,guard)
        self.assertEqual(alias.resolve(),self.incoming)

    def test_unsealed_incoming_and_transaction_overlap_refuse_before_owner_fence(self):
        with self.guard() as guard:
            with self.assertRaisesRegex(ValueError,'identity changed'):tx.prepare(self.output,self.stage_sha,self.backup,'0'*64,guard)
            with self.assertRaisesRegex(ValueError,'outside application'):tx.prepare(self.output,self.stage_sha,self.home/'transaction',self.artifact,guard)
        self.assertFalse((self.home/tx.gate.FENCE).exists());self.assert_before()

    def test_unmanaged_same_home_dsh_host_vetoes_even_with_another_shared_pair(self):
        command=self.base/'dsh';self.write(command,b'import sys\nprint("AUTHORED_READY",flush=True)\nsys.stdin.read()\n')
        env={**os.environ,'DSH_HOME':str(self.home),'AUGMENTOR_SHARED_STATE':str(self.base/'different-state'),'AUGMENTOR_SHARED_DATA':str(self.base/'different-data')}
        for arguments in (['web'],['--profile','authored-custom']):
            with self.subTest(arguments=arguments):
                child=subprocess.Popen([sys.executable,'-I','-B',str(command),*arguments],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                try:
                    self.assertEqual(child.stdout.readline(),b'AUTHORED_READY\n')
                    tx.shared.assert_no_clients([self.pair])
                    with self.assertRaisesRegex(ValueError,'Stop the existing DSH host'):
                        with self.guard():pass
                finally:child.communicate(timeout=5)
        with self.guard():pass
