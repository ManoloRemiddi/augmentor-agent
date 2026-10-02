# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Run the shared first-run transaction against actual OS files and fixture DSH."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))
from dsh import managed, setup
from platform_adapters.paths import private_directory


class AgentFixture:
    label = 'fixture-managed-dsh'
    def __init__(self): self.active = False; self.exists = False
    def loaded(self): return self.active
    def owned(self): return self.exists
    def start(self): self.active = self.exists = True
    def stop_failed_setup(self): self.active = False


class SetupFixture:
    def check(self, params): self.params = params; return {'installed': True, 'token': 'fixture'}
    def save(self, token, managed=None):
        setup.atomic(setup.configuration(), json.dumps({'dsh': {**self.params, 'managed': managed}}))


class ManagedDshTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.base = private_directory(Path(temporary.name)/'owned')
        self.root = self.base/'app'; self.state = self.base/'managed'
        for path in managed.runtime_paths(self.root):
            path.parent.mkdir(parents=True, exist_ok=True); path.write_text('fixture')
        self.agent = AgentFixture(); self.complete = managed.load_complete(ROOT)
        self.voice = Mock(); self.probe = Mock()
        for item in (patch.dict(os.environ, {'AUGMENTOR_SHARED_CONFIG': str(private_directory(self.base/'config'))}),
                     patch.object(setup, 'Setup', SetupFixture)):
            item.start(); self.addCleanup(item.stop)
        item = patch.object(self.complete, 'configure_product')
        self.bootstrap = item.start(); self.addCleanup(item.stop)

    def provision(self):
        return managed.provision(self.root, self.state, {'action': 'install-runtime'},
            agent=self.agent, manager_type='fixture', complete=self.complete,
            voice_initializer=self.voice, probe=self.probe)

    def test_native_profile_links_engine_setup_and_lost_ack_retry(self):
        self.assertTrue(self.provision()['saved']); self.probe.assert_not_called()
        self.assertEqual((self.state/'home/profiles/web/node_modules').resolve(), (self.root/'dsh/node_modules').resolve())
        runtime = managed.private_json(self.state/'runtime.json')
        self.assertEqual(runtime['apiKey'], '')
        record = managed.private_json(self.state/'setup.json'); record['status'] = 'starting'
        managed.atomic_json(self.state/'setup.json', record)
        setup.configuration().unlink()
        self.assertTrue(self.provision()['saved'])
        self.bootstrap.assert_called_once(); self.voice.assert_called_once()
        self.assertEqual(setup.current()['managed']['type'], 'fixture')

    def test_failed_bootstrap_retries_owned_profile(self):
        self.bootstrap.side_effect = ValueError('fixture failure')
        with self.assertRaisesRegex(ValueError, 'fixture failure'): self.provision()
        self.assertFalse(setup.current()); self.assertFalse(self.agent.active)
        self.assertEqual(managed.private_json(self.state/'setup.json')['status'], 'failed')
        self.bootstrap.side_effect = None
        self.assertTrue(self.provision()['saved'])


if __name__ == '__main__': unittest.main()
