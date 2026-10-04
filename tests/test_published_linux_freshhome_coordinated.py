# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Pure/source and disposable-file tests; no container or SDK operations."""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value

m = load('freshhome', ROOT/'release/prove-published-linux-freshhome-coordinated.py')
c = load('historical', ROOT/'release/prove-published-linux-coordinated-version.py')


def synthetic_ending():
    return {'format': 'augmentor-published-freshhome-baseline-ending/1', 'status': 'pass',
            'actualFreshRunSha256': m.BASELINE_RUN_SHA, 'wholeHomeDeltaSha256': m.DELTA_SHA,
            'container': m.CONTAINER, 'image': m.IMAGE, 'volume': m.VOLUME, 'workerExitCode': 0,
            'modelRequests': 0, 'pending': None, 'unknownOutcome': False,
            'selected': {'root':m.BASELINE_ROOT,'artifactSha256':m.BASELINE_ARTIFACT,
                         'version':'0.2.12','sourceRef':m.SOURCES['0.2.12']},
            **{k: True for k in ('nativeInventoryUnchanged', 'normalManagedInventoryVerified',
            'historicalJournalsAndHistoriesPreserved', 'foreignHomeAliasesPreserved', 'wholeHomeDeltaReviewed',
            'processesAbsent', 'socketAbsent', 'portsIdle', 'leasesIdle')}}


def synthetic_admission():
    # Deliberately synthetic schema data; never exported as real evidence.
    groups = {f'1:{i}': [f'profile/{i}', f'cache/{i}'] for i in range(127)}
    groups['1:126'].append('profile/extra')
    return {'format': 'augmentor-published-freshhome-admission/1', 'container': m.CONTAINER,
            'image': m.IMAGE, 'volume': m.VOLUME, 'baselineRunSha256': m.BASELINE_RUN_SHA,
            'baselineSelectorSha256': m.BASELINE_SELECTOR_SHA, 'originalSelectorSha256': m.ORIGINAL_SELECTOR_SHA,
            'wholeHomeDeltaSha256': m.DELTA_SHA, 'coordinatorSha256': m.COORDINATOR_SHA,
            'managedProofSha256': m.MANAGED_SHA, **m.SEED_PINS,
            'baselineEndingAuditSha256': m.digest(json.dumps(synthetic_ending()).encode()),
            'freshMarkerSha256': m.FRESH_MARKER_SHA, 'baselineSelected': {'root': m.BASELINE_ROOT,
            'artifactSha256': m.BASELINE_ARTIFACT, 'version': '0.2.12', 'sourceRef': m.SOURCES['0.2.12']},
            'foreignHomeAliasGroups': groups,
            'foreignHomeAliasRows': {p: {'bytes':1,'sha256':'a'*64,'uid':1000,'gid':1000,'mode':0o600,
                'mtimeNs':10,'ctimeNs':11,'device':1,'inode':int(g.split(':')[1]),'nlink':len(names)}
                for g,names in groups.items() for p in names},
            'historicalJournals': {n: {} for n in ('published-product-baseline-history154',
            'published-product-first-use-history157', 'published-product-cold-history158',
            'published-product-managed-baseline160')}}


def synthetic_binding(mode='upgrade'):
    version = '0.2.13' if mode == 'upgrade' else '0.2.12'
    return {'format': 'augmentor-published-freshhome-coordinated-binding/1', 'mode': mode,
            'proofSha256': 'proof', 'admissionSha256': 'admission', 'coordinatorSha256': m.COORDINATOR_SHA,
            'runToken': 'a'*64, 'createdAt': 100, 'baselineRunSha256': m.BASELINE_RUN_SHA,
            'baselineEndingAuditSha256': 'b'*64, 'nativeAuditSha256': 'c'*64,
            'nativeAudit': {'status': 'pass', 'version': version, 'source': m.SOURCES[version],
                           'pending': None, 'unknownOutcome': False, 'leasesIdle': True,
                           'processesAbsent': True, 'socketAbsent': True, 'portsIdle': True},
            'packageTransaction': {'phase': 'pass', 'exitCode': 0, 'pending': None, 'unknownOutcome': False,
               'versions': {'augmentor-runtime': version, 'augmentor-desktop': version},
               'addedDependencies': sorted(c.NEW_DEPENDENCIES) if mode == 'upgrade' else [],
               'removedPackages': [], 'unrelatedPackageChanges': False, 'receiptSha256': 'd'*64},
            'foreignHardlinks': {}, 'dshCli': {}, 'upgradeRunSha256': 'e'*64}


class AdmissionTests(unittest.TestCase):
    def check_binding(self, b, mode='upgrade', now=120):
        return m.binding_identity(b, mode, 'proof', 'admission', {'baselineEndingAuditSha256':'b'*64}, now, c)

    def test_fresh_native_upgrade_and_rollback_bind_separate_actual_cohorts(self):
        self.assertEqual(self.check_binding(synthetic_binding()), '0.2.13')
        self.assertEqual(self.check_binding(synthetic_binding('rollback'), 'rollback'), '0.2.12')

    def test_old160_or_staged163_binding_cannot_be_substituted(self):
        for change in ({'format':'augmentor-published-coordinated-binding/1'},
                       {'format':'augmentor-published-staged-integration-binding/1'},
                       {'baselineRunSha256':c.BASELINE_RUN_SHA}, {'coordinatorSha256':'x'},
                       {'admissionSha256':'other'}, {'mode':'upgrade-after-known-stage'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.check_binding({**synthetic_binding(), **change})

    def test_stale_future_missing_identity_and_unknown_native_refuse(self):
        for change in ({'createdAt':-200}, {'createdAt':121}, {'createdAt':None},
                       {'proofSha256':'other'}, {'runToken':''}, {'nativeAuditSha256':''}, {'dshCli':None}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.check_binding({**synthetic_binding(), **change})
        for change in ({'unknownOutcome':True}, {'pending':'APT'}, {'version':'0.2.12'},
                       {'source':'other'}, {'leasesIdle':False}, {'socketAbsent':False},
                       {'portsIdle':False}, {'processesAbsent':False}):
            b=synthetic_binding(); b['nativeAudit'].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError): self.check_binding(b)

    def test_known_separate_apt_failure_extra_or_removed_dependency_refuses(self):
        for change in ({'phase':'failed'}, {'exitCode':1}, {'unknownOutcome':True}, {'pending':'APT'},
                       {'receiptSha256':''}, {'addedDependencies':[]}, {'removedPackages':['foreign']},
                       {'unrelatedPackageChanges':True}, {'versions':{'augmentor-runtime':'0.2.12'}}):
            b=synthetic_binding(); b['packageTransaction'].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError): self.check_binding(b)

    def test_component_or_unreviewed_delta_cannot_become_aggregate_pass(self):
        m.ending_identity(synthetic_ending())
        for key,value in [('status','PASS_READONLY_COMPONENTS; WHOLE_HOME_DELTA_REVIEW_REQUIRED'),
                          ('wholeHomeDeltaReviewed',False), ('foreignHomeAliasesPreserved',False),
                          ('workerExitCode',1), ('actualFreshRunSha256',c.BASELINE_RUN_SHA),
                          ('pending','stop'), ('unknownOutcome',True), ('modelRequests',1)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                m.ending_identity({**synthetic_ending(),key:value})

    def test_admission_requires_exact_topology_digest_and_every_alias_row(self):
        a=synthetic_admission(); raw=json.dumps(synthetic_ending()).encode()
        # Synthetic schema exercise; actual topology is separately hard-pinned.
        fake=m.digest(json.dumps(a['foreignHomeAliasGroups'],sort_keys=True,separators=(',',':')).encode())
        with patch.object(m,'ALIAS_TOPOLOGY_SHA',fake), patch.object(m,'BASELINE_ENDING_SHA',m.digest(raw)):
            m.admission_identity(a,raw)
            for change in ({'container':'other'}, {'image':'other'}, {'volume':'other'},
                           {'baselineRunSha256':c.BASELINE_RUN_SHA}, {'baselineEndingAuditSha256':'0'*64},
                           {'historicalJournals':{}}, {'foreignHomeAliasRows':{}}, {'originalSelectorSha256':'x'}):
                with self.subTest(change=change), self.assertRaises(ValueError):m.admission_identity({**a,**change},raw)
        with self.assertRaises(ValueError):m.admission_identity(a,raw)

    def test_namespace_requires_fresh_root_marker_uts_and_real_named_ext4(self):
        marker={'format':'augmentor-fresh-home-root-admission/1',
                'sourceContainer':'eb9127eb22ea22d3bf9f48977f55bce755ee4affc2f015384925a3038a3dbfb8',
                'destinationContainer':m.CONTAINER,'image':m.IMAGE,'volume':m.VOLUME,**m.SEED_PINS}
        raw=json.dumps(marker).encode(); a={'freshMarkerSha256':m.digest(raw)}
        mount=f'100 90 1:2 /volumes/{m.VOLUME}/_data {m.HOME} rw,nosuid,nodev - ext4 /dev/test rw\n'
        pid1=b'/usr/bin/tini\0--\0sleep\0infinity\0'
        m.namespace_identity(raw,a,m.CONTAINER[:12],pid1,mount)
        for bad in (mount.replace('ext4','overlay'), mount.replace(m.VOLUME,'other'), mount+mount,
                    mount.replace('rw,nosuid,nodev','ro,nosuid,nodev')):
            with self.subTest(mount=bad), self.assertRaises(ValueError):m.namespace_identity(raw,a,m.CONTAINER[:12],pid1,bad)
        for host,argv in [('eb9127eb22ea',pid1),(m.CONTAINER[:12],b'sleep\0infinity\0')]:
            with self.assertRaises(ValueError):m.namespace_identity(raw,a,host,argv,mount)

    def test_retained_draft_without_real_ctime_refuses_before_runtime(self):
        a=synthetic_admission(); rows=copy.deepcopy(a['foreignHomeAliasRows'])
        m.alias_rows_identity(a['foreignHomeAliasGroups'],rows)
        for row in rows.values():row.pop('ctimeNs')
        with self.assertRaisesRegex(ValueError,'complete actual'):m.alias_rows_identity(a['foreignHomeAliasGroups'],rows)
        rows=copy.deepcopy(a['foreignHomeAliasRows']);next(iter(rows.values()))['ctimeNs']=None
        with self.assertRaises(ValueError):m.alias_rows_identity(a['foreignHomeAliasGroups'],rows)

    def test_rollback_requires_new_success_same_proof_and_admission_new_token(self):
        r={'format':'augmentor-published-freshhome-coordinated/1','mode':'upgrade','phase':'pass',
           'unknownOutcome':False,'pendingRequest':None,'pendingLifecycle':None,'pendingDeployment':None,
           'pendingAction':None,'nativeVersion':'0.2.13','proofSha256':'proof','admissionSha256':'admission',
           'coordinatorSha256':m.COORDINATOR_SHA,'baselineRunSha256':m.BASELINE_RUN_SHA,
           'integrationAndSelectionVerified':True,'modelRequests':0,'persistencePreserved':True,
           'foreignHomeAliasesPreserved':True,'runToken':'f'*64}
        m.rollback_identity(r,synthetic_binding('rollback'),'admission','proof',c)
        for key,value in [('format','augmentor-published-coordinated/1'),('phase','failed-do-not-resume'),
                          ('pendingAction','install'),('proofSha256','old'),('admissionSha256','old'),
                          ('baselineRunSha256',c.BASELINE_RUN_SHA),('runToken','a'*64),
                          ('foreignHomeAliasesPreserved',False),('integrationAndSelectionVerified',False)]:
            with self.subTest(key=key),self.assertRaises(ValueError):m.rollback_identity({**r,key:value},synthetic_binding('rollback'),'admission','proof',c)

    def test_fresh_baseline_requires_known_success_and_unchanged_selected_identity(self):
        a=synthetic_admission()
        record={'format':'augmentor-published-managed-baseline/1','phase':'pass',
                'pendingRequest':None,'pendingLifecycle':None,'pendingDeployment':None,
                'unknownOutcome':False,'proofSha256':m.MANAGED_SHA,'selected':a['baselineSelected'],
                'fullManagedInventoryVerified':True,'coldHistoryPreserved':True,
                'persistencePreserved':True,'coldBaselineJournalPreserved':True,
                'modelRequests':0,'ownedDshExitCode':0,'nativePackageOperation':False,
                'integrationMutation':False,'companionCleanup':{'phase':'pass'}}
        m.baseline_identity(record,a,c)
        for key,value in [('phase','failed-do-not-resume'),('pendingDeployment','activate'),
                          ('selected',{'root':'old160'}),('modelRequests',1),('ownedDshExitCode',1),
                          ('fullManagedInventoryVerified',False),('integrationMutation',True)]:
            with self.subTest(key=key),self.assertRaises(ValueError):m.baseline_identity({**record,key:value},a,c)


class FileAndPreservationTests(unittest.TestCase):
    def root_owner(self, value, uid=0):
        attrs={k:getattr(value,k) for k in dir(value) if k.startswith('st_')}
        attrs.update(st_uid=uid,st_gid=uid)
        return SimpleNamespace(**attrs)

    def test_mutable_ancestor_refuses_before_open_or_import(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name); p=root/'worker.py';p.write_text('raise AssertionError("never imported")')
            original=Path.lstat
            def mocked(path):
                value=self.root_owner(original(path))
                if path==root:value.st_mode=stat.S_IFDIR|0o777
                return value
            with patch.object(Path,'lstat',mocked), patch.object(m.os,'open') as opened, self.assertRaises(ValueError):
                m.pinned_module(p,'never','wrong')
            opened.assert_not_called()

    def test_verified_module_executes_only_hash_bound_bytes(self):
        p=Path('/synthetic/immutable.py'); raw=b'VALUE = 17\n'
        with patch.object(m,'immutable_read',return_value=raw) as read:
            self.assertEqual(m.pinned_module(p,'synthetic',m.digest(raw)).VALUE,17)
            read.assert_called_once_with(p)
            with self.assertRaises(ValueError):m.pinned_module(p,'synthetic','0'*64)

    def test_root_read_closes_fd_and_refuses_changed_identity(self):
        with tempfile.TemporaryDirectory() as name:
            p=Path(name)/'file';p.write_bytes(b'fixed');p.chmod(0o600)
            lstat=Path.lstat;fstat=os.fstat
            def own(path):
                row=self.root_owner(lstat(path))
                if stat.S_ISDIR(row.st_mode):row.st_mode=stat.S_IFDIR|0o755
                return row
            with patch.object(Path,'lstat',own), patch.object(m.os,'fstat',lambda fd:self.root_owner(fstat(fd))):
                self.assertEqual(m.immutable_read(p),b'fixed')
                with patch.object(m.os,'close',wraps=os.close) as closed:
                    original=m.os.read
                    def change(fd,n):
                        chunk=original(fd,n);p.write_bytes(b'changed');return chunk
                    with patch.object(m.os,'read',side_effect=change),self.assertRaises(ValueError):m.immutable_read(p)
                    closed.assert_called_once()

    def test_real_closed_aliases_remain_readonly_and_replacement_refuses(self):
        with tempfile.TemporaryDirectory() as name:
            h=Path(name); first=h/'.local/share/augmentor/dsh-home/profiles/web/node_modules/ws/index.js'
            second=h/'.local/share/pnpm/store/v11/files/ab/abcdef';first.parent.mkdir(parents=True);second.parent.mkdir(parents=True)
            first.write_bytes(b'unchanged');first.chmod(0o600);os.link(first,second)
            lstat=Path.lstat;fstat=os.fstat
            with patch.object(Path,'lstat',lambda p:self.root_owner(lstat(p),1000)),patch.object(c.os,'fstat',lambda fd:self.root_owner(fstat(fd),1000)):
                i=first.lstat(); row=c.hardlink_row(first,i);row.update(uid=1000,gid=1000,mode=0o600,mtimeNs=i.st_mtime_ns,ctimeNs=i.st_ctime_ns)
                names=[str(first.relative_to(h)),str(second.relative_to(h))]
                a={'foreignHomeAliasGroups':{f'{i.st_dev}:{i.st_ino}':names},'foreignHomeAliasRows':{n:row for n in names}}
                self.assertEqual(m.aliases_snapshot(h,a,c,lambda _:None),a['foreignHomeAliasRows'])
                for field,value in [('sha256','0'*64),('uid',0),('mode',0o755),('mtimeNs',0),('ctimeNs',0),('inode',0)]:
                    bad=copy.deepcopy(a);bad['foreignHomeAliasRows'][names[0]][field]=value
                    with self.subTest(field=field),self.assertRaises(ValueError):m.aliases_snapshot(h,bad,c,lambda _:None)
                second.unlink();second.write_bytes(b'unchanged')
                with self.assertRaises(ValueError):m.aliases_snapshot(h,a,c,lambda _:None)

    def test_compact_inventory_receipt_preserves_full_verified_identity(self):
        verified={'deployment':{'root':'/synthetic/new'},'artifactSha256':'artifact','files':{'big':'x'*4300000}}
        receipt=m.compact_stage(verified)
        self.assertTrue(receipt['fullInventoryVerified']);self.assertLess(len(json.dumps(receipt)),1024)
        self.assertEqual(receipt['verifiedInventorySha256'],m.digest(json.dumps(verified,sort_keys=True,separators=(',',':')).encode()))

    def test_explicit_cordis_timestamps_allow_only_same_bytes_and_inode(self):
        before={'path':'/synthetic/cordis.yml','bytes':6,'sha256':'a'*64,'uid':1000,'gid':1000,'mode':0o600,
                'device':1,'inode':2,'nlink':1,'mtimeNs':10,'ctimeNs':11}
        after={**before,'mtimeNs':20,'ctimeNs':21}
        sparse=lambda r:{k:r[k] for k in ('bytes','sha256','uid','gid','mode','mtimeNs')}
        left={'foreign':{'cordis.yml':sparse(before),'foreign.yml':{'sha256':'keep'}}}
        right={'foreign':{'cordis.yml':sparse(after),'foreign.yml':{'sha256':'keep'}}}
        coordinator=SimpleNamespace(integration_preserved=lambda b,a:self.assertEqual(b,a))
        m.fresh_integration_preserved(left,right,before,after,coordinator)
        for field,value in [('path','other'),('bytes',7),('sha256','b'*64),('uid',0),('gid',0),('mode',0o644),
                            ('device',3),('inode',4),('nlink',2)]:
            changed={**after,field:value}
            with self.subTest(field=field),self.assertRaises(ValueError):m.fresh_integration_preserved(left,right,before,changed,coordinator)
        bad=copy.deepcopy(right);bad['foreign']['foreign.yml']['sha256']='changed'
        with self.assertRaises(AssertionError):m.fresh_integration_preserved(left,bad,before,after,coordinator)
        bad=copy.deepcopy(right);bad['foreign']['cordis.yml']['mtimeNs']=22
        with self.assertRaises(ValueError):m.fresh_integration_preserved(left,bad,before,after,coordinator)


class SourceScopeTests(unittest.TestCase):
    def test_historical_worker_is_byte_identical_and_no_runtime_relabel(self):
        self.assertEqual(hashlib.sha256((ROOT/'release/prove-published-linux-coordinated-version.py').read_bytes()).hexdigest(),m.COORDINATOR_SHA)
        source=Path(m.__file__).read_text(); tree=ast.parse(source)
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
        self.assertFalse(any(isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name)
                             and n.func.value.id=='coordinator' and n.func.attr in ('prove','staged_binding_identity','verified_existing_stage') for n in calls))
        for node in ast.walk(tree):
            if isinstance(node,(ast.Assign,ast.AugAssign,ast.AnnAssign)):
                targets=node.targets if isinstance(node,ast.Assign) else [node.target]
                self.assertFalse(any(isinstance(t,ast.Attribute) and isinstance(t.value,ast.Name) and t.value.id in ('coordinator','managed','cold','base','helper') for t in targets))
        self.assertNotIn('integration_after_stage',source)
        self.assertNotIn('apt-get',source)

    def test_fresh_sources_and_root_authority_are_checked_before_native_or_sdk_imports(self):
        source=Path(m.__file__).read_text();body=source[source.index('def prove(mode):'):]
        self.assertLess(body.index('admission_identity('),body.index('pinned_module('))
        self.assertLess(body.index('namespace_identity('),body.index('pinned_module('))
        self.assertLess(body.index("hold('desktop')"),body.index('coordinator.native_audit('))
        self.assertLess(body.index('aliases_before ='),body.index('folder.mkdir('))
        self.assertLess(body.index('protected_before !='),body.index('folder.mkdir('))
        self.assertIn("folder.mkdir(mode=0o700, exist_ok=False)",body)
        self.assertIn('coordinator.action(',body)

    def test_proof_has_no_shadowed_digest_at_earliest_read(self):
        with patch.object(m.os,'umask'), patch.object(m,'immutable_read',side_effect=ValueError('synthetic admission refusal')):
            with self.assertRaisesRegex(ValueError,'synthetic admission refusal'):m.prove('upgrade')
