# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Discovery uses actual persistent prompt/memory paths, not a guessed socket runtime."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from lifecycle.posix_paths import shared_state_directory


@unittest.skipUnless(sys.platform in ('linux','darwin'),'Actual Unix absolute shared-state conventions.')
class SharedStatePathTests(unittest.TestCase):
    def test_default_and_installed_mac_xdg_locations(self):
        with patch.dict(os.environ,{},clear=True),patch.object(Path,'home',return_value=Path('/fixture-home')):
            self.assertEqual(shared_state_directory(),Path('/fixture-home/.local/state/augmentor'))
        with patch.dict(os.environ,{'XDG_STATE_HOME':'/fixture-home/Library/Application Support/Augmentor/state',
                'XDG_RUNTIME_DIR':'/unrelated-socket-runtime'},clear=True):
            self.assertEqual(shared_state_directory(),Path('/fixture-home/Library/Application Support/Augmentor/state/augmentor'))

    def test_explicit_shared_owner_wins_and_relative_paths_refuse(self):
        with patch.dict(os.environ,{'XDG_STATE_HOME':'/state','AUGMENTOR_SHARED_STATE':'/owned/shared'},clear=True):
            self.assertEqual(shared_state_directory(),Path('/owned/shared'))
        for environment in ({'XDG_STATE_HOME':'relative'},{'AUGMENTOR_SHARED_STATE':'relative'}):
            with patch.dict(os.environ,environment,clear=True),self.assertRaises(ValueError):shared_state_directory()
