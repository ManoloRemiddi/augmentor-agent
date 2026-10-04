# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Build intake rejects incomplete, redirected and wrongly identified payloads."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('package_windows',ROOT/'scripts/package-windows.py')
package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)


class PackageTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)/'payload';self.root.mkdir()
        self.release={'version':'1.2.3','sourceCommit':'a'*40,'target':'windows-arm64',
                      'customerDistribution':False,'qualificationStatus':'development-candidate'}
        self.write_release()
        for name in ('Augmentor.exe','AugmentorBrowserHost.exe','python/python.exe','node/node.exe',
                     'powershell/pwsh.exe','updater/WinSparkle.dll','dsh/payload.json','scripts/launch-windows.py',
                     'scripts/windows-local-health.py','scripts/windows-inspect-payload.py',
                     'scripts/windows-recover-source.py','services/lifecycle/source_restoration.py',
                     'services/lifecycle/payload_integrity.py','services/lifecycle/recovery_source.py',
                     'services/lifecycle/health_report.py',
                     'components/handy/runtime/bin/handy.exe','components/handy/runtime/BUILD.json',
                     'licenses/Windows-installation-terms.txt',
                     'services/lifecycle/update_journal.py','services/platform_adapters/private_files.py',
                     'services/platform_adapters/locks.py'):
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture')
        from lifecycle.payload_integrity import seal_payload
        self.release=seal_payload(self.root)

    def write_release(self): (self.root/'release.json').write_text(json.dumps(self.release))

    def test_foreign_architecture_and_public_artifacts_never_enter_candidate_builder(self):
        self.assertEqual(package.candidate(self.root,'arm64'),self.release)
        with self.assertRaises(ValueError):package.candidate(self.root,'x64')
        self.release['customerDistribution']=True;self.write_release()
        with self.assertRaises(ValueError):package.candidate(self.root,'arm64')

    def test_public_preview_requires_opt_in_and_exact_limitations(self):
        from lifecycle.payload_integrity import seal_payload
        profile=json.loads((ROOT/'release/windows/public-preview.json').read_text())
        (self.root/'payload-integrity.json').unlink();self.release.pop('payloadSHA256')
        self.release.update(profile);self.write_release();self.release=seal_payload(self.root)
        with self.assertRaises(ValueError):package.candidate(self.root,'arm64')
        self.assertEqual(package.candidate(self.root,'arm64',public_preview=True),self.release)
        self.release['automaticUpdates']=True;self.write_release()
        with self.assertRaisesRegex(ValueError,'limitations'):
            package.candidate(self.root,'arm64',public_preview=True)

    def test_partial_payload_refuses_before_build(self):
        (self.root/'node/node.exe').unlink()
        with self.assertRaisesRegex(ValueError,'Incomplete'):package.candidate(self.root,'arm64')

    def test_dictation_is_a_required_part_of_complete_windows_payload(self):
        (self.root/'components/handy/runtime/bin/handy.exe').unlink()
        with self.assertRaisesRegex(ValueError,'Incomplete.*handy.exe'):package.candidate(self.root,'arm64')

    def test_changed_or_extra_build_files_cannot_silently_reseal(self):
        (self.root/'node/node.exe').write_text('changed')
        with self.assertRaisesRegex(ValueError,'changed'):package.candidate(self.root,'arm64')
        (self.root/'node/node.exe').write_text('fixture')
        (self.root/'unintended-secret.txt').write_text('fixture never distribute')
        with self.assertRaisesRegex(ValueError,'unexpected'):package.candidate(self.root,'arm64')

    def test_distribution_never_follows_source_link_to_outside_files(self):
        other=self.root.parent/'foreign';other.mkdir();(other/'secret').write_text('fixture')
        link=self.root/'redirected'
        try:link.symlink_to(other,target_is_directory=True)
        except OSError as error:self.skipTest('This runner cannot create a test symlink: '+str(error))
        with self.assertRaisesRegex(ValueError,'reparse/link'):package.candidate(self.root,'arm64')
        self.assertEqual((other/'secret').read_text(),'fixture')


if __name__=='__main__':unittest.main()
