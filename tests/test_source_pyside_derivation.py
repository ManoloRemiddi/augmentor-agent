# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Artifact tamper and identity checks for separately derived source wheels."""
import base64
import csv
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
import zipfile

spec=importlib.util.spec_from_file_location('source_derivation',Path(__file__).resolve().parents[1]/'release/derive-source-pyside-wheel.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def wheel(path,*,tamper=False,unsafe=False,signed=False):
    members={'PySide6/QtExampleIcons.abi3.so':b'\x7fELFexample',
        'PySide6/QtExampleIcons.pyi':b'example stub','PySide6/QtCore.abi3.so':b'\x7fELFcore',
        'PySide6-6.8.2.1.dist-info/WHEEL':b'Tag: cp37-abi3-manylinux_2_39_x86_64\n',
        'PySide6-6.8.2.1.dist-info/METADATA':b'Name: PySide6\nVersion: 6.8.2.1\n'}
    if unsafe:members['../escape']=b'unsafe'
    if signed:members['PySide6-6.8.2.1.dist-info/RECORD.jws']=b'signature'
    record='PySide6-6.8.2.1.dist-info/RECORD';output=io.StringIO();writer=csv.writer(output)
    for name,data in members.items():writer.writerow((name,'sha256='+base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode(),len(data)))
    writer.writerow((record,'',''));members[record]=output.getvalue().encode()
    if tamper:members['PySide6/QtCore.abi3.so']=b'modified after record'
    with zipfile.ZipFile(path,'w') as archive:
        for name,data in members.items():archive.writestr(name,data)
    return module.digest(path.read_bytes())


class DerivationTests(unittest.TestCase):
    def test_separate_wheel_preserves_producer_and_all_other_bytes_and_tags(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'source.whl';expected=wheel(source);raw=source.read_bytes()
            report=module.derive(source,root/'derived.whl',expected)
            self.assertEqual(source.read_bytes(),raw);self.assertTrue(report['producerUnchanged'])
            before,record,_=module.read_verified(source,expected)
            after,_,_=module.read_verified(root/'derived.whl',report['derivedSha256'])
            for name,(_,data) in before.items():
                if name not in module.REMOVED and name!=record:self.assertEqual(after[name][1],data)
            self.assertFalse(module.REMOVED&after.keys());self.assertFalse(report['licenseReviewComplete'])
            self.assertNotEqual(report['derivedSha256'],expected)

    def test_hash_and_record_tampering_refuse_without_output(self):
        for tamper in (False,True):
            with self.subTest(tamper=tamper),tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);source=root/'source.whl';expected=wheel(source,tamper=tamper)
                if not tamper:expected='0'*64
                with self.assertRaises(RuntimeError):module.derive(source,root/'derived.whl',expected)
                self.assertFalse((root/'derived.whl').exists())

    def test_unsafe_or_signed_wheel_refuses_without_output(self):
        for kwargs in ({'unsafe':True},{'signed':True}):
            with self.subTest(kwargs=kwargs),tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);source=root/'source.whl';expected=wheel(source,**kwargs)
                with self.assertRaises(RuntimeError):module.derive(source,root/'derived.whl',expected)
                self.assertFalse((root/'derived.whl').exists())

    def test_existing_output_and_input_overwrite_refuse(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'source.whl';expected=wheel(source);output=root/'derived.whl';output.write_bytes(b'keep')
            for destination in (source,output):
                with self.assertRaises(RuntimeError):module.derive(source,destination,expected)
            self.assertEqual(output.read_bytes(),b'keep');self.assertEqual(module.digest(source.read_bytes()),expected)

    def test_repeat_derivation_has_identical_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'source.whl';expected=wheel(source)
            module.derive(source,root/'one.whl',expected);module.derive(source,root/'two.whl',expected)
            self.assertEqual((root/'one.whl').read_bytes(),(root/'two.whl').read_bytes())


if __name__=='__main__':unittest.main()
