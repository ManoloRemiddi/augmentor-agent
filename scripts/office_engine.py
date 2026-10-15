# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bind the exact Linux Office payload to its shipped source and licence records.

Private preview identity is distinct from permission to distribute this engine.
The entry has public preferred source; the engine rebuild gate remains open.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
ENGINE = 'node_modules/@deepseek-ai/libreoffice-kit-wasm'
ENTRY = 'dist/runtime/vendor/office-entry'
NOTICES = {
    'kit-LICENSE': (ENTRY, 'LICENSE'),
    'kit-NOTICE': (ENTRY, 'NOTICE'),
    'engine/LICENSE': (ENGINE, 'licenses/LICENSE'),
    'engine/NOTICE': (ENGINE, 'licenses/NOTICE'),
    'engine/DeepSeek-Harness-MIT.txt': (ENGINE, 'licenses/DeepSeek-Harness-MIT.txt'),
    'engine-manifest.json': (ENGINE, 'assets/manifest.json'),
}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def file_at(directory, name, expected=None):
    relative = PurePosixPath(name)
    if (not name or relative.is_absolute() or '..' in relative.parts or '\\' in name or
            relative.as_posix() != name):
        raise ValueError('Unsafe Office artifact path: ' + name)
    path = directory / name
    if (directory.is_symlink() or any((directory / Path(*relative.parts[:i])).is_symlink()
            for i in range(1, len(relative.parts) + 1)) or not path.is_file() or
            not path.resolve().is_relative_to(directory.resolve()) or
            expected is not None and sha(path) != expected):
        raise ValueError('Office artifact missing, linked or changed: ' + name)
    return path


def record(root=ROOT):
    path = file_at(root, 'release/office-engine-linux-wasm.json')
    item = json.loads(path.read_text())
    if (item.get('schema') != 'augmentor-office-engine/2' or
            item.get('package', {}).get('name') != '@deepseek-ai/libreoffice-kit-wasm' or
            item.get('package', {}).get('version') != '0.1.5' or
            item.get('entryPackage', {}).get('name') != '@augmentor/office-entry' or
            item.get('entryPackage', {}).get('version') != '0.1.3-augmentor.1' or
            any(item[key].get('license') != 'MPL-2.0' for key in ('package', 'entryPackage'))):
        raise ValueError('Unreviewed Office package identity')
    for files in (item.get('files', {}), item['entryPackage'].get('files', {})):
        if not files or any(not re.fullmatch(r'[a-f0-9]{64}', value) for value in files.values()):
            raise ValueError('Office file inventory is missing or invalid')
    if (not {'assets/manifest.json', 'assets/soffice.wasm', 'licenses/LICENSE', 'licenses/NOTICE',
            'sources/engine/wasm-source/lok.cxx', 'sources/source-changes.patch'}.issubset(item['files']) or
            not {'package.json', 'LICENSE', 'NOTICE', 'index.js', 'worker.js', 'UPSTREAM.json',
                 'SOURCE.json', 'preferred-source/index.ts', 'preferred-source/engine.ts',
                 'build-support/package-lock.json', 'build-support/build-office-entry.mjs'
                 }.issubset(item['entryPackage']['files'])):
        raise ValueError('Office source/notice inventory is incomplete')
    return item


def validate_inputs(app, root=ROOT):
    item = record(root)
    lock = json.loads(file_at(app, 'package-lock.json').read_text())['packages']
    for directory, pin, files in ((ENGINE, item['package'], item['files']),
            (ENTRY, item['entryPackage'], item['entryPackage']['files'])):
        package = app / directory
        file_at(app, directory + '/package.json', files['package.json'])
        meta = json.loads((package / 'package.json').read_text())
        locked = lock.get(directory, {})
        if (any(meta.get(key) != pin[key] for key in ('name', 'version', 'license')) or
                directory == ENGINE and any(locked.get(key) != pin[key]
                                             for key in ('version', 'license', 'integrity'))):
            raise ValueError('Office installed package differs from the reviewed lock: ' + directory)
        actual = set()
        for path in package.rglob('*'):
            relative = path.relative_to(package)
            if path.is_symlink():
                raise ValueError('Linked Office package content: ' + relative.as_posix())
            if path.is_file():
                actual.add(relative.as_posix())
        if actual != set(files):
            raise ValueError('Office package file inventory changed: ' + directory)
        for name, expected in files.items():
            file_at(app, directory + '/' + name, expected)
    if sha(app / 'package-lock.json') != sha(app / ENTRY / 'build-support/package-lock.json'):
        raise ValueError('Office source build and installed dependency locks differ')
    entry_source = json.loads((app / ENTRY / 'SOURCE.json').read_text())
    preferred = json.loads((app / ENTRY / 'UPSTREAM.json').read_text())
    if (entry_source.get('schema') != 'augmentor-built-office-entry/1' or
            entry_source.get('files') != {name: digest
                for name, digest in item['entryPackage']['files'].items() if name != 'SOURCE.json'} or
            preferred.get('commit') != item['entryPackage']['sourceCommit'] or
            preferred.get('archiveSha256') != item['entryPackage']['sourceArchiveSha256'] or
            len(preferred.get('files', [])) != 32):
        raise ValueError('Office entry preferred source/build identity changed')
    for row in preferred['files']:
        file_at(app, ENTRY + '/' + row['path'], row['sha256'])
    manifest = json.loads((app / ENGINE / 'assets/manifest.json').read_text())
    if (any(manifest.get(key) != value for key, value in item['engine'].items()) or
            manifest.get('inputs', {}).get('source') != item['source'] or
            manifest.get('files') != {PurePosixPath(name).name: digest
                for name, digest in item['files'].items()
                if name.startswith('assets/') and name != 'assets/manifest.json'}):
        raise ValueError('Office engine/source identity differs from its manifest')
    return item


def exports(item):
    return {**NOTICES, **{name: (ENGINE, name) for name in item['files'] if name.startswith('sources/')},
            **{'entry/' + name: (ENTRY, name) for name in item['entryPackage']['files']}}


def component(item):
    return {'component': 'libreoffice-wasm', 'version': item['package']['version'],
            'engineVersion': item['engine']['version'], 'path': ENGINE + '/assets/soffice.wasm',
            'sha256': item['files']['assets/soffice.wasm'],
            'notices': ['office-engine/BUILD.json', *('office-engine/' + name for name in sorted(exports(item)))],
            'publicRedistributionQualified': False,
            'entryComponent': {'name': item['entryPackage']['name'],
                'version': item['entryPackage']['version'], 'license': 'MPL-2.0',
                'preferredSourceFiles': 32, 'sourceBuilt': True},
            'scope': 'Source-built entry plus exact private-preview engine and source/notice identities.'}


def stage_entry(app, root=ROOT):
    """Copy the reviewed compiled/source component before production notice staging."""
    item = record(root)
    for name, expected in item['entryPackage']['files'].items():
        file_at(root, ENTRY + '/' + name, expected)
    target = app / ENTRY
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(root / ENTRY, target)


def stage_engine(app, root=ROOT):
    item = validate_inputs(app, root)
    directory = app / 'licenses/office-engine'
    if (app / 'licenses').is_symlink():
        raise ValueError('Linked Office notice directory')
    directory.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(root / 'release/office-engine-linux-wasm.json', directory / 'BUILD.json')
    for name, (package, source) in exports(item).items():
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(app / package / source, target)
    (directory / 'native-component.json').write_text(json.dumps(component(item), indent=2) + '\n')
    return validate_bundle(app, root, require_public=False)


def validate_bundle(app, root=ROOT, *, require_public=True):
    item = validate_inputs(app, root)
    directory = app / 'licenses/office-engine'
    file_at(app, 'licenses/office-engine/BUILD.json', sha(root / 'release/office-engine-linux-wasm.json'))
    expected = exports(item)
    for name, (package, source) in expected.items():
        file_at(app, 'licenses/office-engine/' + name, sha(app / package / source))
    actual = set()
    for path in directory.rglob('*'):
        if path.is_symlink():
            raise ValueError('Linked Office source/notice content')
        if path.is_file():
            actual.add(path.relative_to(directory).as_posix())
    if actual != {'BUILD.json', 'native-component.json', *expected}:
        raise ValueError('Office source/notice export inventory changed')
    result = component(item)
    if json.loads(file_at(app, 'licenses/office-engine/native-component.json').read_text()) != result:
        raise ValueError('Office native component inventory differs from reviewed inputs')
    if require_public:
        raise ValueError('Office public source/rebuild qualification remains open: '
                         'the exact engine rebuild is not qualified. '
                         'Private-preview identity is not public redistribution approval.')
    return result
