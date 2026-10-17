# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(sys.platform=='linux','MX Linux review IPC and launcher')
class HarnessReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='augmentor review ");$percent%-');self.addCleanup(self.temp.cleanup);self.home=Path(self.temp.name)
        spec=importlib.util.spec_from_file_location('harness_review_test',ROOT/'scripts/harness-review.py');self.tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.tool)
        self.registry=self.home/'registry';self.registry.mkdir(mode=0o700)
        self.release=self.home/'releases'/'authored';self.release.mkdir(parents=True,mode=0o700);(self.release/'node/bin').mkdir(parents=True);(self.release/'node/bin/node').write_bytes(b'AUTHORED-NODE');(self.release/'node/bin/node').chmod(0o700);(self.release/'release').mkdir();(self.release/'release/product.json').write_text('{"version":"authored"}')
        self.selection={'root':str(self.release),'node':str(self.release/'node/bin/node'),'python':sys.executable,'version':'authored','releaseId':'authored','sourceRef':'authored-source'};self.seal()
        for name in ['config','state','shared-state','shared-data','runtime','xdg-config','xdg-data','xdg-state','work']:(self.home/name).mkdir(mode=0o700)
        self.profile=dict(zip(self.tool.PATH_KEYS,[str(self.home/n) for n in ['config','state','state/runtime.sock','shared-state','shared-data','work','runtime','xdg-config','xdg-data','xdg-state']]),port=0,linuxTools=False,llamaCppProviders='authored')
        self.entry={'title':'Authored review','deployment':dict(self.selection),'profile':self.profile}
    def seal(self):
        files={str(p.relative_to(self.release)):self.tool.digest(p.read_bytes()) for p in self.release.rglob('*') if p.is_file() and p.name!='desktop-release.json'}
        self.selection['artifactSha256']=self.tool.digest(json.dumps(files,sort_keys=True).encode());path=self.release/'desktop-release.json';path.write_text(json.dumps({'deployment':self.selection,'files':files,'artifactSha256':self.selection['artifactSha256']}));path.chmod(0o600)
    def test_seal_refuses_changed_bytes_before_executing_any_candidate_code(self):
        selected,_=self.tool.sealed_release(self.release);self.assertEqual(selected,self.selection);(self.release/'node/bin/node').write_bytes(b'CHANGED')
        with self.assertRaisesRegex(ValueError,'changed after staging'):self.tool.sealed_release(self.release)
    def test_external_release_links_are_refused(self):
        (self.release/'outside').symlink_to(self.home/'work')
        with self.assertRaises(ValueError):self.tool.sealed_release(self.release)
    def test_profile_refuses_aliases_unknown_secret_fields_bad_scopes_and_modes(self):
        for change in [{'state':str(self.home/'state')+'/'},{'token':'DO_NOT_LOG'},{'socket':str(self.home/'work/other.sock')},{'port':True},{'sessionId':'../foreign'},{'llamaCppProviders':'bad\nroute'},{'linuxTools':'false'}]:
            with self.subTest(keys=list(change)),self.assertRaises(ValueError):self.tool.profile_record({**self.profile,**change})
        (self.home/'config').chmod(0o755)
        with self.assertRaises(ValueError):self.tool.profile_record(self.profile)
    def test_registry_cas_and_profile_removal_leave_all_review_data_in_place(self):
        original=self.home/'state/original.json';original.write_bytes(b'KEEP-NATIVE-HISTORY')
        first=self.tool.change_registry(self.registry,'main',0,self.entry);self.assertEqual(first['revision'],1)
        with self.assertRaisesRegex(ValueError,'changed'):self.tool.change_registry(self.registry,'pilot',0,self.entry)
        self.assertEqual(self.tool.registry_read(self.registry)['revision'],1);removed=self.tool.change_registry(self.registry,'main',1);self.assertEqual(removed['entries'],{});self.assertEqual(original.read_bytes(),b'KEEP-NATIVE-HISTORY')
    def test_link_validation_never_echoes_a_private_fragment_in_failures(self):
        valid='http://127.0.0.1:12345/#token='+'a'*64
        self.assertEqual(self.tool.private_link({'url':valid},self.profile),valid)
        for url in ['http://127.0.0.1:12345/#PRIVATE-BEARER','https://127.0.0.1:12345/#token=PRIVATE-BEARER','http://example.com:12345/#token=PRIVATE-BEARER',valid+'&session=foreign',valid+'&token='+'b'*64,'http://127.0.0.1:PRIVATE-BEARER/#token='+'a'*64]:
            with self.subTest(url=url.split('#')[0]),self.assertRaises(ValueError) as error:self.tool.private_link({'url':url},self.profile)
            self.assertNotIn('PRIVATE-BEARER',str(error.exception))
    def test_registration_and_manifest_require_private_unlinked_regular_files(self):
        path=self.registry/'reviews.json';path.write_text('{}');path.chmod(0o644)
        with self.assertRaises(ValueError):self.tool.registry_read(self.registry)
        path.chmod(0o600);alias=self.registry/'alias';os.link(path,alias)
        with self.assertRaises(ValueError):self.tool.registry_read(self.registry)
        path.unlink();path.symlink_to(alias)
        with self.assertRaises(OSError):self.tool.registry_read(self.registry)
    def test_runtime_environment_excludes_caller_agent_credentials_and_other_profiles(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':'DO-NOT-FORWARD','AUGMENTOR_PI_STATE':'foreign','PI_CODING_AGENT_DIR':'foreign','PYTHONPATH':'foreign','LD_PRELOAD':'foreign','ANTHROPIC_API_KEY':'DO-NOT-FORWARD'}):env=self.tool.runtime_environment(self.profile,self.selection)
        for key in ['OPENAI_API_KEY','ANTHROPIC_API_KEY','PI_CODING_AGENT_DIR','PYTHONPATH','LD_PRELOAD']:self.assertNotIn(key,env)
        self.assertEqual(env['AUGMENTOR_PI_STATE'],self.profile['state']);self.assertEqual(env['AUGMENTOR_PI_LINUX_TOOLS'],'0');self.assertEqual(env['PI_TELEMETRY'],'0')
    def test_missing_socket_with_live_profile_does_not_attempt_restart(self):
        with patch.object(self.tool,'Owner',side_effect=FileNotFoundError),patch.object(self.tool,'live_profile',return_value=[123]),patch.object(self.tool.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'live process'):self.tool.open_review(self.entry)
            run.assert_not_called()
    def test_an_unconfirmed_start_does_not_issue_a_second_start(self):
        import subprocess
        with patch.object(self.tool,'Owner',side_effect=FileNotFoundError),patch.object(self.tool,'live_profile',return_value=[]),patch.object(self.tool.subprocess,'run',side_effect=subprocess.TimeoutExpired(['PRIVATE-BEARER'],75)) as run:
            with self.assertRaisesRegex(ValueError,'unconfirmed') as error:self.tool.open_review(self.entry)
            self.assertNotIn('PRIVATE-BEARER',str(error.exception));self.assertEqual(run.call_count,1)
    def test_browser_failures_do_not_log_the_link_or_restart_an_owner(self):
        import subprocess
        owner=unittest.mock.Mock();owner.call.return_value={'url':'http://127.0.0.1:1234/#token='+'a'*64}
        with patch.object(self.tool,'Owner',return_value=owner),patch.object(self.tool.subprocess,'run',side_effect=subprocess.CalledProcessError(1,['xdg-open','PRIVATE-BEARER'])) as run:
            with self.assertRaisesRegex(ValueError,'browser did not confirm') as error:self.tool.open_review(self.entry)
            self.assertNotIn('PRIVATE-BEARER',str(error.exception));self.assertEqual(run.call_count,1);owner.close.assert_called_once()
    def install_fixture(self):
        icon=b'<svg xmlns="http://www.w3.org/2000/svg"/>';tool_root=ROOT;files={'scripts/harness-review.py':self.tool.digest((ROOT/'scripts/harness-review.py').read_bytes())};brand=tool_root/'apps/harness/vendor/augmentor-brand/favicon.svg';self.assertTrue(brand.is_file())
        return patch.object(self.tool,'sealed_release',return_value=(self.selection,files))
    def test_menu_escaping_backup_collision_refusal_and_owned_removal(self):
        with self.install_fixture(),patch.object(self.tool.Path,'home',return_value=self.home),patch.dict(os.environ,{'XDG_DATA_HOME':str(self.home/'menu-data')}):
            first=self.tool.change_registry(self.registry,'main',0,dict(self.entry),True);desktop=Path(first['entries']['main']['menuFiles'][0]);text=desktop.read_text();self.assertIn('%%',text);self.assertNotIn(self.selection['root'],text);self.assertNotIn('token=',text)
            self.tool.change_registry(self.registry,'pilot',1,dict(self.entry,title='Authored pilot'),True);desktop.write_text('KEEP-EDITED-DESKTOP')
            with self.assertRaisesRegex(ValueError,'edited'):self.tool.change_registry(self.registry,'main',2)
            self.assertEqual(self.tool.registry_read(self.registry)['revision'],2);self.assertEqual(desktop.read_text(),'KEEP-EDITED-DESKTOP');self.assertTrue((self.registry/'backups').is_dir())
    def test_failed_desktop_validation_rolls_back_owned_files_and_registry(self):
        import subprocess
        with self.install_fixture(),patch.object(self.tool.Path,'home',return_value=self.home),patch.dict(os.environ,{'XDG_DATA_HOME':str(self.home/'menu-data')}),patch.object(self.tool.subprocess,'run',side_effect=subprocess.CalledProcessError(1,['desktop-file-validate'])):
            with self.assertRaises(subprocess.CalledProcessError):self.tool.change_registry(self.registry,'main',0,dict(self.entry),True)
        self.assertEqual(self.tool.registry_read(self.registry)['revision'],0);self.assertFalse((self.home/'.local/bin/augmentor-harness-review').exists());self.assertEqual(list((self.home/'menu-data/applications').glob('*.desktop')),[])
    def test_manifest_metadata_does_not_copy_incidental_integration_fields(self):
        path=self.release/'desktop-release.json';v=json.loads(path.read_text());v['deployment']['incidentalCredential']='DO-NOT-COPY';path.write_text(json.dumps(v));selected,_=self.tool.sealed_release(self.release);self.assertNotIn('incidentalCredential',selected)

if __name__=='__main__':unittest.main()
