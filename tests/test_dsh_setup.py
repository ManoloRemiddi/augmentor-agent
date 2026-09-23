# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import io
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('dsh_setup_test', Path(__file__).resolve().parents[1] / 'services/dsh/setup.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class SetupHistoryTests(unittest.TestCase):
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
