# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Synthetic ownership and one-shot signal failure checks; no live companion."""
import importlib.util
from pathlib import Path
import signal
import stat
import sys
import types
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('published_legacy', Path(__file__).resolve().parents[1]/'release/published-linux-legacy-companion.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


@unittest.skipUnless(sys.platform == 'linux', 'Explicit Linux fixture contract.')
class PublishedLegacyOwnershipTests(unittest.TestCase):
    def metadata(self, mode=stat.S_IFREG|0o664, uid=0, gid=0, links=1):
        return types.SimpleNamespace(st_mode=mode, st_uid=uid, st_gid=gid, st_nlink=links)

    def check(self, info, **kwargs):
        with patch.object(module.os, 'getuid', return_value=1000), patch.object(module.os, 'getgid', return_value=1000), patch.object(module.os, 'getgroups', return_value=[1000]):
            module.historical_root_metadata(info, **kwargs)

    def test_historical_root_group_write_requires_actual_nonmember_account(self):
        self.check(self.metadata())
        self.check(self.metadata(stat.S_IFDIR|0o775), directory=True)
        with patch.object(module.os, 'getgroups', return_value=[0]), patch.object(module.os, 'getuid', return_value=1000), patch.object(module.os, 'getgid', return_value=1000):
            with self.assertRaises(ValueError): module.historical_root_metadata(self.metadata())

    def test_foreign_owner_group_and_world_write_refuse(self):
        for info in (self.metadata(uid=1000), self.metadata(gid=1000), self.metadata(mode=stat.S_IFREG|0o666)):
            with self.subTest(info=info), self.assertRaises(ValueError): self.check(info)

    def test_links_and_special_types_refuse(self):
        for info in (self.metadata(links=2), self.metadata(mode=stat.S_IFLNK|0o777), self.metadata(mode=stat.S_IFSOCK|0o600)):
            with self.subTest(info=info), self.assertRaises(ValueError): self.check(info)

    def test_root_caller_and_primary_root_group_refuse(self):
        for uid,gid in ((0,1000),(1000,0)):
            with patch.object(module.os, 'getuid', return_value=uid), patch.object(module.os, 'getgid', return_value=gid), patch.object(module.os, 'getgroups', return_value=[]):
                with self.assertRaises(ValueError): module.historical_root_metadata(self.metadata())

    def companion(self):
        value = module.PublishedLegacyCompanion.__new__(module.PublishedLegacyCompanion)
        value.attempted=False; value.child=Mock(pid=4242); value.child.wait.return_value=0
        value.record={'pending':None,'signalSent':False,'unknownOutcome':False}
        value.describe=Mock(); value.process_identity=Mock(return_value={'pid':4242})
        value.matches=Mock(side_effect=[[4242],[]]); value.endpoint=Mock()
        value.endpoint.exists.return_value=False; value.endpoint.is_symlink.return_value=False
        value.save=Mock(); value.log=Mock(); value.dsh_home=Path('/synthetic-owned-home/dsh')
        return value

    def test_normal_child_term_has_durable_intent_then_exact_wait_and_no_fallback(self):
        value=self.companion(); seen=[]
        value.save.side_effect=lambda:seen.append(dict(value.record))
        def signal_sent(sig):
            self.assertEqual(sig,signal.SIGTERM); self.assertEqual(seen[-1]['pending'],'SIGTERM')
            self.assertFalse(seen[-1]['signalSent'])
        value.child.send_signal.side_effect=signal_sent
        with patch.object(module.Path,'iterdir',return_value=iter(())):
            result=value.finish()
        value.child.send_signal.assert_called_once_with(signal.SIGTERM)
        value.child.wait.assert_called_once_with(timeout=15)
        self.assertEqual(result['phase'],'pass');self.assertIsNone(result['pending'])
        value.log.close.assert_called_once()
        with self.assertRaisesRegex(ValueError,'one-shot'): value.finish()
        value.child.send_signal.assert_called_once()

    def test_unknown_signal_is_retained_and_never_retried(self):
        value=self.companion();value.child.send_signal.side_effect=OSError('unknown signal result')
        with patch.object(module.Path,'iterdir',return_value=iter(())), self.assertRaises(OSError):value.finish()
        self.assertTrue(value.record['unknownOutcome']);self.assertEqual(value.record['pending'],'SIGTERM')
        value.child.wait.assert_not_called()
        with self.assertRaisesRegex(ValueError,'one-shot'):value.finish()
        value.child.send_signal.assert_called_once_with(signal.SIGTERM)

    def test_unknown_wait_never_escalates_or_reports_pass(self):
        value=self.companion();value.child.wait.side_effect=module.subprocess.TimeoutExpired('synthetic',15)
        with patch.object(module.Path,'iterdir',return_value=iter(())), self.assertRaises(module.subprocess.TimeoutExpired):value.finish()
        self.assertEqual(value.record['phase'],'failed-do-not-retry');self.assertTrue(value.record['unknownOutcome'])
        value.child.send_signal.assert_called_once_with(signal.SIGTERM);value.child.kill.assert_not_called()

    def test_failed_or_ambiguous_idle_admission_sends_no_signal(self):
        for failure in ('read','ambiguous'):
            value=self.companion()
            if failure=='read':value.describe.side_effect=ValueError('configured or active')
            else:value.matches.side_effect=None;value.matches.return_value=[4242,4243]
            with patch.object(module.Path,'iterdir',return_value=iter(())),self.subTest(failure=failure),self.assertRaises(ValueError):value.finish()
            value.child.send_signal.assert_not_called();self.assertFalse(value.record['unknownOutcome'])


if __name__ == '__main__':unittest.main()
