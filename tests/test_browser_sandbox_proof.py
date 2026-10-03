# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fail closed when browser diagnostics and actual renderer evidence disagree."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('sandbox_proof', Path(__file__).resolve().parents[1] / 'scripts/proof_browser_sandbox.py')
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)


class SandboxEvidenceTests(unittest.TestCase):
    def test_actual_chromium_title_and_original_arguments(self):
        for raw, source in [(b'/usr/lib64/chromium/chrome --type=renderer --no-sandbox\0', 'chromium-process-title-tokens'),
                            (b'/usr/lib64/chromium/chrome\0--type=renderer\0--no-sandbox\0', 'nul-separated-argv')]:
            args, actual_source = proof.command_arguments(raw)
            self.assertEqual(actual_source, source)
            self.assertIn(b'--type=renderer', args)
            self.assertIn(b'--no-sandbox', args)

    def fixture(self):
        return {'chromiumExpectedRendererSandbox': {'sandboxGood': True, 'suid': False, 'userNs': True,
                'pidNs': True, 'netNs': True, 'seccompBpf': True},
                'processes': {'browser': {'disabledSandboxArguments': [], 'namespaces': {'pid': 'pid:[1]', 'net': 'net:[2]'}},
                'renderers': [{'browserDescendantVerified': True, 'seccomp': 2, 'noNewPrivs': 1,
                               'namespaces': {'pid': 'pid:[3]', 'net': 'net:[4]'}}]}}

    def test_missing_renderer_is_not_acceptance(self):
        report = self.fixture(); report['processes']['renderers'] = []
        with self.assertRaises(AssertionError): proof.verify(report)

    def test_expected_status_alone_is_not_acceptance(self):
        for key, value in [('seccomp', 0), ('noNewPrivs', 0), ('browserDescendantVerified', False)]:
            with self.subTest(key=key):
                report = self.fixture(); report['processes']['renderers'][0][key] = value
                with self.assertRaises(AssertionError): proof.verify(report)

    def test_inherited_filter_or_unreadable_namespace_is_not_acceptance(self):
        for kind in ('pid', 'net'):
            for actual in (self.fixture()['processes']['browser']['namespaces'][kind], {'error': 'PermissionError'}):
                with self.subTest(kind=kind, actual=actual):
                    report = self.fixture(); report['processes']['renderers'][0]['namespaces'][kind] = actual
                    with self.assertRaises(AssertionError): proof.verify(report)

    def test_process_data_cannot_override_bad_browser_status(self):
        report = self.fixture(); report['chromiumExpectedRendererSandbox']['sandboxGood'] = False
        with self.assertRaises(AssertionError): proof.verify(report)

    def test_explicit_disabling_argument_is_rejected(self):
        report = self.fixture(); report['processes']['browser']['disabledSandboxArguments'] = ['--no-sandbox']
        with self.assertRaises(AssertionError): proof.verify(report)


if __name__ == '__main__': unittest.main()
