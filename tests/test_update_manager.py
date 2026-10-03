# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Persisted scheduling and cross-surface races with synthetic release bytes."""
from copy import deepcopy
import json
import hashlib
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services'))
from updates.manager import UpdateManager
from lifecycle.admission import Admission, MaintenanceBusy
from platform_adapters.private_files import atomic_json


class UpdateManagerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name); self.root = self.base / 'app'
        (self.root / 'release').mkdir(parents=True)
        self.product = {'version': '0.2.12', 'channel': 'preview', 'protocols': {'product': 'augmentor/1'},
                        'dataSchema': 1, 'readableDataSchemas': [1]}
        (self.root / 'release/product.json').write_text(json.dumps(self.product))
        self.now = 1000000
        self.calls = []
        self.manager = UpdateManager(self.base / 'private', root=self.root, clock=lambda: self.now, runner=self.helper)
        self.addCleanup(self.manager.close)
        self.release = {'version': '0.2.13', 'build': 2, 'channel': 'preview', 'target': self.manager.current['target'],
                        'releaseUrl': 'https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.13-complete-preview.2',
                        'authenticated': False, 'artifacts': [{'role': 'bundle', 'bytes': 100, 'sha256': hashlib.sha256(b'x'*100).hexdigest(),
                        'targetPath': 'releases/download/v0.2.13-complete-preview.2/app.tar.gz'}]}

    def helper(self, request):
        self.calls.append(request)
        if request['operation'] == 'discover': return {'authenticated': False, 'releases': [deepcopy(self.release)]}
        folder=self.manager.base/'repository';folder.mkdir(mode=0o700,exist_ok=True)
        file=folder/(request['artifact']['sha256']+'.download');file.write_bytes(b'x'*100);file.chmod(0o600)
        return {'authenticated': False, 'file': str(file)}

    def wait(self):
        self.manager.job.join(timeout=3)
        self.assertFalse(self.manager.job.is_alive())
        return self.manager.snapshot()

    def test_discovery_download_and_notification_are_shared_and_persistent(self):
        self.manager.call('updates.check', {}); value = self.wait()
        self.assertEqual(value['phase'], 'available')
        self.assertEqual(value['lastSuccessfulCheck'], self.now)
        self.assertGreaterEqual(value['nextCheck'], self.now + 24*3600)
        self.assertEqual(self.manager.call('updates.notification', {})['build'], 2)
        self.assertIsNone(self.manager.call('updates.notification', {}))
        self.manager.call('updates.download', {}); value = self.wait()
        self.assertEqual(value['phase'], 'ready')
        self.assertNotIn('file', value['downloads'][0])
        folder=Path(self.manager.call('updates.reveal', {})['folder'])
        self.assertEqual((folder/'app.tar.gz').read_bytes(), b'x'*100)
        other = UpdateManager(self.manager.base, root=self.root, clock=lambda: self.now, runner=self.helper)
        self.addCleanup(other.close)
        self.assertEqual(other.snapshot()['phase'], 'ready')
        self.assertIsNone(other.call('updates.notification', {}))

    def test_postpone_skip_and_new_build_notification(self):
        self.manager.check()
        self.manager.call('updates.postpone', {'hours': 48})
        self.assertIsNone(self.manager.call('updates.notification', {}))
        self.now += 48*3600
        self.assertIsNotNone(self.manager.call('updates.notification', {}))
        self.manager.call('updates.skip', {})
        self.manager.state['notifiedRelease'] = None
        self.assertIsNone(self.manager.call('updates.notification', {}))
        self.release['build'] += 1; self.manager.check()
        self.assertIsNotNone(self.manager.call('updates.notification', {}))

    def test_network_failure_retains_previous_success_and_backs_off(self):
        self.manager.check(); previous = self.manager.snapshot()
        def fail(_): raise TimeoutError('Offline')
        self.manager.runner = fail; self.now += 100
        self.manager.call('updates.check', {}); value = self.wait()
        self.assertEqual(value['phase'], 'failed')
        self.assertEqual(value['lastSuccessfulCheck'], previous['lastSuccessfulCheck'])
        self.assertEqual(value['candidate'], previous['candidate'])
        self.assertGreater(value['nextCheck'], self.now)
        self.assertEqual(value['error'], 'Offline')

    def test_channel_change_discards_reply_and_settings_require_revision(self):
        entered = threading.Event(); finish = threading.Event()
        def held(request): entered.set(); finish.wait(2); return self.helper(request)
        self.manager.runner = held
        self.manager.call('updates.check', {}); self.assertTrue(entered.wait(1))
        value = self.manager.snapshot(); preferences = {**value['preferences'], 'channel': 'stable'}
        self.manager.configure({'revision': value['revision'], 'preferences': preferences})
        with self.assertRaises(ValueError): self.manager.configure({'revision': value['revision'], 'preferences': preferences})
        finish.set(); value = self.wait()
        self.assertIsNone(value['candidate']); self.assertEqual(value['preferences']['channel'], 'stable')

    def test_automatic_download_is_opt_in_and_unsigned_install_is_refused(self):
        value = self.manager.snapshot(); preferences = {**value['preferences'], 'automaticDownload': True}
        self.manager.configure({'revision': value['revision'], 'preferences': preferences})
        self.manager.call('updates.check', {}); value = self.wait()
        self.assertEqual(value['phase'], 'ready')
        with self.assertRaises(ValueError):
            self.manager.configure({'revision': value['revision'], 'preferences': {**preferences, 'automaticInstall': True}})
        for method, params in [('updates.install', {}), ('updates.download', {'url': 'https://evil.invalid'}),
                               ('updates.check', {'command': 'shell'}), ('updates.postpone', {'hours': 3})]:
            with self.subTest(method=method), self.assertRaises(ValueError): self.manager.call(method, params)

    def test_download_holds_maintenance_admission_and_cancel_preserves_work(self):
        self.manager.admission = admission = Admission()
        entered = threading.Event()
        def held(_): entered.set(); self.manager.cancelled.wait(2); raise InterruptedError('Cancelled')
        self.manager.runner = held
        self.manager.call('updates.check', {}); self.assertTrue(entered.wait(1))
        with self.assertRaises(MaintenanceBusy):
            admission.control('host.maintenance.prepare', {'token': 'a'*32})
        self.manager.call('updates.cancel', {}); value = self.wait()
        self.assertEqual(value['phase'], 'cancelled')
        self.assertEqual(admission.control('host.maintenance.status', {})['active'], 0)

    def test_corrupt_or_interrupted_state_never_replays_installation(self):
        self.manager.state['phase'] = 'installing'; self.manager.save()
        other = UpdateManager(self.manager.base, root=self.root, runner=self.helper)
        self.addCleanup(other.close)
        self.assertEqual(other.snapshot()['phase'], 'interrupted')
        self.assertEqual(self.calls, [])
        value = deepcopy(self.manager.state); value['downloads'] = [{'file': '/tmp/arbitrary'}]
        atomic_json(self.manager.file, value)
        with self.assertRaises(ValueError): UpdateManager(self.manager.base, root=self.root)
        self.assertEqual(json.loads(self.manager.file.read_text()), value)

    def test_a_new_running_payload_discards_the_old_update_plan(self):
        self.manager.check()
        (self.root/'release/product.json').write_text(json.dumps({**self.product,'version':'0.2.13'}))
        other=UpdateManager(self.manager.base,root=self.root,runner=self.helper)
        self.addCleanup(other.close)
        self.assertIsNone(other.snapshot()['candidate'])
        self.assertEqual(other.snapshot()['phase'],'idle')
        self.assertEqual(other.snapshot()['nextCheck'],0)


if __name__ == '__main__': unittest.main()
