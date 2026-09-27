# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import json
import plistlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('mac_browser', Path(__file__).resolve().parents[1]/'scripts/register-macos-browser.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MacBrowserRegistrationTests(unittest.TestCase):
    def browser(self, root, name='Comet', product=None):
        app=root/(name+'.app');binary=app/'Contents/MacOS'/name
        binary.parent.mkdir(parents=True);binary.write_text('fixture');binary.chmod(0o755)
        info={'CFBundleExecutable':name,'CFBundleName':name,'CFBundleIdentifier':'fixture.'+name,
              'CFBundleURLTypes':[{'CFBundleURLSchemes':['http','https']}]}
        if product is not None:info['CrProductDirName']=product
        (app/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
        resources=app/'Contents/Frameworks'/(name+' Framework.framework')/'Resources'
        resources.mkdir(parents=True)
        for name in ('chrome_100_percent.pak','resources.pak','icudtl.dat'):(resources/name).touch()
        return app

    def test_discovers_comet_and_unknown_chromium_fork_without_brand_list(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);comet=self.browser(root)
            other=self.browser(root/'Browsers','New Browser','Vendor/New Browser')
            safari=root/'Safari.app/Contents';safari.mkdir(parents=True)
            (safari/'Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':'Safari'}))
            browsers=module.installed_browsers([root])
            self.assertEqual({row['app'] for row in browsers},{str(comet),str(other)})
            support=root/'support';(support/'Comet').mkdir(parents=True)
            (support/'Comet/Local State').write_text('private contents are never read')
            self.assertEqual(module.browser_data_directory(comet,support),support/'Comet')
            self.assertEqual(module.browser_data_directory(other,support),support/'Vendor/New Browser')

    def test_unknown_data_location_requires_explicit_folder_and_preserves_profiles(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);app=self.browser(root,'Custom');support=root/'support'
            with self.assertRaisesRegex(ValueError,'Open Custom once'):module.browser_data_directory(app,support)
            custom=support/'Vendor/Profile Root';custom.mkdir(parents=True)
            state=custom/'Local State';state.write_text('preserved')
            self.assertEqual(module.browser_data_directory(app,support,custom),custom)
            self.assertEqual(state.read_text(),'preserved')
            with self.assertRaisesRegex(ValueError,'Local State'):module.browser_data_directory(app,support,custom/'Default')

    def test_data_paths_cannot_escape_or_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);support=root/'support';support.mkdir()
            outside=root/'private';outside.mkdir();(support/'Linked').symlink_to(outside)
            for product in ('../private','Linked/Browser',str(outside)):
                with self.subTest(product=product):
                    app=self.browser(root/str(len(list(root.iterdir()))),'Fork',product)
                    with self.assertRaises(ValueError):module.browser_data_directory(app,support)
            self.assertEqual(list(outside.iterdir()),[])

    def test_selected_comet_prepares_correct_host_and_lifecycle_discovers_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);comet=self.browser(root);support=root/'support'
            profile=support/'Comet';profile.mkdir(parents=True);(profile/'Local State').write_text('{}')
            app=root/'Augmentor.app';source=app/'Contents/Resources/app/apps/browser/extension'
            source.mkdir(parents=True);(source/'manifest.json').write_text('{}')
            value={'path':str(app/'host'),'allowed_origins':['chrome-extension://fixture/']}
            with patch.object(module,'manifest',return_value=value):
                result=module.prepare_extension(app,comet,support)
            target=profile/'NativeMessagingHosts/com.augmentor.agent.json'
            self.assertEqual(result['manifest'],str(target));self.assertEqual(json.loads(target.read_text()),value)
            self.assertIn(target.parent,module.registration_directories(support))
            self.assertFalse((support/'Google').exists())

    def test_prepared_extension_is_stable_and_edits_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); app = root/'Augmentor.app'
            source = app/'Contents/Resources/app/apps/browser/extension'; source.mkdir(parents=True)
            (source/'manifest.json').write_text('{"version":"1.0"}')
            value = {'path': str(app/'Contents/MacOS/host'), 'allowed_origins': ['chrome-extension://fixture/']}
            with patch.object(module, 'manifest', return_value=value):
                first = module.prepare_extension(app, 'chrome', root/'support')
                second = module.prepare_extension(app, 'chrome', root/'support')
                self.assertEqual(first['extensionDirectory'], second['extensionDirectory'])
                self.assertFalse(second['changed'])
                target = Path(first['extensionDirectory'])/'manifest.json'; target.write_text('user edits')
                with self.assertRaisesRegex(ValueError, 'edited'):
                    module.prepare_extension(app, 'chrome', root/'support')
                self.assertEqual(target.read_text(), 'user edits')
                self.assertEqual((source/'manifest.json').read_text(), '{"version":"1.0"}')

    def test_prepared_extension_refuses_links_before_browser_registration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); app = root/'Augmentor.app'
            source = app/'Contents/Resources/app/apps/browser/extension'; source.mkdir(parents=True)
            (source/'linked').symlink_to(root/'private-data')
            with patch.object(module, 'manifest', return_value={}), patch.object(module, 'register') as register:
                with self.assertRaisesRegex(ValueError, 'link'):
                    module.prepare_extension(app, 'chrome', root/'support')
                register.assert_not_called()

    def test_removal_retains_exact_manifest_and_other_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);value={'path':'/Applications/Preview.app/Contents/MacOS/host','allowed_origins':['chrome-extension://fixture/']}
            module.register(value,root)
            unrelated=root/'other-host.json';unrelated.write_text('preserve')
            result=module.unregister(value,root)
            self.assertTrue(result['changed'])
            self.assertFalse((root/'com.augmentor.agent.json').exists())
            self.assertEqual(json.loads(Path(result['backup']).read_text()),value)
            self.assertEqual(unrelated.read_text(),'preserve')
            self.assertFalse(module.unregister(value,root)['changed'])

    def test_modified_or_other_installation_manifest_is_preserved(self):
        for current in ({'path':'/Applications/Other.app/host'}, {'path':'/Applications/Preview.app/host','extra':True}):
            with self.subTest(current=current),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);module.register(current,root)
                before=(root/'com.augmentor.agent.json').read_bytes()
                with self.assertRaises(ValueError):module.unregister({'path':'/Applications/Preview.app/host'},root)
                self.assertEqual((root/'com.augmentor.agent.json').read_bytes(),before)

    def test_removal_does_not_follow_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target=root/'keep.json';target.write_text('{}')
            path=root/'com.augmentor.agent.json';path.symlink_to(target)
            with self.assertRaises(OSError):module.unregister({},root)
            self.assertTrue(path.is_symlink());self.assertEqual(target.read_text(),'{}')

    def test_registration_retains_existing_manifest_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root/'com.augmentor.agent.json'
            path.write_text('{"legacy":"retained"}\n')
            value = {'path': '/Applications/An App.app/Contents/MacOS/host'}
            result = module.register(value, root)
            self.assertEqual(Path(result['backup']).read_text(), '{"legacy":"retained"}\n')
            self.assertEqual(json.loads(path.read_text()), value)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertFalse(module.register(value, root)['changed'])

    def test_symlink_manifest_preserves_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); target = root/'user-file'; target.write_text('retained')
            (root/'com.augmentor.agent.json').symlink_to(target)
            with self.assertRaises(ValueError):
                module.register({}, root)
            self.assertEqual(target.read_text(), 'retained')
