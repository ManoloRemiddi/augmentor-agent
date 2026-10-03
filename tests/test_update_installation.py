# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Synthetic catalog authority plus actual private bytes, handles and consent."""
from copy import deepcopy
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
from updates.installation import AutomaticInstallAuthority
from updates.packaging import build_receipt
from platform_adapters.paths import private_directory
from platform_adapters.private_files import atomic_json,descriptor,read_json


class InstallationAuthorityTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name);self.root=self.base/'application';(self.root/'release').mkdir(parents=True)
        self.patch=patch('updates.policy.machine_target',return_value='windows-x64');self.patch.start();self.addCleanup(self.patch.stop)
        self.product={'version':'1.0.0','channel':'preview','protocols':{'product':'augmentor/1'},'dataSchema':1,'readableDataSchemas':[1]}
        (self.root/'release/product.json').write_text(json.dumps(self.product))
        stamp=build_receipt(version='1.0.0',source_commit='a'*40,target='windows-x64',channel='preview',build=1)
        stamp['automaticInstallQualified']=True # Qualification fixture only, never a packaged default.
        self.receipt={**self.product,'target':'windows-x64','sourceCommit':'a'*40,'update':stamp}
        self.write_receipt()
        self.updates=private_directory(self.base/'private');cache=private_directory(self.updates/'repository')
        payload=b'MZ inert installer fixture; never executed'
        artifact={'role':'installer','targetPath':'releases/download/v1.1.0-windows-preview.1/app.exe',
                  'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
        self.file=cache/(artifact['sha256']+'.download')
        with os.fdopen(descriptor(self.file,writable=True,create=True),'wb') as stream:stream.write(payload)
        self.release={**self.product,'version':'1.1.0','build':1,'sourceCommit':'b'*40,'target':'windows-x64',
            'installType':'windows-inno','minimumOS':'26200','releaseUrl':'https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v1.1.0-windows-preview.1',
            'artifacts':[artifact]}
        self.state={'schema':'augmentor-update-state/1','authenticated':True,'phase':'ready','candidate':self.release,
            'preferences':{'automaticChecks':True,'automaticDownload':True,'automaticInstall':True,'channel':'preview','intervalHours':24},
            'postponedUntil':0,'skippedRelease':None,'downloads':[{**artifact,'file':str(self.file)}]}
        self.save();self.calls=0

    def save(self):atomic_json(self.updates/'state.json',self.state)
    def write_receipt(self):(self.root/'release.json').write_text(json.dumps(self.receipt))
    def repository(self):
        self.calls+=1
        return {'authenticated':True,'catalog':{'schema':'augmentor-update-catalog/1','releases':[deepcopy(self.release)]}}
    def authority(self,repository=None):
        return AutomaticInstallAuthority(self.root,self.updates,os_version='26200',clock=lambda:1000,repository=repository or self.repository)

    def test_exact_bytes_and_live_consent_revalidate_then_context_cannot_replay(self):
        guard=self.authority()
        with guard:
            self.assertTrue(guard.check('prepared'));self.assertTrue(guard.check('installer-ready'))
            self.assertEqual(len(guard.files),1)
        self.assertEqual(self.calls,3)
        self.assertEqual(guard.files,[])
        with self.assertRaises(ValueError):guard.check('verified')
        with self.assertRaises(ValueError):guard.__enter__()

    def test_unqualified_source_unsigned_selection_incomplete_or_corrupt_download_cannot_enter(self):
        self.receipt['update']['automaticInstallQualified']=False;self.write_receipt()
        with self.assertRaisesRegex(ValueError,'qualify'):self.authority().__enter__()
        self.receipt['update']['automaticInstallQualified']=True;self.write_receipt()
        self.state['authenticated']=False;self.save()
        with self.assertRaisesRegex(ValueError,'publisher-verified'):self.authority().__enter__()
        self.state['authenticated']=True;self.state['downloads']=[];self.save()
        with self.assertRaisesRegex(ValueError,'complete'):self.authority().__enter__()
        self.state['downloads']=[{**self.release['artifacts'][0],'file':str(self.file)}];self.save()
        with os.fdopen(descriptor(self.file,writable=True),'wb') as stream:stream.write(b'corrupt fixture');stream.truncate()
        with self.assertRaisesRegex(ValueError,'damaged'):self.authority().__enter__()
        self.assertEqual(self.file.read_bytes(),b'corrupt fixture')

    def test_withdrawal_changed_artifacts_unsigned_or_missing_fresh_authority_refuse(self):
        for change in ('removed','withdrawn','changed','unsigned','offline'):
            with self.subTest(change=change),self.authority() as guard:
                def refresh():
                    if change=='offline':raise TimeoutError('synthetic offline')
                    result=self.repository()
                    if change=='unsigned':result['authenticated']=False
                    elif change=='removed':result['catalog']['releases']=[]
                    elif change=='withdrawn':result['catalog']['releases'][0]['revoked']=True
                    else:result['catalog']['releases'][0]['artifacts'][0]['sha256']='c'*64
                    return result
                guard.repository=refresh
                with self.assertRaises((ValueError,TimeoutError)):guard.check('installer-ready')

    def test_consent_change_during_refresh_and_skip_or_postponement_are_observed(self):
        with self.authority() as guard:
            def refresh():
                value=self.repository();self.state['preferences']['automaticInstall']=False;self.save();return value
            guard.repository=refresh
            with self.assertRaisesRegex(ValueError,'revoked'):guard.check('prepared')
        self.state['preferences']['automaticInstall']=True
        for field,value in [('postponedUntil',2000),('skippedRelease','preview:windows-x64:1.1.0:1')]:
            self.state[field]=value;self.save()
            with self.assertRaisesRegex(ValueError,'skipped or postponed'):self.authority().__enter__()
            self.state[field]=0 if field=='postponedUntil' else None

    def test_installed_identity_or_selected_bytes_cannot_change_under_live_authority(self):
        with self.authority() as guard:
            self.receipt['update']['automaticInstallQualified']=False;self.write_receipt()
            with self.assertRaisesRegex(ValueError,'qualify'):guard.check('prepared')
        self.receipt['update']['automaticInstallQualified']=True;self.write_receipt()
        with self.authority() as guard:
            if sys.platform=='win32':
                with self.assertRaises(OSError):os.close(descriptor(self.file,writable=True))
            else:
                with os.fdopen(descriptor(self.file,writable=True),'wb') as stream:stream.write(b'changed')
                with self.assertRaisesRegex(ValueError,'bytes changed'):guard.check('installer-ready')


if __name__=='__main__':unittest.main()
