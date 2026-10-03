# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Streaming native archive inspection must refuse corruption without extraction."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_inspection', ROOT/'scripts/inspect-system-qt-package.py')
inspection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspection)


def archive(entries):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w') as output:
        for path, body, kind in entries:
            info = tarfile.TarInfo(path)
            info.mode = 0o644
            if kind == 'file':
                info.size = len(body)
                output.addfile(info, io.BytesIO(body))
            else:
                info.type = tarfile.LNKTYPE
                info.linkname = body
                output.addfile(info)
    stream.seek(0)
    return stream


def cpio(entries):
    result = bytearray()
    for path, body, mode, inode, count in entries+[('TRAILER!!!', b'', 0, 0, 1)]:
        raw = path.encode()+b'\0'
        fields = [inode, mode, 0, 0, count, 0, len(body), 0, 0, 0, 0, len(raw), 0]
        result += b'070701'+''.join(f'{value:08x}' for value in fields).encode()+raw
        result += b'\0'*((-len(result)) % 4)
        result += body
        result += b'\0'*((-len(result)) % 4)
    return io.BytesIO(result)


class NativeInspection(unittest.TestCase):
    def test_tar_rejects_duplicate_escape_and_unresolved_link(self):
        cases = [[('usr/file', b'first', 'file'), ('usr/file', b'second', 'file')],
                 [('../outside', b'escape', 'file')],
                 [('usr/file', 'usr/absent', 'hardlink')]]
        for entries in cases:
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                inspection.tar_records(archive(entries))

    def test_newc_rejects_truncated_duplicate_and_unsafe_filename(self):
        mode = stat.S_IFREG | 0o644
        for stream in (io.BytesIO(b'070701'), cpio([('usr/file', b'a', mode, 1, 1), ('usr/file', b'b', mode, 2, 1)]),
                       cpio([('/outside', b'bad', mode, 1, 1)])):
            with self.subTest(stream=stream), self.assertRaises(ValueError):
                inspection.cpio_records(stream)

    def test_newc_real_hardlink_group_preserves_content_and_executable_mode(self):
        mode = stat.S_IFREG | 0o755
        records, _ = inspection.cpio_records(cpio([('usr/bin/first', b'', mode, 7, 2),
                                                  ('usr/bin/second', b'checked executable', mode, 7, 2)]))
        self.assertEqual(records['usr/bin/first'], records['usr/bin/second'])
        self.assertEqual(records['usr/bin/first']['mode'], 0o755)
        self.assertEqual(records['usr/bin/first']['sha256'], hashlib.sha256(b'checked executable').hexdigest())

    def test_corrupt_preparation_or_prior_output_refuses_before_native_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'payload.tar').write_bytes(b'corrupt input')
            (root/'preparation.json').write_text(json.dumps({'format': 'augmentor-system-qt-package-preparation/1',
                'payloadArchive': {'bytes': 13, 'sha256': 'a'*64}}))
            for existing in (False, True):
                out = root/('prior.json' if existing else 'new.json')
                if existing:
                    out.write_bytes(b'preserve prior result')
                with self.subTest(existing=existing), patch.object(inspection.subprocess, 'Popen') as producer, self.assertRaises(ValueError):
                    inspection.inspect(root, root/'candidate.rpm', out)
                producer.assert_not_called()
                if existing:
                    self.assertEqual(out.read_bytes(), b'preserve prior result')
                else:
                    self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
