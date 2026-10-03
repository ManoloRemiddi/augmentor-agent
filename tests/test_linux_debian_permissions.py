# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('debian_permission_test', ROOT/'scripts/package-debian.py')
debian = importlib.util.module_from_spec(spec); spec.loader.exec_module(debian)


class DebianPermissionTests(unittest.TestCase):
    def test_copied_checkout_permissions_do_not_become_package_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'checkout'; source.mkdir(mode=0o775); source.chmod(0o775)
            nested = source/'services/memory'; nested.mkdir(parents=True); nested.chmod(0o775)
            program = nested/'service.py'; program.write_bytes(b'# synthetic package source\n'); program.chmod(0o664)
            stage = Path(directory)/'runtime/usr/lib/augmentor'
            debian.copy(source, stage)
            self.assertEqual(stat.S_IMODE((stage/'services/memory/service.py').stat().st_mode), 0o664)
            before = {p.relative_to(stage).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in stage.rglob('*') if p.is_file()}
            owners = {p: (p.stat().st_uid, p.stat().st_gid) for p in [stage, *stage.rglob('*')]}
            debian.normalize_staging_permissions(Path(directory)/'runtime')
            for path in [stage, *stage.rglob('*')]:
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o755 if path.is_dir() else 0o644)
                self.assertEqual((path.stat().st_uid, path.stat().st_gid), owners[path])
            self.assertEqual(before, {p.relative_to(stage).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in stage.rglob('*') if p.is_file()})
            self.assertEqual(stat.S_IMODE(source.stat().st_mode), 0o775)
            self.assertEqual(stat.S_IMODE(program.stat().st_mode), 0o664)

    def test_any_existing_execute_bit_is_preserved_without_write_or_special_bits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, mode in enumerate((0o775, 0o710, 0o604, 0o7644)):
                path = root/str(index); path.write_bytes(b'unchanged'); path.chmod(mode)
            debian.normalize_staging_permissions(root)
            for index, expected in enumerate((0o755, 0o755, 0o644, 0o644)):
                self.assertEqual(stat.S_IMODE((root/str(index)).stat().st_mode), expected)
                self.assertEqual((root/str(index)).read_bytes(), b'unchanged')

    def test_internal_and_external_symlinks_keep_targets_and_do_not_traverse(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/'stage'; root.mkdir()
            outside = Path(directory)/'outside'; outside.mkdir(); outside.chmod(0o775)
            target = outside/'private'; target.write_bytes(b'external fixture'); target.chmod(0o664)
            inside = root/'program'; inside.write_bytes(b'internal fixture'); inside.chmod(0o775)
            (root/'internal').symlink_to('program'); (root/'directory-link').symlink_to(outside, target_is_directory=True)
            (root/'dangling').symlink_to('absent')
            links = {p.name: (os.readlink(p), p.lstat().st_ino) for p in root.iterdir() if p.is_symlink()}
            debian.normalize_staging_permissions(root)
            self.assertEqual(links, {p.name: (os.readlink(p), p.lstat().st_ino) for p in root.iterdir() if p.is_symlink()})
            self.assertEqual(stat.S_IMODE(inside.stat().st_mode), 0o755)
            self.assertEqual(stat.S_IMODE(outside.stat().st_mode), 0o775)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o664)
            self.assertEqual(target.read_bytes(), b'external fixture')

    def test_linked_staging_root_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'real'; target.mkdir(); target.chmod(0o775)
            link = Path(directory)/'link'; link.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'ordinary directory'):
                debian.normalize_staging_permissions(link)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o775)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'requires Unix path types')
    def test_fifo_refusal_precedes_any_permission_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); root.chmod(0o775)
            regular = root/'ordinary'; regular.write_bytes(b'retained'); regular.chmod(0o664)
            os.mkfifo(root/'unsupported')
            with self.assertRaisesRegex(ValueError, 'Unsupported package staging path type'):
                debian.normalize_staging_permissions(root)
            self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o775)
            self.assertEqual(stat.S_IMODE(regular.stat().st_mode), 0o664)

    @unittest.skipUnless(shutil.which('dpkg-deb'), 'requires native Debian archive builder')
    def test_actual_deb_archive_records_normalized_modes_root_owners_and_exact_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/'runtime'; app = root/'usr/lib/augmentor'; app.mkdir(parents=True)
            source = Path(directory)/'checkout'; source.mkdir(); source.chmod(0o775)
            (source/'service.py').write_bytes(b'synthetic immutable service\n'); (source/'service.py').chmod(0o664)
            (source/'launcher').write_bytes(b'#!/bin/sh\nexit 0\n'); (source/'launcher').chmod(0o775)
            debian.copy(source, app)
            (app/'link').symlink_to('service.py')
            control = root/'DEBIAN'; control.mkdir()
            (control/'control').write_text('Package: augmentor-permission-fixture\nVersion: 1\nArchitecture: all\nMaintainer: Synthetic fixture <fixture@example.invalid>\nDescription: Archive metadata only; never installed\n')
            debian.normalize_staging_permissions(root)
            artifact = Path(directory)/'fixture.deb'
            subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(root), str(artifact)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            with subprocess.Popen(['dpkg-deb', '--fsys-tarfile', str(artifact)], stdout=subprocess.PIPE) as process:
                with tarfile.open(fileobj=process.stdout, mode='r|') as archive:
                    rows = {}
                    for member in archive:
                        content = archive.extractfile(member).read() if member.isreg() else None
                        rows[member.name] = (member.mode, member.uid, member.gid, member.linkname, content)
                self.assertEqual(process.wait(), 0)
            self.assertEqual(rows['./usr/lib/augmentor/service.py'], (0o644, 0, 0, '', b'synthetic immutable service\n'))
            self.assertEqual(rows['./usr/lib/augmentor/launcher'], (0o755, 0, 0, '', b'#!/bin/sh\nexit 0\n'))
            self.assertEqual(rows['./usr/lib/augmentor'][:3], (0o755, 0, 0))
            self.assertEqual(rows['./usr/lib/augmentor/link'][3], 'service.py')
            self.assertEqual(stat.S_IMODE((source/'service.py').stat().st_mode), 0o664)


if __name__ == '__main__':
    unittest.main()
