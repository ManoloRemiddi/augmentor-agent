# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual ZIP/held-byte/local-selection staging with inert interpreter fixtures."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
import zipfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from updates.linux_staging import stage_download,copy_archive,extract,NAME
from updates.linux_managed import load_deployment
from updates.packaging import build_receipt
from platform_adapters.private_files import descriptor,atomic_json,read_json


@unittest.skipUnless(sys.platform=='linux','Actual Linux links, archive modes and immutable local staging.')
class LinuxStagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='augmentor-linux-bundle-')
        self.addCleanup(self.temporary.cleanup);self.base=Path(self.temporary.name)
        self.data=self.base/'data';self.stage=self.base/'stage'
        self.data.mkdir(mode=0o700);self.stage.mkdir(mode=0o700)
        self.tool=load_deployment(self.data);self.tool.check=Mock()
        self.mock_loader=patch('updates.linux_staging.load_deployment',return_value=self.tool)
        self.mock_loader.start();self.addCleanup(self.mock_loader.stop)
        self.previous={'root':str(self.base/'original'),'python':'/inert/original/python','node':'/inert/original/node',
            'dshService':'fixture-owned.service','dshEndpoint':'http://127.0.0.1:1','dshHome':str(self.base/'fixture-profile')}
        atomic_json(self.data/'desktop.json',self.previous)
        product=json.loads((ROOT/'release/product.json').read_text())
        self.candidate={'version':product['version'],'build':1,'sourceCommit':'a'*40,'target':'linux-x64',
            'channel':'stable','installType':'managed-linux','component':'desktop','protocols':product['protocols'],
            'dataSchema':product['dataSchema'],'readableDataSchemas':product['readableDataSchemas'],
            'minimumOS':'6.12','distributions':{'debian':'13'},
            'releaseUrl':'https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/test-bundle','artifacts':[]}
        receipt={**product,**{key:self.candidate[key] for key in ('version','sourceCommit','target','channel','component')},
            'update':build_receipt(version=product['version'],source_commit='a'*40,target='linux-x64',channel='stable',build=1)}
        self.rows=[('release.json',json.dumps(receipt).encode(),stat.S_IFREG|0o644),
            ('release/product.json',json.dumps(product).encode(),stat.S_IFREG|0o644),
            ('apps/native/augmentor_linux/window.py',b'--ensure-running',stat.S_IFREG|0o644),
            ('python/bin/python3',b'Inert Python fixture; never execute.',stat.S_IFREG|0o755),
            ('node/bin/node',b'Inert Node fixture; never execute.',stat.S_IFREG|0o755),
            ('scripts/linux-local-health.py',b'Inert health fixture.',stat.S_IFREG|0o644),
            ('scripts/desktop-deployment.py',b'Publisher code never owns local selection.',stat.S_IFREG|0o644)]

    def held(self,rows=None):
        path=self.base/'download.zip'
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            for name,raw,mode in self.rows if rows is None else rows:
                item=zipfile.ZipInfo(NAME+'/'+name);item.create_system=3;item.external_attr=mode<<16
                archive.writestr(item,raw)
        path.chmod(0o600)
        fd=descriptor(path);self.addCleanup(os.close,fd)
        item={'role':'bundle','targetPath':'releases/download/test-bundle/managed-linux.zip',
            'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        self.candidate['artifacts']=[item]
        return {'artifact':item,'path':path,'fd':fd}

    def test_local_configuration_and_bundled_interpreters_follow_final_release(self):
        held=self.held(self.rows+[('services/data',b'Immutable module.',stat.S_IFREG|0o644),
            ('services/link',b'data',stat.S_IFLNK|0o777)])
        target,raw,payload=stage_download(held,self.stage,self.candidate,self.data,development=True)
        manifest=self.tool.verify(target);config=manifest['deployment']
        self.assertEqual(read_json(self.data/'desktop.json'),self.previous)
        self.assertEqual(config['dshService'],self.previous['dshService'])
        self.assertEqual(config['dshEndpoint'],self.previous['dshEndpoint'])
        self.assertEqual(config['dshHome'],self.previous['dshHome'])
        self.assertEqual(config['python'],str(target/'python/bin/python3'))
        self.assertEqual(config['node'],str(target/'node/bin/node'))
        self.assertEqual((target/'services/link').read_bytes(),b'Immutable module.')
        self.assertEqual(stat.S_IMODE((target/'python/bin/python3').stat().st_mode),0o755)
        self.assertEqual(json.loads(raw)['sourceCommit'],self.candidate['sourceCommit'])
        self.assertEqual(payload['entries']['services/link']['symlink'],'data')
        self.assertEqual(os.lseek(held['fd'],0,os.SEEK_CUR),0)
        self.assertFalse((self.data/'desktop.previous.json').exists())

    def test_changed_exact_download_is_refused_before_extraction(self):
        held=self.held()
        with held['path'].open('r+b') as stream:stream.write(b'Damaged publisher bytes.')
        with self.assertRaisesRegex(ValueError,'original signed bytes'):
            stage_download(held,self.stage,self.candidate,self.data,development=True)
        self.assertFalse((self.stage/NAME).exists());self.tool.check.assert_not_called()

    def test_unsafe_paths_and_links_never_reach_imports(self):
        additions=[('../outside',b'Outside.',stat.S_IFREG|0o644),
            ('services/outside',b'/outside',stat.S_IFLNK|0o777),
            ('services/outside',b'../../outside',stat.S_IFLNK|0o777),
            ('services/alias',b'data',stat.S_IFLNK|0o777)]
        for index,row in enumerate(additions):
            stage=self.base/('stage-'+str(index));stage.mkdir(mode=0o700)
            rows=self.rows+[row]
            if index==3:rows.append(('services/alias/file',b'Writes through link.',stat.S_IFREG|0o644))
            held=self.held(rows)
            with self.subTest(row=row),self.assertRaises(ValueError):stage_download(held,stage,self.candidate,self.data,development=True)
            self.assertFalse((stage/NAME).exists())
        self.tool.check.assert_not_called()

    def test_mac_resource_sidecars_are_not_part_of_a_linux_bundle(self):
        held=self.held()
        with zipfile.ZipFile(held['path'],'a') as archive:
            item=zipfile.ZipInfo('__MACOSX/'+NAME+'/._release.json');item.create_system=3
            item.external_attr=(stat.S_IFREG|0o644)<<16
            archive.writestr(item,b'Foreign platform sidecar.')
        held['artifact']['bytes']=held['path'].stat().st_size
        held['artifact']['sha256']=hashlib.sha256(held['path'].read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'sidecar'):
            stage_download(held,self.stage,self.candidate,self.data,development=True)
        self.assertFalse((self.stage/NAME).exists());self.tool.check.assert_not_called()

    def test_publisher_cannot_ship_a_local_selection(self):
        held=self.held(self.rows+[('desktop.json',b'{"root":"/other-user"}',stat.S_IFREG|0o644)])
        with self.assertRaisesRegex(ValueError,'local deployment selection'):
            stage_download(held,self.stage,self.candidate,self.data,development=True)
        self.assertEqual(read_json(self.data/'desktop.json'),self.previous);self.tool.check.assert_not_called()

    def test_wrong_build_and_public_unqualified_receipt_refuse_before_import(self):
        held=self.held();self.candidate['build']=2
        with self.assertRaisesRegex(ValueError,'publisher-verified candidate'):
            stage_download(held,self.stage,self.candidate,self.data,development=True)
        self.tool.check.assert_not_called()
        other=self.base/'public-stage';other.mkdir(mode=0o700);self.candidate['build']=1
        with self.assertRaisesRegex(ValueError,'not qualified'):
            stage_download(held,other,self.candidate,self.data)
        self.tool.check.assert_not_called()

    def test_import_failure_preserves_original_selection_and_discards_only_local_staging(self):
        held=self.held();self.tool.check.side_effect=RuntimeError('Synthetic candidate import failure.')
        with self.assertRaisesRegex(RuntimeError,'import failure'):
            stage_download(held,self.stage,self.candidate,self.data,development=True)
        self.assertEqual(read_json(self.data/'desktop.json'),self.previous)
        self.assertFalse((self.data/'desktop.previous.json').exists())
        self.assertEqual(list((self.data/'releases').iterdir()),[])
        self.assertTrue((self.stage/NAME/'release.json').exists())

    def test_room_for_extraction_does_not_imply_room_for_immutable_duplication(self):
        held=self.held()
        with patch('updates.linux_staging.shutil.disk_usage',side_effect=[
                SimpleNamespace(free=100*1024**2),SimpleNamespace(free=0)]):
            with self.assertRaisesRegex(OSError,'immutable managed release'):
                stage_download(held,self.stage,self.candidate,self.data,development=True)
        self.assertEqual(read_json(self.data/'desktop.json'),self.previous)
        self.tool.check.assert_not_called()
