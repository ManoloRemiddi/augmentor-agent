# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual original backend/archive/selection; explicit simulated systemd/peers."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock,patch

import test_update_linux_services as fixtures
from updates.linux_reopen import reopen_dsh_observed
from platform_adapters.private_files import atomic_json,read_json


@unittest.skipUnless(sys.platform=='linux','Owned Linux observed reopening.')
class ReopenTests(unittest.TestCase):
    def scene(self,exercise):
        fixture=fixtures.ServiceTests('runTest');fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.completed_scene(exercise)

    def test_completed_original_service_restarts_once_and_checks_target_connection(self):
        def exercise(coordinator,result,state,run):
            backend=coordinator.backend;plan=backend.plan
            def start(arguments,**kwargs):
                self.assertEqual(arguments,['/usr/bin/systemctl','--user','start','augmentor-dsh.service'])
                state.update(ActiveState='active',SubState='running',MainPID='456')
            run.side_effect=start
            peer=Mock();peer.process.pid=456;peer.process.exited.return_value=False
            with patch('updates.linux_reopen.discover_sockets',return_value=[peer]):
                self.assertTrue(reopen_dsh_observed(backend,result))
                self.assertEqual(plan.tool.check.call_args.args[0],plan.proposed)
                self.assertEqual(plan.tool.check.call_args.kwargs,{'connected':True})
                with self.assertRaisesRegex(ValueError,'one-shot reopening'):reopen_dsh_observed(backend,result)
            self.assertEqual(run.call_count,2)  # Original reload and one normal start.
        self.scene(exercise)

    def test_wrong_completed_archive_or_changed_target_cannot_start_service(self):
        def exercise(coordinator,result,state,run):
            backend=coordinator.backend;archive=Path(result['archive']);record=read_json(archive)
            atomic_json(archive,{**record,'revision':record['revision']+1})
            with self.assertRaisesRegex(ValueError,'exact observed'):reopen_dsh_observed(backend,result)
            atomic_json(archive,record)
            path=backend.plan.target/'apps/browser/plugin/dist/index.js';path.write_bytes(b'Changed target.')
            with self.assertRaisesRegex(ValueError,'artifacts changed'):reopen_dsh_observed(backend,result)
            self.assertFalse(getattr(backend,'service_reopening_started',False));self.assertEqual(run.call_count,1)
        self.scene(exercise)

    def test_failed_start_outcome_cannot_be_replayed(self):
        def exercise(coordinator,result,state,run):
            run.side_effect=OSError('Synthetic uncertain service start.')
            with self.assertRaisesRegex(OSError,'uncertain service start'):reopen_dsh_observed(coordinator.backend,result)
            with self.assertRaisesRegex(ValueError,'one-shot reopening'):reopen_dsh_observed(coordinator.backend,result)
            self.assertEqual(run.call_count,2)
        self.scene(exercise)

    def test_new_pending_attempt_blocks_reopening_even_with_completed_archive(self):
        def exercise(coordinator,result,state,run):
            backend=coordinator.backend
            atomic_json(backend.journal.directory/'active.json',backend.journal.record)
            with self.assertRaisesRegex(RuntimeError,'unfinished Augmentor update'):
                reopen_dsh_observed(backend,result)
            self.assertFalse(getattr(backend,'service_reopening_started',False));self.assertEqual(run.call_count,1)
        self.scene(exercise)

    def test_wrong_target_socket_process_refuses_followup_health_and_retry(self):
        def exercise(coordinator,result,state,run):
            backend=coordinator.backend;checks=backend.plan.tool.check.call_count
            run.side_effect=lambda *args,**kwargs:state.update(ActiveState='active',SubState='running',MainPID='456')
            peer=Mock();peer.process.pid=789;peer.process.exited.return_value=False
            with patch('updates.linux_reopen.discover_sockets',return_value=[peer]):
                with self.assertRaisesRegex(ValueError,'actual target socket peer'):reopen_dsh_observed(backend,result)
            self.assertEqual(backend.plan.tool.check.call_count,checks)
            with self.assertRaisesRegex(ValueError,'one-shot reopening'):reopen_dsh_observed(backend,result)
        self.scene(exercise)

    def test_changed_target_during_connection_health_is_refused_without_restart(self):
        def exercise(coordinator,result,state,run):
            backend=coordinator.backend;plan=backend.plan
            run.side_effect=lambda *args,**kwargs:state.update(ActiveState='active',SubState='running',MainPID='456')
            peer=Mock();peer.process.pid=456;peer.process.exited.return_value=False
            plan.tool.check.side_effect=lambda *args,**kwargs:(plan.target/'apps/browser/plugin/dist/index.js').write_bytes(b'Changed during health.')
            with patch('updates.linux_reopen.discover_sockets',return_value=[peer]):
                with self.assertRaisesRegex(ValueError,'artifacts changed'):reopen_dsh_observed(backend,result)
            self.assertEqual(run.call_count,2)
        self.scene(exercise)
