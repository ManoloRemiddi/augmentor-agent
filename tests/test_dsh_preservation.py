# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Synthetic private profiles; exercise provenance, precise edits and stale refusal."""
import hashlib
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services'))
from dsh import preserve as migration


def sha(data):return hashlib.sha256(data).hexdigest()


@unittest.skipUnless(sys.platform=='linux','MX preservation stage')
class PreservationFixture(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='authored-dsh-preserve-',dir=os.environ.get('AUGMENTOR_BUILD_WORKSPACE'))
        self.addCleanup(temporary.cleanup);self.base=Path(temporary.name)
        self.home=self.base/'home';self.old=self.base/'old café';self.incoming=self.base/'incoming';self.output=self.base/'review'
        self.profile=self.home/'profiles/web';self.target=self.profile/'augmentor-product';self.compat=self.base/'compat/browser'
        self.cli=self.base/'cli';self.write(self.cli/'package.json',{'name':'@deepseek-ai/dsh','version':'0.2.0-rc.2'})
        for name,version in {'dsh-base':'0.2.0-rc.2','dsh-tools':'0.2.0-rc.2','dsh-agent-preset':'0.2.0-rc.2','dsh-agent-preset-registry':'0.2.0-rc.2','cordis':'4.0.4','schemastery':'3.18.4'}.items():
            self.write(self.cli/'node_modules/@deepseek-ai'/name/'package.json',{'name':'@deepseek-ai/'+name,'version':version})
        self.old_package={'name':'authored-plugin','version':'0.2.11','peerDependencies':{'@deepseek-ai/dsh-tools':'0.1.5-rc.1'},'license':'AUTHORED'}
        self.peers={'@deepseek-ai/cordis':'4.0.2 || 4.0.4','@deepseek-ai/dsh-tools':'0.1.5-rc.1 || 0.2.0-rc.2'}
        current={**self.old_package,'peerDependencies':self.peers};new={**current,'version':'0.2.13','description':'incoming authored feature'}
        self.write(self.old/'apps/browser/plugin/package.json',self.old_package)
        for directory in [self.target/'browser',self.compat]:
            self.write(directory/'package.json',current);self.write(directory/'dist/index.js',b'// AUTHORED OLD CODE\n')
        self.write(self.incoming/'apps/browser/plugin/package.json',new);self.write(self.incoming/'apps/browser/plugin/dist/index.js',b'// AUTHORED NEW CODE\n')
        self.write(self.incoming/'release/product.json',{'version':'0.2.13'})
        for root in [self.old,self.incoming]:
            for name in ['dsh-product','dsh-memory','dsh-desktop']:
                self.write(root/'adapters'/name/'index.mjs',('// AUTHORED '+root.name+' '+name+'\n').encode())
        presets={}
        for role in migration.ROLES:
            presets[role]={}
            for name in ['preset.yml','agent.cordis.yml']:
                raw=('AUTHORED legacy snapshot '+role+' '+name+'\n').encode();self.write(self.home/'.agent-presets'/role/name,raw);presets[role][name]=sha(raw)
        self.owner={'version':'0.2.11','files':{'browser/dist/index.js':sha(b'// AUTHORED OLD CODE\n'),'browser/package.json':sha((self.old/'apps/browser/plugin/package.json').read_bytes())},'presets':presets,'patchEntry':'AUTHORED HISTORICAL INSERTION NO LONGER PRESENT'}
        self.write(self.target/'ownership.json',self.owner)
        rows=[{'id':'augmentor-product','name':str(self.old/'adapters/dsh-product/index.mjs')},{'id':'augmentor-product-browser','name':str(self.compat/'dist/index.js'),'config':{'chatDir':'/authored/private chat','deleteAfterDays':0}}]
        for role in sorted(migration.ROLES):
            rows.append({'id':'authored-'+role,'name':'@deepseek-ai/dsh-agent-preset','config':{'id':role,'plugins':[{'id':'memory','name':(self.old/'adapters/dsh-memory/index.mjs').as_uri()},{'id':'desktop','name':str(self.old/'adapters/dsh-desktop/index.mjs')},{'id':'keep-voice','name':str(self.old/'adapters/voice/index.mjs')},{'id':'authored-private','name':'authored-private-plugin','config':{'privatePrompt':'AUTHORED KEEP'}}]}})
        self.prefix='# AUTHORED Café 😀 — expressions and off stay exact.\n- id: authored-settings\n  name: authored-only\n  config:\n    off: off\n    value: !!js "throw new Error(\'MUST NOT EXECUTE\')"\n'
        self.write(self.profile/'cordis.patch.yml',(self.prefix+'- insert: '+json.dumps(rows,ensure_ascii=False)+'\n- id: augmentor-product-browser\n  config:\n    authoredOverride: KEEP\n').encode())
        self.write(self.home/'settings.yaml',b'off: off\nprovider: AUTHORED PRIVATE KEEP\n')
        self.write(self.home/'augmentor-product-token',b'AUTHORED_TOKEN_KEEP\n')

    def write(self,path,value):
        path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        raw=value if isinstance(value,bytes) else (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
        path.write_bytes(raw);path.chmod(0o600)

    def stage(self):return migration.stage(self.home,self.incoming,self.output,self.cli)
    def inputs(self):return {str(p.relative_to(self.base)):p.read_bytes() for p in self.base.rglob('*') if p.is_file() and not p.is_relative_to(self.output)}

    def legacy_bundle(self,version='0.2.0'):
        supplier=self.base/'legacy-library';self.write(supplier/'package.json',{'name':'dsh-prompt-library','version':version})
        self.write(supplier/'cordis.patch.yml',b'- insert:\n  - id: prompt-library\n    name: dsh-prompt-library\n')
        self.write(supplier/'lib/index.js',b'// AUTHORED legacy backend only.\n');self.write(supplier/'lib/client.js',b'// AUTHORED retained frontend.\n')
        alias=self.profile/'node_modules/dsh-prompt-library';alias.parent.mkdir(parents=True,exist_ok=True);alias.symlink_to(supplier,target_is_directory=True)
        self.write(self.profile/'package.json',{'dsh':{'profile':{'bundles':['authored-other','dsh-prompt-library']}}})
        self.write(self.incoming/'adapters/dsh-prompt-library/lib/index.js',b'// AUTHORED new shared-instructions backend.\n')
        return supplier,alias



class DshPreservationTests(PreservationFixture):
    def test_stage_changes_only_owned_module_scalars_and_preserves_peers(self):
        before=self.inputs();receipt=self.stage();self.assertFalse(receipt['activated']);self.assertEqual(receipt['rewrittenModuleReferences'],6)
        self.assertEqual(self.inputs(),before)
        text=(self.output/'cordis.patch.yml').read_text();self.assertTrue(text.startswith(self.prefix));self.assertTrue(text.endswith('- id: augmentor-product-browser\n  config:\n    authoredOverride: KEEP\n'))
        self.assertIn('AUTHORED KEEP',text);self.assertIn('authored-private-plugin',text);self.assertIn('/adapters/voice/index.mjs',text)
        package=json.loads((self.output/'integration/browser/package.json').read_text());self.assertEqual(package['peerDependencies'],self.peers);self.assertEqual(package['version'],'0.2.13');self.assertEqual(package['description'],'incoming authored feature')
        owner=json.loads((self.output/'integration/ownership.json').read_text());self.assertEqual(owner['schema'],migration.OWNERSHIP);self.assertNotIn('patchEntry',owner)
        plan=json.loads((self.output/'plan.json').read_text());self.assertEqual(plan['retainedOldRootModules'],['adapters/voice/index.mjs']);self.assertTrue(plan['requiresColdBackupAndImmutableIncomingForActivation']);self.assertEqual(len(plan['moduleEdits']),6)
        self.assertTrue(migration.verify(self.output,receipt['planSha256'])['valid'])

    def test_legacy_library_frontend_is_retained_with_one_new_backend_override(self):
        supplier,alias=self.legacy_bundle();before=self.inputs();receipt=self.stage();self.assertEqual(self.inputs(),before)
        text=(self.output/'cordis.patch.yml').read_text();self.assertTrue(text.startswith(self.prefix));self.assertEqual(text.count('\n- id: prompt-library\n'),1)
        plan=json.loads((self.output/'plan.json').read_text());bridge=plan['libraryBackendBridge'];self.assertTrue(bridge['frontendRetained']);self.assertTrue(bridge['appendedOverride']);self.assertEqual(bridge['module'],str(self.incoming/'adapters/dsh-prompt-library/lib/index.js'))
        self.assertEqual(plan['aliasBindings'][str(alias)],str(supplier));self.assertIn(str(supplier/'lib/client.js'),plan['systemSupplierInputs'])
        self.assertTrue(migration.verify(self.output,receipt['planSha256'])['valid'])

    def test_legacy_library_alias_changes_and_unknown_custom_overrides_refuse(self):
        supplier,alias=self.legacy_bundle();receipt=self.stage();alias.unlink();alias.symlink_to(self.incoming,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'alias changed'):migration.verify(self.output,receipt['planSha256'])
        alias.unlink();alias.symlink_to(supplier,target_is_directory=True);self.output=self.base/'next-stage'
        with (self.profile/'cordis.patch.yml').open('a') as stream:stream.write('\n- id: prompt-library\n  name: authored-custom-library\n')
        before=self.inputs()
        with self.assertRaisesRegex(ValueError,'overrides require capability review'):self.stage()
        self.assertEqual(self.inputs(),before);self.assertFalse(self.output.exists())

    def test_unknown_legacy_library_versions_are_not_silently_replaced(self):
        self.legacy_bundle('AUTHORED-UNREVIEWED');before=self.inputs()
        with self.assertRaisesRegex(ValueError,'version needs separate'):self.stage()
        self.assertEqual(self.inputs(),before);self.assertFalse(self.output.exists())

    def test_reviewed_library_bridge_is_updated_without_duplicate_backend_rows(self):
        self.legacy_bundle();self.stage()
        for source,destination in [('cordis.patch.yml',self.profile/'cordis.patch.yml'),('integration/browser/dist/index.js',self.target/'browser/dist/index.js'),('integration/browser/package.json',self.target/'browser/package.json'),('integration/ownership.json',self.target/'ownership.json')]:self.write(destination,(self.output/source).read_bytes())
        self.output=self.base/'next-stage';receipt=self.stage();plan=json.loads((self.output/'plan.json').read_text());self.assertFalse(plan['libraryBackendBridge']['appendedOverride']);self.assertEqual((self.output/'cordis.patch.yml').read_text().count('\n- id: prompt-library\n'),1);self.assertTrue(migration.verify(self.output,receipt['planSha256'])['valid'])

    def test_identical_public_entries_in_other_releases_move_but_private_edits_stay(self):
        alternate=self.base/'other-release';same=alternate/'adapters/dsh-memory/index.mjs';modified=alternate/'adapters/dsh-desktop/index.mjs'
        self.write(same,(self.incoming/'adapters/dsh-memory/index.mjs').read_bytes());self.write(modified,b'// AUTHORED PRIVATE DESKTOP CUSTOMIZATION KEEP\n')
        path=self.profile/'cordis.patch.yml';text=path.read_text().replace((self.old/'adapters/dsh-memory/index.mjs').as_uri(),str(same)).replace(str(self.old/'adapters/dsh-desktop/index.mjs'),str(modified));path.write_text(text)
        receipt=self.stage();plan=json.loads((self.output/'plan.json').read_text());edits=[row for row in plan['moduleEdits'] if row['reason']=='identical-public-entry'];self.assertEqual(len(edits),2)
        candidate=(self.output/'cordis.patch.yml').read_text();self.assertNotIn(str(same),candidate);self.assertIn(str(modified),candidate);self.assertEqual(modified.read_bytes(),b'// AUTHORED PRIVATE DESKTOP CUSTOMIZATION KEEP\n')
        self.assertTrue(migration.verify(self.output,receipt['planSha256'])['valid'])

    def test_cli_stage_and_verify_are_private_and_refusal_does_not_echo_profile(self):
        cli=Path(__file__).resolve().parents[1]/'scripts/stage-dsh-preservation.py'
        result=subprocess.run([sys.executable,'-B',str(cli),'stage','--home',str(self.home),'--incoming',str(self.incoming),'--output',str(self.output),'--cli',str(self.cli)],capture_output=True,text=True,check=True)
        receipt=json.loads(result.stdout);self.assertNotIn('AUTHORED',result.stdout)
        verified=subprocess.run([sys.executable,'-B',str(cli),'verify','--output',str(self.output),'--sha256',receipt['planSha256']],capture_output=True,text=True,check=True)
        self.assertTrue(json.loads(verified.stdout)['valid'])
        invalid=subprocess.run([sys.executable,'-B',str(cli),'verify','--output',str(self.output),'--sha256','bad'],capture_output=True,text=True)
        self.assertEqual(invalid.returncode,1);self.assertNotIn(str(self.home),invalid.stderr);self.assertNotIn('AUTHORED',invalid.stderr)
        self.assertEqual((self.output/'plan.json').stat().st_mode&0o777,0o600)

    def test_stage_rejects_active_untracked_code_and_does_not_allocate_output(self):
        self.write(self.compat/'dist/index.js',b'AUTHORED CUSTOM CODE KEEP');before=self.inputs()
        with self.assertRaisesRegex(ValueError,'compatibility code'):self.stage()
        self.assertEqual(self.inputs(),before);self.assertFalse(self.output.exists())

    def test_nonpeer_metadata_edits_are_preserved_and_refused(self):
        for directory in [self.target/'browser',self.compat]:self.write(directory/'package.json',{**self.old_package,'peerDependencies':self.peers,'license':'AUTHORED PRIVATE EDIT KEEP'})
        before=self.inputs()
        with self.assertRaisesRegex(ValueError,'beyond peer'):self.stage()
        self.assertEqual(self.inputs(),before);self.assertFalse(self.output.exists())

    def test_original_reference_and_legacy_presets_must_match_provenance(self):
        self.write(self.old/'apps/browser/plugin/package.json',{**self.old_package,'version':'forged'})
        with self.assertRaisesRegex(ValueError,'provenance'):self.stage()
        self.write(self.old/'apps/browser/plugin/package.json',self.old_package)
        self.write(self.home/'.agent-presets'/sorted(migration.ROLES)[0]/'agent.cordis.yml',b'AUTHORED EDIT KEEP')
        with self.assertRaisesRegex(ValueError,'Edited preset'):self.stage()
        self.assertFalse(self.output.exists())

    def test_relevant_alias_or_duplicate_identity_is_not_rewritten(self):
        original=(self.profile/'cordis.patch.yml').read_bytes()
        for raw in [b'- id: one\n  id: two\n',b'- &shared {id: one, name: authored}\n- *shared\n']:
            self.write(self.profile/'cordis.patch.yml',raw)
            with self.assertRaises(ValueError):self.stage()
            self.assertEqual((self.profile/'cordis.patch.yml').read_bytes(),raw);self.assertFalse(self.output.exists())
        self.write(self.profile/'cordis.patch.yml',original)

    def test_unknown_peer_ranges_and_mixed_sdk_refuse_without_writes(self):
        for directory in [self.target/'browser',self.compat]:self.write(directory/'package.json',{**self.old_package,'peerDependencies':{**self.peers,'@deepseek-ai/dsh-tools':'^99.0.0'}})
        with self.assertRaisesRegex(ValueError,'Preserved peers'):self.stage()
        self.write(self.cli/'node_modules/@deepseek-ai/schemastery/package.json',{'version':'different'})
        with self.assertRaisesRegex(ValueError,'dependency family'):self.stage()
        self.assertFalse(self.output.exists())

    def test_stale_profile_and_new_optional_configuration_refuse_verification(self):
        receipt=self.stage();self.write(self.home/'.credentials.yaml',b'AUTHORED NEW PRIVATE VALUE')
        with self.assertRaisesRegex(ValueError,'input changed'):migration.verify(self.output,receipt['planSha256'])
        (self.home/'.credentials.yaml').unlink();self.write(self.profile/'cordis.patch.yml',b'AUTHORED CONCURRENT EDIT KEEP')
        with self.assertRaisesRegex(ValueError,'input changed'):migration.verify(self.output,receipt['planSha256'])

    def test_stage_or_review_hash_tampering_refuses(self):
        receipt=self.stage()
        with self.assertRaisesRegex(ValueError,'plan changed'):migration.verify(self.output,'0'*64)
        self.write(self.output/'integration/browser/dist/index.js',b'AUTHORED TAMPER KEEP')
        with self.assertRaisesRegex(ValueError,'asset changed'):migration.verify(self.output,receipt['planSha256'])

    def test_links_hardlinks_overlap_and_existing_output_are_never_swept(self):
        path=self.target/'browser/dist/index.js';os.link(path,self.base/'authored-hardlink')
        with self.assertRaises(ValueError):self.stage()
        (self.base/'authored-hardlink').unlink();self.output.mkdir();self.write(self.output/'KEEP',b'KEEP')
        with self.assertRaisesRegex(ValueError,'absent'):self.stage()
        self.assertEqual((self.output/'KEEP').read_bytes(),b'KEEP')
        with self.assertRaisesRegex(ValueError,'outside'):migration.stage(self.home,self.incoming,self.incoming/'unwanted-stage',self.cli)

    def test_late_supplier_edit_is_caught_and_partial_stage_is_removed(self):
        original=migration.verify
        def altered(output,expected):
            self.write(self.incoming/'apps/browser/plugin/dist/index.js',b'AUTHORED SUPPLIER CHANGED')
            return original(output,expected)
        with patch.object(migration,'verify',side_effect=altered):
            with self.assertRaisesRegex(ValueError,'input changed'):self.stage()
        self.assertFalse(self.output.exists());self.assertTrue((self.profile/'cordis.patch.yml').read_text().startswith(self.prefix))


if __name__=='__main__':unittest.main()
