# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Synthetic descriptor/path refusal cases, separate from the real base export."""
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('base_archive', Path(__file__).resolve().parents[1] / 'release/verify-ubuntu-base-archive.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(path, change=None):
    files = {}
    plain = b'synthetic rootfs bytes; never an executable image'
    def blob(value, kind):
        data = value if isinstance(value, bytes) else json.dumps(value).encode()
        digest = hashlib.sha256(data).hexdigest()
        files['blobs/sha256/' + digest] = data
        return {'digest': 'sha256:' + digest, 'size': len(data), 'mediaType': kind}
    layer = blob(gzip.compress(plain), 'application/vnd.oci.image.layer.v1.tar+gzip')
    config = blob({'os': 'linux', 'architecture': 'amd64', 'rootfs': {'type': 'layers',
        'diff_ids': ['sha256:' + hashlib.sha256(plain).hexdigest()]}}, 'application/vnd.oci.image.config.v1+json')
    manifest = blob({'schemaVersion': 2, 'config': config, 'layers': [layer]}, 'application/vnd.oci.image.manifest.v1+json')
    manifest['platform'] = {'architecture': 'amd64', 'os': 'linux'}
    root = blob({'schemaVersion': 2, 'manifests': [manifest]}, 'application/vnd.oci.image.index.v1+json')
    files['index.json'] = json.dumps({'schemaVersion': 2, 'manifests': [root]}).encode()
    files['oci-layout'] = b'{"imageLayoutVersion":"1.0.0"}'
    files['manifest.json'] = json.dumps([{'Config': 'blobs/sha256/' + config['digest'][7:],
        'Layers': ['blobs/sha256/' + layer['digest'][7:]], 'RepoTags': None}]).encode()
    if change:
        change(files)
    with tarfile.open(path, 'w') as bundle:
        for name, data in files.items():
            member = tarfile.TarInfo(name)
            member.size = len(data)
            bundle.addfile(member, io.BytesIO(data))
    return root['digest'][7:]


class BaseArchiveTests(unittest.TestCase):
    def test_synthetic_chain_validates_without_import_or_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'base.tar'
            root = fixture(path)
            result = module.verify(path, root)
            self.assertFalse(result['dockerImportExecuted'])
            self.assertFalse(result['rootfsExtracted'])
            self.assertFalse(result['fullSourceKitQualified'])

    def test_wrong_public_index_pin_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'base.tar'
            fixture(path)
            with self.assertRaisesRegex(ValueError, 'index differs'):
                module.verify(path)  # CLI pin cannot be replaced with a test image.

    def test_changed_blob_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'base.tar'
            root = fixture(path, lambda files: files.__setitem__(next(iter(files)), b'corrupt'))
            with self.assertRaisesRegex(ValueError, 'blob differs'):
                module.verify(path, root)

    def test_unpinned_docker_mapping_and_repo_tag_refused(self):
        for mapping in ([{'Config': 'elsewhere', 'Layers': [], 'RepoTags': None}],
                        [{'Config': 'elsewhere', 'Layers': [], 'RepoTags': ['owner/image:latest']}]):
            with self.subTest(mapping=mapping), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'base.tar'
                root = fixture(path, lambda files: files.__setitem__('manifest.json', json.dumps(mapping).encode()))
                with self.assertRaisesRegex(ValueError, 'mapping differs'):
                    module.verify(path, root)

    def test_unsafe_member_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'base.tar'
            root = fixture(path, lambda files: files.__setitem__('../escape', b'no'))
            with self.assertRaisesRegex(ValueError, 'unsafe member'):
                module.verify(path, root)
            self.assertFalse((Path(directory).parent / 'escape').exists())

    def test_duplicate_member_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'base.tar'
            root = fixture(path)
            with tarfile.open(path, 'a') as bundle:
                member = tarfile.TarInfo('index.json')
                member.size = 2
                bundle.addfile(member, io.BytesIO(b'{}'))
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                module.verify(path, root)


if __name__ == '__main__':
    unittest.main()
