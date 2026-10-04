# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Public plugin sources cannot be silently replaced by another archive."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('complete',ROOT/'scripts/package-complete.py')
complete=importlib.util.module_from_spec(spec);spec.loader.exec_module(complete)


class PublishedSources(unittest.TestCase):
    def test_exact_distributed_plugin_source_retains_bytes_and_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);package=root/'published.tgz';package.write_bytes(b'public synthetic source')
            target=root/'source.tar.gz'
            ref=complete.source_archive(package,target,package)
            self.assertEqual(target.read_bytes(),package.read_bytes())
            self.assertEqual(ref,'package-sha256:'+complete.sha(package))

    def test_another_source_archive_cannot_enter_the_public_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);package=root/'published.tgz';package.write_bytes(b'public synthetic source')
            other=root/'other.tgz';other.write_bytes(b'unreviewed synthetic source')
            with self.assertRaises(ValueError):complete.source_archive(other,root/'source.tar.gz',package)
            self.assertFalse((root/'source.tar.gz').exists())


if __name__=='__main__':unittest.main()
