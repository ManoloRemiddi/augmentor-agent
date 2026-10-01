# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('codex_credentials', Path(__file__).resolve().parents[1] / 'services/codex/credentials.py')
credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(credentials)


class Store:
    def __init__(self): self.values = {}
    def get_password(self, service, ref): return self.values.get((service, ref))
    def set_password(self, service, ref, value): self.values[(service, ref)] = value
    def delete_password(self, service, ref): self.values.pop((service, ref), None)


class CodexCredentialsTests(unittest.TestCase):
    def test_scoped_credential_roundtrip_and_idempotent_removal(self):
        store = Store()
        request = {'reference': 'codex-fixture', 'operation': 'put', 'value': 'synthetic-key'}
        self.assertEqual(credentials.handle(request, store), {'saved': True})
        self.assertEqual(credentials.handle({**request, 'operation': 'get'}, store), {'value': 'synthetic-key'})
        for _ in range(2): self.assertEqual(credentials.handle({**request, 'operation': 'delete'}, store), {'deleted': True})
        self.assertEqual(credentials.handle({**request, 'operation': 'get'}, store), {'value': None})

    def test_invalid_references_values_and_operations_never_reach_store(self):
        store = Store()
        for request in [None, {'operation': 'list'}, {'operation': 'get', 'reference': 'other-app'},
                        {'operation': 'put', 'reference': 'codex-fixture', 'value': ''},
                        {'operation': 'put', 'reference': 'codex-fixture', 'value': 'a' * 65537}]:
            with self.assertRaises(ValueError): credentials.handle(request, store)
        self.assertEqual(store.values, {})


if __name__ == '__main__': unittest.main()
