# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Typed Mac evidence boundaries; actual sealed target probe is native-only."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from lifecycle.macos_health import validate_report


class MacHealthReportTests(unittest.TestCase):
    def setUp(self):
        self.release={'version':'1.0.0','sourceCommit':'a'*40,'target':'macos-arm64'}
        self.raw=json.dumps(self.release).encode()
        self.report={'schema':'augmentor-macos-health/1','releaseSHA256':hashlib.sha256(self.raw).hexdigest(),
            **self.release,'qtPlatform':'offscreen','rendered':True,'width':424,'height':484,'fontCoverage':True}

    def test_exact_offline_report_requires_metadata_identity(self):
        self.assertEqual(validate_report(json.dumps(self.report).encode(),self.raw),self.report)
        for key,value in (('sourceCommit','b'*40),('target','macos-x64'),('version','1.1.0'),('qtPlatform','cocoa'),
                          ('rendered',1),('fontCoverage',False),('width',True),('height',0),('width',32769)):
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                validate_report(json.dumps({**self.report,key:value}).encode(),self.raw)

    def test_unknown_duplicate_oversized_and_changed_metadata_refuse(self):
        for raw in (b'{}',b'null',b'{"schema":1,"schema":2}',b'X'*4097,json.dumps({**self.report,'applyAuthorized':True}).encode()):
            with self.subTest(raw=raw[:30]),self.assertRaises(ValueError):validate_report(raw,self.raw)
        with self.assertRaises(ValueError):validate_report(json.dumps(self.report).encode(),self.raw+b' ')


if __name__=='__main__':unittest.main()
