# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Independent source matching is read-only and never grants replay authority."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))
from lifecycle.recovery_source import assess_source, assess_target


def raw(value):return json.dumps(value).encode('utf-8')


class RecoverySourceTests(unittest.TestCase):
    def setUp(self):
        self.source={'version':'1.2.3','sourceCommit':'a'*40,'target':'windows-arm64',
            'channel':'preview','sha256':'b'*64,'dataSchema':1,'readableDataSchemas':[1]}
        self.release={k:v for k,v in self.source.items() if k!='sha256'}
        self.release['payloadSHA256']='c'*64
        self.record={'schema':'augmentor-update/1','id':'d'*48,'source':deepcopy(self.source),
            'target':{**self.source,'version':'1.2.4','sourceCommit':'e'*40,'sha256':'f'*64},
            'phase':'apply-intent','revision':5,'updatedAt':'2026-09-28T10:00:00+00:00','steps':[]}

    def assess(self):return assess_source(raw(self.record),raw(self.release),self.source['sha256'])

    def test_exact_source_binds_record_and_artifact_without_authorizing_replay(self):
        before=deepcopy(self.record);result=self.assess()
        self.assertEqual(result['recordSHA256'],hashlib.sha256(raw(self.record)).hexdigest())
        self.assertEqual(result['releaseSHA256'],hashlib.sha256(raw(self.release)).hexdigest())
        self.assertEqual(result['installerSHA256'],self.source['sha256'])
        self.assertTrue(result['recordedSourceMatches']);self.assertFalse(result['applyAuthorized'])
        self.assertEqual(result['requiredObservation'],'inspect-installation')
        self.assertEqual(self.record,before)

    def test_same_version_another_build_or_installer_cannot_become_source(self):
        for key,value in (('version','1.2.4'),('sourceCommit','e'*40),('target','windows-x64'),
                          ('channel','stable'),('dataSchema',2),('readableDataSchemas',[1,2])):
            release={**self.release,key:value}
            with self.subTest(key=key),self.assertRaises(ValueError):
                assess_source(raw(self.record),raw(release),self.source['sha256'])
        with self.assertRaisesRegex(ValueError,'exact recorded'):
            assess_source(raw(self.record),raw(self.release),'f'*64)

    def test_incompatible_data_pair_is_not_recoverable_from_this_assessment(self):
        self.record['target'].update(dataSchema=2,readableDataSchemas=[1,2])
        with self.assertRaisesRegex(ValueError,'migration'):self.assess()

    def test_recorded_shutdown_pid_is_only_history(self):
        self.record['phase']='draining'
        self.record['steps']=[{'participant':0,'pid':123456,'kind':'WindowParticipant','phase':'commit-intent'},
            {'participant':0,'pid':123456,'kind':'WindowParticipant','phase':'commit-unknown'}]
        result=self.assess()
        self.assertFalse(result['applyAuthorized'])
        self.assertEqual(result['requiredObservation'],'inspect-stopped-components')
        self.assertNotIn('pid',result);self.assertNotIn('steps',result)

    def test_completed_cancelled_and_prepared_records_never_authorize_apply(self):
        for phase,observation in (('complete','complete'),('cancelled','inspect-cancelled-preparation'),
                                  ('prepared','release-reservations'),('healthy','verify-local-health')):
            with self.subTest(phase=phase):
                self.record['phase']=phase;result=self.assess()
                self.assertEqual(result['requiredObservation'],observation)
                self.assertFalse(result['applyAuthorized'])

    def test_malformed_oversized_duplicate_or_unsupported_record_refuses(self):
        for record in (b'broken',b' '*65537,b'{"schema":1,"schema":2}',raw([]),
                       raw({**self.record,'phase':'force-rollback'})):
            with self.subTest(record=record[:80]),self.assertRaises(ValueError):
                assess_source(record,raw(self.release),self.source['sha256'])

    def test_target_assessment_identifies_new_release_without_replaying_or_completing(self):
        release={key:value for key,value in self.record['target'].items() if key!='sha256'}
        before=raw(self.record)
        result=assess_target(before,raw(release),self.record['target']['sha256'])
        self.assertTrue(result['recordedTargetMatches']);self.assertFalse(result['applyAuthorized'])
        self.assertEqual(result['recordSHA256'],hashlib.sha256(before).hexdigest())
        self.assertEqual(result['installerSHA256'],'f'*64)
        self.assertEqual(raw(self.record),before)
        # Even healthy prior-version metadata cannot become the new target.
        with self.assertRaisesRegex(ValueError,'exact recorded update target'):
            assess_target(before,raw(self.release),self.source['sha256'])
        for key,value in [('version','1.2.5'),('sourceCommit','1'*40),('target','windows-x64')]:
            with self.subTest(field=key),self.assertRaises(ValueError):
                assess_target(before,raw({**release,key:value}),self.record['target']['sha256'])

    def test_target_health_refuses_a_record_that_never_authorized_apply(self):
        release={key:value for key,value in self.record['target'].items() if key!='sha256'}
        for phase in ('verified','preparing','prepared','drained','installer-ready','cancelled'):
            with self.subTest(phase=phase),self.assertRaisesRegex(ValueError,'authorized installation'):
                assess_target(raw({**self.record,'phase':phase}),raw(release),self.record['target']['sha256'])


if __name__=='__main__':unittest.main()
