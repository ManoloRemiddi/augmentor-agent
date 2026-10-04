# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Installed Mac capability follows actual profile/location boundaries."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from updates.macos_bootstrap import locations
from updates.manager import UpdateManager


@unittest.skipUnless(sys.platform in ('linux','darwin'),'requires POSIX ownership/mode semantics')
class MacLocationsTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='mac-profile-');self.addCleanup(temporary.cleanup)
        self.home=Path(temporary.name).resolve();self.base=self.home/'Library/Application Support/Augmentor'
        self.root=self.home/'Applications/Augmentor Agent Desktop.app/Contents/Resources/app'
        self.environment={**os.environ,'HOME':str(self.home),'XDG_CONFIG_HOME':str(self.base/'config'),
            'XDG_DATA_HOME':str(self.base/'data'),'XDG_STATE_HOME':str(self.base/'state'),
            'XDG_RUNTIME_DIR':'/tmp/augmentor-'+str(os.getuid())}

    def test_system_shared_location_and_readable_home_remain_manual(self):
        with patch('sys.platform','darwin'),patch.dict(os.environ,self.environment,clear=True):
            self.assertEqual(locations(self.root)[0],self.home/'Applications/Augmentor Agent Desktop.app')
            with self.assertRaisesRegex(ValueError,'manual updates'):locations(Path('/Applications/Augmentor Agent Desktop.app/Contents/Resources/app'))
            self.home.chmod(0o755)
            try:
                with self.assertRaisesRegex(ValueError,'manual updates'):locations(self.root)
            finally:self.home.chmod(0o700)

    def test_custom_runtime_or_profile_is_not_silently_adopted(self):
        with patch('sys.platform','darwin'),patch.dict(os.environ,self.environment,clear=True):
            os.environ['XDG_RUNTIME_DIR']=str(self.home/'custom-runtime')
            with self.assertRaisesRegex(ValueError,'custom runtime'):locations(self.root)
            os.environ['XDG_RUNTIME_DIR']=self.environment['XDG_RUNTIME_DIR']
            os.environ['XDG_STATE_HOME']=str(self.home/'custom-state')
            with self.assertRaisesRegex(ValueError,'custom profile'):locations(self.root)

    def test_manager_offers_only_matching_per_user_profile_with_fixed_entrypoints(self):
        # No manager worker, app, credential operation or external process runs.
        manager=UpdateManager.__new__(UpdateManager);manager.root=self.root
        manager.current={'installType':'macos-app','component':'desktop'};manager.base=self.base/'data/augmentor/updates'
        (self.root/'scripts').mkdir(parents=True)
        for name in ('macos-update-bootstrap.py','macos-update-observer.py'):
            (self.root/'scripts'/name).write_text('# Inert boundary fixture.\n')
        with patch('sys.platform','darwin'),patch.dict(os.environ,self.environment,clear=True):
            self.assertTrue(manager.installer_available())
            self.assertEqual(manager.installation_directory(),self.base/'state/augmentor/updates')
            manager.base=self.home/'another-profile';self.assertFalse(manager.installer_available())
            manager.base=self.base/'data/augmentor/updates';manager.current['component']='companion'
            self.assertFalse(manager.installer_available())


if __name__=='__main__':unittest.main()
