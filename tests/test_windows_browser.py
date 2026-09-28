# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))


@unittest.skipUnless(sys.platform == 'win32', 'requires actual HKCU native-host registration')
class WindowsBrowserRegistrationTests(unittest.TestCase):
    def setUp(self):
        import winreg
        from platform_adapters import windows_browser as registration
        from platform_adapters.paths import private_directory
        self.registry, self.registration = winreg, registration
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = private_directory(Path(self.temp.name)/'private')
        self.path = self.root/'com.augmentor.agent.json'
        self.executable = self.root/'AugmentorBrowserHost.exe'; self.executable.write_bytes(b'fixture')
        self.value = registration.manifest(self.executable, ROOT/'apps/browser/extension/manifest.json')
        self.prefix = 'Software\\Augmentor.Qualification.'+uuid.uuid4().hex
        self.keys = tuple(self.prefix+'\\'+name for name in ('first', 'second', 'third'))
        self.addCleanup(self.cleanup_registry)

    def cleanup_registry(self):
        # Only fixture-owned unique names, never a browser's actual registry key.
        for path in (*self.keys, self.prefix):
            try: self.registry.DeleteKeyEx(self.registry.HKEY_CURRENT_USER, path, self.registration.VIEW)
            except FileNotFoundError: pass

    def write(self, path, value, *, name=''):
        with self.registry.CreateKeyEx(self.registry.HKEY_CURRENT_USER, path, 0,
                self.registry.KEY_SET_VALUE | self.registration.VIEW) as key:
            self.registry.SetValueEx(key, name, 0, self.registry.REG_SZ, value)

    def test_registration_is_shared_across_views_idempotent_and_removes_only_owned_values(self):
        api = self.registration
        self.assertTrue(api.register(self.value, self.path, keys=self.keys)['changed'])
        self.assertEqual(json.loads(self.path.read_text()), self.value)
        for path in self.keys:
            for view in (self.registry.KEY_WOW64_32KEY, self.registry.KEY_WOW64_64KEY):
                with self.registry.OpenKey(self.registry.HKEY_CURRENT_USER, path, 0,
                        self.registry.KEY_READ | view) as key:
                    self.assertEqual(self.registry.QueryValueEx(key, '')[0], str(self.path))
        with patch.object(self.registry, 'SetValueEx', side_effect=AssertionError('Unexpected rewrite')):
            self.assertFalse(api.register(self.value, self.path, keys=self.keys)['changed'])
        self.write(self.keys[0], 'preserve me', name='Unrelated')
        self.assertTrue(api.unregister(self.value, self.path, keys=self.keys)['changed'])
        self.assertFalse(self.path.exists())
        for path in self.keys: self.assertIsNone(api.current(path))
        with self.registry.OpenKey(self.registry.HKEY_CURRENT_USER, self.keys[0]) as key:
            self.assertEqual(self.registry.QueryValueEx(key, 'Unrelated')[0], 'preserve me')
        self.assertFalse(api.unregister(self.value, self.path, keys=self.keys)['changed'])

    def test_conflict_is_found_before_any_manifest_or_other_key_is_written(self):
        self.write(self.keys[-1], r'C:\Other App\host.json')
        with self.assertRaisesRegex(ValueError, 'Another installation'):
            self.registration.register(self.value, self.path, keys=self.keys)
        self.assertFalse(self.path.exists())
        for path in self.keys[:-1]: self.assertIsNone(self.registration.current(path))
        self.assertEqual(self.registration.current(self.keys[-1]), r'C:\Other App\host.json')

    def test_partial_registration_failure_rolls_back_this_attempt(self):
        original = self.registry.SetValueEx
        count = 0
        def write(*args):
            nonlocal count
            count += 1
            if count == 2: raise OSError('Fixture registry write failure')
            return original(*args)
        with patch.object(self.registry, 'SetValueEx', side_effect=write):
            with self.assertRaisesRegex(OSError, 'Fixture registry'):
                self.registration.register(self.value, self.path, keys=self.keys)
        self.assertFalse(self.path.exists())
        for path in self.keys: self.assertIsNone(self.registration.current(path))

    def test_changed_manifest_blocks_removal_and_stable_launcher_path_is_retained(self):
        from platform_adapters.private_files import atomic_json
        from platform_adapters.paths import private_directory, link_directory
        version = private_directory(self.root/'version'); (version/'AugmentorBrowserHost.exe').write_bytes(b'fixture')
        link = self.root/'current'; link_directory(link, version)
        desired = self.registration.manifest(link/'AugmentorBrowserHost.exe', ROOT/'apps/browser/extension/manifest.json')
        self.assertEqual(desired['path'], str(link/'AugmentorBrowserHost.exe'))
        self.assertNotEqual(desired['path'], str((link/'AugmentorBrowserHost.exe').resolve()))
        self.registration.register(self.value, self.path, keys=self.keys)
        atomic_json(self.path, {**self.value, 'description': 'Edited externally'})
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.registration.unregister(self.value, self.path, keys=self.keys)
        self.assertTrue(self.path.exists())
        for path in self.keys: self.assertEqual(self.registration.current(path), str(self.path))
        os.rmdir(link)  # Remove the fixture junction itself, not its target.

    def test_preparation_requires_installer_anchor_and_preserves_edited_extension(self):
        from platform_adapters.paths import private_directory
        api = self.registration
        app = private_directory(self.root/'application')
        for name in ('Augmentor.exe','AugmentorBrowserHost.exe'): (app/name).write_bytes(b'fixture')
        target = {'win-amd64':'windows-x64','win-arm64':'windows-arm64'}[sysconfig.get_platform()]
        (app/'release.json').write_text(json.dumps({'target':target}))
        source = private_directory(app/'apps/browser/extension')
        shutil.copy2(ROOT/'apps/browser/extension/manifest.json',source/'manifest.json')
        (source/'example.js').write_text('const test = "Unicode café";',encoding='utf-8')
        browser = private_directory(self.root/'unlisted browser')
        executable = browser/'comet.exe'; shutil.copy2(sys.executable,executable)
        for name in ('resources.pak','icudtl.dat','fork_100_percent.pak'): (browser/name).write_bytes(b'fixture')
        data = private_directory(self.root/'data')
        with patch.dict(os.environ,{'XDG_DATA_HOME':str(data)}):
            with self.assertRaisesRegex(ValueError,'Install Augmentor'):
                api.prepare_extension(app,executable,key_path=self.prefix,keys=self.keys)
            self.assertFalse((data/'browser-extensions').exists())
            self.write(self.prefix,'com.augmentor.Agent',name='AppId')
            self.write(self.prefix,str(app),name='Root')
            prepared = api.prepare_extension(app,executable,key_path=self.prefix,keys=self.keys)
            import hashlib
            with self.registry.OpenKey(self.registry.HKEY_CURRENT_USER,self.prefix) as key:
                self.assertEqual(self.registry.QueryValueEx(key,'BrowserManifestSHA256'),
                    (hashlib.sha256(Path(prepared['manifest']).read_bytes()).hexdigest(),self.registry.REG_SZ))
            destination = Path(prepared['extensionDirectory'])
            self.assertEqual((destination/'example.js').read_bytes(),(source/'example.js').read_bytes())
            self.assertTrue(destination.is_relative_to(data))
            self.assertEqual(api.prepare_extension(app,executable,key_path=self.prefix,keys=self.keys)['extensionDirectory'],str(destination))
            self.assertEqual(json.loads(Path(prepared['manifest']).read_text())['path'],str(app/'AugmentorBrowserHost.exe'))
            (destination/'example.js').write_text('user edited')
            with self.assertRaisesRegex(ValueError,'edited'):
                api.prepare_extension(app,executable,key_path=self.prefix,keys=self.keys)
            self.assertEqual((destination/'example.js').read_text(),'user edited')
            self.write(self.prefix,str(self.root/'other-install'),name='Root')
            with self.assertRaisesRegex(ValueError,'installed Augmentor'):
                api.prepare_extension(app,executable,key_path=self.prefix,keys=self.keys)

    def test_ownership_receipt_failure_never_publishes_new_browser_pointers(self):
        calls=[]
        def refusal(path):
            self.assertTrue(path.is_file())
            self.assertTrue(all(self.registration.current(key) is None for key in self.keys))
            calls.append('before-registration')
            raise OSError('Fixture receipt failure')
        with self.assertRaisesRegex(OSError,'receipt failure'):
            self.registration.register(self.value,self.path,keys=self.keys,before_registration=refusal)
        self.assertEqual(calls,['before-registration'])
        self.assertFalse(self.path.exists())
        self.assertTrue(all(self.registration.current(key) is None for key in self.keys))


@unittest.skipUnless(sys.platform == 'win32', 'requires Windows registry discovery and PE metadata')
class WindowsBrowserDiscoveryTests(unittest.TestCase):
    def test_unlisted_browser_resources_unicode_command_and_registry_discovery(self):
        import winreg
        from platform_adapters import windows_browsers as browsers
        prefix = 'Software\\Augmentor.BrowserDiscovery.'+uuid.uuid4().hex
        registered, capabilities, classes = prefix+'\\Registered', prefix+'\\Capabilities', prefix+'\\Classes'
        touched = []
        def set_value(path, name, value):
            parts = path.split('\\')
            for count in range(2, len(parts)+1):
                partial = '\\'.join(parts[:count])
                if partial not in touched: touched.append(partial)
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        with tempfile.TemporaryDirectory(prefix='browser café ') as temporary:
            folder = Path(temporary)
            executable = folder/'Unlisted Chromium browser.exe'
            shutil.copy2(sys.executable, executable)  # Read actual PE version metadata; never execute this fixture.
            resources = folder/'123.4.5.6'; resources.mkdir()
            for filename in ('resources.pak', 'icudtl.dat', 'renamed_100_percent.pak'):
                (resources/filename).write_bytes(b'fixture')
            try:
                command = subprocess.list2cmdline([str(executable), '--profile-directory=Test Profile', '%1'])
                self.assertEqual(browsers.command_executable(command), executable)
                details = browsers.browser_application(executable)
                self.assertEqual(details['app'], str(executable.resolve()))
                self.assertTrue(details['name'])
                self.assertEqual(details['engineResources'], str(resources.resolve()))
                set_value(registered, 'A browser absent from any brand list', capabilities)
                for scheme in ('http', 'https'): set_value(capabilities+r'\URLAssociations', scheme, 'UnlistedBrowser.HTML')
                set_value(classes+r'\UnlistedBrowser.HTML\shell\open\command', '', command)
                found = browsers.installed_browsers(hives=(winreg.HKEY_CURRENT_USER,),
                    registered_path=registered, classes_path=classes)
                self.assertEqual(found, [details])  # Registry-view duplicates collapse.
                (resources/'icudtl.dat').unlink()
                with self.assertRaisesRegex(ValueError, 'Chromium'):
                    browsers.browser_application(executable)
                self.assertEqual(browsers.installed_browsers(hives=(winreg.HKEY_CURRENT_USER,),
                    registered_path=registered, classes_path=classes), [])
                for unsafe in ('relative.exe --arg', 'cmd.exe /c anything', '', '\x00'):
                    with self.assertRaises(ValueError): browsers.command_executable(unsafe)
            finally:
                for path in sorted(touched, key=lambda value: value.count('\\'), reverse=True):
                    try: winreg.DeleteKeyEx(winreg.HKEY_CURRENT_USER, path, winreg.KEY_WOW64_64KEY)
                    except FileNotFoundError: pass


if __name__ == '__main__': unittest.main()
