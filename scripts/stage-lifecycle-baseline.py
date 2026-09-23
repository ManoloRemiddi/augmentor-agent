#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Stage pinned public 0.2.9 Debian packages for upgrade/rollback qualification."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.2.9'
PREFIX = 'augmentor-0.2.9-complete-preview.1/'
URL = ('https://github.com/ManoloRemiddi/augmentor-agent-app/releases/download/'
       'v0.2.9-complete-preview.1/augmentor-0.2.9-complete-preview.1.tar.gz')
SHA256 = '8149ac66866d79422cdcd84f672b228c4b6ac7db162e07eef846454e20035da4'
PACKAGES = {
    'augmentor-desktop_0.2.9_amd64.deb': '581099ffef589fc506f84b8dbe2493dd2fa82984f8b6ea58d8ba083edb1f93e0',
    'augmentor-runtime_0.2.9_amd64.deb': '359a00c835ff18b5cc5080ba44190f893784aa93d934d5a3ce018100346a9538',
}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stage(archive, output):
    # Check the complete known public artifact before reading any archive member.
    if digest(archive) != SHA256:
        raise ValueError('Public baseline archive checksum mismatch')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use an empty baseline output directory')
    with tempfile.TemporaryDirectory(prefix='augmentor-baseline-') as temporary:
        staged = Path(temporary)
        with tarfile.open(archive) as bundle:
            manifest = json.load(bundle.extractfile(PREFIX + 'bundle.json'))
            if manifest['version'] != VERSION or manifest['target'] != 'debian13-amd64':
                raise ValueError('Unexpected public baseline identity')
            artifacts = []
            for name, expected in PACKAGES.items():
                member = bundle.getmember(PREFIX + name)
                if not member.isfile() or manifest['sha256'].get(name) != expected:
                    raise ValueError('Unexpected public baseline package')
                target = staged / name
                with bundle.extractfile(member) as source, target.open('wb') as destination:
                    shutil.copyfileobj(source, destination)
                if digest(target) != expected:
                    raise ValueError('Public baseline package checksum mismatch')
                artifacts.append({'file': name, 'sha256': expected, 'bytes': target.stat().st_size})
        result = {
            'version': VERSION,
            'source': {'commit': manifest['sourceCommit'], 'dirty': False},
            'target': manifest['target'],
            'baseline': {'url': URL, 'sha256': SHA256},
            'artifacts': artifacts,
        }
        (staged / 'artifacts.json').write_text(json.dumps(result, indent=2) + '\n')
        output.mkdir(parents=True, exist_ok=True)
        for source in staged.iterdir():
            shutil.copy2(source, output / source.name)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Optional already-downloaded archive; the same checksum is required')
    parser.add_argument('--out', type=Path, default=ROOT / 'outputs' / 'baseline')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='augmentor-baseline-download-') as temporary:
        archive = args.archive
        if archive is None:
            archive = Path(temporary) / 'baseline.tar.gz'
            with urllib.request.urlopen(URL, timeout=60) as response, archive.open('wb') as destination:
                shutil.copyfileobj(response, destination)
        print(json.dumps(stage(archive, args.out), indent=2))


if __name__ == '__main__':
    main()
