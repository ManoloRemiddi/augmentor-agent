# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from augmentor_linux.managed_setup import WINDOWS_RUNTIME_PAYLOAD

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/name)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


launcher = load('launch-windows.py')
components = load('launch-component.py')
browser = load('launch-windows-browser.py')


class WindowsLauncherTests(unittest.TestCase):
    def test_browser_origin_and_parent_window_arguments_are_bounded(self):
        origin = browser.origin(ROOT)
        self.assertRegex(origin, r'^chrome-extension://[a-p]{32}/$')
        browser.validate_arguments([origin], ROOT)
        browser.validate_arguments([origin, '--parent-window=123'], ROOT)
        for arguments in ([], ['chrome-extension://'+'a'*32+'/'], [origin, '--arbitrary'],
                          [origin, '--parent-window=-1'], [origin, '--parent-window='+'1'*21],
                          [origin, '--parent-window=0', '--parent-window=1']):
            with self.subTest(arguments=arguments), self.assertRaisesRegex(ValueError, 'matching Augmentor'):
                browser.validate_arguments(arguments, ROOT)

    def test_partial_native_library_configuration_closes_search_handles(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ('python/Lib/site-packages/PySide6/plugins', 'python/Lib/site-packages/shiboken6'):
                (root/name).mkdir(parents=True)
            handle = Mock()
            with patch.object(launcher.os, 'add_dll_directory', create=True, side_effect=[handle, OSError('fixture failure')]):
                with self.assertRaises(OSError): launcher.configure_qt(root)
            handle.close.assert_called_once()

    def test_foreign_architecture_and_incomplete_payload_fail_before_launch(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(launcher.sysconfig, 'get_platform', return_value='win-arm64'):
            root = Path(temporary)
            (root/'release.json').write_text(json.dumps({'target': 'windows-x64'}))
            with self.assertRaisesRegex(ValueError, 'architecture'): launcher.preflight(root)
            (root/'release.json').write_text(json.dumps({'target': 'windows-arm64'}))
            with self.assertRaisesRegex(ValueError, 'incomplete'): launcher.preflight(root)
            for name, _label in WINDOWS_RUNTIME_PAYLOAD:
                path = root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('fixture')
            self.assertEqual(launcher.preflight(root)['target'], 'windows-arm64')

    def test_customer_artifact_cannot_redirect_qualification_state(self):
        for metadata in ({}, {'customerDistribution': True}, {'customerDistribution': False},
                         {'customerDistribution': True, 'qualificationStatus': 'development-candidate'}):
            with self.subTest(metadata=metadata), self.assertRaisesRegex(ValueError, 'development candidate'):
                launcher.configure_qualification('never-created', metadata)

    def test_windows_launch_uses_its_bundled_tools_even_with_inherited_overrides(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ('node/node.exe', 'python/python.exe', 'powershell/pwsh.exe', 'dsh/node_modules/@deepseek-ai/dsh/lib/bin.js'):
                path = root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('fixture')
            with patch.object(components, 'ROOT', root), patch.object(sys, 'platform', 'win32'), patch.dict(os.environ, {
                'AUGMENTOR_PYTHON': str(root/'foreign/python.exe'), 'AUGMENTOR_PI_NODE': str(root/'foreign/node.exe'),
                'RESONANT_VOICE_HOME':str(root/'foreign/voice')
            }):
                components.configure(windows_paths={'XDG_RUNTIME_DIR': str(root/'run'),'XDG_CONFIG_HOME':str(root/'config')})
                self.assertEqual(os.environ['AUGMENTOR_PYTHON'], str(root/'python/python.exe'))
                self.assertEqual(os.environ['AUGMENTOR_PI_NODE'], str(root/'node/node.exe'))
                self.assertEqual(os.environ['RESONANT_VOICE_HOME'],str(root/'config/resonant-voice'))
                self.assertEqual(os.environ['PATH'].split(os.pathsep)[:3], [str(root/'powershell'), str(root/'node'), str(root/'python')])


if __name__ == '__main__': unittest.main()
