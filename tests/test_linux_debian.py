# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('debian_target_test',ROOT/'scripts/package-debian.py')
debian=importlib.util.module_from_spec(spec);spec.loader.exec_module(debian)


class DebianTargetTests(unittest.TestCase):
    def test_noble_dependencies_use_system_gi_and_managed_pyside(self):
        runtime,desktop=debian.dependencies(debian.NOBLE,'0.2.13')
        self.assertIn('python3.12-venv',runtime);self.assertIn('python3-gi',runtime)
        self.assertIn('python3-flatbuffers',runtime);self.assertIn('libportaudio2',runtime)
        self.assertNotIn('python3-pyside6',runtime+desktop)
        self.assertNotIn('python3-keyring',runtime+desktop)
        self.assertIn('augmentor-runtime (= 0.2.13)',desktop)
        legacy=debian.dependencies('debian13-amd64','0.2.13')
        self.assertIn('python3-pyside6.qtcore (>= 6.8.2.1)',legacy[1])
        self.assertIn('python3-keyring (>= 25.6)',legacy[0])

    def test_wrong_host_hook_refuses_before_any_maintenance_directory_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            debian.control(root,'augmentor-runtime','0.2.13','python3','fixture',debian.NOBLE)
            source=(root/'DEBIAN/preinst').read_text()
            self.assertNotIn('@TARGET@',source)
            for release,machine in [('ID=fedora\nVERSION_ID=44\n','x86_64'),
                                    ('ID=ubuntu\nVERSION_ID="26.04"\n','x86_64'),
                                    ('ID=linuxmint\nVERSION_ID=22.3\n','x86_64'),
                                    ('ID=ubuntu\nVERSION_ID="24.04"\n','aarch64')]:
                with self.subTest(release=release,machine=machine),patch.object(Path,'read_text',return_value=release),\
                        patch.object(Path,'mkdir') as mkdir,patch('platform.machine',return_value=machine),\
                        patch('sys.argv',['preinst','install']):
                    with self.assertRaisesRegex(SystemExit,'requires Ubuntu 24.04'):exec(compile(source,'preinst','exec'),{})
                    mkdir.assert_not_called()

    def test_missing_or_cross_target_wheelhouse_refuses_before_building(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'out'
            with patch.object(debian.subprocess,'run') as run:
                with self.assertRaisesRegex(ValueError,'seven-wheel cache'):debian.build(root,debian.NOBLE)
                with self.assertRaisesRegex(ValueError,'cannot embed'):debian.build(root,'debian13-amd64',Path(directory))
                run.assert_not_called()
            self.assertFalse(root.exists())


if __name__=='__main__':unittest.main()
