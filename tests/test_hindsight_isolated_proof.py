# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Pure preparation gates; no Docker, model or personal configuration needed."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('isolated_memory_proof', Path(__file__).resolve().parents[1] / 'scripts/hindsight-isolated-proof-engine.py')
proof = importlib.util.module_from_spec(spec); spec.loader.exec_module(proof)


class ProofInputTests(unittest.TestCase):
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


if __name__ == '__main__': unittest.main()
