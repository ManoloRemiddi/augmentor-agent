# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Private receipt readback; inert installer bytes are never executed."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))
from lifecycle.installed_source import open_installed_source, PREFIX
from platform_adapters.paths import private_directory
from platform_adapters.private_files import descriptor


class InstalledSourceTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=private_directory(Path(temporary.name)/'recovery')
        self.installer=b'MZ inert source-retention fixture'
        self.digest=hashlib.sha256(self.installer).hexdigest()
        self.release={'version':'1.0.0','channel':'preview','sourceCommit':'a'*40,
            'target':'windows-x64','dataSchema':1,'readableDataSchemas':[1]}
        self.raw=json.dumps(self.release).encode('utf-8')
        self.release_digest=hashlib.sha256(self.raw).hexdigest().encode('ascii')
        self.selected=PREFIX+self.digest.encode('ascii')+b'\n'+self.release_digest+b'\n'
        self.write(self.digest+'.exe',self.installer)
        self.write(self.digest+'.release',self.release_digest)
        self.write('selected-installer',self.selected)

    def write(self,name,value):
        with os.fdopen(descriptor(self.root/name,writable=True,create=True),'wb') as stream:
            stream.write(value);stream.truncate()

    def open(self, raw=None, target='windows-x64'):
        return open_installed_source(self.root,self.raw if raw is None else raw,target=target)

    def test_exact_selection_pins_original_source_without_execution(self):
        with self.open() as source:
            self.assertEqual(source.identity,{**self.release,'sha256':self.digest})
            self.assertEqual(source.release_digest,self.release_digest.decode('ascii'))
            self.assertEqual(source.installer.read_bytes(),self.installer)
            if sys.platform=='win32':
                with self.assertRaises(OSError):os.close(descriptor(source.installer,writable=True))
                with self.assertRaises(OSError):source.installer.unlink()
        self.assertIsNone(source.fd)

    def test_changed_installed_metadata_and_wrong_cpu_refuse(self):
        with self.assertRaisesRegex(ValueError,'identified application'):self.open(self.raw+b' ')
        with self.assertRaisesRegex(ValueError,'CPU'):self.open(target='windows-arm64')

    def test_missing_selection_never_guesses_from_cached_files(self):
        (self.root/'selected-installer').unlink()
        with self.assertRaises(FileNotFoundError):self.open()
        self.assertEqual((self.root/(self.digest+'.exe')).read_bytes(),self.installer)

    def test_invalid_or_oversized_selection_is_preserved(self):
        for raw in (b'',self.selected[:-1],self.selected+b'extra',self.selected.upper(),b'X'*65536):
            self.write('selected-installer',raw)
            with self.subTest(size=len(raw)),self.assertRaises(ValueError):self.open()
            self.assertEqual((self.root/'selected-installer').read_bytes(),raw)

    def test_damaged_source_or_receipt_does_not_select_alternative_or_delete_data(self):
        for name,original in ((self.digest+'.exe',self.installer),(self.digest+'.release',self.release_digest)):
            self.write(name,b'X'+original[1:])
            with self.subTest(name=name),self.assertRaises(ValueError):self.open()
            self.assertEqual((self.root/name).read_bytes(),b'X'+original[1:])
            self.write(name,original)

    def test_hardlinked_selection_receipt_and_installer_refuse(self):
        for name in ('selected-installer',self.digest+'.release',self.digest+'.exe'):
            alias=self.root/'alias';os.link(self.root/name,alias)
            try:
                with self.subTest(name=name),self.assertRaises((ValueError,PermissionError)):self.open()
            finally:alias.unlink()


if __name__=='__main__':unittest.main()
