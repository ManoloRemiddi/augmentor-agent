# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Synthetic wheel inventories exercise byte identity and archive boundaries."""
import hashlib
import importlib.util
from pathlib import Path
import stat
import tempfile
import unittest
import warnings
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('wheel_inventory',ROOT/'scripts/linux-wheel-inventory.py')
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)


class WheelInventoryTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.root=Path(folder.name);self.wheel=self.root/'fixture-1.0-py3-none-any.whl'

    def value(self,members=(),metadata=b'Name: fixture\nVersion: 1.0\nLicense: MIT\n'):
        with warnings.catch_warnings(),zipfile.ZipFile(self.wheel,'w') as archive:
            warnings.simplefilter('ignore',UserWarning)
            archive.writestr('fixture-1.0.dist-info/METADATA',metadata)
            for name,content in members:archive.writestr(name,content)
        return {'target':'ubuntu24.04-amd64','profile':'synthetic', 'pythonAbi':[3,12],
                'architecture':'x86_64','systemSitePackages':True,'python':'/usr/bin/python3',
                'wheels':[{'name':'fixture','version':'1.0','file':self.wheel.name,
                           'sha256':hashlib.sha256(self.wheel.read_bytes()).hexdigest(),
                           'bytes':self.wheel.stat().st_size}]}

    def test_preserves_notice_bytes_and_hashes_versioned_elf_and_executable(self):
        notice=b'Copyright fixture\r\nMIT\r\n';elf=b'\x7fELFfixture bytes'
        value=self.value([('fixture/LICENSE.txt',notice),('fixture/lib.so.73',elf),('fixture/tool',elf)])
        report,texts=tool.inventory(value,self.root)
        self.assertEqual(texts,{'fixture-1.0/fixture/LICENSE.txt':notice})
        row=report['wheels'][0]
        self.assertEqual(row['declaredLicense'],'MIT')
        self.assertEqual({r['path'] for r in row['elfBinaries']},{'fixture/lib.so.73','fixture/tool'})
        self.assertTrue(all(r['sha256']==hashlib.sha256(elf).hexdigest() for r in row['elfBinaries']))
        self.assertFalse(report['licenseReviewComplete']);self.assertFalse(report['embeddedSourceCoverageComplete'])

    def test_absent_wheel_notices_are_reported_without_invented_text(self):
        report,texts=tool.inventory(self.value(),self.root)
        self.assertEqual(report['missingWheelNotices'],['fixture']);self.assertEqual(texts,{})

    def test_archive_paths_duplicates_and_symlinks_are_refused(self):
        symlink=zipfile.ZipInfo('fixture/link');symlink.external_attr=(stat.S_IFLNK|0o777)<<16
        for members in [[('../LICENSE',b'escape')],[('/LICENSE',b'escape')],
                        [('fixture\\LICENSE',b'escape')],[(symlink,b'target')],
                        [('fixture/LICENSE',b'one'),('fixture/LICENSE',b'two')]]:
            with self.subTest(members=members),self.assertRaisesRegex(ValueError,'Unsafe or duplicate'):
                tool.inventory(self.value(members),self.root)

    def test_changed_archive_is_refused_before_zip_inspection(self):
        value=self.value();self.wheel.write_bytes(b'corrupted')
        with self.assertRaisesRegex(ValueError,'checksum/size'):tool.inventory(value,self.root)

    def test_mismatching_or_duplicate_metadata_is_refused(self):
        for metadata in (b'Name: another\nVersion: 1.0\n',b'Name: fixture\nVersion: 2.0\n',b'Version: 1.0\n'):
            with self.subTest(metadata=metadata),self.assertRaises(ValueError):
                tool.inventory(self.value(metadata=metadata),self.root)
        value=self.value([('other.dist-info/METADATA',b'Name: fixture\nVersion: 1.0\n')])
        with self.assertRaisesRegex(ValueError,'Multiple'):tool.inventory(value,self.root)


if __name__=='__main__':unittest.main()
