# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real registration/completion files; explicit service and window process mocks."""
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock,patch

import test_update_linux_services as fixtures
from updates.linux_desktop import OwnedDesktopPlan,render,UNIT
from updates.linux_reopen import reopen_desktop_observed


@unittest.skipUnless(sys.platform=='linux','Owned Linux desktop reopening.')
class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ServiceTests('runTest');self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)

    def owner(self,*,active=True):
        f=self.fixture.fixture;data=f.base/'data/augmentor';data.mkdir(parents=True,mode=0o700);data.parent.chmod(0o700)
        self.env=patch.dict(os.environ,{'XDG_DATA_HOME':str(data.parent)});self.env.start();self.addCleanup(self.env.stop)
        for root in (f.source,f.target):
            (root/'scripts').mkdir();(root/'scripts/desktop-launch.py').write_bytes(b'# Synthetic owned launcher\n')
        launcher=data/'desktop-launch.py';launcher.write_bytes(b'# Synthetic owned launcher\n');launcher.chmod(0o600)
        unit=self.fixture.config/'systemd/user'/UNIT;unit.write_bytes(render(launcher));unit.chmod(0o600)
        state={**self.fixture.report,'Id':UNIT,'FragmentPath':str(unit),'MainPID':'234'}
        if not active:state.update(ActiveState='inactive',SubState='dead',MainPID='0')
        registration=self.fixture.fixture.plan(bind=False)
        with patch.object(OwnedDesktopPlan,'query',return_value=state.copy()):owner=OwnedDesktopPlan(registration,data)
        return owner,state

    def graph(self,owner,*,main=True,pid=234):
        process=Mock(pid=pid,closed=False);process.exited.return_value=False
        return SimpleNamespace(root=owner.registration.source,
            windows=[SimpleNamespace(process=process,endpoint=Path('/fixture/augmentor-linux-pi.sock'))] if main else [],
            reopen_plan=lambda:{'instances':['main'] if main else [],'hadBrowser':False})

    def test_actual_main_peer_required_and_normal_exit_observed(self):
        owner,state=self.owner();graph=self.graph(owner)
        with patch.object(owner,'query',return_value=state.copy()):
            owner.bind(graph);self.assertTrue(owner.validate_preparation())
            with self.assertRaisesRegex(ValueError,'original desktop exit'):owner.require_drained()
        graph.windows[0].process.exited.return_value=True
        with patch.object(owner,'query',return_value={**state,'ActiveState':'inactive','SubState':'dead','MainPID':'0'}):
            self.assertTrue(owner.validate_preparation());owner.require_drained()
        self.assertTrue(owner.drained)

    def test_wrong_peer_or_external_main_cannot_bind(self):
        owner,state=self.owner()
        with patch.object(owner,'query',return_value=state.copy()):
            with self.assertRaisesRegex(ValueError,'actual reserved'):owner.bind(self.graph(owner,pid=999))
        self.assertFalse(owner.bound)

    def test_inactive_owner_preserves_no_main_and_refuses_external_main(self):
        owner,state=self.owner(active=False)
        with patch.object(owner,'query',return_value=state.copy()):
            with self.assertRaisesRegex(ValueError,'externally owned'):owner.bind(self.graph(owner))
            owner.bind(self.graph(owner,main=False));owner.require_drained()
        self.assertEqual(owner.instances,());self.assertFalse(owner.was_running)

    def test_live_restart_enablement_and_dropin_changes_refused(self):
        owner,state=self.owner()
        for changes in ({'MainPID':'999'},{'UnitFileState':'disabled'},{'DropInPaths':'/fixture/custom.conf'}):
            with self.subTest(changes=changes),patch.object(owner,'query',return_value={**state,**changes}):
                with self.assertRaises(ValueError):owner.validate_preparation()
        self.assertFalse(owner.drained)

    def test_custom_launcher_refused_before_registration_mutation(self):
        owner,_=self.owner();owner.launcher.write_bytes(b'# Customized launcher\n')
        registration=self.fixture.fixture.plan(bind=False)
        with self.assertRaisesRegex(ValueError,'customized'):OwnedDesktopPlan(registration,owner.data)
        self.assertNotIn('desktop-launcher',registration.anchors)

    def scene(self,exercise):self.fixture.completed_scene(exercise,desktop=True)

    def peers(self,backend):
        peers=[]
        for name,pid in (('main',456),('secondary',457)):
            peer=Mock();peer.endpoint=backend.gate.path.parent/('augmentor-linux-pi'+('' if name=='main' else '-'+name)+'.sock')
            peer.process.pid=pid;peer.process.exited.return_value=False
            peer.exchange.return_value={'online':True,'repairing':False,'sessionRestoreError':''}
            peers.append(peer)
        return peers

    def launching(self,backend):
        desktop=backend.plan.desktop
        inactive=desktop.query();active={**inactive,'ActiveState':'active','SubState':'running','MainPID':'456'}
        state=inactive.copy()
        def start(arguments,**kwargs):
            self.assertEqual(arguments,['/usr/bin/systemctl','--user','start',UNIT]);state.update(active)
        child=Mock(pid=457);child.poll.return_value=None
        return state,start,child

    def test_original_completed_owner_main_and_named_window_reopen_once(self):
        def exercise(coordinator,result,state,run):
            backend=coordinator.backend;backend.service_reopened=True;desktop=backend.plan.desktop
            state,start,child=self.launching(backend)
            peers=self.peers(backend)
            with patch.object(desktop,'query',side_effect=lambda:state.copy()),patch(
                    'updates.linux_reopen.subprocess.run',side_effect=start) as start_run,patch(
                    'updates.linux_reopen.subprocess.Popen',return_value=child) as launch,patch(
                    'updates.linux_reopen.discover_sockets',return_value=peers):
                self.assertTrue(reopen_desktop_observed(backend,coordinator.reopen_plan,result))
                self.assertEqual(start_run.call_count,1);self.assertEqual(launch.call_count,1)
                self.assertEqual(launch.call_args.args[0],['/usr/bin/python3','-I','-B',str(desktop.launcher),
                    '--ensure-running','--instance','secondary'])
                self.assertNotIn('PYTHONPATH',launch.call_args.kwargs['env'])
                with self.assertRaisesRegex(ValueError,'one-shot'):reopen_desktop_observed(backend,coordinator.reopen_plan,result)
            for peer in peers:peer.close.assert_called_once()
        self.scene(exercise)

    def test_changed_capture_or_missing_target_service_completion_refuses_before_launch(self):
        def exercise(coordinator,result,state,run):
            backend=coordinator.backend
            with self.assertRaisesRegex(ValueError,'original captured'):
                reopen_desktop_observed(backend,{'instances':['main'],'hadBrowser':False},result)
            with self.assertRaisesRegex(ValueError,'target DSH'):reopen_desktop_observed(backend,coordinator.reopen_plan,result)
            self.assertFalse(getattr(backend,'desktop_reopening_started',False));self.assertEqual(run.call_count,1)
        self.scene(exercise)

    def test_unknown_start_outcome_and_partial_launch_cannot_replay(self):
        def exercise(coordinator,result,state,run):
            backend=coordinator.backend;backend.service_reopened=True
            with patch('updates.linux_reopen.subprocess.run',side_effect=TimeoutError('Synthetic unknown start.')) as start:
                with self.assertRaisesRegex(TimeoutError,'unknown start'):reopen_desktop_observed(backend,coordinator.reopen_plan,result)
                with self.assertRaisesRegex(ValueError,'one-shot'):reopen_desktop_observed(backend,coordinator.reopen_plan,result)
                self.assertEqual(start.call_count,1)
        self.scene(exercise)

    def test_wrong_actual_window_owner_refuses_without_replay(self):
        def exercise(coordinator,result,state,run):
            backend=coordinator.backend;backend.service_reopened=True;desktop=backend.plan.desktop
            state,start,child=self.launching(backend);peers=self.peers(backend);peers[1].process.pid=999
            with patch.object(desktop,'query',side_effect=lambda:state.copy()),patch(
                    'updates.linux_reopen.subprocess.run',side_effect=start),patch(
                    'updates.linux_reopen.subprocess.Popen',return_value=child),patch(
                    'updates.linux_reopen.discover_sockets',return_value=peers):
                with self.assertRaisesRegex(ValueError,'actual target owner'):reopen_desktop_observed(backend,coordinator.reopen_plan,result)
                with self.assertRaisesRegex(ValueError,'one-shot'):reopen_desktop_observed(backend,coordinator.reopen_plan,result)
        self.scene(exercise)

    def test_failed_conversation_restore_preserves_target_and_refuses_restart(self):
        def exercise(coordinator,result,state,run):
            backend=coordinator.backend;backend.service_reopened=True;desktop=backend.plan.desktop
            state,start,child=self.launching(backend);peers=self.peers(backend)
            peers[1].exchange.return_value={'sessionRestoreError':'Synthetic restoration failure.'}
            with patch.object(desktop,'query',side_effect=lambda:state.copy()),patch(
                    'updates.linux_reopen.subprocess.run',side_effect=start),patch(
                    'updates.linux_reopen.subprocess.Popen',return_value=child),patch(
                    'updates.linux_reopen.discover_sockets',return_value=peers):
                with self.assertRaisesRegex(ValueError,'restore its saved'):reopen_desktop_observed(backend,coordinator.reopen_plan,result)
                with self.assertRaisesRegex(ValueError,'one-shot'):reopen_desktop_observed(backend,coordinator.reopen_plan,result)
            self.assertEqual(backend.plan.tool.verify(backend.plan.target),backend.plan.target_manifest)
        self.scene(exercise)
