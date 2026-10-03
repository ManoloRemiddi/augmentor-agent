# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Portable binding/failure proofs, distinct from actual observed Windows health."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from lifecycle.payload_integrity import seal_payload
from lifecycle.recovery_source import assess_target
from lifecycle.update_journal import UpdateJournal,artifact
from platform_adapters.paths import private_directory
from updates.windows_completion import validate_target_report


class TargetCompletionTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name).resolve();root=private_directory(self.base/'payload')
        release={'version':'2.0.0','sourceCommit':'a'*40,'target':'windows-x64','channel':'preview',
                 'dataSchema':1,'readableDataSchemas':[1]}
        (root/'release.json').write_text(json.dumps(release));(root/'inert.bin').write_bytes(b'Public inert completion fixture.')
        seal_payload(root)
        self.release=(root/'release.json').read_bytes();self.inventory=(root/'payload-integrity.json').read_bytes()
        self.candidate={**release,'build':2,'installType':'windows-inno','minimumOS':'26200',
            'releaseUrl':'https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v2.0.0',
            'protocols':{'app':'augmentor-app/1'},'artifacts':[{'role':'installer',
                'targetPath':'releases/download/v2.0.0/installer.exe','bytes':100,'sha256':'b'*64}]}
        target=artifact(release|{'sha256':'b'*64});source={**target,'version':'1.0.0','sourceCommit':'c'*40,'sha256':'d'*64}
        directory=private_directory(self.base/'updates')
        with UpdateJournal(directory,source,target) as journal:
            for phase in ('preparing','prepared','drained','installer-ready','apply-intent','apply-acknowledged'):journal.advance(phase)
        self.record=(directory/'active.json').read_bytes();inventory=json.loads(self.inventory)
        health={'schema':'augmentor-local-health/1','releaseSHA256':hashlib.sha256(self.release).hexdigest(),
            'version':'2.0.0','sourceCommit':'a'*40,'target':'windows-x64','qtPlatform':'windows',
            'rendered':True,'width':424,'height':484,'fontCoverage':True}
        self.report={'schema':'augmentor-payload-inspection/1','releaseSHA256':health['releaseSHA256'],
            'inventorySHA256':hashlib.sha256(self.inventory).hexdigest(),'complete':True,
            'files':len(inventory['files'])+2,'bytes':inventory['totalBytes']+len(self.release)+len(self.inventory),
            'differences':{key:0 for key in ('missing','changed','unexpected','missingDirectories','unexpectedDirectories')},
            'updateTarget':assess_target(self.record,self.release,'b'*64),'localHealth':health}

    def validate(self,report=None,record=None):
        return validate_target_report(json.dumps(report or self.report).encode(),record or self.record,
            self.release,self.inventory,self.candidate)

    def test_exact_record_payload_and_local_health_bind_without_completing_state(self):
        self.assertEqual(self.validate(),self.report)
        self.assertEqual((self.base/'updates/active.json').read_bytes(),self.record)

    def test_swapped_inventory_or_record_refuses_even_with_healthy_ui(self):
        for key in ('inventorySHA256','releaseSHA256'):
            with self.subTest(key=key):
                report=deepcopy(self.report);report[key]='e'*64
                with self.assertRaises(ValueError):self.validate(report)
        record=json.loads(self.record);record['id']='f'*48
        with self.assertRaises(ValueError):self.validate(record=json.dumps(record).encode())

    def test_incomplete_or_miscounted_payload_never_uses_health_as_a_substitute(self):
        for key,value in (('complete',False),('files',True),('files',self.report['files']+1),('bytes',self.report['bytes']+1)):
            with self.subTest(key=key,value=value):
                report=deepcopy(self.report);report[key]=value
                with self.assertRaises(ValueError):self.validate(report)
        report=deepcopy(self.report);report['differences']['changed']=1
        with self.assertRaises(ValueError):self.validate(report)

    def test_wrong_build_health_or_before_apply_record_refuses_without_archival(self):
        report=deepcopy(self.report);report['localHealth']['sourceCommit']='0'*40
        with self.assertRaises(ValueError):self.validate(report)
        record=json.loads(self.record);record['phase']='installer-ready'
        with self.assertRaises(ValueError):self.validate(record=json.dumps(record).encode())
        self.assertEqual((self.base/'updates/active.json').read_bytes(),self.record)


if __name__=='__main__':unittest.main()
