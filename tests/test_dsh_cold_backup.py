# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Authored cold profiles; real tar readback, no installed/private source copied."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
from types import SimpleNamespace
from unittest.mock import patch

from test_dsh_preservation_transaction import PreservationTransactionFixture
from dsh import cold_backup as backup
from dsh import preservation_transaction as tx


class ColdBackupTests(PreservationTransactionFixture):
    def setUp(self):
        super().setUp()
        self.destination=self.base/'cold-data'
        self.space=patch.object(backup.shutil,'disk_usage',return_value=SimpleNamespace(free=128*backup.GIB))
        self.space.start();self.addCleanup(self.space.stop)

    def capture(self,guard,additional=None):return backup.capture(self.destination,guard,additional)

    def test_full_data_named_components_and_extra_profile_restore_without_following_links(self):
        extra=self.deployment/'native-profile';self.write(extra/'history.jsonl',b'AUTHORED HISTORY AND UNSENT DRAFT KEEP\n')
        self.write(self.home/'sessions/session.txt',b'AUTHORED EXACT HISTORICAL BYTES\n');(self.home/'sessions/session.txt').chmod(0o640)
        self.write(self.home/'sessions/record café 🟣.txt',b'AUTHORED UNICODE NAME KEEP\n')
        os.link(self.home/'sessions/session.txt',self.home/'sessions/hardlink.txt')
        outside=self.base/'outside';self.write(outside/'not-in-backup',b'AUTHORED EXTERNAL SOURCE DO NOT FOLLOW')
        (self.home/'external-module').symlink_to(outside,target_is_directory=True)
        self.write(self.deployment/'releases/never-copy-app.bin',b'AUTHORED MIXED ROOT APP EXCLUSION')
        self.write(Path(self.pair['data'])/'unrelated-application.bin',b'AUTHORED SHARED ROOT EXCLUSION')
        with self.guard() as guard:
            result=self.capture(guard,[{'id':'native-profile','path':str(extra)}])
            self.assertTrue(result['sourceUnchanged']);self.assertFalse(result['activationComplete'])
        verified=backup.verify(self.destination,result['backupSha256']);self.assertTrue(verified['valid'])
        self.assertFalse(verified['restorePerformed']);self.assertEqual(len(verified['coverage']),4)
        with tarfile.open(self.destination/'data.tar') as archive:
            names=archive.getnames();self.assertIn('dsh/sessions/session.txt',names);self.assertIn('native-profile/history.jsonl',names)
            self.assertNotIn('deployment/releases',names);self.assertNotIn('shared-0/unrelated-application.bin',names)
            self.assertFalse(any('not-in-backup' in name for name in names))
            self.assertTrue(archive.getmember('dsh/external-module').issym())
            self.assertTrue(archive.getmember('dsh/sessions/session.txt').islnk() or archive.getmember('dsh/sessions/hardlink.txt').islnk())
        # Independent GNU tar restores only these authored, verified members to
        # a new private directory. This is not an installed restore command.
        restored=self.base/'restored';restored.mkdir(mode=0o700)
        subprocess.run(['tar','--extract','--file',str(self.destination/'data.tar'),'--directory',str(restored),'--no-same-owner','--same-permissions'],check=True,capture_output=True)
        self.assertEqual((restored/'dsh/sessions/session.txt').read_bytes(),b'AUTHORED EXACT HISTORICAL BYTES\n')
        self.assertEqual((restored/'dsh/sessions/session.txt').stat().st_mode&0o777,0o640)
        self.assertEqual((restored/'dsh/sessions/session.txt').stat().st_ino,(restored/'dsh/sessions/hardlink.txt').stat().st_ino)
        self.assertEqual(os.readlink(restored/'dsh/external-module'),str(outside))
        self.assertEqual((restored/'dsh/sessions/record café 🟣.txt').read_bytes(),b'AUTHORED UNICODE NAME KEEP\n')
        self.assertEqual((restored/'native-profile/history.jsonl').read_bytes(),(extra/'history.jsonl').read_bytes())
        self.assert_before()
        for file in self.destination.iterdir():self.assertEqual(file.stat().st_mode&0o777,0o600)

    def test_cold_guard_and_original_unfenced_configuration_are_required(self):
        with self.guard() as guard:pass
        with self.assertRaisesRegex(ValueError,'cold maintenance'):self.capture(guard)
        self.assertFalse(self.destination.exists())
        with self.guard() as guard:
            digest=self.prepare(guard)
            with self.assertRaisesRegex(ValueError,'before preparing'):self.capture(guard)
            tx.rollback(self.backup,digest,guard)
        self.assertFalse(self.destination.exists())

    def test_space_reserve_and_bounded_inventory_refuse_before_creating_backup(self):
        with self.guard() as guard:
            with patch.object(backup.shutil,'disk_usage',return_value=SimpleNamespace(free=backup.RESERVE)):
                with self.assertRaisesRegex(ValueError,'64 GiB'):self.capture(guard)
            with patch.object(backup,'MAX_ENTRIES',1):
                with self.assertRaisesRegex(ValueError,'inventory exceeds'):self.capture(guard)
        self.assertFalse(self.destination.exists());self.assert_before()

    def test_low_space_during_copy_discards_only_its_incomplete_bulk_files(self):
        with self.guard() as guard:
            with patch.object(backup.Budget,'check',side_effect=ValueError('AUTHORED LOW SPACE')):
                with self.assertRaisesRegex(ValueError,'LOW SPACE'):self.capture(guard)
        self.assertEqual({p.name for p in self.destination.iterdir()},{'incomplete.json'})
        self.assertTrue(json.loads((self.destination/'incomplete.json').read_text())['bulkCopiesRemoved']);self.assert_before()

    def test_source_edit_is_preserved_and_never_publishes_a_success_receipt(self):
        original=backup.Reader.read;changed=False
        def edit(reader,size):
            nonlocal changed
            if not changed:
                changed=True;self.write(self.home/'settings.yaml',b'AUTHORED NEW USER EDIT KEEP')
            return original(reader,size)
        with self.guard() as guard,patch.object(backup.Reader,'read',edit):
            with self.assertRaisesRegex(ValueError,'source file changed|data tree changed'):self.capture(guard)
        self.assertEqual((self.home/'settings.yaml').read_bytes(),b'AUTHORED NEW USER EDIT KEEP')
        self.assertFalse((self.destination/'complete.json').exists());self.assertFalse((self.destination/'data.tar').exists())

    def test_late_tree_addition_and_sqlite_journal_make_the_capture_incomplete(self):
        original=backup.verify_members
        def edit(*args):
            original(*args);self.write(self.home/'late-new-data',b'AUTHORED KEEP NEW DATA')
        with self.guard() as guard,patch.object(backup,'verify_members',edit):
            with self.assertRaisesRegex(ValueError,'data tree changed'):self.capture(guard)
        self.assertTrue((self.home/'late-new-data').exists());self.assertFalse((self.destination/'complete.json').exists())
        self.destination=self.base/'journal-backup'
        self.write(Path(self.pair['data'])/'prompts.sqlite3-wal',b'AUTHORED LIVE JOURNAL KEEP')
        with self.guard() as guard:
            with self.assertRaisesRegex(ValueError,'SQLite journals'):self.capture(guard)
        self.assertFalse(self.destination.exists())

    def test_tampered_receipt_manifest_archive_and_linked_archive_are_refused(self):
        with self.guard() as guard:result=self.capture(guard)
        for name in ('complete.json','manifest.json','data.tar'):
            with self.subTest(name=name):
                p=self.destination/name;raw=p.read_bytes();p.write_bytes(raw+b'AUTHORED CORRUPTION')
                with self.assertRaises(ValueError):backup.verify(self.destination,result['backupSha256'])
                p.write_bytes(raw)
        archive=self.destination/'data.tar';outside=self.base/'outside.tar';archive.rename(outside);archive.symlink_to(outside)
        with self.assertRaises((ValueError,OSError)):backup.verify(self.destination,result['backupSha256'])
        self.assertTrue(archive.is_symlink())

    def test_unsafe_destinations_extra_roots_and_special_files_never_copy_data(self):
        with self.guard() as guard:
            for destination in (self.home/'backup',self.deployment/'backup',Path(self.pair['data'])/'backup'):
                with self.subTest(destination=destination),self.assertRaises(ValueError):backup.capture(destination,guard)
                self.assertFalse(destination.exists())
            for additional in ([{'id':'../escape','path':str(self.base)}],[{'id':'dsh','path':str(self.base)}],[{'id':'nested','path':str(self.home)}],[{'id':'mixed','path':str(self.deployment)}],[{'id':'app','path':str(self.old)}]):
                with self.assertRaises(ValueError):self.capture(guard,additional)
            os.mkfifo(self.home/'must-not-open-fifo')
            with self.assertRaisesRegex(ValueError,'socket, device or FIFO'):self.capture(guard)
        self.assertFalse(self.destination.exists())

    def test_replaced_bulk_file_is_preserved_during_failure_cleanup(self):
        original=backup.hash_file
        def replace(path,*args):
            if path.name=='data.tar':
                path.rename(self.base/'saved-original.tar');self.write(path,b'AUTHORED FOREIGN FILE KEEP')
                raise ValueError('AUTHORED changed output')
            return original(path,*args)
        with self.guard() as guard,patch.object(backup,'hash_file',replace):
            with self.assertRaisesRegex(ValueError,'changed output'):self.capture(guard)
        self.assertEqual((self.destination/'data.tar').read_bytes(),b'AUTHORED FOREIGN FILE KEEP')
        self.assertFalse(json.loads((self.destination/'incomplete.json').read_text())['bulkCopiesRemoved'])

    def test_valid_old_archive_is_not_a_current_backup_after_source_or_selection_changes(self):
        with self.guard() as guard:
            result=self.capture(guard)
            self.assertTrue(backup.verify_for_guard(self.destination,result['backupSha256'],guard)['matchesCurrentCoveredData'])
            self.write(self.home/'settings.yaml',b'AUTHORED LATER SETTINGS KEEP')
            self.assertTrue(backup.verify(self.destination,result['backupSha256'])['valid'])
            with self.assertRaisesRegex(ValueError,'no longer matches'):backup.verify_for_guard(self.destination,result['backupSha256'],guard)
        self.write(self.deployment/'desktop.json',{'root':str(self.old),'sharedProfile':self.pair,'authoredNewSelection':True})
        with self.guard() as guard:
            with self.assertRaisesRegex(ValueError,'another configuration'):backup.verify_for_guard(self.destination,result['backupSha256'],guard)
        self.assertEqual((self.home/'settings.yaml').read_bytes(),b'AUTHORED LATER SETTINGS KEEP')
