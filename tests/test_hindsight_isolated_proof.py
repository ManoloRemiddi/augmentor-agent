# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Pure preparation gates; no Docker, model or personal configuration needed."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('isolated_memory_proof', Path(__file__).resolve().parents[1] / 'scripts/hindsight-isolated-proof-engine.py')
proof = importlib.util.module_from_spec(spec); spec.loader.exec_module(proof)


class ProofInputTests(unittest.TestCase):
    def test_memory_only_mode_preserves_the_existing_choice_unless_explicitly_selected(self):
        off = {'HINDSIGHT_API_' + op + 'LLM_EXTRA_BODY': json.dumps({'chat_template_kwargs': {'enable_thinking': False}})
               for op in ('', 'RETAIN_', 'REFLECT_', 'CONSOLIDATION_')}
        self.assertEqual(proof.thinking_mode({}), ('default', 'default'))
        self.assertEqual(proof.thinking_mode(off), ('off', 'off'))
        self.assertEqual(proof.thinking_mode({}, 'off'), ('default', 'off'))
        self.assertEqual(proof.thinking_mode(off, 'default'), ('off', 'default'))
        with self.assertRaisesRegex(ValueError, 'uniform'):
            proof.thinking_mode({**off, 'HINDSIGHT_API_RETAIN_LLM_EXTRA_BODY': 'null'}, 'off')
        with self.assertRaisesRegex(ValueError, 'default/off'):
            proof.thinking_mode({}, 'automatic')

    def test_local_public_declaration_preserves_limits_and_rejects_credentials_or_remote_targets(self):
        good = {'api': 'openai-completions', 'baseUrl': 'http://127.0.0.1:8080/v1',
                'models': [{'id': 'declared-model', 'contextWindow': 262144, 'maxTokens': 8192}]}
        self.assertEqual(proof.provider(good)['maxTokens'], 8192)
        for bad in [{**good, 'apiKey': 'synthetic-key'}, {**good, 'baseUrl': 'https://example.invalid/v1'},
                    {**good, 'baseUrl': 'http://user:pass@127.0.0.1:8080/v1'},
                    {**good, 'models': [{**good['models'][0], 'contextWindow': 8192}]}]:
            with self.assertRaises(ValueError): proof.provider(bad)

    def test_cache_has_exact_public_roots_and_rejects_credentials_and_symlink_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'cache'; root.mkdir()
            for name in proof.CACHE_MODELS: (root / name).mkdir()
            blob = root / proof.CACHE_MODELS[0] / 'public-weights'; blob.write_bytes(b'authored-model-fixture')
            self.assertEqual(len(proof.cache_inventory(root)), 1)
            secret = root / proof.CACHE_MODELS[1] / 'token'; secret.write_text('synthetic-credential')
            with self.assertRaisesRegex(ValueError, 'Credentials'): proof.cache_inventory(root)
            secret.unlink(); outside = Path(temp) / 'outside'; outside.write_text('outside')
            link = root / proof.CACHE_MODELS[1] / 'link'; link.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, 'escapes'): proof.cache_inventory(root)
            link.unlink(); (root / 'unexpected').mkdir()
            with self.assertRaisesRegex(ValueError, 'exactly'): proof.cache_inventory(root)

    def test_changed_container_identity_is_never_managed_as_the_owned_instance(self):
        proof.same_instance({'Id': 'authored-owned'}, 'authored-owned')
        with self.assertRaisesRegex(ValueError, 'identity changed'):
            proof.same_instance({'Id': 'different-instance'}, 'authored-owned')

    def test_installer_proof_cleanup_requires_both_exact_identity_and_ready_private_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); shared = root / 'shared-data'; shared.mkdir()
            receipt = {'protocol': 'augmentor-memory-installation/1', 'phase': 'ready', 'installationId': 'authored-installation',
                       'containerId': 'authored-instance', 'name': 'augmentor-pi-memory-proof-authored', 'volume': 'authored-volume'}
            (shared / 'hindsight-installation.json').write_text(json.dumps(receipt))
            record = {**receipt, 'installerOwnership': {'protocol': receipt['protocol'], 'installationId': receipt['installationId']}}
            current = {'Id': receipt['containerId'], 'Config': {'Labels': {'org.augmentor.memory.installation': receipt['installationId']}}}
            proof.validate_stop_owner(record, current, root)
            for bad in [{**current, 'Id': 'replacement'}, {**current, 'Config': {'Labels': {}}}]:
                with self.assertRaisesRegex(ValueError, 'exact installer-owned'): proof.validate_stop_owner(record, bad, root)
            (shared / 'hindsight-installation.json').write_text(json.dumps({**receipt, 'phase': 'creating'}))
            with self.assertRaisesRegex(ValueError, 'exact installer-owned'): proof.validate_stop_owner(record, current, root)

    def test_backport_refuses_an_unknown_engine_before_creating_an_overlay(self):
        backport = proof.backport_module()
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / 'overlay'
            with self.assertRaisesRegex(ValueError, 'pinned base'):
                backport.prepare(b'Independently authored unknown engine', destination)
            self.assertFalse(destination.exists())

    def test_backport_rejects_changed_supplier_inputs_and_changed_mounted_output(self):
        backport = proof.backport_module()
        with tempfile.TemporaryDirectory() as temp:
            vendor = Path(temp) / 'vendor'; vendor.mkdir()
            for name in ('SOURCE.json', 'LICENSE', 'refresh-budget.patch'):
                (vendor / name).write_bytes((backport.VENDOR / name).read_bytes())
            with patch.object(backport, 'VENDOR', vendor):
                backport.manifest()
                (vendor / 'refresh-budget.patch').write_bytes(b'Independently authored replacement')
                with self.assertRaisesRegex(ValueError, 'input changed'):
                    backport.manifest()
            output = Path(temp) / 'memory_engine.py'; output.write_bytes(b'Independently authored original')
            value = {'path': str(output), 'sha256': backport.digest(output.read_bytes())}
            backport.verify(value); output.write_bytes(b'Independently authored replacement')
            with self.assertRaisesRegex(ValueError, 'overlay changed'):
                backport.verify(value)


if __name__ == '__main__': unittest.main()
