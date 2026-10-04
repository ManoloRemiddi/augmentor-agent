# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import io
import json
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from contextlib import ExitStack

spec = importlib.util.spec_from_file_location('dsh_setup_test', Path(__file__).resolve().parents[1] / 'services/dsh/setup.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class SetupHistoryTests(unittest.TestCase):
    def test_product_token_has_private_user_ownership_without_changing_external_home(self):
        with tempfile.TemporaryDirectory() as temporary:
            home=Path(temporary)/'external DSH';home.mkdir()
            if setup.sys.platform=='win32':
                import win32security
                mask=win32security.OWNER_SECURITY_INFORMATION|win32security.DACL_SECURITY_INFORMATION
                acl=lambda:win32security.ConvertSecurityDescriptorToStringSecurityDescriptor(
                    win32security.GetFileSecurity(str(home),mask),win32security.SDDL_REVISION_1,mask)
                before=acl()
            path=home/'augmentor-product-token'
            token=setup.product_token(path,create=True)
            self.assertEqual(len(token),64)
            self.assertEqual(setup.product_token(path),token)
            with self.assertRaises(OSError):setup.product_token(path,create=True)
            self.assertEqual(setup.product_token(path),token)
            if setup.sys.platform=='win32':
                self.assertEqual(acl(),before)
            alias=home/'token-alias';os.link(path,alias)
            with self.assertRaises((OSError,ValueError)):setup.product_token(alias)
            self.assertEqual(path.read_text().strip(),token)

    def test_explicit_cli_is_located_without_executing_shell_shims(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)/'DSH café'/'node_modules/@deepseek-ai/dsh'
            (root/'lib').mkdir(parents=True)
            (root/'lib/bin.js').write_text('fixture')
            meta = {'name':'@deepseek-ai/dsh','version':'0.1.5-rc.1','bin':{'dsh':'lib/bin.js'}}
            (root/'package.json').write_text(json.dumps(meta))
            with patch.dict(os.environ, {'AUGMENTOR_DSH_CLI':str(root/'lib/bin.js')}):
                self.assertEqual(setup.cli_directory(), root.resolve())
                (root/'package.json').write_text(json.dumps({**meta,'version':'unreviewed'}))
                with self.assertRaisesRegex(ValueError, 'supported Node DSH'):
                    setup.cli_directory()

    def test_existing_prompt_plugin_is_checked_without_including_our_owned_entry(self):
        from unittest.mock import Mock
        remote=Mock()
        own={'entryId':'include:augmentor-product-prompts','moduleName':'file:///usr/lib/augmentor/adapters/dsh-prompt-library/lib/index.js','enabled':True,'fiberPhase':'active'}
        external={'entryId':'include:prompt-library','moduleName':'dsh-prompt-library','enabled':True,'fiberPhase':'active'}
        remote.invoke.return_value={'entries':[own]}
        with patch.object(setup,'http') as request:
            self.assertIsNone(setup.existing_prompt_plugin(remote,'http://127.0.0.1:3080'))
            request.assert_not_called()
            remote.invoke.return_value={'entries':[external]}
            request.return_value={'ok':True,'library':{'prompts':[]}}
            self.assertEqual(setup.existing_prompt_plugin(remote,'http://127.0.0.1:3080'),'include:prompt-library')
            request.return_value={'ok':True,'library':'wrong'}
            with self.assertRaisesRegex(ValueError,'not compatible'):
                setup.existing_prompt_plugin(remote,'http://127.0.0.1:3080')
            remote.invoke.return_value={'entries':[external,{**external,'entryId':'another'}]}
            with self.assertRaisesRegex(ValueError,'Multiple active'):
                setup.existing_prompt_plugin(remote,'http://127.0.0.1:3080')

    def test_pinned_dependencies_can_be_hoisted_in_a_local_cli_install(self):
        with tempfile.TemporaryDirectory() as directory:
            modules=Path(directory)/'node_modules';cli=modules/'@deepseek-ai/dsh';cli.mkdir(parents=True)
            for name,version in [('dsh-base','0.1.5-rc.1'),('dsh-tools','0.1.5-rc.1'),('schemastery','3.18.2')]:
                path=modules/'@deepseek-ai'/name;path.mkdir(parents=True)
                (path/'package.json').write_text(json.dumps({'version':version}))
            self.assertEqual(setup.modules_directory(cli)[0],modules)
            (modules/'@deepseek-ai/dsh-tools/package.json').write_text('{"version":"different"}')
            with self.assertRaises(ValueError):setup.modules_directory(cli)

    def test_large_history_is_accepted_without_raising_other_endpoint_limits(self):
        # Real DSH histories contain full projections; the host's 273 sessions
        # returned 28 MB. Keep the same allowance as the native history adapter.
        payload = b'{"items":[],"projection":"' + b'x' * (28 * 1024 * 1024) + b'"}'
        with patch.object(setup.urllib.request, 'build_opener') as opener:
            opener.return_value.open.return_value = io.BytesIO(payload)
            self.assertEqual(setup.http('http://127.0.0.1:3080', '/api/session.list')['items'], [])
            opener.return_value.open.return_value = io.BytesIO(payload)
            with self.assertRaisesRegex(ValueError, 'preview limit'):
                setup.http('http://127.0.0.1:3080', '/api/host.describe')

    def test_oversized_history_still_refuses_before_json_parsing(self):
        with patch.object(setup.urllib.request, 'build_opener') as opener:
            response = opener.return_value.open.return_value.__enter__.return_value
            response.read.return_value = b'x' * (128 * 1024 * 1024 + 1)
            with self.assertRaisesRegex(ValueError, 'preview limit'):
                setup.http('http://127.0.0.1:3080', '/api/session.list')


if __name__ == '__main__':
    unittest.main()

class SharedPersonalAgentTests(unittest.TestCase):
    def test_windows_selects_the_native_powershell_tool(self):
        with patch.object(setup.sys, 'platform', 'win32'):
            entries=setup.personal_agent_entries()
        modules={row['name'] for row in entries}
        self.assertIn('@deepseek-ai/dsh-tool-pwsh',modules)
        self.assertNotIn('@deepseek-ai/dsh-tool-bash',modules)

    def test_single_composition_has_full_tools_and_one_prompt(self):
        entries=setup.personal_agent_entries()
        ids={row['id'] for row in entries}
        shell='tool-pwsh' if setup.sys.platform=='win32' else 'tool-bash'
        self.assertTrue({shell,'tool-fs','tool-ask-user','augmentor-desktop','augmentor-memory','augmentor-execution','augmentor-response-metrics'} <= ids)
        self.assertNotIn('augmentor-browser-policy',ids)
        persona=next(row for row in entries if row['id']=='persona')['config']['prefix']
        self.assertIn('one personal assistant',persona)
        self.assertNotIn('Operate only',persona)


class ContextBudgetCompositionTests(unittest.TestCase):
    def test_context_budget_uses_the_isolated_pruner_in_both_personal_presets(self):
        entries=setup.personal_agent_entries()
        group=next(row for row in entries if row['id']=='compaction')
        self.assertTrue(group['isolate']['toolResultPruner'])
        guard=next(row for row in group['config'] if row['id']=='augmentor-context-budget')
        self.assertTrue(Path(guard['name']).is_file())
        self.assertNotIn('augmentor-context-budget', [row['id'] for row in entries])


class OwnedIntegrationCheckTests(unittest.TestCase):
    """A real temporary install, with only endpoint reads replaced by a fixture."""
    def setUp(self):
        from unittest.mock import Mock
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        root=Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.home=root/'home';self.home.mkdir();self.source=root/'selected-source'
        self.config=root/'config/harnesses.json';self.modules=root/'node_modules'
        for name in ('dsh-tools','schemastery'):(self.modules/'@deepseek-ai'/name).mkdir(parents=True)
        (self.source/'node_modules/ws').mkdir(parents=True)
        files={'apps/browser/plugin/dist/index.js':'export default () => {};\n',
               'apps/browser/plugin/package.json':'{"name":"synthetic-browser"}\n',
               'config/agent-persona.md':'Synthetic personal assistant',
               'config/browser-recovery.md':'Synthetic recovery rules',
               'release/dsh/desktop-capabilities.json':'[{"id":"compaction","config":[]}]'}
        for name,text in files.items():
            path=self.source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
        profile=self.home/'profiles/web';profile.mkdir(parents=True)
        (profile/'cordis.patch.yml').write_text('# Unrelated fixture comment\n[]\n')
        self.remote=Mock()
        def call(method,*args):
            if method=='host.describe':return {'version':'0.1.5-rc.1'}
            if method=='agentPresets.list':return {'presets':[{'id':p,'broken':False} for p in setup.PRESETS.values()]}
            if method=='session.list':return {'items':[]}
            raise AssertionError('Unexpected endpoint operation: '+method)
        self.remote.call.side_effect=call;self.remote.invoke.return_value={'entries':[]}
        self.stack.enter_context(patch.object(setup,'ROOT',self.source))
        self.stack.enter_context(patch.object(setup,'configuration',return_value=self.config))
        self.stack.enter_context(patch.object(setup,'cli_directory',return_value=self.modules))
        self.stack.enter_context(patch.object(setup,'modules_directory',return_value=(self.modules,{})))
        self.stack.enter_context(patch.object(setup,'remote_client',return_value=self.remote))
        self.request=self.stack.enter_context(patch.object(setup,'http',side_effect=self.product))
        self.integration=setup.Setup()
        checked=self.check();self.integration.install(checked['token'])
        self.target=profile/'augmentor-product';self.ownership=self.target/'ownership.json'
        self.remote.reset_mock();self.request.reset_mock()

    def product(self,*args,**kwargs):
        token=(self.home/'augmentor-product-token').read_text().strip()
        return {'protocol':'augmentor-dsh/1','version':setup.VERSION,
                'homeId':setup.hashlib.sha256(token.encode()).hexdigest()}

    def check(self):
        return self.integration.check({'endpoint':'http://127.0.0.1:3080','home':str(self.home)})

    def snapshot(self):
        return {str(p.relative_to(self.home)):(p.read_bytes(),p.stat().st_ino,p.stat().st_mtime_ns,p.stat().st_mode)
                for p in self.home.rglob('*') if p.is_file() and not p.is_symlink()}

    def test_fresh_install_preserves_existing_profile_comments_and_composition(self):
        home=self.home.parent/'existing-profile';profile=home/'profiles/web';profile.mkdir(parents=True)
        original='# Existing unrelated plugin and settings\n- insert: [{id: external-plugin, name: external-plugin}]\n'
        composition=profile/'cordis.patch.yml';composition.write_text(original)
        checked=self.integration.check({'endpoint':'http://127.0.0.1:3080','home':str(home)})
        self.integration.install(checked['token'])
        installed=composition.read_text()
        self.assertTrue(installed.startswith(original),installed)
        self.assertEqual(installed.count('external-plugin, name: external-plugin'),1)
        self.assertEqual(next(profile.glob('cordis.patch.yml.before-augmentor-*')).read_text(),original)
        owned=json.loads((profile/'augmentor-product/ownership.json').read_text())
        self.assertEqual(installed.count(owned['patchEntry']),1)

    def test_refresh_preserves_entire_existing_profile_and_owned_entry(self):
        composition=self.home/'profiles/web/cordis.patch.yml'
        original=composition.read_text()+'# Later unrelated customization\n- insert: [{id: later-plugin, name: later-plugin}]\n'
        composition.write_text(original)
        checked=self.check();self.integration.install(checked['token'])
        self.assertEqual(composition.read_text(),original)
        self.assertTrue(setup.current_owned_integration(self.home))

    def test_current_normal_install_is_accepted_without_writing_or_dispatching(self):
        before=self.snapshot()
        with patch.object(setup,'atomic',side_effect=AssertionError('Check wrote a file')), \
                patch.object(self.integration,'install') as install,patch.object(self.integration,'save') as save:
            self.assertTrue(self.check()['installed']);install.assert_not_called();save.assert_not_called()
        self.assertEqual(self.snapshot(),before)
        self.assertEqual([c.args[0] for c in self.remote.call.call_args_list],['host.describe','agentPresets.list'])

    def test_matching_live013_and_valid_copied012_ownership_requires_install(self):
        owned=json.loads(self.ownership.read_text());owned['version']='0.2.12'
        for name in setup.PRESETS.values():
            path=self.home/'.agent-presets'/name/'agent.cordis.yml'
            path.write_text('# Independently authored legacy role fixture\n[]\n')
            owned['presets'][name]['agent.cordis.yml']=setup.digest(path)
        self.ownership.write_text(json.dumps(owned));before=self.snapshot()
        self.assertFalse(self.check()['installed']);self.assertEqual(self.snapshot(),before)
        with self.assertRaisesRegex(ValueError,'Install the integration'):self.integration.save(self.integration.pending['token'])
        self.assertFalse(self.config.exists())

    def test_same_version_self_consistent_old_presets_are_not_current(self):
        owned=json.loads(self.ownership.read_text())
        path=self.home/'.agent-presets'/setup.PRESETS['browser']/'agent.cordis.yml'
        path.write_text('[{"id":"obsolete-role-persona"}]\n')
        owned['presets'][setup.PRESETS['browser']]['agent.cordis.yml']=setup.digest(path)
        self.ownership.write_text(json.dumps(owned))
        self.assertFalse(self.check()['installed'])

    def test_same_version_self_consistent_old_browser_copy_is_not_current(self):
        owned=json.loads(self.ownership.read_text());path=self.target/'browser/dist/index.js'
        path.write_text('export default () => "obsolete";\n');owned['files']['browser/dist/index.js']=setup.digest(path)
        self.ownership.write_text(json.dumps(owned));self.assertFalse(self.check()['installed'])

    def test_missing_malformed_or_duplicate_ownership_refuses(self):
        original=self.ownership.read_bytes();patch_path=self.home/'profiles/web/cordis.patch.yml'
        for payload in (None,b'[]',b'{"version":"0.2.13","files":null}'):
            with self.subTest(payload=payload):
                if payload is None:self.ownership.unlink()
                else:self.ownership.write_bytes(payload)
                self.assertFalse(self.check()['installed'])
                self.ownership.write_bytes(original)
        owned=json.loads(original);patch_path.write_text(patch_path.read_text()+'\n'+owned['patchEntry']+'\n')
        self.assertFalse(self.check()['installed'])

    def test_changed_selected_source_and_unusable_live_preset_require_install(self):
        (self.source/'config/agent-persona.md').write_text('Updated source persona')
        self.assertFalse(self.check()['installed'])
        (self.source/'config/agent-persona.md').write_text('Synthetic personal assistant')
        self.assertTrue(self.check()['installed'])
        self.remote.call.side_effect=lambda method,*args:({'version':'0.1.5-rc.1'} if method=='host.describe' else {'presets':[]})
        self.assertFalse(self.check()['installed'])

    def test_same_source_bytes_at_another_selected_root_require_explicit_refresh(self):
        import shutil
        relocated=self.source.with_name('another-selected-source');shutil.copytree(self.source,relocated)
        with patch.object(setup,'ROOT',relocated):self.assertFalse(self.check()['installed'])

    def test_owned_file_tamper_missing_file_and_symlink_refuse(self):
        path=self.target/'browser/dist/index.js';original=path.read_bytes()
        path.write_bytes(b'unrecorded edit');self.assertFalse(self.check()['installed'])
        path.unlink();self.assertFalse(self.check()['installed'])
        path.symlink_to(self.source/'apps/browser/plugin/dist/index.js')
        self.assertFalse(self.check()['installed']);path.unlink();path.write_bytes(original)
        self.assertTrue(self.check()['installed'])

    def test_protocol_version_and_home_identity_remain_required(self):
        expected=self.product()
        for field,value in (('protocol','other/1'),('version','0.2.12'),('homeId','foreign')):
            with self.subTest(field=field),patch.object(setup,'http',return_value={**expected,field:value}):
                self.assertFalse(self.check()['installed'])

    def test_normal_windows_text_serialization_matches_recorded_owned_bytes(self):
        owned=json.loads(self.ownership.read_text())
        for name in setup.PRESETS.values():
            for filename in ('preset.yml','agent.cordis.yml'):
                path=self.home/'.agent-presets'/name/filename
                path.write_bytes(path.read_text().replace('\n','\r\n').encode())
                owned['presets'][name][filename]=setup.digest(path)
        self.ownership.write_text(json.dumps(owned))
        with patch.object(setup.os,'linesep','\r\n'):
            self.assertTrue(self.check()['installed'])
