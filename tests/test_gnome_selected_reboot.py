# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Unknown reboot transport outcomes must not cause a second request."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('selected_reboot',
    Path(__file__).resolve().parents[1]/'release/prove-gnome-selected-reboot.py')
proof = importlib.util.module_from_spec(spec); spec.loader.exec_module(proof)


@unittest.skipUnless(sys.platform.startswith('linux'), 'Owned GNOME reboot proof uses Linux file ownership and no-follow guards.')
class RebootOwnershipTests(unittest.TestCase):
    def test_interrupted_receipt_and_symlink_cannot_be_adopted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'run.json'
            pending = {'phase': 'request-pending', 'artifactSha256': 'a'*64}
            proof.begin_receipt(path, pending)
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):proof.begin_receipt(path, pending)
            self.assertEqual(path.read_bytes(), original)
            link = path.with_name('linked.json'); link.symlink_to(path)
            with self.assertRaises(FileExistsError):proof.begin_receipt(link, pending)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_real_transport_timeout_dispatches_one_child_and_retains_unknown_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            count = Path(directory)/'dispatches'
            # Real subprocess transport: dispatch writes once, then the caller
            # loses its response. The accelerated timeout exercises run's actual
            # child termination instead of mocking a successful reboot.
            script = Path(directory)/'transport.py'
            script.write_text('import pathlib,time\npathlib.Path('+repr(str(count))+').write_text("one request")\ntime.sleep(2)\n')
            actual_run = subprocess.run
            def bounded(command, **kwargs):
                kwargs['timeout'] = .5
                return actual_run(['python3', str(script)], **kwargs)
            record = {}
            with patch.object(proof.subprocess, 'run', side_effect=bounded) as run:
                proof.request_once(['synthetic-ssh'], 'synthetic input', record)
            self.assertEqual(run.call_count, 1)
            self.assertEqual(count.read_text(), 'one request')
            self.assertTrue(record['singleRebootRequestAttempted'])
            self.assertTrue(record['requestTransportTimeout'])
            self.assertNotIn('requestExitCode', record)

    def test_lost_connection_does_not_claim_reboot_or_retry(self):
        result = subprocess.CompletedProcess(['synthetic-ssh'], 255, 'request begun', 'connection closed')
        record = {}
        with patch.object(proof.subprocess, 'run', return_value=result) as run:
            proof.request_once(['synthetic-ssh'], 'one request', record)
        run.assert_called_once()
        self.assertEqual(record['requestExitCode'], 255)
        self.assertNotIn('kernelBootIdentityChanged', record)
        self.assertNotIn('passed', record)


if __name__ == '__main__':unittest.main()
