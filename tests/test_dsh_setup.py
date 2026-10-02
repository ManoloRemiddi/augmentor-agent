# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import io
import json
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

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
