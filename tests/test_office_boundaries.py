# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Trace evidence refuses unpaired calls, wrong attribution and extra access.

These are parser negative controls. Real-engine/cgroup evidence is separate.
"""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('office_boundaries', ROOT / 'release/office-rebuild/contained-boundaries.py')
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class OfficeBoundaryTraceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / 'trace.log'
        self.result = {'driverPid': 9, 'canaryPort': 31337}
        self.lines = [f'{pid:<6}openat(AT_FDCWD, "/app/assets/soffice.wasm", O_RDONLY|O_CLOEXEC) = 50'
                      for pid in range(20, 28)]
        for name in ['only-on-host.png', 'only-on-host.txt']:
            self.lines += [f'9     openat(AT_FDCWD, "/work/outside/{name}", O_RDONLY|O_CLOEXEC) = 18'] * 2
        self.lines += ['9     connect(19, {sa_family=AF_INET, sin_port=htons(31337), sin_addr=inet_addr("127.0.0.1")}, 16) = -1 EINPROGRESS (Operation now in progress)']
        self.nss = '9     connect(21, {sa_family=AF_UNIX, sun_path="/var/run/nscd/socket"}, 110) = -1 ENOENT (No such file or directory)'
        self.lines += [self.nss] * 2

    def evidence(self, lines=None):
        self.path.write_text('\n'.join(self.lines if lines is None else lines) + '\n')
        return PROBE.trace_evidence(self.path, self.result)

    def test_actual_padding_and_failed_unix_nss_are_distinct_from_ip_positive_control(self):
        result = self.evidence()
        self.assertEqual(result['successfulWasmOpens'], 8)
        self.assertEqual(result['connectCalls'], 3)
        self.assertEqual(result['failedParentContainerNssSocketCalls'], 2)
        self.assertEqual(result['ipConnectCalls'], 1)
        self.assertTrue(result['soleIpConnectIsDriverHttpPositiveControl'])

    def test_interleaved_unfinished_and_resumed_calls_keep_thread_identity(self):
        lines = ['20    openat(AT_FDCWD, "/app/assets/soffice.wasm", O_RDONLY|O_CLOEXEC <unfinished ...>',
                 self.lines[1], '20    <... openat resumed>) = 50', *self.lines[2:]]
        self.assertEqual(self.evidence(lines)['successfulWasmOpens'], 8)
        with self.assertRaises(ValueError):
            self.evidence(['20    <... openat resumed>) = 50', *self.lines])
        with self.assertRaises(ValueError):
            self.evidence([*self.lines, '20    openat(AT_FDCWD, "/tmp/pending", O_RDONLY <unfinished ...>'])

    def test_converter_canary_reads_fail_even_when_driver_still_reads_twice(self):
        for name in ['only-on-host.png', 'only-on-host.txt']:
            with self.subTest(name=name), self.assertRaises(AssertionError):
                self.evidence([*self.lines, f'40    openat(AT_FDCWD, "/work/outside/{name}", O_RDONLY) = 33'])

    def test_extra_ip_or_unix_destination_and_wrong_driver_attribution_fail(self):
        for extra in [
            '40    connect(19, {sa_family=AF_INET, sin_port=htons(31337), sin_addr=inet_addr("127.0.0.1")}, 16) = -1 EINPROGRESS (Operation now in progress)',
            '40    connect(19, {sa_family=AF_INET, sin_port=htons(80), sin_addr=inet_addr("203.0.113.1")}, 16) = -1 ENETUNREACH (Network is unreachable)',
            '40    connect(21, {sa_family=AF_UNIX, sun_path="/tmp/other"}, 110) = -1 ENOENT (No such file or directory)',
            self.nss.replace('9     ', '40    '),
        ]:
            with self.subTest(extra=extra), self.assertRaises(AssertionError):
                self.evidence([*self.lines, extra])

    def test_missing_canary_or_engine_observation_is_not_a_clean_trace(self):
        for omitted in [0, 8]:
            with self.subTest(omitted=omitted), self.assertRaises(AssertionError):
                self.evidence(self.lines[:omitted] + self.lines[omitted+1:])

    def test_owned_closed_renderer_nss_attribution_does_not_allow_its_file_or_ip_access(self):
        self.result.update(diagnosticProcessBoundary=True, rendererProcesses=[{'pid': 40, 'closed': True}])
        lines = [*self.lines, self.nss.replace('9     ', '40    ')]
        result = self.evidence(lines)
        self.assertEqual(result['ownedRendererProcessesConfirmedClosed'], 1)
        self.assertEqual(result['failedParentContainerNssSocketCalls'], 3)
        without_nss = [line for line in self.lines if '/var/run/nscd/socket' not in line]
        self.assertEqual(self.evidence(without_nss)['failedParentContainerNssSocketCalls'], 0)
        for access in [
            '40    openat(AT_FDCWD, "/work/outside/only-on-host.txt", O_RDONLY) = 33',
            '40    connect(19, {sa_family=AF_INET, sin_port=htons(31337), sin_addr=inet_addr("127.0.0.1")}, 16) = -1 EINPROGRESS (Operation now in progress)',
            self.nss.replace('9     ', '41    '),
        ]:
            with self.subTest(access=access), self.assertRaises(AssertionError):
                self.evidence([*lines, access])
        self.result['rendererProcesses'][0]['closed'] = False
        with self.assertRaises(AssertionError):
            self.evidence(lines)


if __name__ == '__main__':
    unittest.main()
