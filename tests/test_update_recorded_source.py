# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Interrupted-source lookup with real private files; installer bytes are inert."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))
from lifecycle.installed_source import open_recorded_source, PREFIX
from lifecycle.recovery_source import assess_source
from lifecycle.update_journal import UpdateJournal
from platform_adapters.paths import private_directory
from platform_adapters.private_files import descriptor


class RecordedSourceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = private_directory(Path(temporary.name)/'recovery')
        self.updates = private_directory(Path(temporary.name)/'updates')
        self.original = b'MZ inert recorded source fixture'
        self.digest = hashlib.sha256(self.original).hexdigest()
        self.release = {'version':'1.0.0','sourceCommit':'a'*40,'target':'windows-x64',
                        'channel':'preview','dataSchema':1,'readableDataSchemas':[1]}
        self.metadata = json.dumps(self.release).encode()
        self.release_digest = hashlib.sha256(self.metadata).hexdigest()
        self.identity = {**self.release, 'sha256':self.digest}
        self.future_bytes = b'MZ inert newer target fixture'
        self.future_digest = hashlib.sha256(self.future_bytes).hexdigest()
        self.future = {**self.identity, 'version':'1.1.0','sourceCommit':'b'*40,'sha256':self.future_digest}
        self.write(self.digest+'.exe', self.original)
        self.write(self.digest+'.release', self.release_digest.encode())
        self.write(self.future_digest+'.exe', self.future_bytes)
        self.write(self.future_digest+'.release', b'f'*64)
        with UpdateJournal(self.updates,self.identity,self.future) as journal:
            for phase in ('preparing','prepared','drained','installer-ready','apply-intent'):
                journal.advance(phase)
        self.record = (self.updates/'active.json').read_bytes()

    def write(self, name, raw):
        with os.fdopen(descriptor(self.root/name,writable=True,create=True),'wb') as stream:
            stream.write(raw); stream.truncate()

    def open(self, raw=None, target='windows-x64'):
        return open_recorded_source(self.root,self.record if raw is None else raw,target=target)

    def test_previous_source_survives_new_missing_or_corrupt_selection(self):
        for selected in (None, b'incomplete selection', PREFIX+self.future_digest.encode()+b'\n'+b'f'*64+b'\n'):
            if selected is not None:self.write('selected-installer',selected)
            with self.subTest(selected=selected), self.open() as source:
                self.assertEqual(source.identity,self.identity)
                self.assertEqual(source.installer,self.root/(self.digest+'.exe'))
                self.assertEqual(source.release_digest,self.release_digest)
                self.assertEqual(source.record_digest,hashlib.sha256(self.record).hexdigest())
                self.assertEqual(source.transaction_id,json.loads(self.record)['id'])
                assessed=assess_source(self.record,self.metadata,source.identity['sha256'])
                self.assertEqual(assessed['recordSHA256'],source.record_digest)
                self.assertFalse(assessed['applyAuthorized'])
            self.assertIsNone(source.fd)
            self.assertEqual((self.updates/'active.json').read_bytes(),self.record)
            if selected is not None:self.assertEqual((self.root/'selected-installer').read_bytes(),selected)

    def test_missing_previous_source_never_falls_back_to_newer_cached_installer(self):
        for suffix in ('.exe','.release'):
            path=self.root/(self.digest+suffix); original=path.read_bytes(); path.unlink()
            try:
                with self.subTest(suffix=suffix),self.assertRaises(FileNotFoundError):self.open()
                self.assertEqual((self.root/(self.future_digest+'.exe')).read_bytes(),self.future_bytes)
                self.assertEqual((self.updates/'active.json').read_bytes(),self.record)
            finally:self.write(path.name,original)

    def test_damaged_source_and_invalid_receipt_are_preserved(self):
        for suffix,raw in (('.exe',b'changed source'),('.release',b'f'*63),
                           ('.release',b'F'*64),('.release',b'f'*65)):
            path=self.root/(self.digest+suffix); original=path.read_bytes(); self.write(path.name,raw)
            try:
                with self.subTest(suffix=suffix,raw=raw),self.assertRaises(ValueError):self.open()
                self.assertEqual(path.read_bytes(),raw)
            finally:self.write(path.name,original)

    def test_foreign_cpu_and_malformed_records_refuse_before_cache_access(self):
        with self.assertRaisesRegex(ValueError,'CPU'):self.open(target='windows-arm64')
        for raw in (b'',b'X'*65537,b'{"schema":1,"schema":2}',b'[]'):
            with self.subTest(raw=raw[:30]),self.assertRaises(ValueError):self.open(raw)
        record=json.loads(self.record); record['target']['dataSchema']=2
        with self.assertRaises(ValueError):self.open(json.dumps(record).encode())
        self.assertEqual((self.updates/'active.json').read_bytes(),self.record)

    def test_receipt_and_installer_aliases_refuse(self):
        for suffix in ('.exe','.release'):
            alias=self.root/'alias'; os.link(self.root/(self.digest+suffix),alias)
            try:
                with self.subTest(suffix=suffix),self.assertRaises((ValueError,PermissionError)):self.open()
                self.assertTrue(alias.exists())
            finally:alias.unlink()

    @unittest.skipUnless(sys.platform=='win32','Windows native sharing semantics')
    def test_retained_source_is_pinned_against_write_and_removal(self):
        with self.open() as source:
            with self.assertRaises(OSError):os.close(descriptor(source.installer,writable=True))
            with self.assertRaises(OSError):source.installer.unlink()
        self.write(self.digest+'.exe',self.original)


if __name__=='__main__':unittest.main()
