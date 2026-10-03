# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exact external code staging with inert public fixtures; no process execution."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from lifecycle.payload_integrity import seal_payload
from lifecycle.observer_runtime import REQUIRED, stage_observer_runtime, verify_observer_runtime
from platform_adapters.paths import private_directory


class ObserverRuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name);self.root=private_directory(self.base/'payload')
        self.parent=private_directory(self.base/'observers')
        for name in sorted(REQUIRED|{'scripts/fixed-observer.py','services/public.json','data/inert.fixture'}):
            file=self.root/name;file.parent.mkdir(parents=True,exist_ok=True)
            file.write_bytes(b'Independently authored inert observer fixture.\n')
        (self.root/'python/empty').mkdir()
        (self.root/'release.json').write_text(json.dumps({'version':'1.2.3'}))
        seal_payload(self.root)
        self.release=(self.root/'release.json').read_bytes();self.inventory=(self.root/'payload-integrity.json').read_bytes()

    def stage(self):return stage_observer_runtime(self.root,self.parent,self.release,self.inventory)

    def test_ready_copy_is_exact_private_and_independent_of_later_payload_replacement(self):
        staged=self.stage();self.assertTrue(verify_observer_runtime(staged,self.release,self.inventory))
        self.assertTrue((staged/'python/empty').is_dir())
        self.assertFalse((staged/'data').exists())
        self.assertEqual((staged/'services/public.json').read_bytes(),(self.root/'services/public.json').read_bytes())
        # The staged code survives the actual source directory moving away.
        self.root.rename(self.base/'previous-payload')
        self.assertTrue(verify_observer_runtime(staged,self.release,self.inventory))

    def test_damaged_source_and_wrong_metadata_refuse_before_ready_staging(self):
        name=sorted(REQUIRED)[0];(self.root/name).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'incomplete'):self.stage()
        self.assertEqual(list(self.parent.iterdir()),[])
        with self.assertRaises(ValueError):
            stage_observer_runtime(self.root,self.parent,self.release,self.inventory+b' ')

    def test_failure_retains_unready_copy_and_never_adopts_existing_attempt(self):
        with patch('lifecycle.observer_runtime.atomic_json',side_effect=OSError('inert durable-write failure')):
            with self.assertRaises(OSError):self.stage()
        staged,=self.parent.iterdir()
        self.assertFalse((staged/'observer-runtime.json').exists())
        with self.assertRaises(FileNotFoundError):verify_observer_runtime(staged,self.release,self.inventory)
        with patch('lifecycle.observer_runtime.secrets.token_hex',return_value=staged.name.removeprefix('observer-')):
            with self.assertRaisesRegex(ValueError,'earlier'):self.stage()
        self.assertEqual(list(self.parent.iterdir()),[staged])

    def test_same_size_modified_code_extra_entries_or_changed_receipt_refuse(self):
        staged=self.stage();code=staged/'python/python.exe';before=code.read_bytes()
        with code.open('r+b') as stream:stream.write(b'x'*len(before))
        with self.assertRaisesRegex(ValueError,'differs'):verify_observer_runtime(staged,self.release,self.inventory)
        with code.open('r+b') as stream:stream.write(before)
        extra=staged/'inert-extra';extra.write_bytes(b'fixture')
        with self.assertRaisesRegex(ValueError,'unexpected'):verify_observer_runtime(staged,self.release,self.inventory)
        extra.unlink()
        with (staged/'observer-runtime.json').open('r+b') as stream:
            stream.write(b'{}');stream.truncate()
        with self.assertRaisesRegex(ValueError,'bound'):verify_observer_runtime(staged,self.release,self.inventory)

    def test_staging_inside_replaceable_source_refuses_without_copying(self):
        with self.assertRaisesRegex(ValueError,'outside'):
            stage_observer_runtime(self.root,self.root,self.release,self.inventory)


if __name__=='__main__':unittest.main()
