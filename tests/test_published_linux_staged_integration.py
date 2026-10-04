# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import ast
import copy
from functools import wraps
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('staged_coordinator', ROOT/'release/prove-published-linux-coordinated-version.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


def fixture_uid(test):
    @wraps(test)
    def run(self):
        lstat, fstat = Path.lstat, os.fstat
        def owner(info):
            fields = {n: getattr(info, n) for n in dir(info) if n.startswith('st_')}
            return SimpleNamespace(**{**fields, 'st_uid': 1000, 'st_gid': 1000})
        with patch.object(Path, 'lstat', lambda p, *a, **k: owner(lstat(p, *a, **k))), \
                patch.object(module.os, 'fstat', lambda fd: owner(fstat(fd))):
            return test(self)
    return run


class ExactCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.home = Path(self.temp.name)/'home'
        self.runtime = self.home/'.local/share/augmentor/dsh-runtime/node_modules'
        self.target = self.runtime/'@deepseek-ai/dsh/lib/bin.js'
        self.shim = self.runtime/'.bin/dsh'; self.package = self.target.parent.parent/'package.json'
        self.target.parent.mkdir(parents=True); self.shim.parent.mkdir(parents=True)
        self.target.write_bytes(b'#!/usr/bin/env node\n// synthetic CLI; never executed\n'); self.target.chmod(0o700)
        self.package.write_text(json.dumps({'name': '@deepseek-ai/dsh', 'version': '0.1.5-rc.1'})); self.package.chmod(0o600)
        self.shim.symlink_to('../@deepseek-ai/dsh/lib/bin.js')
        self.app = Path(self.temp.name)/'native'
        self.pins = patch.multiple(module, DSH_CLI_SHA=hashlib.sha256(self.target.read_bytes()).hexdigest(),
                                   DSH_PACKAGE_SHA=hashlib.sha256(self.package.read_bytes()).hexdigest())
        self.pins.start()

    def tearDown(self): self.pins.stop(); self.temp.cleanup()

    def admit(self, bound=None):
        return module.verified_dsh_path(self.home, self.app, lambda p: self.assertTrue(p.is_dir()), bound)

    @fixture_uid
    def test_real_npm_symlink_is_found_without_executing_command(self):
        with patch.object(module.subprocess, 'run') as spawning:
            path, observed = self.admit()
            self.assertEqual(path, str(self.shim.parent)+':'+str(self.app/'node/bin')+':/usr/bin:/bin')
            self.assertEqual(module.shutil.which('dsh', path=path), str(self.shim))
            self.assertEqual(observed['target']['nlink'], 1)
            self.assertEqual(self.admit(observed), (path, observed))
            spawning.assert_not_called()

    @fixture_uid
    def test_same_resolved_target_with_unapproved_literal_link_refuses(self):
        self.shim.unlink(); self.shim.symlink_to('../@deepseek-ai/dsh/lib/../lib/bin.js')
        with self.assertRaises(ValueError): self.admit()

    @fixture_uid
    def test_missing_shim_ordinary_file_or_foreign_target_refuses(self):
        self.shim.unlink()
        with self.assertRaises(FileNotFoundError): self.admit()
        self.shim.write_bytes(b'fake'); self.shim.chmod(0o700)
        with self.assertRaises(ValueError): self.admit()
        self.shim.unlink(); self.shim.symlink_to('../foreign/bin.js')
        with self.assertRaises(ValueError): self.admit()

    @fixture_uid
    def test_no_exec_group_write_hardlink_and_changed_content_refuse(self):
        for mode in (0o600, 0o720):
            self.target.chmod(mode)
            with self.subTest(mode=mode), self.assertRaises(ValueError): self.admit()
        self.target.chmod(0o700); os.link(self.target, Path(self.temp.name)/'alias')
        with self.assertRaises(ValueError): self.admit()
        (Path(self.temp.name)/'alias').unlink(); self.target.write_bytes(b'changed')
        with self.assertRaises(ValueError): self.admit()

    @fixture_uid
    def test_root_admitted_inode_or_package_identity_must_match(self):
        _, observed = self.admit(); changed = copy.deepcopy(observed); changed['target']['inode'] += 1
        with self.assertRaises(ValueError): self.admit(changed)
        changed = copy.deepcopy(observed); changed['package']['sha256'] = '0'*64
        with self.assertRaises(ValueError): self.admit(changed)

    @fixture_uid
    def test_supported_cli_package_identity_is_required_even_with_matching_content_pin(self):
        for document in ({'name': 'foreign', 'version': '0.1.5-rc.1'},
                         {'name': '@deepseek-ai/dsh', 'version': 'other'}):
            self.package.write_text(json.dumps(document))
            with patch.object(module, 'DSH_PACKAGE_SHA', hashlib.sha256(self.package.read_bytes()).hexdigest()), self.assertRaises(ValueError):
                self.admit()

    def test_foreign_owner_is_refused_before_open(self):
        info = self.target.lstat(); values = {n: getattr(info, n) for n in dir(info) if n.startswith('st_')}
        for key in ('st_uid', 'st_gid'):
            bad = SimpleNamespace(**{**values, 'st_uid': 1000, 'st_gid': 1000, key: 1001})
            with patch.object(Path, 'lstat', return_value=bad), patch.object(module.os, 'open') as opening, self.assertRaises(ValueError):
                module.stable_owned_read(self.target)
            opening.assert_not_called()

    @fixture_uid
    def test_parent_guard_and_changed_during_fd_read_refuse(self):
        with self.assertRaises(ValueError):
            module.verified_dsh_path(self.home, self.app, Mock(side_effect=ValueError('foreign parent')))
        reading = os.read; mutated = False
        def replacing(fd, count):
            nonlocal mutated
            raw = reading(fd, count)
            if raw and not mutated:
                mutated = True; self.target.write_bytes(b'changed during reading')
            return raw
        with patch.object(module.os, 'read', replacing), self.assertRaises(ValueError): self.admit()

    @fixture_uid
    def test_read_induced_atime_is_not_content_change(self):
        first, metadata = module.stable_owned_read(self.target)
        os.utime(self.target, ns=(1, self.target.stat().st_mtime_ns))
        # utime changes ctime intentionally; each individual read stays stable.
        second, current = module.stable_owned_read(self.target)
        self.assertEqual(first, second); self.assertEqual(metadata['sha256'], current['sha256'])


class StagedAdmissionTests(unittest.TestCase):
    def prior(self):
        return {'format': 'augmentor-published-coordinated/1', 'mode': 'upgrade', 'phase': 'failed-do-not-resume',
                'proofSha256': module.EXECUTED_161_SHA, 'rootBindingSha256': module.PRIOR_BINDING_SHA,
                'nativeVersion': '0.2.13', 'nativeSource': module.SOURCES['0.2.13'],
                'baselineRunSha256': module.BASELINE_RUN_SHA, 'unknownOutcome': False,
                'pendingRequest': None, 'pendingLifecycle': None, 'pendingDeployment': None, 'pendingAction': None,
                'error': 'ValueError: Make the installed DSH command available on PATH before connecting it.',
                'completedDeployments': [{'label': 'stage', 'exitCode': 0}], 'settingsBefore': {'settings': 'exact'},
                'settingsAfter': {'settings': 'exact'}, 'ownedDshExitCode': 0, 'modelRequests': 0,
                'persistencePreserved': True, 'baselineJournalPreserved': True,
                'companionCleanup': {'phase': 'pass', 'pending': None, 'unknownOutcome': False, 'exitCode': 0, 'normalExit': True}}

    def binding(self):
        return {'format': 'augmentor-published-staged-integration-binding/1', 'mode': 'upgrade-after-known-stage',
                'proofSha256': 'proof', 'coordinatorSha256': 'coordinator', 'createdAt': 100, 'runToken': 'f'*64,
                'priorFailedRunSha256': module.FAILED_161_SHA, 'priorRootBindingSha256': module.PRIOR_BINDING_SHA,
                'stageVerifiedSha256': module.STAGE_161_SHA, 'readOnly162bSha256': module.READONLY_162B_SHA,
                'originalHostFailureSha256': module.HOST_FAILURE_161_SHA, 'priorIndependentEndingAuditSha256': module.ENDING_161_SHA,
                'baselineRunSha256': module.BASELINE_RUN_SHA, 'baselineEndingAuditSha256': module.BASELINE_ENDING_SHA,
                'nativeAuditSha256': 'a'*64, 'dshCli': {}, 'packageTransaction': {'phase': 'pass', 'exitCode': 0,
                    'pending': None, 'unknownOutcome': False, 'versions': {'augmentor-runtime': '0.2.13', 'augmentor-desktop': '0.2.13'},
                    'addedDependencies': sorted(module.NEW_DEPENDENCIES), 'removedPackages': [],
                    'unrelatedPackageChanges': False, 'receiptSha256': module.APT_161_SHA},
                'nativeAudit': {'status': 'pass', 'version': '0.2.13', 'source': module.SOURCES['0.2.13'], 'pending': None,
                    'unknownOutcome': False, 'leasesIdle': True, 'processesAbsent': True, 'socketAbsent': True, 'portsIdle': True}}

    def test_exact_known_pre_install_failure_can_admit_separate_phase(self):
        module.known_staged_failure(self.prior(), {'settings': 'exact'})
        self.assertEqual(module.staged_binding_identity(self.binding(), 'proof', 'coordinator', 120), '0.2.13')

    def test_any_pending_unknown_completed_action_or_changed_state_refuses(self):
        cases = [{key: 'pending'} for key in ('pendingRequest', 'pendingLifecycle', 'pendingDeployment', 'pendingAction')]
        cases += [{'unknownOutcome': True}, {'error': 'other'}, {'proofSha256': 'other'}, {'rootBindingSha256': 'other'},
                  {'completedActions': ['normal-setup-install']}, {'completedDeployments': [{'label': 'activate', 'exitCode': 0}]},
                  {'integrationAndSelectionVerified': True}, {'selected': {}}, {'settingsAfter': {'changed': 'yes'}},
                  {'ownedDshExitCode': 1}, {'modelRequests': 1}, {'persistencePreserved': False}, {'baselineJournalPreserved': False}]
        for change in cases:
            with self.subTest(change=change), self.assertRaises(ValueError):
                module.known_staged_failure({**self.prior(), **change}, {'settings': 'exact'})
        prior = self.prior(); prior['companionCleanup']['unknownOutcome'] = True
        with self.assertRaises(ValueError): module.known_staged_failure(prior, {'settings': 'exact'})

    def test_fresh_binding_pins_original_unknown_host_receipt_without_changing_it(self):
        for key in ('priorFailedRunSha256', 'priorRootBindingSha256', 'stageVerifiedSha256', 'readOnly162bSha256',
                    'originalHostFailureSha256', 'priorIndependentEndingAuditSha256', 'coordinatorSha256', 'runToken'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                module.staged_binding_identity({**self.binding(), key: 'other'}, 'proof', 'coordinator', 120)
        binding = self.binding(); binding['packageTransaction']['receiptSha256'] = '0'*64
        with self.assertRaises(ValueError): module.staged_binding_identity(binding, 'proof', 'coordinator', 120)
        for field, value in (('createdAt', -1000), ('proofSha256', 'other')):
            with self.assertRaises(ValueError): module.staged_binding_identity({**self.binding(), field: value}, 'proof', 'coordinator', 120)

    @fixture_uid
    def test_reuses_full_existing_inventory_without_stage_dispatch_and_preserves_prior_bytes(self):
        with tempfile.TemporaryDirectory() as name:
            home = Path(name); prior = home/'.local/state/published-product-coordinated-upgrade161'; prior.mkdir(parents=True)
            root = home/'.local/share/augmentor/releases'/module.STAGE_161_ROOT; root.mkdir(parents=True)
            staged = {'deployment': {'root': str(root), 'artifactSha256': module.STAGE_161_ARTIFACT},
                      'artifactSha256': module.STAGE_161_ARTIFACT, 'files': {'synthetic': {'sha256': 'a'*64}}}
            raw = json.dumps(self.prior()).encode(); stage_raw = json.dumps(staged).encode()
            (prior/'run.json').write_bytes(raw); (prior/'stage-verified.json').write_bytes(stage_raw)
            for p in prior.iterdir(): p.chmod(0o600)
            helper = SimpleNamespace(private_parents=Mock()); deployment = SimpleNamespace(verify=Mock(return_value=staged))
            pins = {'FAILED_161_SHA': hashlib.sha256(raw).hexdigest(), 'STAGE_161_SHA': hashlib.sha256(stage_raw).hexdigest()}
            with patch.multiple(module, **pins), patch.object(module.subprocess, 'run') as spawning:
                result = module.verified_existing_stage(deployment, home, helper, {'stagedDeployment': staged['deployment']}, {'settings': 'exact'})
                self.assertEqual(result, staged); deployment.verify.assert_called_once_with(root); spawning.assert_not_called()
                self.assertEqual((prior/'run.json').read_bytes(), raw); self.assertEqual((prior/'stage-verified.json').read_bytes(), stage_raw)
                deployment.verify.return_value = {**staged, 'files': {'changed': {}}}
                with self.assertRaises(ValueError): module.verified_existing_stage(deployment, home, helper, {'stagedDeployment': staged['deployment']}, {'settings': 'exact'})

    def test_entrypoint_pins_orchestration_and_only_selects_fresh_integration_branch(self):
        source = ROOT/'release/prove-published-linux-staged-integration.py'
        spec = importlib.util.spec_from_file_location('entry', source); entry = importlib.util.module_from_spec(spec); spec.loader.exec_module(entry)
        self.assertEqual(entry.COORDINATOR_SHA, hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest())
        tree = ast.parse(source.read_text()); calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'prove']
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].args[0].value, 'upgrade')
        self.assertTrue(next(k.value.value for k in calls[0].keywords if k.arg == 'integration_after_stage'))
        tree = ast.parse(Path(module.__file__).read_text())
        # The fresh branch is the first arm; the stage dispatch exists only in
        # its mutually exclusive default upgrade arm.
        arms = [n for n in ast.walk(tree) if isinstance(n, ast.If) and isinstance(n.test, ast.Name)
                and n.test.id == 'integration_after_stage' and any(isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute)
                and x.func.attr == 'transaction' for x in ast.walk(ast.Module(body=n.orelse, type_ignores=[])))]
        self.assertEqual(len(arms), 1)
        self.assertFalse(any(isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and x.func.attr == 'transaction'
                             for x in ast.walk(ast.Module(body=arms[0].body, type_ignores=[]))))

    @fixture_uid
    def test_exact_retained_large_manifest_has_narrow_stable_read_exception(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); prior = root/'published-product-coordinated-upgrade161'; prior.mkdir()
            file = prior/'stage-verified.json'; raw = b'x'*4232400; file.write_bytes(raw); file.chmod(0o600)
            with patch.object(module, 'STAGE_161_SHA', hashlib.sha256(raw).hexdigest()):
                with self.assertRaises(ValueError): module.tree(prior)
                rows = module.tree(prior, retained_staged_inventory=True)
                self.assertEqual(rows['stage-verified.json']['bytes'], 4232400)
                self.assertEqual(rows['stage-verified.json']['inode'], file.lstat().st_ino)
                self.assertEqual(rows, module.tree(prior, retained_staged_inventory=True))
                file.rename(prior/'foreign-large.json')
                with self.assertRaises(ValueError): module.tree(prior, retained_staged_inventory=True)
                (prior/'foreign-large.json').rename(file)
                prior.rename(root/'foreign-folder')
                with self.assertRaises(ValueError): module.tree(root/'foreign-folder', retained_staged_inventory=True)
                (root/'foreign-folder').rename(prior)
                file.write_bytes(b'y'*4232400)
                with self.assertRaises(ValueError): module.tree(prior, retained_staged_inventory=True)
                file.write_bytes(raw+b'extra')
                with self.assertRaises(ValueError): module.tree(prior, retained_staged_inventory=True)
                file.unlink(); file.symlink_to(root/'missing')
                with self.assertRaises(ValueError): module.tree(prior, retained_staged_inventory=True)


if __name__ == '__main__': unittest.main()
