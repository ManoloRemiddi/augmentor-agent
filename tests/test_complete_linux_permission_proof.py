# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('permission_legacy_helpers', ROOT/'tests/test_complete_linux_fresh_proof.py')
legacy = importlib.util.module_from_spec(spec); spec.loader.exec_module(legacy)
proof = legacy.proof


def binding(scope=None):
    scope = scope or proof.MINT_PERMISSION_SCOPE
    return {**legacy.binding(), 'format': scope.format, 'sourceCommit': scope.source,
        'artifactId': scope.artifact, 'bundleManifestSha256': scope.manifest_sha, 'setupSha256': scope.setup_sha,
        'uid': scope.uid, 'gid': scope.uid, 'user': scope.user, 'home': str(scope.home),
        'protectedAccountsSha256': scope.protected_sha,
        'protectedAccountsPath': str(proof.MINT_PERMISSION_STAGE/'protected-accounts.json'),
        'protectedPreflightPath': str(proof.MINT_PERMISSION_STAGE/'protected-preflight.json')}


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux finite proof')
class PermissionAdmission(unittest.TestCase):
    def test_profiles_refuse_each_others_artifact_account_and_journal_identity(self):
        new = binding(); proof.fresh_binding(new, scope=proof.MINT_PERMISSION_SCOPE)
        proof.fresh_binding(legacy.binding())
        with self.assertRaises(ValueError): proof.fresh_binding(new)
        with self.assertRaises(ValueError): proof.fresh_binding(legacy.binding(), scope=proof.MINT_PERMISSION_SCOPE)
        for field, value in (('uid', 1002), ('sourceCommit', proof.FRESH_SOURCE),
                             ('protectedAccountsSha256', '0'*64), ('protectedAccountsPath', '/tmp/adopted'),
                             ('protectedPreflightPath', '/tmp/adopted'), ('priorFailure', {})):
            with self.subTest(field=field), self.assertRaises(ValueError):
                proof.fresh_binding({**new, field: value}, scope=proof.MINT_PERMISSION_SCOPE)
        with self.assertRaises(ValueError): proof.fresh_scope(proof.MINT_PERMISSION_SCOPE._replace(uid=1004))

    def test_new_cli_refuses_foreign_or_special_metadata_before_reading_or_starting(self):
        for mode, owner in ((stat.S_IFIFO|0o600, 0), (stat.S_IFREG|0o644, 1003)):
            with self.subTest(mode=mode,owner=owner), patch.object(sys, 'argv',
                    ['proof', '--bundle', '/synthetic', '--owned-vm-mint-permission-fixture', '/synthetic/root.json']), \
                    patch.object(Path, 'lstat', return_value=SimpleNamespace(st_mode=mode,st_uid=owner,st_nlink=1,st_size=100)), \
                    patch.object(Path, 'read_bytes') as read, patch.object(proof, 'mint_permission_emulated_proof') as start:
                with self.assertRaises(SystemExit): proof.main()
                read.assert_not_called(); start.assert_not_called()

    def test_new_profile_empty_state_refusal_precedes_native_or_installer_use(self):
        for name in ('.local/share/augmentor', '.local/state/augmentor-install', 'fresh-permission-proof365'):
            with tempfile.TemporaryDirectory() as directory:
                home = Path(directory); (home/name).mkdir(parents=True)
                scope = proof.MINT_PERMISSION_SCOPE._replace(home=home)
                with patch.object(proof, 'MINT_PERMISSION_SCOPE', scope), patch.object(proof, 'fresh_vm_identity'), \
                        patch.object(proof, 'fresh_native_bundle') as native:
                    with self.assertRaisesRegex(ValueError, 'absent application'):
                        proof.validate_fresh_fixture(home, binding(scope), scope=scope)
                    native.assert_not_called()

    def test_new_account_euid_mismatch_refuses_before_any_private_old_home_read(self):
        with patch.object(proof.os, 'getuid', return_value=1003), patch.object(proof.os, 'geteuid', return_value=1002), \
                patch.object(proof, 'permission_protected_files') as private:
            with self.assertRaisesRegex(ValueError, 'ordinary fresh Mint account'):
                proof.fresh_vm_identity(binding(), scope=proof.MINT_PERMISSION_SCOPE)
            private.assert_not_called()

    def test_new_exclusive_journal_binds_source_fixture_and_proof_without_adoption(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = proof.MINT_PERMISSION_SCOPE._replace(home=Path(directory))
            with patch.object(proof, 'MINT_PERMISSION_SCOPE', scope):
                fixture = binding(scope); root, record = proof.begin_fresh_run(fixture, scope=scope)
                original = (root/'run.json').read_bytes()
                self.assertEqual(record['sourceCommit'], scope.source)
                proof.fresh_audit_record(record, fixture, scope=scope)
                with self.assertRaises(ValueError): proof.fresh_audit_record(record, legacy.binding(), scope=scope)
                with self.assertRaises(ValueError): proof.fresh_audit_record(record, {**fixture, 'proofScriptSha256': '0'*64}, scope=scope)
                with self.assertRaisesRegex(ValueError, 'no run or action'):
                    proof.begin_fresh_run({**fixture, 'runToken': 'cd'*16}, scope=scope)
                self.assertEqual((root/'run.json').read_bytes(), original)


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux private-file identity')
class PermissionProtectedFiles(unittest.TestCase):
    def synthetic(self, directory):
        root = Path(directory); homes = {}; rows = {}
        for uid, count in ((1000, 10), (1001, 30), (1002, 5)):
            home = root/str(uid); home.mkdir(); homes[uid] = home; rows[str(uid)] = {}
            for index in range(count):
                path = home/str(index); raw = ('synthetic protected '+str(uid)+'/'+str(index)).encode()
                path.write_bytes(raw); path.chmod(0o600)
                rows[str(uid)][path.name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'uid': uid, 'mode': '0o600'}
        snapshot = root/'protected-accounts.json'; snapshot.write_text(json.dumps(rows, sort_keys=True, separators=(',', ':'))+'\n'); snapshot.chmod(0o644)
        scope = proof.MINT_PERMISSION_SCOPE._replace(protected_sha=hashlib.sha256(snapshot.read_bytes()).hexdigest())
        fixture = {**binding(scope), 'protectedAccountsPath': str(snapshot)}
        original = Path.lstat
        def attributes(path):
            info = original(path); fields = list(info)
            if path == snapshot: fields[4] = fields[5] = 0
            elif path in (root, *root.parents): fields[0] = stat.S_IFDIR|0o755; fields[4] = fields[5] = 0
            elif path.parent in homes.values(): fields[4] = int(path.parent.name)
            return os.stat_result(fields)
        return SimpleNamespace(stage=root, homes=homes, rows=rows, snapshot=snapshot, scope=scope, fixture=fixture, attributes=attributes)

    def test_all45_actual_bytes_are_checked_and_changed_file_refuses_without_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            x = self.synthetic(directory)
            with patch.object(proof, 'MINT_PERMISSION_STAGE', x.stage), patch.object(proof, 'MINT_PERMISSION_SCOPE', x.scope), patch.object(proof, 'MINT_PROTECTED_HOMES', x.homes), \
                    patch.object(Path, 'lstat', x.attributes), patch.object(proof.os, 'geteuid', return_value=0), patch.object(proof, 'MINT_PERMISSION_FAILED_EVIDENCE', {}):
                result = proof.permission_protected_files(x.fixture, read_files=True)
                self.assertTrue(result['oldFilesVerified']); self.assertEqual(sum(result['protectedCounts'].values()), 45)
                changed = x.homes[1002]/'0'; raw = changed.read_bytes(); changed.write_bytes(b'x'*len(raw))
                with self.assertRaisesRegex(ValueError, 'file changed'):
                    proof.permission_protected_files(x.fixture, read_files=True)
                self.assertEqual(changed.read_bytes(), b'x'*len(raw))

    def test_retained_failed_journal_or_log_change_refuses_without_old_run_adoption(self):
        with tempfile.TemporaryDirectory() as directory:
            x = self.synthetic(directory); evidence = x.homes[1002]/'retained-failure'
            evidence.write_bytes(b'known failed evidence'); evidence.chmod(0o600)
            expected = {'retained-failure': hashlib.sha256(evidence.read_bytes()).hexdigest()}
            with patch.object(proof, 'MINT_PERMISSION_STAGE', x.stage), patch.object(proof, 'MINT_PERMISSION_SCOPE', x.scope), patch.object(proof, 'MINT_PROTECTED_HOMES', x.homes), \
                    patch.object(Path, 'lstat', x.attributes), patch.object(proof.os, 'geteuid', return_value=0), \
                    patch.object(proof, 'MINT_PERMISSION_FAILED_EVIDENCE', expected):
                self.assertTrue(proof.permission_protected_files(x.fixture, read_files=True)['retainedFailedEvidenceVerified'])
                evidence.write_bytes(b'changed failure')
                with self.assertRaisesRegex(ValueError, 'retained failed16b'):
                    proof.permission_protected_files(x.fixture, read_files=True)
                self.assertEqual(evidence.read_bytes(), b'changed failure')

    def test_ordinary_profile_can_validate_snapshot_but_cannot_reread_private_accounts(self):
        with tempfile.TemporaryDirectory() as directory:
            x = self.synthetic(directory)
            with patch.object(proof, 'MINT_PERMISSION_STAGE', x.stage), patch.object(proof, 'MINT_PERMISSION_SCOPE', x.scope), patch.object(Path, 'lstat', x.attributes), \
                    patch.object(proof.os, 'geteuid', return_value=1003):
                self.assertFalse(proof.permission_protected_files(x.fixture)['oldFilesVerified'])
                with self.assertRaisesRegex(ValueError, 'external root wrapper'):
                    proof.permission_protected_files(x.fixture, read_files=True)

    def test_root_metadata_wrong_owner_write_mode_links_hash_and_size_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory); path = stage/'protected-accounts.json'; path.write_text('{}'); digest = hashlib.sha256(path.read_bytes()).hexdigest()
            info = path.lstat()
            parent = SimpleNamespace(st_mode=stat.S_IFDIR|0o755, st_uid=0)
            for field, value in (('st_uid', 1003), ('st_mode', stat.S_IFREG|0o664), ('st_mode', stat.S_IFLNK|0o777), ('st_nlink', 2), ('st_size', 10000)):
                values = {name: getattr(info, name) for name in ('st_mode', 'st_uid', 'st_nlink', 'st_size')}; values['st_uid'] = 0; values[field] = value
                with self.subTest(field=field), patch.object(proof, 'MINT_PERMISSION_STAGE', stage), \
                        patch.object(Path, 'lstat', lambda p: SimpleNamespace(**values) if p == path else parent), \
                        patch.object(Path, 'read_bytes') as read:
                    with self.assertRaisesRegex(ValueError, 'immutable root metadata'):
                        proof.permission_root_json(path, digest, 8192)
                    read.assert_not_called()
            fields = SimpleNamespace(st_mode=stat.S_IFREG|0o644, st_uid=0, st_nlink=1, st_size=2)
            with patch.object(proof, 'MINT_PERMISSION_STAGE', stage), patch.object(Path, 'lstat', lambda p: fields if p == path else parent):
                self.assertEqual(proof.permission_root_json(path, digest, 8192), {})
                with self.assertRaisesRegex(ValueError, 'hash differs'): proof.permission_root_json(path, '0'*64, 8192)

    def stage_attributes(self):
        stage = proof.MINT_PERMISSION_STAGE
        values = {p: SimpleNamespace(st_mode=stat.S_IFDIR|0o755, st_uid=0) for p in (stage, *stage.parents)}
        values[Path('/var/tmp')] = SimpleNamespace(st_mode=stat.S_IFDIR|0o1777, st_uid=0)
        for name in ('protected-accounts.json', 'protected-preflight.json'):
            values[stage/name] = SimpleNamespace(st_mode=stat.S_IFREG|0o644, st_uid=0, st_nlink=1, st_size=2)
        return values

    def test_foreign_writable_linked_or_special_stage_and_ancestors_refuse_before_file_read(self):
        stage = proof.MINT_PERMISSION_STAGE; path = stage/'protected-accounts.json'
        cases = [(stage, mode, uid) for mode, uid in (
            (stat.S_IFDIR|0o755, 1003), (stat.S_IFDIR|0o775, 0), (stat.S_IFDIR|0o1777, 0),
            (stat.S_IFLNK|0o777, 0), (stat.S_IFREG|0o755, 0))]
        cases += [(ancestor, mode, uid) for ancestor in stage.parents for mode, uid in (
            (stat.S_IFDIR|0o755, 1003), (stat.S_IFLNK|0o777, 0), (stat.S_IFDIR|0o777, 0))]
        cases += [(Path('/var'), stat.S_IFDIR|0o1777, 0)]
        for directory, mode, uid in cases:
            values = self.stage_attributes(); values[directory] = SimpleNamespace(st_mode=mode, st_uid=uid)
            with self.subTest(directory=str(directory), mode=oct(mode), uid=uid), \
                    patch.object(Path, 'lstat', lambda p: values[p]) as lookup, patch.object(Path, 'read_bytes') as read:
                with self.assertRaisesRegex(ValueError, 'stage and ancestors'):
                    proof.permission_root_json(path, '0'*64, 8192)
                read.assert_not_called()

    def test_exact_root_sticky_var_tmp_parent_accepts_both_fixed_metadata_files(self):
        values = self.stage_attributes(); digest = hashlib.sha256(b'{}').hexdigest()
        for name in ('protected-accounts.json', 'protected-preflight.json'):
            with self.subTest(name=name), patch.object(Path, 'lstat', lambda p: values[p]), \
                    patch.object(Path, 'read_bytes', return_value=b'{}') as read:
                self.assertEqual(proof.permission_root_json(proof.MINT_PERMISSION_STAGE/name, digest, 8192), {})
                read.assert_called_once_with()

    def test_metadata_wrong_stage_traversal_or_filename_refuses_before_any_lookup(self):
        stage = proof.MINT_PERMISSION_STAGE
        for path in (stage.parent/'protected-accounts.json', stage/'nested/protected-accounts.json',
                     stage/'../protected-accounts.json', stage/'other.json', Path('protected-accounts.json')):
            with self.subTest(path=str(path)), patch.object(Path, 'lstat') as lookup, patch.object(Path, 'read_bytes') as read:
                with self.assertRaisesRegex(ValueError, 'exact fixed stage path'):
                    proof.permission_root_json(path, '0'*64, 8192)
                lookup.assert_not_called(); read.assert_not_called()

    def test_attestation_pins_fresh_root_snapshot_run_source_proof_boot_and_actual_counts(self):
        fixture = {**binding(), 'guestBootId': 'owned-boot', 'protectedPreflightSha256': 'a'*64}
        observed = {'format': 'augmentor-mint-permission-protected-preflight/1', 'runToken': fixture['runToken'],
            'sourceCommit': proof.MINT_PERMISSION_SCOPE.source, 'proofScriptSha256': proof.PROOF_SHA256,
            'guestBootId': fixture['guestBootId'], 'observedUnix': 900, 'oldFilesVerified': True,
            'protectedAccountsSha256': proof.MINT_PERMISSION_SCOPE.protected_sha,
            'protectedCounts': {'1000': 10, '1001': 30, '1002': 5},
            'retainedFailedEvidence': dict(proof.MINT_PERMISSION_FAILED_EVIDENCE), 'retainedFailedEvidenceVerified': True}
        with patch.object(proof, 'permission_protected_files'), patch.object(proof.time, 'time', return_value=1000):
            with patch.object(proof, 'permission_root_json', return_value=observed): proof.permission_protected_attestation(fixture)
            for field, value in (('runToken', 'cd'*16), ('sourceCommit', proof.FRESH_SOURCE),
                                 ('proofScriptSha256', '0'*64), ('guestBootId', 'another'),
                                 ('protectedAccountsSha256', '0'*64), ('oldFilesVerified', 1),
                                 ('protectedCounts', {'1000': 10, '1001': 30}), ('retainedFailedEvidence', {}), ('retainedFailedEvidenceVerified', False), ('observedUnix', 699), ('observedUnix', 1001)):
                with self.subTest(field=field,value=value), patch.object(proof, 'permission_root_json', return_value={**observed, field: value}):
                    with self.assertRaisesRegex(ValueError, 'stale or belongs'): proof.permission_protected_attestation(fixture)

    def test_external_before_and_finally_reread45_even_when_native_audit_fails(self):
        with patch.object(proof, 'fresh_vm_identity'), patch.object(proof, 'permission_protected_files') as protected, \
                patch.object(proof, '_fresh_external_audit', side_effect=ValueError('native refusal')):
            with self.assertRaisesRegex(ValueError, 'native refusal'):
                proof.fresh_external_audit(Path('/synthetic'), binding(), scope=proof.MINT_PERMISSION_SCOPE)
            self.assertEqual(protected.call_count, 2)
            self.assertTrue(all(call.kwargs['read_files'] for call in protected.call_args_list))


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux finite proof')
class PermissionExecution(unittest.TestCase):
    def execute_case(self, directory, **kwargs):
        x = legacy.FreshExecution().execution(directory, **kwargs)
        scope = proof.MINT_PERMISSION_SCOPE._replace(home=x.home)
        x.fixture = {**x.fixture, **binding(scope)}
        x.stack.enter_context(patch.object(proof, 'MINT_PERMISSION_SCOPE', scope))
        return x, scope

    def record(self, x, scope): return json.loads((x.home/scope.run_directory/'run.json').read_text())

    def test_new_profile_reuses_finite_two_role_restart_cleanup_and_preserves_historical_identity(self):
        original = (proof.FRESH_SOURCE, proof.FRESH_ARTIFACT, proof.FRESH_HOME)
        with tempfile.TemporaryDirectory() as directory:
            x, scope = self.execute_case(directory, host_delay=75)
            with x.stack: report = proof.mint_permission_emulated_proof(Path(directory)/'bundle', x.fixture)
            self.assertEqual(report['sourceCommit'], scope.source); self.assertEqual(report['artifactId'], scope.artifact)
            self.assertEqual(len(x.setup_calls), 2); self.assertEqual(len(x.processes), 2)
            self.assertEqual(len(x.mutations), 6); self.assertTrue(report['restartPreservesHistoryWithoutReplay'])
            self.assertFalse(report['originalPublic60FullProofPass']); self.assertEqual(report['startupBudgetSeconds'], 120)
            self.assertEqual(report['turnBudgetSeconds'], 60); self.assertEqual(x.companion.finish.call_count, 1)
            self.assertTrue(self.record(x,scope)['settingsPreserved'])
        self.assertEqual((proof.FRESH_SOURCE, proof.FRESH_ARTIFACT, proof.FRESH_HOME), original)

    def test_new_late_authenticated_start_refuses_before_sdk_and_retains_measured_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            x, scope = self.execute_case(directory, host_delay=121)
            with x.stack, self.assertRaisesRegex(RuntimeError, 'exceeded120'):
                proof.mint_permission_emulated_proof(Path(directory)/'bundle', x.fixture)
            record = self.record(x,scope); self.assertEqual(x.mutations, [])
            self.assertFalse(record['startupObservations'][0]['withinBudget']); self.assertIsNone(record['pendingRequest'])
            self.assertEqual(record['modelRequests'], 0)

    def test_new_finished_turn_crossing60_refuses_before_browser_and_does_not_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            x, scope = self.execute_case(directory, turn_read_delay=61)
            with x.stack, self.assertRaisesRegex(RuntimeError, 'turn reads exceeded60'):
                proof.mint_permission_emulated_proof(Path(directory)/'bundle', x.fixture)
            record = self.record(x,scope); self.assertEqual(len(x.mutations), 3)
            self.assertEqual(record['status'], 'failed'); self.assertIsNone(record['pendingRequest'])
            self.assertEqual(len(x.processes), 1)

    def test_new_unknown_prompt_outcome_remains_pending_without_browser_restart_or_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            x, scope = self.execute_case(directory, lost=True)
            with x.stack, self.assertRaisesRegex(OSError, 'lost prompt'):
                proof.mint_permission_emulated_proof(Path(directory)/'bundle', x.fixture)
            record = self.record(x,scope); self.assertEqual(len(x.mutations), 3)
            self.assertTrue(record['unknownRequestOutcome']); self.assertIn('session.prompt', record['pendingRequest']['action'])
            self.assertEqual(len(x.processes), 1); self.assertEqual(x.companion.finish.call_count, 1)


if __name__ == '__main__':
    unittest.main()
