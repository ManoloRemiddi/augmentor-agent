# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real staged trust inputs and exact release identity, without installing apps."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))
from updates.packaging import build_receipt, stage_repository, source_revision


class UpdatePackagingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.source = self.base/'source'; (self.source/'release').mkdir(parents=True)
        self.destination = self.base/'payload'
        self.config = json.loads((ROOT/'release/updates.json').read_text())
        self.node = str(Path(sys.executable).resolve().parents[1]/'node/node.exe') if sys.platform == 'win32' else shutil.which('node')
        self.write_config()

    def write_config(self):
        (self.source/'release/updates.json').write_text(json.dumps(self.config))

    def test_numbered_build_source_cannot_be_dirty_or_mislabeled(self):
        hooks=self.base/'empty-hooks';hooks.mkdir()
        environment={key:value for key,value in os.environ.items() if not key.startswith('GIT_')}
        commands=[['init'],['config','user.name','Synthetic release fixture'],['config','user.email','fixture@example.invalid'],
                  ['add','.'],['commit','-m','Independently authored fixture']]
        for command in commands:subprocess.run(['git','-c','commit.gpgsign=false','-c','core.hooksPath='+str(hooks),*command],
            cwd=self.source,check=True,capture_output=True,env=environment)
        current=source_revision(self.source,build=2)
        self.assertFalse(current['dirty'])
        with self.assertRaisesRegex(ValueError,'actual checkout'):source_revision(self.source,build=2,declared='a'*40)
        (self.source/'changed').write_text('inert fixture')
        self.assertTrue(source_revision(self.source,build=0)['dirty'])
        with self.assertRaisesRegex(ValueError,'clean reviewed'):source_revision(self.source,build=2)

    def test_build_identity_is_deterministic_and_tracks_build_cpu_channel_and_source(self):
        values = dict(version='1.2.3',source_commit='a'*40,target='macos-arm64',channel='preview',build=2)
        stamp = build_receipt(**values)
        self.assertEqual(build_receipt(**values),stamp)
        self.assertFalse(stamp['automaticInstallQualified'])
        for changes in ({'build':3},{'source_commit':'b'*40},{'target':'macos-x64'},{'channel':'stable'},{'component':'companion'}):
            self.assertNotEqual(build_receipt(**{**values,**changes})['releaseId'],stamp['releaseId'])
        for changes in ({'build':True},{'build':-1},{'build':2**31},{'source_commit':None},{'target':'debian13-amd64'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):build_receipt(**{**values,**changes})
        self.assertEqual(build_receipt(**{**values,'build':0})['build'],0)

    def test_installed_stamp_matches_payload_and_zero_build_cannot_claim_qualification(self):
        from updates.policy import installed_identity
        product={'version':'1.2.3','channel':'preview','protocols':{'product':'augmentor/1'},'dataSchema':1,'readableDataSchemas':[1]}
        (self.source/'release/product.json').write_text(json.dumps(product))
        receipt={**product,'sourceCommit':'a'*40,'target':'macos-arm64'}
        stamp=build_receipt(version='1.2.3',source_commit='a'*40,target='macos-arm64',channel='preview',build=2)
        receipt['update']=stamp
        def write(): (self.source/'release.json').write_text(json.dumps(receipt))
        write();self.assertEqual(installed_identity(self.source,target='macos-arm64')['build'],2)
        receipt['sourceCommit']='b'*40;write()
        with self.assertRaisesRegex(ValueError,'stamp differs'):installed_identity(self.source,target='macos-arm64')
        receipt['sourceCommit']='a'*40
        receipt['update']=build_receipt(version='1.2.3',source_commit='a'*40,target='macos-arm64',channel='preview',build=0)
        receipt['update']['automaticInstallQualified']=True;write()
        with self.assertRaisesRegex(ValueError,'stamp differs'):installed_identity(self.source,target='macos-arm64')

    def test_disabled_config_ships_without_root_and_never_copies_secret_material(self):
        secret=self.source/'release/updates/root-1.pem';secret.parent.mkdir();secret.write_text('inert fixture, never a real key')
        stage_repository(self.source,self.destination,node=self.node)
        self.assertEqual(json.loads((self.destination/'release/updates.json').read_text()),self.config)
        self.assertFalse((self.destination/'release/updates').exists())
        self.assertEqual(secret.read_text(),'inert fixture, never a real key')

    def test_enabled_config_without_a_root_and_noncanonical_delivery_refuse(self):
        self.config['enabled']=True;self.write_config()
        with self.assertRaisesRegex(ValueError,'trust root'):stage_repository(self.source,self.destination,node=self.node)
        self.assertFalse(self.destination.exists())
        for field,value in [('enabled','yes'),('artifactBaseUrl','https://evil.invalid/'),('rootFile','../../secret.pem'),('metadataBaseUrl','https://augmentoragent.com/updates/../metadata/')]:
            config=self.config.copy();self.config[field]=value;self.write_config()
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'Unsupported'):stage_repository(self.source,self.destination,node=self.node)
            self.config=config

    def test_real_public_root_signature_is_verified_before_copying_and_tampering_refuses(self):
        if not self.node or not (ROOT/'node_modules/@tufjs/models').exists():
            self.skipTest('Real pinned TUF-model verification needs the production JavaScript dependencies.')
        # In-memory authorities keep this consumer proof portable to Windows;
        # the production key-custody tool intentionally requires POSIX hosts.
        code="""import {generateKeyPairSync,createHash,sign} from 'node:crypto';
const {Metadata,Root,Key,Signature}=await import(process.argv[1]);
const root=new Root({version:1,expires:new Date(Date.now()+86400000).toISOString(),consistentSnapshot:true});root.roles.root.threshold=2;
const signers=[];
for(const role of ['root','root','root','targets','snapshot','timestamp']){
 const {publicKey,privateKey}=generateKeyPairSync('ed25519');
 const value={keytype:'ed25519',keyval:{public:Buffer.from(publicKey.export({format:'jwk'}).x,'base64url').toString('hex')},scheme:'ed25519'};
 const key=Key.fromJSON(createHash('sha256').update(JSON.stringify(value)).digest('hex'),value);root.addKey(key,role);
 if(role==='root')signers.push({key,privateKey});
}
const metadata=new Metadata(root);
for(const {key,privateKey} of signers.slice(0,2))metadata.sign(bytes=>new Signature({keyID:key.keyID,sig:sign(null,bytes,privateKey).toString('hex')}));
process.stdout.write(JSON.stringify(metadata.toJSON()));"""
        generated=subprocess.run([self.node,'--input-type=module','-e',code,(ROOT/'node_modules/@tufjs/models/dist/index.js').as_uri()],
                                 check=True,capture_output=True,timeout=15)
        root=self.source/'release/updates/root.json';root.parent.mkdir()
        original=generated.stdout;root.write_bytes(original)
        self.config['enabled']=True;self.write_config()
        stage_repository(self.source,self.destination,node=self.node)
        self.assertEqual((self.destination/'release/updates/root.json').read_bytes(),original)
        self.assertFalse((self.destination/'release/updates/root-1.pem').exists())
        marker=self.base/'preload-ran';preload=self.base/'preload.cjs'
        preload.write_text('require("node:fs").writeFileSync('+json.dumps(str(marker))+',"unexpected");')
        from unittest.mock import patch
        with patch.dict(os.environ,{'NODE_OPTIONS':'--require='+str(preload)}):
            stage_repository(self.source,self.base/'without-preload',node=self.node)
        self.assertFalse(marker.exists())
        modified=json.loads(original);modified['signed']['expires']='2099-01-01T00:00:00Z';root.write_text(json.dumps(modified))
        with self.assertRaisesRegex(ValueError,'signature/policy'):stage_repository(self.source,self.base/'refused',node=self.node)
        self.assertFalse((self.base/'refused').exists())


if __name__ == '__main__':unittest.main()
