# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Portable evidence validation; actual UI/owned-process checks are separate."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))
from lifecycle.health_report import validate_health_report


class HealthReportTests(unittest.TestCase):
    def setUp(self):
        self.release={'version':'1.0.0','sourceCommit':'a'*40,'target':'windows-x64'}
        self.raw=json.dumps(self.release).encode()
        self.report={'schema':'augmentor-local-health/1','releaseSHA256':hashlib.sha256(self.raw).hexdigest(),
                     **self.release,'qtPlatform':'windows','rendered':True,'width':424,'height':484,'fontCoverage':True}

    def check(self, report=None, release=None):
        return validate_health_report(json.dumps(self.report if report is None else report).encode(),
                                      self.raw if release is None else release)

    def test_exact_native_report_binds_full_metadata_bytes(self):
        self.assertEqual(self.check(),self.report)
        with self.assertRaises(ValueError):self.check(release=self.raw+b' ')

    def test_other_build_cpu_or_qpa_refuses(self):
        for key,value in (('sourceCommit','b'*40),('version','1.1.0'),('target','windows-arm64'),
                          ('qtPlatform','offscreen'),('releaseSHA256','b'*64)):
            with self.subTest(key=key),self.assertRaises(ValueError):self.check({**self.report,key:value})

    def test_render_font_and_integer_dimension_evidence_are_required(self):
        for key,value in (('rendered',False),('rendered',1),('fontCoverage',False),
                          ('width',True),('width',0),('height',32769),('height','484')):
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.check({**self.report,key:value})

    def test_unknown_missing_or_wrong_protocol_fields_refuse(self):
        for report in ({**self.report,'applyAuthorized':True},
                       {key:value for key,value in self.report.items() if key!='fontCoverage'},
                       {**self.report,'schema':'augmentor-local-health/2'},[]):
            with self.subTest(report=report),self.assertRaises(ValueError):self.check(report)

    def test_bounded_duplicate_and_malformed_json_refuses(self):
        for raw in (b'X'*4097,b'{"schema":1,"schema":2}',b'[]',b'null',b'\xff'):
            with self.subTest(raw=raw[:30]),self.assertRaises(ValueError):validate_health_report(raw,self.raw)
        for raw in (b'X'*65537,b'{"version":1,"version":2}',b'[]'):
            with self.subTest(release=raw[:30]),self.assertRaises(ValueError):self.check(release=raw)


if __name__=='__main__':unittest.main()
