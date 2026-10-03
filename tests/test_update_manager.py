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
from platform_adapters.private_files import atomic_json, descriptor
from platform_adapters.paths import private_directory
import os
from unittest.mock import Mock,patch
from updates.attempt import write_result


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
        folder=private_directory(self.manager.base/'repository')
        file=folder/(request['artifact']['sha256']+'.download')
        with os.fdopen(descriptor(file,writable=True,create=True),'wb') as output:output.write(b'x'*100)
        return {'authenticated': False, 'file': str(file)}

    def test_unnumbered_development_bundle_uses_valid_preferences_after_restart(self):
        from updates.packaging import build_receipt
        receipt={**self.product,'channel':'development','target':'macos-arm64','sourceCommit':'a'*40,'component':'companion'}
        receipt['update']=build_receipt(version=receipt['version'],source_commit='a'*40,target=receipt['target'],
            channel=receipt['channel'],component='companion')
        (self.root/'release.json').write_text(json.dumps(receipt))
        from unittest.mock import patch
        with patch('updates.policy.machine_target',return_value='macos-arm64'):
            for _ in range(2):
                manager=UpdateManager(self.base/'development',root=self.root,runner=lambda _: {'authenticated':False,'releases':[]})
                try:
                    self.assertEqual(manager.snapshot()['preferences']['channel'],'preview')
                    self.assertFalse(manager.snapshot()['preferences']['automaticChecks'])
                    self.assertFalse(manager.current['buildKnown'])
                    manager.check()
                finally:manager.close()

    def test_unsigned_desktop_discovery_cannot_offer_a_companion_replacement(self):
        self.manager.current['component']='companion'
        with self.assertRaisesRegex(ValueError,'public release discovery'):
            self.manager.check()
        self.assertEqual(self.calls[-1]['component'],'companion')

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
        self.assertEqual(value['phase'], 'ready',value.get('error'))
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
        self.assertEqual(value['phase'], 'ready',value.get('error'))
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


class InstallationControllerTests(unittest.TestCase):
    """Service orchestration with an inert adapter; native/TUF proofs are separate."""
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name).resolve();root=private_directory(self.base/'app')
        (root/'release').mkdir()
        (root/'release/product.json').write_text(json.dumps({'version':'1.0.0','channel':'preview',
            'protocols':{'product':'augmentor/1'},'dataSchema':1,'readableDataSchemas':[1]}))
        self.now=1000000;self.admission=Admission()
        self.manager=UpdateManager(self.base/'state',root=root,admission=self.admission,clock=lambda:self.now)
        self.addCleanup(self.manager.close)
        self.receipts=private_directory(self.base/'receipts')
        self.manager.installation_directory=lambda:self.receipts
        # This adapter never launches an executable or grants install authority.
        self.manager.automatic_capability=Mock(return_value=True)
        self.id='a'*48
        self.manager.launch_installer=Mock(return_value={'started':True,'attempt':self.id})
        payload=b'Independently authored inert installer controller fixture.'
        digest=hashlib.sha256(payload).hexdigest()
        artifact={'role':'installer','targetPath':'releases/download/v1.1.0/app.exe','bytes':len(payload),'sha256':digest}
        self.candidate={'version':'1.1.0','build':2,'sourceCommit':'b'*40,'channel':'preview','target':'windows-x64',
            'installType':'windows-inno','releaseUrl':'https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v1.1.0',
            'protocols':{'product':'augmentor/1'},'dataSchema':1,'readableDataSchemas':[1],'minimumOS':'26200',
            'automaticInstallQualified':True,'artifacts':[artifact]}
        folder=private_directory(self.manager.base/'repository');file=folder/(digest+'.download')
        file.write_bytes(payload)
        self.manager.state.update(phase='ready',candidate=deepcopy(self.candidate),authenticated=True,
            downloads=[{**artifact,'file':str(file)}])
        self.manager.state['preferences'].update(automaticDownload=True,automaticInstall=True)
        self.manager.save()

    def test_download_work_ends_before_install_launch_and_close_does_not_stop_it(self):
        def operation():self.assertEqual(self.admission.active,1)
        def launch():
            self.assertEqual(self.admission.active,0)
            self.assertEqual(self.manager.state['phase'],'installing')
            return {'started':True,'attempt':self.id}
        self.manager.launch_installer.side_effect=launch
        self.manager.work(operation)
        self.assertEqual(self.manager.state['installAttempt'],self.id)
        self.assertTrue(self.manager.snapshot()['busy'])
        self.assertIsNone(self.manager.process)
        with self.assertRaises(ValueError):self.manager.call('updates.cancel',{})
        with self.assertRaises(ValueError):self.manager.call('updates.check',{})
        self.manager.close();self.manager.launch_installer.assert_called_once()

    def test_current_local_work_defers_launch_without_shutdown_or_busy_polling(self):
        with self.admission.work():self.assertFalse(self.manager.attempt_install())
        self.assertEqual(self.manager.state['phase'],'ready')
        self.assertEqual(self.manager.state['nextInstallAttempt'],self.now+300)
        self.manager.launch_installer.assert_not_called()
        self.assertFalse(self.manager.attempt_install())
        self.now+=300;self.assertTrue(self.manager.attempt_install())

    def test_no_launch_without_consent_downloads_qualification_or_when_skipped(self):
        original=deepcopy(self.manager.state)
        changes=[('automaticInstall',False),('automaticDownload',False),('authenticated',False),
                 ('downloads',[]),('qualified',False),('postponedUntil',self.now+1),
                 ('skippedRelease',self.manager.release_id()),('installationBlocked',True)]
        for field,value in changes:
            with self.subTest(field=field):
                self.manager.state=deepcopy(original)
                if field in ('automaticInstall','automaticDownload'):self.manager.state['preferences'][field]=value
                elif field=='qualified':self.manager.state['candidate']['automaticInstallQualified']=value
                else:self.manager.state[field]=value
                self.assertFalse(self.manager.attempt_install())
        self.manager.launch_installer.assert_not_called()

    def test_live_deferred_result_can_schedule_a_fresh_attempt_after_delay(self):
        self.assertTrue(self.manager.attempt_install())
        write_result(self.receipts,self.id,'deferred',candidate=self.candidate,transaction='c'*48,error='Busy fixture')
        self.manager.collect_installation_result()
        self.assertEqual(self.manager.state['phase'],'ready')
        self.assertFalse(self.manager.state['installationBlocked'])
        self.assertIsNone(self.manager.state['installAttempt'])
        self.assertFalse(self.manager.attempt_install())
        self.now+=300;self.manager.launch_installer.return_value={'started':True,'attempt':'d'*48}
        self.assertTrue(self.manager.attempt_install())
        self.assertEqual(self.manager.launch_installer.call_count,2)

    def test_unknown_launch_or_failed_result_blocks_automatic_resubmission(self):
        self.manager.launch_installer.side_effect=TimeoutError('Lost launch reply')
        self.assertFalse(self.manager.attempt_install())
        self.assertTrue(self.manager.state['installationBlocked'])
        self.manager.state['phase']='ready';self.now+=3600
        self.assertFalse(self.manager.attempt_install());self.manager.launch_installer.assert_called_once()
        self.manager.launch_installer.side_effect=None;self.manager.state['installationBlocked']=False
        self.assertTrue(self.manager.attempt_install())
        write_result(self.receipts,self.id,'failed',error='Unknown installer outcome')
        self.manager.collect_installation_result()
        self.assertEqual(self.manager.state['phase'],'failed');self.assertTrue(self.manager.state['installationBlocked'])

    def test_receipt_never_changes_running_identity_or_executes_recovery_reopen(self):
        original=deepcopy(self.manager.current)
        self.assertTrue(self.manager.attempt_install())
        write_result(self.receipts,self.id,'target-healthy',candidate=self.candidate,transaction='e'*48,reopened=True)
        value=self.manager.snapshot()
        self.assertEqual(value['phase'],'installed');self.assertEqual(value['installed'],original)
        self.manager.launch_installer.assert_called_once()

    def test_invalid_result_and_invalid_persisted_launch_id_are_preserved(self):
        self.assertTrue(self.manager.attempt_install())
        file=self.receipts/('attempt-'+self.id+'.json');file.write_bytes(b'{"command":"untrusted"}')
        self.manager.collect_installation_result()
        self.assertTrue(self.manager.state['installationBlocked']);self.assertEqual(file.read_bytes(),b'{"command":"untrusted"}')
        self.manager.state['installAttempt']='../../untrusted';self.manager.save()
        with self.assertRaises(ValueError):UpdateManager(self.manager.base,root=self.manager.root)


if __name__ == '__main__': unittest.main()
