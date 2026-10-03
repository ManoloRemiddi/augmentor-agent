# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('qt_inventory', ROOT/'scripts/qt-library-inventory.py')
qt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qt)


class ElfInventoryTests(unittest.TestCase):
    def test_tools_plugins_versioned_libraries_and_shiboken_are_included(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pyside = root/'PySide6'
            shiboken = root/'shiboken6'
            pyside.mkdir(); shiboken.mkdir()
            (pyside/'plugins').mkdir()
            files = [pyside/'tool', pyside/'libQt6Core.so.6',
                     pyside/'plugins/libqxcb.so', shiboken/'Shiboken.abi3.so']
            for file in files:
                file.write_bytes(b'\x7fELFsynthetic '+file.name.encode())
            (pyside/'unrelated.so').write_bytes(b'not an ELF file')
            (pyside/'libQt6Core.so').symlink_to('libQt6Core.so.6')
            rows, links = qt.elf_inventory({'PySide6': pyside, 'shiboken6': shiboken})
            self.assertEqual({r['path'] for r in rows}, {str(p.relative_to(root)) for p in files})
            self.assertEqual(links, [{'path': 'PySide6/libQt6Core.so', 'target': 'libQt6Core.so.6'}])
            for row in rows:
                self.assertEqual(row['sha256'], hashlib.sha256((root/row['path']).read_bytes()).hexdigest())

    def test_external_link_is_refused_instead_of_recording_host_binary_as_shipped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root/'PySide6'
            package.mkdir()
            (root/'system.so').write_bytes(b'\x7fELF')
            (package/'libQt6.so').symlink_to('../system.so')
            with self.assertRaisesRegex(RuntimeError, 'escapes its root'):
                qt.elf_inventory({'PySide6': package})


if __name__ == '__main__':
    unittest.main()
