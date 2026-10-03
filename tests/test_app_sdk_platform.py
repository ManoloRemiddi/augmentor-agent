# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Synthetic platform/startup contracts; never installs services or reads secrets."""
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import shlex
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/f'{name}.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class AppSdkPlatform(unittest.TestCase):
    def test_linux_discovery_requires_selected_root_and_performs_no_writes(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value); data = root/'data'; (data/'augmentor').mkdir(parents=True)
            descriptor = {'root':str(root), 'node':str(root/'node'), 'python':str(root/'python')}
            (data/'augmentor/desktop.json').write_text(json.dumps(descriptor))
            before = sorted(str(p.relative_to(root)) for p in root.rglob('*'))
            module = load('app-sdk-runtime')
            result = module.describe(root, platform='linux', environ={'XDG_DATA_HOME':str(data)})
            self.assertEqual(result['root'], str(root)); self.assertEqual(result['platform'], 'linux')
            self.assertEqual(before, sorted(str(p.relative_to(root)) for p in root.rglob('*')))
            with self.assertRaisesRegex(ValueError, 'selected'):
                module.describe(root/'foreign', platform='linux', environ={'XDG_DATA_HOME':str(data)})

    def test_mac_bootstrap_checks_packaged_dependencies_without_creating_state(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            (root/'release.json').write_text(json.dumps({'version':'fixture', 'target':'macos-arm64'}))
            module = load('app-sdk-runtime')
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                module.describe(root, platform='darwin', environ={})
            for path in ['node/bin/node','python/bin/python3','apps/browser/native-host.mjs','services/workspaces/sdk.json']:
                file = root/path; file.parent.mkdir(parents=True, exist_ok=True); file.write_text('fixture')
            result = module.describe(root, platform='darwin', environ={'XDG_CONFIG_HOME':str(root/'isolated')})
            self.assertEqual(result['environment']['XDG_CONFIG_HOME'], str(root/'isolated'))
            self.assertFalse((root/'isolated').exists())
            with self.assertRaises(ValueError):
                module.describe(root, platform='win32', environ={})

    def test_startup_plans_keep_paths_with_spaces_as_distinct_arguments(self):
        with tempfile.TemporaryDirectory() as value:
            home = Path(value)/'owner with spaces'; root = home/'Augmentor app'
            runtime = {'root':str(root), 'python':str(root/'python/bin/python3'),
                       'environment':{'XDG_CONFIG_HOME':str(home/'config')}}
            module = load('install-embedding')
            with patch.dict(os.environ, {'XDG_DATA_HOME':str(home/'data'),'XDG_CONFIG_HOME':str(home/'config')}):
                linux = module.startup_plan(runtime, platform='linux', home=home)
            command = next(line.removeprefix('ExecStart=') for line in linux['bytes'].decode().splitlines() if line.startswith('ExecStart='))
            self.assertEqual(shlex.split(command), [runtime['python'], str(linux['launcher'])])
            mac = module.startup_plan(runtime, platform='darwin', home=home)
            plist = plistlib.loads(mac['bytes'])
            self.assertEqual(plist['ProgramArguments'], [runtime['python'],'-I','-B',str(root/'scripts/app-sdk-launch.py'),'embed'])
            self.assertEqual(plist['EnvironmentVariables'], runtime['environment'])
            windows = module.startup_plan(runtime, platform='win32', home=home, startup=home/'Startup')
            self.assertIn('WScript.Shell', windows['bytes'].decode('utf-16'))
            self.assertIn(', 0, False', windows['bytes'].decode('utf-16'))
            self.assertFalse(home.exists(), 'Planning must not create startup/configuration state')

    def test_private_token_is_preserved_and_broad_existing_permissions_fail_closed(self):
        module = load('app-sdk-private')
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)/'private'; token = root/'proxy.token'
            module.prepare('token',token); first = token.read_bytes()
            module.prepare('token',token); self.assertEqual(token.read_bytes(), first)
            self.assertEqual(len(first.strip()),64)
            if os.name != 'nt':
                token.chmod(0o644)
                with self.assertRaises(ValueError):module.prepare('token',token)
                self.assertEqual(token.read_bytes(),first)
            else:
                from platform_adapters.windows_identity import require_private_directory, private_file_descriptor
                require_private_directory(root); os.close(private_file_descriptor(token))


if __name__ == '__main__':unittest.main()
