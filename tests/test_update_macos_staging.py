# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual ZIP boundaries and paths are checked before native extraction."""
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from updates.macos_staging import validate_zip
from updates.macos_reopen import validate_plan

NAME='Augmentor Agent Desktop.app'


class MacStagingTests(unittest.TestCase):
    def archive(self,rows):
        temporary=tempfile.TemporaryFile();self.addCleanup(temporary.close)
        with zipfile.ZipFile(temporary,'w') as bundle:
            for name,content,kind in rows:
                item=zipfile.ZipInfo(name);item.create_system=3;item.external_attr=(kind|0o755)<<16
                bundle.writestr(item,content)
        temporary.seek(0);return temporary

    def test_real_framework_link_and_resource_sidecars_are_retained_without_execution(self):
        prefix=NAME+'/Contents/Frameworks/Foo.framework/'
        stream=self.archive([(prefix+'Versions/A/binary',b'Inert framework.',stat.S_IFREG),
            (prefix+'Versions/Current',b'A',stat.S_IFLNK),
            ('__MACOSX/'+NAME+'/Contents/._Info.plist',b'Inert metadata.',stat.S_IFREG)])
        report=validate_zip(stream,NAME)
        self.assertEqual(report['entries'],3);self.assertEqual(report['bundle'],NAME)

    def test_traversal_external_links_and_writes_below_links_are_refused_before_extraction(self):
        cases=[[(NAME+'/../../owner-profile',b'Unsafe traversal.',stat.S_IFREG)],
            [(NAME+'/Contents/external',b'/outside',stat.S_IFLNK)],
            [(NAME+'/Contents/external',b'../../outside',stat.S_IFLNK)],
            [(NAME+'/Contents/Alias',b'Other',stat.S_IFLNK),(NAME+'/Contents/Alias/data',b'Writes through link.',stat.S_IFREG)],
            [('__MACOSX/Other.app/._file',b'Foreign resource.',stat.S_IFREG)]]
        for rows in cases:
            with self.subTest(rows=rows),self.assertRaises(ValueError):validate_zip(self.archive(rows),NAME)

    def test_conflicting_local_path_cannot_bypass_safe_central_directory(self):
        stream=self.archive([(NAME+'/aa/bb/owner-profile',b'Host sentinel must remain untouched.',stat.S_IFREG)])
        raw=stream.read();central=raw.index(b'PK\x01\x02')
        local=raw[:central].replace(b'/aa/bb/',b'/../../',1)
        self.assertEqual(len(local),central)
        stream.seek(0);stream.write(local+raw[central:]);stream.seek(0)
        with self.assertRaises(zipfile.BadZipFile):validate_zip(stream,NAME)

    def test_case_collision_trailing_bytes_and_oversized_directory_are_refused(self):
        with self.assertRaises(ValueError):validate_zip(self.archive([(NAME+'/A',b'a',stat.S_IFREG),(NAME+'/a',b'b',stat.S_IFREG)]),NAME)
        stream=self.archive([(NAME+'/Contents/file',b'Inert.',stat.S_IFREG)])
        raw=stream.read();stream.seek(0);stream.write(raw+b'Unexpected trailing data.');stream.seek(0)
        with self.assertRaises(ValueError):validate_zip(stream,NAME)
        stream=self.archive([(NAME+'/Contents/file',b'Inert.',stat.S_IFREG)])
        raw=bytearray(stream.read());struct.pack_into('<I',raw,len(raw)-10,65*1024**2)
        stream.seek(0);stream.write(raw);stream.seek(0)
        with self.assertRaises(ValueError):validate_zip(stream,NAME)

    def test_real_zip64_locator_is_bounded_before_parsing(self):
        stream=self.archive([(NAME+'/Contents/file',b'Inert.',stat.S_IFREG)])
        raw=stream.read();tag,disk,start,on_disk,count,size,offset,comment=struct.unpack('<4s4H2IH',raw[-22:])
        position=len(raw)-22
        zip64=struct.pack('<4sQ2H2I4Q',b'PK\x06\x06',44,45,45,0,0,count,count,size,offset)
        locator=struct.pack('<4sIQI',b'PK\x06\x07',0,position,1)
        end=struct.pack('<4s4H2IH',tag,0,0,65535,65535,0xffffffff,0xffffffff,0)
        stream.seek(0);stream.write(raw[:-22]+zip64+locator+end);stream.seek(0)
        self.assertEqual(validate_zip(stream,NAME)['entries'],1)

    def test_reopening_names_cannot_be_commands_paths_or_mutated_aliases(self):
        original={'instances':['main','mobile'],'hadBrowser':False};captured=validate_plan(original)
        original['instances'].append('secondary');self.assertEqual(captured['instances'],['main','mobile'])
        for names in (['--command'],['../outside'],['main','main'],['main;open'],['a/b']):
            with self.subTest(names=names),self.assertRaises(ValueError):validate_plan({'instances':names,'hadBrowser':False})


if __name__=='__main__':unittest.main()
