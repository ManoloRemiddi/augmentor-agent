# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import io
import itertools
import json
import os
from pathlib import Path
import plistlib
import tempfile
import unittest
import urllib.error
from unittest.mock import patch
from unittest.mock import Mock
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('managed_mac_setup', ROOT/'scripts/setup-macos.py')
managed = importlib.util.module_from_spec(spec); spec.loader.exec_module(managed)
complete = managed.load_complete(ROOT)
import sys
sys.path.insert(0, str(ROOT/'services'))
import dsh.setup as dsh


class Agent:
    label = 'com.augmentor.Agent.DSH'
    def __init__(self): self.active = False; self.stopped = False; self.exists = False
    def loaded(self): return self.active
    def owned(self): return self.exists
    def start(self): self.active = True; self.exists = True
    def stop_failed_setup(self): self.active = False; self.stopped = True


class SetupFixture:
    def check(self, params): self.params = params; return {'installed': True, 'token': 'checked'}
    def save(self, token, managed=None):
        assert token == 'checked'
        dsh.atomic(dsh.configuration(), json.dumps({'dsh': {**self.params, 'version': '0.2.12', 'managed': managed}}))


class ManagedMacSetupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name); self.root = self.base/'app'; self.state = self.base/'managed'
        for relative in ('dsh/node_modules/.bin/dsh', 'node/bin/node'):
            file = self.root/relative; file.parent.mkdir(parents=True, exist_ok=True); file.write_text('fixture')
        self.request = {'url': 'https://model.example/v1', 'model': 'example-model', 'apiKey': 'private-test-key', 'context': 32768}
        env = patch.dict(os.environ, {'AUGMENTOR_SHARED_CONFIG': str(self.base/'config')})
        env.start(); self.addCleanup(env.stop)
        loader = patch.object(managed, 'load_complete', return_value=complete)
        loader.start(); self.addCleanup(loader.stop)
        bootstrap = patch.object(complete, 'configure_product')
        self.bootstrap = bootstrap.start(); self.addCleanup(bootstrap.stop)
        setup = patch.object(dsh, 'Setup', SetupFixture)
        setup.start(); self.addCleanup(setup.stop)
        self.agent = Agent()

    def provision(self, probe=lambda *_: None):
        return managed.provision(self.root, self.state, self.request, agent=self.agent, probe=probe)

    def test_private_credentials_managed_owner_and_repeat_without_reconfiguration(self):
        self.assertTrue(self.provision()['saved'])
        self.bootstrap.assert_called_once()
        self.assertFalse(self.bootstrap.call_args.kwargs['save'])
        settings = json.loads((self.state/'home/settings.yaml').read_text())
        self.assertNotIn(self.request['apiKey'], json.dumps(settings))
        runtime = managed.private_json(self.state/'runtime.json')
        self.assertEqual(runtime['apiKey'], self.request['apiKey'])
        self.assertEqual((self.state/'runtime.json').stat().st_mode & 0o777, 0o600)
        descriptor = managed.service_plist(self.root, self.state)
        self.assertNotIn(self.request['apiKey'].encode(), descriptor)
        service = plistlib.loads(descriptor)
        self.assertTrue(service['KeepAlive'])
        self.assertEqual(service['ProcessType'], 'Interactive')
        self.assertTrue(managed.private_json(self.state/'startup-check.json')['integrationInstalled'])
        self.assertEqual(dsh.current()['managed']['type'], 'launchd')
        self.assertTrue(self.agent.active)
        self.assertTrue(self.provision()['saved'])
        self.bootstrap.assert_called_once()

    def test_bad_key_can_be_corrected_without_an_unrecognized_partial_folder(self):
        def fail(*_): raise ValueError('HTTP 401')
        with self.assertRaisesRegex(ValueError, '401'): self.provision(probe=fail)
        self.assertFalse(dsh.current()); self.assertFalse(self.agent.active)
        self.assertEqual(managed.private_json(self.state/'setup.json')['status'], 'preparing')
        self.assertTrue(self.provision()['saved'])

    def test_existing_external_configuration_is_preserved(self):
        dsh.atomic(dsh.configuration(), json.dumps({'dsh': {'home': '/existing/private', 'endpoint': 'http://127.0.0.1:3080'}}))
        before = dsh.configuration().read_bytes()
        with self.assertRaisesRegex(ValueError, 'already exists'): self.provision()
        self.assertEqual(dsh.configuration().read_bytes(), before)
        self.bootstrap.assert_not_called(); self.assertFalse(self.agent.active)

    def test_bootstrap_failure_leaves_no_selected_connection_and_can_retry(self):
        self.bootstrap.side_effect = ValueError('bootstrap fixture failed')
        with self.assertRaisesRegex(ValueError, 'fixture failed'): self.provision()
        self.assertEqual(managed.private_json(self.state/'setup.json')['status'], 'failed')
        self.assertFalse(dsh.current()); self.assertTrue(self.agent.stopped)
        self.bootstrap.side_effect = None
        self.assertTrue(self.provision()['saved'])

    def test_readiness_timeout_preserves_retry_and_private_redacted_diagnostics(self):
        ticks = itertools.count(0, 20)
        with patch.object(SetupFixture, 'check', side_effect=ValueError('rejected private-test-key')), \
             patch.object(managed.time, 'monotonic', side_effect=lambda: next(ticks)), \
             patch.object(managed.time, 'sleep'):
            with self.assertRaisesRegex(ValueError, 'did not become ready'): self.provision()
        self.assertFalse(dsh.current()); self.assertTrue(self.agent.stopped)
        diagnostic = managed.private_json(self.state/'startup-check.json')
        self.assertFalse(diagnostic['integrationInstalled'])
        self.assertGreater(diagnostic['attempts'], 0)
        self.assertNotIn(self.request['apiKey'], json.dumps(diagnostic))
        self.assertTrue(self.provision()['saved'])

    def test_foreign_service_is_not_stopped_or_overwritten(self):
        self.agent.active = True
        with self.assertRaisesRegex(ValueError, 'different DSH login service'): self.provision()
        self.assertTrue(self.agent.active); self.assertFalse(self.agent.stopped)
        self.bootstrap.assert_not_called()

    def test_changed_configuration_during_bootstrap_is_not_overwritten(self):
        def configure(*args, **kwargs):
            dsh.atomic(dsh.configuration(), json.dumps({'dsh': {'home': '/new-choice', 'endpoint': 'http://127.0.0.1:3090'}}))
        self.bootstrap.side_effect = configure
        with self.assertRaisesRegex(ValueError, 'Another window'): self.provision()
        self.assertEqual(dsh.current()['home'], '/new-choice')
        self.assertFalse(self.agent.active); self.assertTrue(self.agent.stopped)

    def test_lost_final_acknowledgement_recovers_without_reconfiguring_or_stopping(self):
        self.provision()
        marker = managed.private_json(self.state/'setup.json'); marker['status'] = 'starting'
        managed.atomic_json(self.state/'setup.json', marker)
        dsh.configuration().unlink()
        self.assertTrue(self.provision()['saved'])
        self.bootstrap.assert_called_once(); self.assertFalse(self.agent.stopped)
        self.assertEqual(managed.private_json(self.state/'setup.json')['status'], 'ready')

    def test_linked_private_data_is_refused(self):
        outside = self.base/'outside'; outside.mkdir(mode=0o700)
        self.state.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'private data'): self.provision()
        self.assertFalse(list(outside.iterdir()))

    def test_service_file_cannot_silently_replace_an_existing_job(self):
        directory = self.base/'agents'; directory.mkdir()
        agent = managed.LaunchAgent(self.root, self.state, directory=directory)
        agent.path.write_bytes(b'unrelated existing job')
        with self.assertRaisesRegex(ValueError, 'preserved'): agent.owned()
        self.assertEqual(agent.path.read_bytes(), b'unrelated existing job')

    def test_recovery_keeps_launchd_as_owner_instead_of_spawning_without_credentials(self):
        import recovery
        saved = {'home': str(self.state/'home'), 'endpoint': 'http://127.0.0.1:31999',
                 'managed': {'type': 'launchd', 'label': managed.LABEL, 'state': str(self.state)}}
        client = SimpleNamespace(home=self.state/'home', base=saved['endpoint'])
        owner = SimpleNamespace(start_saved=Mock())
        with patch.object(dsh, 'current', return_value=saved), patch.object(recovery.sys, 'platform', 'darwin'), \
             patch.object(recovery, 'port_open', side_effect=[False, True]), \
             patch('importlib.util.spec_from_file_location'), patch('importlib.util.module_from_spec', return_value=owner), \
             patch.object(recovery.subprocess, 'run') as command:
            recovery._start_dsh(client, lambda _: None)
        owner.start_saved.assert_called_once_with(saved); command.assert_not_called()

    def test_saved_recovery_requires_matching_owned_profile(self):
        self.provision(); saved = dsh.current()
        with patch.object(managed, 'ROOT', self.root), patch.object(managed, 'LaunchAgent') as factory:
            factory.return_value.owned.return_value = True
            managed.start_saved(saved); factory.return_value.start.assert_called_once()
            changed = {**saved, 'home': '/some-other-profile'}
            with self.assertRaisesRegex(ValueError, 'does not match'): managed.start_saved(changed)
            factory.return_value.start.assert_called_once()

    def test_provider_errors_do_not_expose_secrets_and_empty_results_are_rejected(self):
        settings, secret = managed.model_configuration(self.root, self.request)
        with patch.object(managed.urllib.request, 'build_opener') as build:
            build.return_value.open.side_effect = urllib.error.HTTPError(self.request['url'], 401,
                'private-test-key', {}, io.BytesIO(b'private-test-key'))
            with self.assertRaisesRegex(ValueError, 'HTTP 401') as error: managed.probe_model(settings, secret)
            self.assertNotIn(secret, str(error.exception))
            build.return_value.open.side_effect = None
            build.return_value.open.return_value = io.BytesIO(b'{"choices":[]}')
            with self.assertRaisesRegex(ValueError, 'compatible chat response'): managed.probe_model(settings, secret)


if __name__ == '__main__': unittest.main()
