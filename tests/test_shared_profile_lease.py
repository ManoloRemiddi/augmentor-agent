# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services'))
from lifecycle.shared_profile import SharedProfile,descriptor
from platform_adapters import locks
from platform_adapters.paths import private_directory


class SharedProfileLeaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=private_directory(Path(self.tmp.name));self.data=self.base/'data'
    def test_component_kinds_share_lifetime_but_not_duplicate_writers(self):
        prompts=SharedProfile(self.data,'prompts');self.addCleanup(prompts.close)
        memory=SharedProfile(self.data,'memory');self.addCleanup(memory.close)
        with self.assertRaises(BlockingIOError):SharedProfile(self.data,'prompts')
        with self.assertRaises(BlockingIOError):SharedProfile(self.data,'memory')
        fd=descriptor(self.base/'.data.augmentor-owner.lock');self.addCleanup(os.close,fd)
        with self.assertRaises(BlockingIOError):locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)
        prompts.close()
        with self.assertRaises(BlockingIOError):locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)
        memory.close();locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)
        with self.assertRaises(BlockingIOError):SharedProfile(self.data,'prompts')
        locks.flock(fd,locks.LOCK_UN)
    def test_pending_adoption_refuses_before_creating_missing_data(self):
        (self.base/'.data.augmentor-migration.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'unfinished'):SharedProfile(self.data,'memory')
        self.assertFalse(self.data.exists())
    def test_generated_stage_backup_and_archive_roots_are_not_active_profiles(self):
        for name in ['.data.import-00000000-0000-0000-0000-000000000000.stage','.data.import-00000000-0000-0000-0000-000000000000.backup','shared-imports/'+'a'*64+'/data']:
            with self.assertRaisesRegex(ValueError,'evidence copies'):SharedProfile(self.base/name,'prompts')
