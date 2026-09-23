# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'services'))
from recovery import RecoveryError, recover, repair_history, start_dsh, repair_adaptive_history, recover_saved_session

class HistoryRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)/'home'
        self.session = self.home/'sessions/workspace/chat'; self.session.mkdir(parents=True)
        self.env = patch.dict(os.environ, {'XDG_STATE_HOME':str(Path(self.tmp.name)/'state')})
        self.env.start(); self.addCleanup(self.env.stop)
        self.plain = self.session/'session.v3.jsonl'
        self.compressed = Path(str(self.plain)+'.zstd')
    def pair(self, plain=b'old\n', compressed=b'old\nnew\n'):
        self.plain.write_bytes(plain)
        self.compressed.write_bytes(subprocess.run(['node','-e', "process.stdout.write(require('node:zlib').zstdCompressSync(require('node:fs').readFileSync(0)))"], input=compressed, capture_output=True, check=True).stdout)
    def test_prefix_repair_has_verified_backup_and_keeps_newer_history(self):
        self.pair(); compressed = self.compressed.read_bytes()
        backup = repair_history(self.home, Mock())
        self.assertFalse(self.plain.exists()); self.assertEqual(self.compressed.read_bytes(), compressed)
        row = json.loads((backup/'manifest.jsonl').read_text())
        self.assertEqual(Path(row['backup']).read_bytes(), b'old\n')
        self.assertEqual(Path(row['backup']).stat().st_mode & 0o777, 0o600)
    def test_divergence_preserves_both(self):
        self.pair(b'other\n')
        with self.assertRaisesRegex(RecoveryError, 'differ'): repair_history(self.home, Mock())
        self.assertEqual(self.plain.read_bytes(), b'other\n'); self.assertTrue(self.compressed.exists())
    def test_missing_counterpart_preserves_plain(self):
        self.plain.write_bytes(b'only history\n')
        with self.assertRaisesRegex(RecoveryError, 'counterpart'): repair_history(self.home, Mock())
        self.assertTrue(self.plain.exists())
    def test_active_session_is_not_modified(self):
        self.pair()
        with (self.session/'session.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(RecoveryError, 'using'): repair_history(self.home, Mock())
        self.assertTrue(self.plain.exists())
    def test_symlink_is_not_followed(self):
        self.pair(); self.plain.unlink()
        external = Path(self.tmp.name)/'outside'; external.write_bytes(b'old\n'); self.plain.symlink_to(external)
        with self.assertRaisesRegex(RecoveryError, 'ordinary'): repair_history(self.home, Mock())
        self.assertEqual(external.read_bytes(), b'old\n')
    def test_corrupt_compressed_file_is_not_a_success(self):
        self.pair(); self.compressed.write_bytes(b'broken')
        with self.assertRaisesRegex(RecoveryError, 'verified'): repair_history(self.home, Mock())
        self.assertTrue(self.plain.exists())
    def test_known_error_repairs_then_rechecks_without_prompt(self):
        self.pair(); client = Mock(home=self.home)
        client.session_rows.side_effect = [RuntimeError('backend configured for compression "zstd"'), [{'sessionId':'chat'}]]
        recover(client, 'dsh', Mock())
        self.assertEqual(client.session_rows.call_count, 2); client.model_catalog.assert_called_once()
        self.assertEqual([c.args[0] for c in client.call.call_args_list], ['host.describe'])
    def test_unknown_storage_failure_does_not_modify_files(self):
        self.pair(); client = Mock(home=self.home); client.session_rows.side_effect = RuntimeError('disk full')
        with self.assertRaisesRegex(RuntimeError, 'disk full'): recover(client, 'dsh', Mock())
        self.assertTrue(self.plain.exists())
    def test_missing_server_starts_then_checks_history(self):
        client = Mock(home=self.home, base='http://127.0.0.1:3080'); client.call.side_effect = [ConnectionRefusedError(), {}]; client.session_rows.return_value = []
        with patch('recovery.start_dsh') as start, patch('recovery.port_open', return_value=False): recover(client, 'dsh', Mock())
        start.assert_called_once(); client.session_rows.assert_called_once()
    def test_occupied_port_is_never_killed(self):
        client = Mock(base='http://127.0.0.1:3080', home=self.home)
        client.call.side_effect=RuntimeError('unidentified service')
        with patch('dsh.setup.current', return_value={'endpoint':client.base,'home':str(self.home)}), patch('recovery.port_open', return_value=True), patch('recovery.subprocess.Popen') as spawn:
            with self.assertRaisesRegex(RecoveryError, 'occupied'): start_dsh(client, Mock())
        spawn.assert_not_called()

    def test_running_server_keeps_original_error(self):
        client = Mock(base='http://127.0.0.1:3080', home=self.home)
        client.call.side_effect = RuntimeError('integration version mismatch')
        with patch('recovery.port_open', return_value=True), patch('recovery.start_dsh') as start:
            with self.assertRaisesRegex(RecoveryError, 'integration version mismatch'): recover(client, 'dsh', Mock())
        start.assert_not_called()

    def test_managed_server_uses_service_and_never_detaches_duplicate(self):
        client = Mock(base='http://127.0.0.1:3080', home=self.home)
        with patch.dict(os.environ, {'AUGMENTOR_DSH_SERVICE':'dsh-web.service'}), patch('dsh.setup.current', return_value={'endpoint':client.base,'home':str(self.home)}), patch('recovery.port_open', side_effect=[False,False,True]), patch('recovery.subprocess.run', return_value=Mock(returncode=0)) as run, patch('recovery.subprocess.Popen') as spawn:
            start_dsh(client, Mock())
        run.assert_called_once(); self.assertEqual(run.call_args.args[0], ['systemctl','--user','start','dsh-web.service']); spawn.assert_not_called()


class AdaptiveHistoryRecoveryTests(unittest.TestCase):
    setUp = HistoryRecoveryTests.setUp
    def legacy(self):
        records = [{'type':'session','version':3,'id':'chat'},
                   {'type':'adaptive-reasoning/decision','seq':0,'time':1,'data':{'version':2,'turn':1,'step':1}},
                   {'type':'user/message','seq':1,'time':2,'data':{'text':'preserve exactly'}},
                   {'type':'adaptive-reasoning/measurement','seq':2,'time':3,'data':{'version':1,'turn':1,'step':1}}]
        # Multiple frames, as real DSH appends. A single-frame decoder misses the bug.
        raw = [json.dumps(r).encode()+b'\n' for r in records]
        self.compressed.write_bytes(b''.join(subprocess.run(['node','-e', "process.stdout.write(require('node:zlib').zstdCompressSync(require('node:fs').readFileSync(0)))"], input=line, capture_output=True, check=True).stdout for line in raw))
        return records

    def test_legacy_repair_preserves_all_records_and_original_backup(self):
        records = self.legacy(); original = self.compressed.read_bytes()
        backup = repair_adaptive_history(self.home, 'chat', Mock())
        self.assertEqual((backup/self.compressed.name).read_bytes(), original)
        decoded = subprocess.run(['node',str(Path(__file__).resolve().parents[1]/'services/recovery/decode-zstd.mjs'),str(self.compressed)], capture_output=True, check=True).stdout
        after = [json.loads(line) for line in decoded.splitlines()]
        self.assertEqual([e.pop('ignorable',None) for e in after], [None,True,None,True])
        self.assertEqual(after, records)
        self.assertIsNone(repair_adaptive_history(self.home, 'chat', Mock()))

    def test_busy_legacy_chat_is_never_rewritten(self):
        self.legacy(); before = self.compressed.read_bytes()
        with (self.session/'session.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(RecoveryError, 'still open'): repair_adaptive_history(self.home,'chat',Mock())
        self.assertEqual(self.compressed.read_bytes(), before)

    def test_unknown_required_event_does_not_trigger_repair(self):
        self.legacy(); client=Mock(home=self.home)
        client.call.side_effect=RuntimeError('event type "future/required" unknown to this harness')
        with patch('recovery.repair_adaptive_history') as repair:
            with self.assertRaisesRegex(RuntimeError, 'future/required'):recover_saved_session(client,'chat',Mock())
        repair.assert_not_called()

    def test_corrupt_legacy_file_is_preserved(self):
        self.compressed.write_bytes(b'corrupt')
        with self.assertRaisesRegex(RecoveryError, 'verification failed'):repair_adaptive_history(self.home,'chat',Mock())
        self.assertEqual(self.compressed.read_bytes(),b'corrupt')

class ControllerRecoveryTests(unittest.TestCase):
    def test_unreadable_saved_chat_does_not_disable_the_app_or_erase_pointer(self):
        from augmentor_linux.controller import Controller
        from augmentor_linux.pi_client import ContractError
        client = Mock()
        client.harness='dsh'; client.preset='augmentor-linux-product'
        client.session_rows.return_value=[{'sessionId':'owned','cwd':'/tmp','agentPreset':client.preset}]
        def call(method, payload=None):
            if method=='session.create': raise ContractError('event type "adaptive-reasoning/decision" unknown to this harness')
            return {}
        client.call.side_effect=call;client.saved_chats.return_value=[];client.model_catalog.return_value={}
        controller=Controller(client=client);controller.session='owned';controller.save_session=Mock()
        controller.subscribe=lambda sid:setattr(controller,'connected',True)
        controller.recover_connection()
        self.assertTrue(controller.online);self.assertIsNone(controller.session)
        self.assertEqual(controller.unavailable_session,'owned');controller.save_session.assert_not_called()
        self.assertNotIn('session.prompt',[c.args[0] for c in client.call.call_args_list])
        controller.close()

    def test_transient_network_failure_never_detaches_saved_chat(self):
        from augmentor_linux.controller import Controller
        controller=Controller(client=Mock());controller.session='owned'
        controller.client.call.side_effect=TimeoutError('slow startup')
        with self.assertRaises(TimeoutError):controller.recover_connection()
        self.assertEqual(controller.session,'owned');self.assertIsNone(controller.unavailable_session)
        controller.close()

    def test_dsh_refusal_starts_runtime_without_resending_a_prompt(self):
        from augmentor_linux.controller import Controller
        import urllib.error
        client=Mock();client.harness='dsh';client.call.side_effect=[urllib.error.URLError(ConnectionRefusedError()),{}]
        client.saved_chats.return_value=[];client.model_catalog.return_value={}
        controller=Controller(client=client);controller.subscribe=lambda sid:setattr(controller,'connected',True)
        with patch('recovery.start_dsh') as start:controller.recover_connection()
        start.assert_called_once();self.assertTrue(controller.online)
        self.assertEqual([c.args[0] for c in client.call.call_args_list],['host.describe','host.describe'])
        controller.close()

    def test_worker_reconnects_and_preserves_selection(self):
        from augmentor_linux.controller import Controller
        controller = Controller(client=Mock()); controller.selection = {'provider':'local','model':'chosen'}
        controller.task = lambda fn: fn()
        def connected(**_): controller.online = True
        controller.recover_connection = connected
        with patch('recovery.recover') as repair: self.assertTrue(controller.repair_connection())
        repair.assert_called_once(); self.assertEqual(controller.selection, {'provider':'local','model':'chosen'})
        self.assertTrue(controller.online); self.assertFalse(controller.repairing); controller.client.call.assert_not_called(); controller.close()
    def test_active_turn_blocks_repair(self):
        from augmentor_linux.controller import Controller
        controller = Controller(client=Mock()); controller.running = controller.online = True
        with patch('recovery.recover') as repair: self.assertFalse(controller.repair_connection())
        repair.assert_not_called(); controller.running = False; controller.close()
    def test_failure_exposes_error_and_releases_locks(self):
        from augmentor_linux.controller import Controller
        controller = Controller(client=Mock()); controller.task = lambda fn: fn()
        with patch('recovery.recover', side_effect=RuntimeError('history conflict')): self.assertTrue(controller.repair_connection())
        self.assertEqual(controller.last_connection_error, 'history conflict')
        self.assertFalse(controller.recovery_lock.locked()); self.assertFalse(controller.repairing); controller.close()

class RecoveryDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])
    def test_one_click_runs_worker_and_displays_verified_result(self):
        import time
        from PySide6.QtWidgets import QWidget
        from augmentor_linux.controller import Controller
        from augmentor_linux.recovery import RecoveryDialog
        owner = QWidget(); owner.controller = Controller(client=Mock())
        def connected(**_): owner.controller.online = True
        owner.controller.recover_connection = connected
        with patch('recovery.recover', side_effect=lambda c,h,emit: emit('History verified')):
            dialog = RecoveryDialog(owner); dialog.show()
            until = time.monotonic()+3
            while time.monotonic() < until:
                self.app.processEvents()
                if 'conversation is ready' in dialog.progress.toPlainText(): break
                time.sleep(.01)
            self.assertIn('History verified', dialog.progress.toPlainText())
            self.assertIn('conversation is ready', dialog.progress.toPlainText())
            self.assertTrue(dialog.close_button.isEnabled()); self.assertFalse(dialog.active)
            dialog.accept()
        owner.controller.close(); owner.close()
    def test_recovery_dialog_cannot_close_while_working(self):
        from PySide6.QtWidgets import QWidget
        from augmentor_linux.controller import Controller
        from augmentor_linux.recovery import RecoveryDialog
        owner = QWidget(); owner.controller = Controller(client=Mock())
        owner.controller.repair_connection = lambda: True
        dialog = RecoveryDialog(owner); dialog.show(); self.app.processEvents()
        dialog.reject(); self.assertTrue(dialog.isVisible()); self.assertFalse(dialog.close_button.isEnabled())
        dialog.finished_repair(False, 'Both conflicting copies were preserved.')
        self.assertIn('preserved', dialog.progress.toPlainText()); self.assertTrue(dialog.retry.isEnabled())
        dialog.reject(); owner.controller.close(); owner.close()
