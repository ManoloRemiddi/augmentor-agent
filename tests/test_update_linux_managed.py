# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real isolated selection/locks/journals; imports/UI are explicit inert fixtures."""
import json
import os
import shutil
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))
from lifecycle.posix_startup import Startup
from platform_adapters import locks
from platform_adapters.private_files import descriptor,atomic_json,read_json
from updates.linux_managed import ManagedPlan,load_deployment
from updates.linux_coordinator import LinuxCoordinator
from updates.linux_completion import verify_health


@unittest.skipUnless(sys.platform=='linux','Actual Linux managed selection and flock checks.')
class LinuxManagedTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='augmentor-managed-update-')
        self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name)
        self.data=self.base/'data';self.runtime=self.base/'runtime';self.transactions=self.base/'transactions'
        for folder in (self.data,self.runtime,self.transactions):folder.mkdir(mode=0o700)
        self.tool=load_deployment(self.data);self.tool.check=Mock()
        candidate=self.base/'candidate';(candidate/'release').mkdir(parents=True)
        (candidate/'apps/native/augmentor_linux').mkdir(parents=True)
        (candidate/'apps/native/augmentor_linux/window.py').write_text('--ensure-running')
        product=json.loads((ROOT/'release/product.json').read_text())
        (candidate/'release/product.json').write_text(json.dumps(product))
        (candidate/'release.json').write_text(json.dumps({**product,'component':'desktop','target':'linux-x64',
            'sourceCommit':'a'*40,'update':{'build':1,'automaticInstallQualified':False}}))
        self.tool.atomic(self.data/'desktop.json',{'root':str(candidate),'python':sys.executable,
            'node':'/usr/bin/node','dshService':'fixture-dsh.service','dshEndpoint':'http://127.0.0.1:1'})
        self.source=self.tool.stage(candidate,'inert-source');self.tool.activate(self.source)
        self.target=self.tool.stage(self.source,'inert-target')
        self.selected=read_json(self.data/'desktop.json')
        self.loader=patch('updates.linux_managed.load_deployment',return_value=self.tool)
        self.loader.start();self.addCleanup(self.loader.stop)
        self.health=patch('updates.linux_completion.verify_health',return_value=True)
        self.mock_health=self.health.start();self.addCleanup(self.health.stop)
        self.tool.check.reset_mock()

    def plan(self):return ManagedPlan(self.data,self.source,self.target,development=True)

    def coordinator(self,plan):return LinuxCoordinator(plan,self.runtime,self.runtime/'shared',self.transactions)

    def test_complete_transaction_preflights_live_then_imports_offline_and_preserves_source(self):
        with self.plan() as plan:
            self.assertEqual(self.tool.check.call_args.kwargs,{'connected':True})
            original=plan.source_payload
            coordinator=self.coordinator(plan)
            result=coordinator.run(lambda stage:True)
            self.assertTrue(result['installationComplete']);self.assertFalse(result['reopened'])
            self.assertEqual(read_json(self.data/'desktop.json'),plan.proposed)
            self.assertEqual(read_json(self.data/'desktop.previous.json'),self.selected)
            self.assertEqual(plan.source_payload,original)
            self.assertTrue(self.source.exists());self.assertTrue(self.target.exists())
            self.assertFalse((self.transactions/'active.json').exists())
            self.assertEqual(read_json(Path(result['archive']))['phase'],'complete')
            self.assertEqual([call.kwargs['connected'] for call in self.tool.check.call_args_list],[True,False,False])
            self.mock_health.assert_called_once_with(plan)
            with self.assertRaisesRegex(ValueError,'fresh coordinator'):coordinator.run(lambda stage:True)
        with Startup(self.runtime,transactions=self.transactions):pass

    def test_incompatible_live_preflight_never_prepares_or_changes_selection(self):
        self.tool.check.side_effect=RuntimeError('Exact DSH product version mismatch.')
        with self.assertRaisesRegex(RuntimeError,'version mismatch'):
            with self.plan():pass
        self.assertEqual(read_json(self.data/'desktop.json'),self.selected)
        self.assertFalse((self.transactions/'active.json').exists())

    def test_selection_mutation_before_preparation_cancels_without_apply(self):
        with self.plan() as plan:
            atomic_json(self.data/'desktop.json',{**self.selected,'sourceRef':'external change'})
            with self.assertRaisesRegex(ValueError,'selected bytes changed'):
                self.coordinator(plan).run(lambda stage:True)
            self.assertFalse(plan.applied)
        self.assertFalse((self.transactions/'active.json').exists())

    def test_mode_damage_after_preflight_is_refused_before_pointer_change(self):
        with self.plan() as plan:
            (self.target/'apps/native/augmentor_linux/window.py').chmod(0o700)
            with self.assertRaisesRegex(ValueError,'artifact changed'):
                self.coordinator(plan).run(lambda stage:True)
            self.assertEqual(read_json(self.data/'desktop.json'),self.selected)

    def test_an_unobserved_lifetime_holder_blocks_selection(self):
        with self.plan() as plan:
            fd=descriptor(self.runtime/'installation.lock',writable=True,create=True)
            try:
                locks.flock(fd,locks.LOCK_SH|locks.LOCK_NB)
                with self.assertRaises(BlockingIOError):self.coordinator(plan).run(lambda stage:True)
            finally:os.close(fd)
            self.assertEqual(read_json(self.data/'desktop.json'),self.selected)

    def test_revoked_fresh_authority_before_drain_archives_only_known_cancellation(self):
        with self.plan() as plan:
            with self.assertRaisesRegex(ValueError,'authorization changed') as caught:
                self.coordinator(plan).run(lambda stage:stage=='verified')
            self.assertIsNotNone(getattr(caught.exception,'augmentor_preparation_cancelled',None))
            self.assertFalse((self.transactions/'active.json').exists())
            self.assertEqual(read_json(self.data/'desktop.json'),self.selected)

    def test_failed_health_keeps_applied_selection_and_persistent_barrier(self):
        self.mock_health.side_effect=RuntimeError('Synthetic offline UI failure.')
        with self.plan() as plan:
            with self.assertRaisesRegex(RuntimeError,'offline UI failure'):self.coordinator(plan).run(lambda stage:True)
            self.assertTrue(plan.applied)
            self.assertEqual(read_json(self.data/'desktop.json'),plan.proposed)
            self.assertEqual(read_json(self.data/'desktop.previous.json'),self.selected)
            self.assertEqual(read_json(self.transactions/'active.json')['phase'],'apply-acknowledged')
        with self.assertRaises(RuntimeError):Startup(self.runtime,transactions=self.transactions)

    def test_runtime_profile_changes_in_staged_descriptor_are_not_publisher_authority(self):
        manifest=read_json(self.target/'desktop-release.json')
        manifest['deployment']['dshService']='other-owner.service'
        self.tool.atomic(self.target/'desktop-release.json',manifest)
        with self.assertRaisesRegex(ValueError,'runtime/profile migration'):
            with self.plan():pass
        self.tool.check.assert_not_called()

    def test_public_plan_refuses_development_receipts(self):
        with self.assertRaisesRegex(ValueError,'not qualified'):
            with ManagedPlan(self.data,self.source,self.target):pass
        self.tool.check.assert_not_called()

    def test_unknown_namespace_flush_never_retries_or_clears_pending(self):
        publish=atomic_json
        def uncertain(path,value):
            publish(path,value)
            if Path(path)==self.data/'desktop.json':raise OSError('Synthetic post-replace namespace flush failure.')
        with self.plan() as plan:
            coordinator=self.coordinator(plan)
            with patch('updates.linux_managed.atomic_json',side_effect=uncertain):
                with self.assertRaisesRegex(OSError,'post-replace'):coordinator.run(lambda stage:True)
            self.assertTrue(plan.started);self.assertFalse(plan.applied)
            self.assertEqual(read_json(self.data/'desktop.json'),plan.proposed)
            self.assertEqual(read_json(self.data/'desktop.previous.json'),self.selected)
            self.assertEqual(read_json(self.transactions/'active.json')['phase'],'apply-intent')
            with self.assertRaisesRegex(ValueError,'already attempted'):coordinator.backend.authorize()
            self.mock_health.assert_not_called()


@unittest.skipUnless(sys.platform=='linux','Actual isolated Linux Qt health action.')
class LinuxOfflineHealthTests(unittest.TestCase):
    def test_fixed_target_action_renders_with_disposable_profile(self):
        with tempfile.TemporaryDirectory(prefix='augmentor-linux-target-health-') as temporary:
            root=Path(temporary)
            for part in ('apps/native','services'):
                shutil.copytree(ROOT/part,root/part,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            (root/'scripts').mkdir()
            shutil.copy2(ROOT/'scripts/linux-local-health.py',root/'scripts/linux-local-health.py')
            (root/'release.json').write_text(json.dumps({'version':'0.2.13','sourceCommit':'a'*40,
                'target':'linux-x64','component':'desktop'}))
            # Sentinels are deliberately outside the copied installation. The
            # subprocess must replace inherited profile/service choices before
            # any UI import; it opens preview mode and no real controller.
            sentinel=root/'owner-profile';sentinel.mkdir();(sentinel/'preserved').write_text('unchanged')
            with patch.dict(os.environ,{'XDG_DATA_HOME':str(sentinel),'AUGMENTOR_DSH_ENDPOINT':'http://127.0.0.1:1'}):
                self.assertTrue(verify_health(SimpleNamespace(target=root,proposed={'python':sys.executable})))
            self.assertEqual(list(sentinel.iterdir()),[sentinel/'preserved'])
            self.assertEqual((sentinel/'preserved').read_text(),'unchanged')

    def test_actual_staged_ui_import_selection_and_health_complete_without_service_owners(self):
        with tempfile.TemporaryDirectory(prefix='augmentor-linux-controller-proof-') as temporary:
            base=Path(temporary);candidate=base/'candidate';data=base/'data';runtime=base/'runtime';transactions=base/'transactions'
            for directory in (candidate,data,runtime,transactions):directory.mkdir(mode=0o700)
            for part in ('apps/native','services'):
                shutil.copytree(ROOT/part,candidate/part,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            (candidate/'scripts').mkdir()
            shutil.copy2(ROOT/'scripts/linux-local-health.py',candidate/'scripts/linux-local-health.py')
            (candidate/'release').mkdir()
            product=json.loads((ROOT/'release/product.json').read_text())
            (candidate/'release/product.json').write_text(json.dumps(product))
            (candidate/'release.json').write_text(json.dumps({**product,'component':'desktop','target':'linux-x64',
                'sourceCommit':'b'*40,'update':{'build':1,'automaticInstallQualified':False}}))
            tool=load_deployment(data)
            atomic_json(data/'desktop.json',{'root':str(candidate),'python':sys.executable,'node':shutil.which('node')})
            source=tool.stage(candidate,'real-offline-source')
            tool.activate(source)
            target=tool.stage(source,'real-offline-target')
            with ManagedPlan(data,source,target,development=True) as plan:
                coordinator=LinuxCoordinator(plan,runtime,runtime/'shared',transactions)
                result=coordinator.run(lambda stage:True)
                self.assertTrue(result['installationComplete'])
                self.assertEqual(read_json(data/'desktop.json'),plan.proposed)
                self.assertEqual(read_json(data/'desktop.previous.json'),plan.previous)
                self.assertEqual(read_json(Path(result['archive']))['phase'],'complete')
                self.assertFalse((transactions/'active.json').exists())
            # This empty-graph, same-build development proof launches no normal
            # app, provider or background service and makes no signed-update claim.
