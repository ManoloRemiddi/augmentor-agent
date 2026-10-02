# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Ensure RPM configuration checking does not weaken Debian or version checks."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
spec=importlib.util.spec_from_file_location('fedora_lease',Path(__file__).resolve().parents[1]/'services/lifecycle/lease.py')
lease=importlib.util.module_from_spec(spec);spec.loader.exec_module(lease)
class PackageConfiguration(unittest.TestCase):
    def test_fedora_requires_exact_installed_version(self):
        with tempfile.TemporaryDirectory() as d,patch.object(lease,'ROOT',Path(d)):
            (Path(d)/'fedora-package.json').write_text('{}')
            (Path(d)/'release.json').write_text(json.dumps({'version':'0.2.9'}))
            for code,version,valid in [(0,'0.2.9',True),(0,'0.2.8',False),(1,'',False)]:
                with patch.object(lease.subprocess,'run',return_value=SimpleNamespace(returncode=code,stdout=version)) as run:
                    if valid:lease.configured('desktop')
                    else:
                        with self.assertRaises(RuntimeError):lease.configured('desktop')
                    self.assertEqual(run.call_args.args[0],['rpm','-q','--qf','%{VERSION}','augmentor-agent'])
    def test_debian_still_checks_each_component(self):
        with tempfile.TemporaryDirectory() as d,patch.object(lease,'ROOT',Path(d)),patch.object(lease.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='installed')) as run:
            lease.configured('desktop')
            self.assertEqual(run.call_args.args[0][-1],'augmentor-desktop')
            self.assertEqual(run.call_args.args[0][0],'dpkg-query')

    def test_explicit_next_targets_require_full_version_release_and_source(self):
        for target,manager,version,stdout in [('opensuse-leap16.0-x86_64','rpm','0.2.13-1.leap16','augmentor-agent\n0.2.13-1.leap16\nx86_64'),
                ('arch20261001-x86_64','pacman','0.2.13-1','augmentor-agent 0.2.13-1\n')]:
            with self.subTest(target=target),tempfile.TemporaryDirectory() as d,patch.object(lease,'ROOT',Path(d)):
                source={'commit':'a'*40,'dirty':False}
                release={'version':'0.2.13','target':target,'source':source}
                value={'format':'augmentor-linux-package-receipt/1','target':target,'manager':manager,
                       'version':'0.2.13','source':source,'package':{'name':'augmentor-agent','versionRelease':version,'architecture':'x86_64'}}
                (Path(d)/'release.json').write_text(json.dumps(release));receipt=Path(d)/'linux-package.json'
                receipt.write_text(json.dumps(value))
                with patch.object(lease.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=stdout)) as run:
                    lease.configured('desktop');self.assertEqual(run.call_args.args[0][0],manager)
                with patch.object(lease.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=stdout.replace(version,'0.2.13-99'))):
                    with self.assertRaises(RuntimeError):lease.configured('desktop')
                value['source']={'commit':'b'*40,'dirty':False};receipt.write_text(json.dumps(value))
                with patch.object(lease.subprocess,'run') as run:
                    with self.assertRaisesRegex(RuntimeError,'identity'):lease.configured('desktop')
                    run.assert_not_called()
if __name__=='__main__':unittest.main()
