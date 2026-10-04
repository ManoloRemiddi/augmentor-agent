# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Whole-bundle boundaries with inert framework links; no signing claim."""
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from lifecycle.macos_payload import snapshot


@unittest.skipUnless(sys.platform in ('linux','darwin'),'requires Unix symlinks')
class MacPayloadTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='ab-');self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name);self.bundle=self.base/'Fixture.app'
        self.framework=self.bundle/'Contents/Frameworks/Inert.framework'
        (self.framework/'Versions/A').mkdir(parents=True)
        (self.framework/'Versions/A/Inert').write_bytes(b'Inert framework bytes.')
        (self.framework/'Versions/Current').symlink_to('A',target_is_directory=True)
        (self.framework/'Inert').symlink_to('Versions/Current/Inert')

    def test_relocated_copy_preserves_whole_bundle_and_internal_links(self):
        original=snapshot(self.bundle)
        copy=self.base/'retained/Copy.app';copy.parent.mkdir()
        shutil.copytree(self.bundle,copy,symlinks=True)
        self.assertEqual(snapshot(copy),original)
        (copy/'Contents/Frameworks/Inert.framework/Versions/A/Inert').write_bytes(b'Changed inert bytes.')
        self.assertNotEqual(snapshot(copy)['sha256'],original['sha256'])
        self.assertEqual((self.framework/'Inert').read_bytes(),b'Inert framework bytes.')

    def test_external_dangling_and_hard_links_refuse_without_removing_source(self):
        sentinel=self.base/'keep';sentinel.write_bytes(b'Preserve this fixture.')
        link=self.bundle/'external';link.symlink_to(sentinel)
        with self.assertRaises(ValueError):snapshot(self.bundle)
        link.unlink();link.symlink_to('missing')
        with self.assertRaises(FileNotFoundError):snapshot(self.bundle)
        link.unlink();os.link(sentinel,link)
        with self.assertRaises(ValueError):snapshot(self.bundle)
        self.assertEqual(sentinel.read_bytes(),b'Preserve this fixture.')


if __name__=='__main__':unittest.main()
