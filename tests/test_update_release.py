# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real Ed25519/ZIP/private storage checks; fixture keys never authorize releases."""
import base64
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))
from lifecycle.release_bundle import SCHEMA, stage_bundle, verify_manifest
from platform_adapters.paths import private_directory
from platform_adapters.private_files import descriptor

# Public RFC 8032 test seed. Never used in an installed trust configuration.
SIGNER = """
const c = require('node:crypto');
const key = c.createPrivateKey({format:'der',type:'pkcs8',key:Buffer.from(
  '302e020100300506032b6570042204209d61b19deffd5a60ba844af492ec2cc4'+
  '4449c5697b326919703bac031cae7f60','hex')});
const chunks=[];process.stdin.on('data',b=>chunks.push(b));process.stdin.on('end',()=>{
 const raw=Buffer.concat(chunks);
 const pub=c.createPublicKey(key).export({format:'jwk'});
 console.log(JSON.stringify({key:Buffer.from(pub.x,'base64url').toString('base64'),
   signature:c.sign(null,Buffer.concat([Buffer.from('augmentor-release-manifest/1\\0'),raw]),key).toString('base64')}));
});
"""


class UpdateReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sys.platform == 'win32':
            cls.node = Path(sys.executable).resolve().parents[1]/'node/node.exe'
        else:
            cls.node = Path(shutil.which('node') or '/unavailable-node').resolve()
        if not cls.node.is_file(): raise RuntimeError('Release verification tests require the native bundled Node runtime.')

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.cache = private_directory(self.root/'private café')
        self.installer = b'MZ deterministic installer byte fixture; never executable'
        self.current = {'version':'1.0.0','sourceCommit':'a'*40,'target':'windows-x64',
            'channel':'preview','sha256':'c'*64,'dataSchema':1,'readableDataSchemas':[1]}
        self.manifest = {'schema':SCHEMA,'release':{**self.current,'version':'1.1.0','sourceCommit':'b'*40,
            'sha256':hashlib.sha256(self.installer).hexdigest()},'installerBytes':len(self.installer),
            'minimumOSBuild':26200,'protocols':{'product':'augmentor/1'},'issuedAt':100000,'expiresAt':100900}

    def signed(self, manifest=None, raw=None):
        if raw is None: raw = json.dumps(self.manifest if manifest is None else manifest).encode('utf-8')
        result = subprocess.run([str(self.node),'-e',SIGNER],input=raw,capture_output=True,check=True,timeout=15)
        signed = json.loads(result.stdout)
        policy = {'public_key':signed['key'],'node':self.node,'current':self.current,
            'protocols':{'product':'augmentor/1'},'os_build':26200,'now':100100}
        return raw, base64.b64decode(signed['signature']), policy

    def bundle(self, *, manifest=None, installer=None, transform=None):
        raw, signature, policy = self.signed(manifest)
        entries = [('manifest.json',raw),('manifest.sig',signature),
                   ('installer.exe',self.installer if installer is None else installer)]
        if transform: entries = transform(entries)
        path = self.root/'download.zip'
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_STORED) as bundle:
            for name, content in entries: bundle.writestr(name,content)
        return path, policy

    def test_verified_release_retains_signed_metadata_and_exact_installer(self):
        path, policy = self.bundle()
        with stage_bundle(path,self.cache,**policy) as release:
            self.assertEqual(release.identity,self.manifest['release'])
            self.assertEqual(release.installer.read_bytes(),self.installer)
            self.assertEqual(json.loads((release.directory/'manifest.json').read_bytes()),self.manifest)
            self.assertEqual(len((release.directory/'manifest.sig').read_bytes()),64)
            if sys.platform == 'win32':
                with self.assertRaises(OSError): os.close(descriptor(release.installer,writable=True))
                with self.assertRaises(OSError): release.installer.unlink()
        self.assertIsNone(release.fd)
        self.assertTrue(release.installer.is_file())

    def test_wrong_key_missing_key_tampered_manifest_or_signature_cannot_stage(self):
        raw, signature, policy = self.signed()
        wrong_key = base64.b64encode(b'X'*32).decode()
        cases = [(raw,signature,{**policy,'public_key':wrong_key}),
                 (raw,signature,{**policy,'public_key':''}),
                 (raw+b' ',signature,policy),
                 (raw,b'X'*64,policy)]
        for content, sig, config in cases:
            with self.subTest(config=config['public_key']), self.assertRaisesRegex(ValueError,'signature|trust root'):
                verify_manifest(content,sig,**config)
        self.assertEqual(list(self.cache.iterdir()),[])

    def test_signed_wrong_architecture_os_channel_and_protocol_refuse(self):
        for field, value in [('target','windows-arm64'),('target','macos-x64'),('channel','stable')]:
            manifest = deepcopy(self.manifest); manifest['release'][field] = value
            raw, signature, policy = self.signed(manifest)
            with self.subTest(field=field,value=value), self.assertRaises(ValueError):
                verify_manifest(raw,signature,**policy)
        manifest=deepcopy(self.manifest);manifest['protocols']['product']='augmentor/2'
        with self.assertRaisesRegex(ValueError,'protocol'):
            raw,sig,policy=self.signed(manifest);verify_manifest(raw,sig,**policy)

    def test_downgrade_same_version_and_source_relabel_refuse(self):
        for version in ('0.9.0','1.0.0','01.1.0','1.1.0-rc.1'):
            manifest=deepcopy(self.manifest);manifest['release']['version']=version
            raw,sig,policy=self.signed(manifest)
            with self.subTest(version=version), self.assertRaises(ValueError): verify_manifest(raw,sig,**policy)
        manifest=deepcopy(self.manifest);manifest['release']['sourceCommit']=self.current['sourceCommit']
        raw,sig,policy=self.signed(manifest)
        with self.assertRaisesRegex(ValueError,'revision'): verify_manifest(raw,sig,**policy)
        manifest=deepcopy(self.manifest);manifest['release']['version']='1.10.0'
        raw,sig,policy=self.signed(manifest);policy['current']={**self.current,'version':'1.9.0'}
        self.assertEqual(verify_manifest(raw,sig,**policy)['release']['version'],'1.10.0')

    def test_expired_future_and_unbounded_delivery_windows_refuse(self):
        for changes in ({'expiresAt':100099},{'issuedAt':100401},{'expiresAt':100000+91*86400}):
            raw,sig,policy=self.signed({**self.manifest,**changes})
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError,'clock'):
                verify_manifest(raw,sig,**policy)

    def test_os_build_and_recovery_data_compatibility_enforced_before_staging(self):
        manifest=deepcopy(self.manifest);manifest['minimumOSBuild']=28000
        raw,sig,policy=self.signed(manifest)
        with self.assertRaisesRegex(ValueError,'newer Windows'): verify_manifest(raw,sig,**policy)
        for schemas in ([2],[1,2]):
            manifest=deepcopy(self.manifest)
            manifest['release'].update(dataSchema=2,readableDataSchemas=schemas)
            path,policy=self.bundle(manifest=manifest)
            with self.assertRaisesRegex(ValueError,'migration'): stage_bundle(path,self.cache,**policy)
            self.assertEqual(list(self.cache.iterdir()),[])

    def test_even_signed_duplicate_and_unknown_metadata_fields_refuse(self):
        raw=json.dumps(self.manifest).encode();raw=b'{"schema":"shadow",'+raw[1:]
        raw,sig,policy=self.signed(raw=raw)
        with self.assertRaisesRegex(ValueError,'metadata'): verify_manifest(raw,sig,**policy)
        raw,sig,policy=self.signed({**self.manifest,'command':'untrusted command'})
        with self.assertRaisesRegex(ValueError,'metadata'): verify_manifest(raw,sig,**policy)

    def test_installer_replacement_and_signed_length_mismatch_leave_no_release(self):
        for content in (b'X'*len(self.installer),self.installer+b'X'):
            path,policy=self.bundle(installer=content)
            with self.assertRaisesRegex(ValueError,'installer|Installer'): stage_bundle(path,self.cache,**policy)
            self.assertEqual(list(self.cache.iterdir()),[])

    def test_extra_duplicate_traversal_and_symlink_members_refuse(self):
        link=zipfile.ZipInfo('installer.exe');link.create_system=3;link.external_attr=(stat.S_IFLNK|0o777)<<16
        variants=[lambda entries:entries+[('extra.exe',b'X')],
                  lambda entries:entries[:2]+[('../outside.exe',self.installer)],
                  lambda entries:[entries[0],entries[0],entries[2]],
                  lambda entries:entries[:2]+[(link,b'outside.exe')]]
        import warnings
        for transform in variants:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',UserWarning)
                path,policy=self.bundle(transform=transform)
            with self.assertRaises(ValueError): stage_bundle(path,self.cache,**policy)
            self.assertEqual(list(self.cache.iterdir()),[])
        self.assertFalse((self.root/'outside.exe').exists())

    def test_unbounded_central_directory_rejected_before_zip_parse(self):
        path,policy=self.bundle()
        data=bytearray(path.read_bytes());struct.pack_into('<I',data,len(data)-10,0x7fffffff);path.write_bytes(data)
        with self.assertRaisesRegex(ValueError,'bounded'): stage_bundle(path,self.cache,**policy)
        self.assertEqual(list(self.cache.iterdir()),[])

    def test_inherited_node_preload_cannot_run_during_verification(self):
        marker=self.root/'preload-ran'
        preload=self.root/'preload.cjs'
        preload.write_text('require("node:fs").writeFileSync('+json.dumps(str(marker))+',"unexpected");')
        raw,sig,policy=self.signed()
        from unittest.mock import patch
        with patch.dict(os.environ,{'NODE_OPTIONS':'--require='+str(preload)}):
            self.assertEqual(verify_manifest(raw,sig,**policy)['schema'],SCHEMA)
        self.assertFalse(marker.exists())


if __name__=='__main__': unittest.main()
