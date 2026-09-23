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
if __name__=='__main__':unittest.main()
