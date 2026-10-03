# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Published source reuse must verify bytes without reading supplier repositories."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('complete_package',ROOT/'scripts/package-complete.py')
package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)


class PublishedSourceReuse(unittest.TestCase):
    def fixture(self,bundle):
        (bundle/'sources').mkdir()
        manifest={'format':'augmentor-complete/1','artifactId':'synthetic-published-bundle',
                  'sourceRefs':{'voice':'a'*40,'adaptive':'b'*40},'sha256':{}}
        for name in ('resonant-voice-0.1.19','adaptive-reasoning-0.2.3'):
            key='sources/'+name+'-source.tar.gz'
            content=('Synthetic public snapshot '+name).encode()
            (bundle/key).write_bytes(content)
            manifest['sha256'][key]=hashlib.sha256(content).hexdigest()
        (bundle/'bundle.json').write_text(json.dumps(manifest))
        return manifest

    def test_checked_snapshots_and_refs_are_reused_without_git_access(self):
        with tempfile.TemporaryDirectory() as folder:
            bundle=Path(folder)/'bundle';bundle.mkdir();out=Path(folder)/'out';out.mkdir()
            manifest=self.fixture(bundle)
            with patch.object(package.subprocess,'check_output',side_effect=AssertionError('Repository access')),patch.object(package.subprocess,'run',side_effect=AssertionError('Repository access')):
                refs,origin,coverage=package.reuse_sources(bundle,out)
            self.assertEqual(refs,manifest['sourceRefs'])
            self.assertEqual(origin['artifactId'],manifest['artifactId'])
            self.assertEqual(origin['manifestSha256'],package.sha(bundle/'bundle.json'))
            self.assertEqual(origin['rolesReused'],['voice','adaptive'])
            self.assertEqual({row['kind'] for row in coverage.values()},{'published-repository-source-snapshot'})
            for key in manifest['sha256']:
                self.assertEqual((out/Path(key).name).read_bytes(),(bundle/key).read_bytes())

    def test_changed_archive_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            bundle=Path(folder);manifest=self.fixture(bundle);out=bundle/'out';out.mkdir()
            first=next(iter(manifest['sha256']))
            (bundle/first).write_bytes(b'Changed synthetic snapshot')
            with self.assertRaisesRegex(ValueError,'checksum'):
                package.reuse_sources(bundle,out)
            self.assertEqual(list(out.iterdir()),[])

    def test_unknown_format_and_malformed_source_refs_are_refused(self):
        for changes in ({'format':'unknown'},{'sourceRefs':{'voice':'not-a-commit','adaptive':'b'*40}}):
            with self.subTest(changes=changes),tempfile.TemporaryDirectory() as folder:
                bundle=Path(folder);manifest=self.fixture(bundle);out=bundle/'out';out.mkdir()
                manifest.update(changes);(bundle/'bundle.json').write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):package.reuse_sources(bundle,out)


if __name__=='__main__':unittest.main()
