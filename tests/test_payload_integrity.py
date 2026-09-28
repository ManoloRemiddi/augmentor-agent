# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real file inventory, torn payloads and unsafe paths; no publisher-trust claim."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))
from lifecycle.payload_integrity import INVENTORY,seal_payload,inspect_payload,verify_payload,validate_inventory
from lifecycle.payload_integrity import _digest


class PayloadIntegrityTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)/'payload café';self.root.mkdir()
        (self.root/'scripts').mkdir();(self.root/'empty').mkdir()
        (self.root/'scripts/action.py').write_bytes(b'alpha')
        (self.root/'runtime.dll').write_bytes(b'native fixture')
        (self.root/'release.json').write_text('{"version":"1.2.3"}',encoding='utf-8')
        seal_payload(self.root)
        self.release=(self.root/'release.json').read_bytes()
        self.inventory=(self.root/INVENTORY).read_bytes()

    def inspect(self):return inspect_payload(self.root,self.release,self.inventory)

    def signed_fixture(self,inventory):
        # Digest rebinding only, deliberately no cryptographic trust claim.
        raw=json.dumps(inventory).encode()
        release=json.loads(self.release);release['payloadSHA256']=hashlib.sha256(raw).hexdigest()
        return json.dumps(release).encode(),raw

    def test_sealed_tree_verifies_every_file_and_cannot_be_resealed(self):
        result=verify_payload(self.root,self.release)
        self.assertTrue(result['complete']);self.assertEqual(result['files'],4)
        self.assertEqual(result['bytes'],sum(p.stat().st_size for p in self.root.rglob('*') if p.is_file()))
        with self.assertRaisesRegex(ValueError,'reseal'):seal_payload(self.root)

    def test_same_size_modification_missing_files_and_obsolete_entries_are_distinct(self):
        (self.root/'scripts/action.py').write_bytes(b'bravo')
        (self.root/'runtime.dll').unlink()
        (self.root/'obsolete').mkdir();(self.root/'obsolete/old.dll').write_bytes(b'old version')
        (self.root/'empty').rmdir()
        result=self.inspect()
        self.assertFalse(result['complete'])
        self.assertEqual(result['changed'],['scripts/action.py'])
        self.assertEqual(result['missing'],['runtime.dll'])
        self.assertEqual(result['unexpected'],['obsolete/old.dll'])
        self.assertEqual(result['missingDirectories'],['empty'])
        self.assertEqual(result['unexpectedDirectories'],['obsolete'])
        self.assertTrue((self.root/'obsolete/old.dll').exists(),'Inspection must never remove files.')
        with self.assertRaisesRegex(ValueError,'incomplete'):verify_payload(self.root,self.release)

    def test_independent_metadata_can_inspect_a_torn_installed_metadata_pair(self):
        (self.root/'release.json').unlink();(self.root/INVENTORY).write_bytes(b'interrupted')
        result=self.inspect()
        self.assertEqual(result['missing'],['release.json'])
        self.assertEqual(result['changed'],[INVENTORY]);self.assertFalse(result['complete'])
        self.assertEqual((self.root/INVENTORY).read_bytes(),b'interrupted')

    def test_manifest_cannot_redefine_an_independently_identified_release(self):
        manifest=json.loads(self.inventory);manifest['files']['runtime.dll']['sha256']='0'*64
        raw=json.dumps(manifest).encode()
        with self.assertRaisesRegex(ValueError,'independently identified'):
            inspect_payload(self.root,self.release,raw)
        (self.root/'release.json').write_bytes(b'{}')
        self.assertEqual(self.inspect()['changed'],['release.json'])

    def test_even_rebound_inventory_rejects_unsafe_paths_collisions_and_invalid_sizes(self):
        for path in ('../outside','C:/outside','scripts/../../outside','scripts\\other.py',
                     'scripts/CON.txt','scripts/trailing.','scripts/stream:payload','/absolute',
                     'runtime.DLL','scripts//empty.py'):
            with self.subTest(path=path):
                manifest=json.loads(self.inventory)
                manifest['files'][path]={'bytes':0,'sha256':'0'*64}
                with self.assertRaises(ValueError):validate_inventory(*self.signed_fixture(manifest))
        for change in ('wrong-size','missing-parent','duplicate-directory','file-is-directory','boolean-bytes'):
            manifest=json.loads(self.inventory)
            if change=='wrong-size':manifest['totalBytes']+=1
            elif change=='missing-parent':manifest['directories'].remove('scripts')
            elif change=='duplicate-directory':manifest['directories'].append('EMPTY')
            elif change=='file-is-directory':manifest['directories'].append('runtime.dll')
            else:manifest['files']['runtime.dll']['bytes']=True
            with self.subTest(change=change),self.assertRaises(ValueError):
                validate_inventory(*self.signed_fixture(manifest))

    def test_duplicate_json_and_bounded_inventory_refuse(self):
        raw=b'{"schema":"augmentor-payload/1","schema":"augmentor-payload/1"}'
        release=json.loads(self.release);release['payloadSHA256']=hashlib.sha256(raw).hexdigest()
        with self.assertRaises(ValueError):validate_inventory(json.dumps(release).encode(),raw)
        with patch('lifecycle.payload_integrity.MAX_INVENTORY',8),self.assertRaisesRegex(ValueError,'size'):
            validate_inventory(self.release,self.inventory)
        with patch('lifecycle.payload_integrity.MAX_ENTRIES',3),self.assertRaises(ValueError):self.inspect()

    def test_file_and_parent_aliases_refuse_without_reading_foreign_payload(self):
        foreign=self.root.parent/'foreign';foreign.mkdir();(foreign/'secret').write_bytes(b'preserve')
        link=self.root/'redirect'
        try:link.symlink_to(foreign,target_is_directory=True)
        except OSError as error:self.skipTest('Symlink fixture unavailable: '+str(error))
        try:
            with self.assertRaisesRegex(ValueError,'reparse/link'):self.inspect()
            with self.assertRaisesRegex(ValueError,'reparse/link'):
                inspect_payload(link,self.release,self.inventory)
        finally:link.unlink()
        self.assertEqual((foreign/'secret').read_bytes(),b'preserve')

    def test_hard_link_refuses(self):
        os.link(self.root/'runtime.dll',self.root/'alias.dll')
        with self.assertRaisesRegex(ValueError,'reparse/link'):self.inspect()

    def test_replaced_file_between_scan_and_open_refuses(self):
        path=self.root/'runtime.dll';before=path.stat()
        replacement=self.root/'replacement.dll';replacement.write_bytes(path.read_bytes())
        os.replace(replacement,path)
        with self.assertRaisesRegex(ValueError,'changed during inspection'):_digest(path,before)

    def test_file_changed_during_hash_refuses(self):
        path=self.root/'runtime.dll';before=path.stat();read_digest=hashlib.file_digest
        def change_after_hash(source,algorithm):
            result=read_digest(source,algorithm)
            os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns+10_000_000_000))
            return result
        with patch('lifecycle.payload_integrity.hashlib.file_digest',change_after_hash):
            with self.assertRaisesRegex(ValueError,'changed during inspection'):_digest(path,before)

    @unittest.skipUnless(sys.platform=='win32','Native Windows creation/change times.')
    def test_distinct_windows_creation_and_change_times_verify(self):
        import pywintypes
        import win32con
        import win32file
        path=self.root/'runtime.dll'
        handle=win32file.CreateFile(str(path),win32con.FILE_WRITE_ATTRIBUTES,
            win32con.FILE_SHARE_READ|win32con.FILE_SHARE_WRITE,None,win32con.OPEN_EXISTING,0,None)
        try:win32file.SetFileTime(handle,pywintypes.Time(946684800),None,None)
        finally:handle.Close()
        # A release hash describes bytes, not their creation/change timestamps.
        self.assertTrue(self.inspect()['complete'])

    @unittest.skipUnless(sys.platform=='win32','Native Windows junction check.')
    def test_windows_junction_refuses(self):
        import _winapi
        target=self.root.parent/'junction-target';target.mkdir()
        link=self.root/'redirect'
        _winapi.CreateJunction(str(target),str(link))
        try:
            with self.assertRaisesRegex(ValueError,'reparse/link'):self.inspect()
        finally:os.rmdir(link)


if __name__=='__main__':unittest.main()
