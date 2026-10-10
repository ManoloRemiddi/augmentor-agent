# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Verify and stage the reviewed codemode engine on every product platform."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
NOTICES = {
    'quickjs-wasi-MIT.txt', 'quickjs-ng-MIT.txt', 'wasi-libc-LICENSE.txt',
    'wasi-libc-APACHE.txt', 'wasi-libc-APACHE-LLVM.txt', 'wasi-libc-MIT.txt',
    'musl-COPYRIGHT.txt', 'cloudlibc-BSD-2.txt', 'dlmalloc-malloc.c',
    'emmalloc.c', 'musl-fts-BSD-3.txt', 'LLVM-LICENSE.txt', 'compiler-rt-LICENSE.txt',
    'components.json', 'link-extraction.tsv', 'build-log.txt', 'wasm-abi.json',
}
FILES = {'quickjs.wasm', *('third-party/' + name for name in NOTICES),
         *('sources/' + name + '.tar.gz' for name in ('quickjs-wasi', 'quickjs-ng', 'wasi-libc', 'llvm-builtins'))}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verified_file(directory, name, expected):
    relative = PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name:
        raise ValueError('Unsafe QuickJS artifact path')
    path = directory / name
    if (directory.is_symlink() or any((directory / Path(*relative.parts[:i])).is_symlink() for i in range(1, len(relative.parts) + 1)) or
            not path.is_file() or not path.resolve().is_relative_to(directory.resolve()) or sha(path) != expected):
        raise ValueError('QuickJS artifact missing, linked or changed: ' + name)
    return path


def reviewed(root=ROOT):
    config = json.loads((root / 'release/quickjs/build.json').read_text())
    pin = json.loads((root / 'release/quickjs/artifact.json').read_text())
    vendor = root / 'vendor/quickjs-engine'
    if (root / 'vendor').is_symlink() or any(path.is_symlink() for path in vendor.rglob('*')):
        raise ValueError('Linked QuickJS vendor content is not a reviewed artifact')
    if pin.get('schema') != 'augmentor-quickjs-artifact/1' or set(pin.get('files', {})) != FILES | {'BUILD.json'}:
        raise ValueError('QuickJS artifact/notice inventory changed; review distribution')
    for name, expected in pin['files'].items():
        verified_file(vendor, name, expected)
    if {path.relative_to(vendor).as_posix() for path in vendor.rglob('*') if path.is_file()} != set(pin['files']):
        raise ValueError('Unexpected file in reviewed QuickJS artifact')
    record = json.loads((vendor / 'BUILD.json').read_text())
    if (config.get('schema') != 'augmentor-quickjs-build/1' or
            any(record.get(key) != value for key, value in config.items()) or
            record.get('files') != {name: digest for name, digest in pin['files'].items() if name != 'BUILD.json'} or
            record['files']['quickjs.wasm'] != config['expectedWasmSha256']):
        raise ValueError('QuickJS source/build/artifact records differ; rebuild and review')
    return vendor, record


def resolve_engine(app, record):
    sdk = app / 'node_modules/@earendil-works/pi-coding-agent/package.json'
    if json.loads(sdk.read_text())['version'] != record['piVersion']:
        raise ValueError('Unreviewed Pi codemode dependency layout')
    # Select the import export condition used by Pi's ESM module, then resolve
    # QuickJS from codemode itself. SDK-root resolution alone can miss nesting.
    paths = json.loads(subprocess.check_output(['node', '--conditions=import', '--input-type=module', '-e',
        'import {createRequire} from "node:module"; const r=createRequire(process.argv[1]);'
        'const c=r.resolve("@earendil-works/pi-codemode"); const q=createRequire(c);'
        'console.log(JSON.stringify([c,q.resolve("quickjs-wasi/package.json"),q.resolve("quickjs-wasi/quickjs.wasm")]));',
        str(sdk)], text=True, encoding='utf-8'))
    codemode, metadata, wasm = map(Path, paths)
    modules = app / 'node_modules'
    if not all(path.resolve().is_relative_to(modules.resolve()) for path in (codemode, metadata, wasm)):
        raise ValueError('QuickJS resolution escaped production dependencies')
    owner = json.loads((codemode.parent.parent / 'package.json').read_text())
    package = json.loads(metadata.read_text())
    if (owner.get('name') != '@earendil-works/pi-codemode' or owner.get('version') != record['piVersion'] or
            package.get('name') != 'quickjs-wasi' or package.get('version') != record['npmVersion'] or
            wasm != metadata.parent / 'quickjs.wasm'):
        raise ValueError('QuickJS/codemode package identity changed')
    return wasm


def component(app, wasm, record):
    return {'component': 'quickjs', 'version': record['npmVersion'], 'path': wasm.relative_to(app).as_posix(),
            'sha256': record['files']['quickjs.wasm'],
            'notices': ['quickjs/BUILD.json', *('quickjs/' + name for name in sorted(FILES - {'quickjs.wasm'}))]}


def stage_engine(app, excluded, root=ROOT):
    vendor, record = reviewed(root)
    wasm = resolve_engine(app, record); package = wasm.parent
    if package.is_symlink() or any(path.is_symlink() for path in package.rglob('*')) or (app / 'licenses').is_symlink():
        raise ValueError('Linked QuickJS staging content is not a reviewed input')
    if sha(wasm) != record['originalNpmWasmSha256']:
        raise ValueError('Published QuickJS engine differs from the reviewed npm input')
    assets = {path.relative_to(package).as_posix(): path for path in (package / 'extensions').glob('*/*.so')}
    if set(assets) != set(record['excludedAssets']):
        raise ValueError('QuickJS optional extension inventory changed')
    for name, path in sorted(assets.items()):
        if path.is_symlink() or sha(path) != record['excludedAssets'][name] or path.read_bytes()[:4] != b'\x00asm':
            raise ValueError('QuickJS optional extension differs: ' + name)
        excluded.append({'name': 'quickjs-wasi', 'version': record['npmVersion'],
                         'path': path.relative_to(app).as_posix(), 'sha256': record['excludedAssets'][name],
                         'reason': 'optional WASM extension; Pi codemode does not load it; excluded from the qualified minimal engine'})
        path.unlink()
    shutil.copyfile(vendor / 'quickjs.wasm', wasm)
    shutil.copytree(vendor, app / 'licenses/quickjs', ignore=shutil.ignore_patterns('quickjs.wasm'))
    item = component(app, wasm, record)
    (app / 'licenses/quickjs/native-component.json').write_text(json.dumps(item, indent=2) + '\n')
    validate_bundle(app, root)
    return {'npmVersion': record['npmVersion'], 'sources': record['sources'],
            'originalWasmSha256': record['originalNpmWasmSha256'], 'wasmSha256': record['files']['quickjs.wasm'],
            'changes': record['changes']}


def validate_bundle(app, root=ROOT):
    vendor, record = reviewed(root)
    directory = app / 'licenses/quickjs'
    if (app / 'licenses').is_symlink() or any(path.is_symlink() for path in directory.rglob('*')):
        raise ValueError('Linked QuickJS source/notice content is not a reviewed bundle')
    verified_file(directory, 'BUILD.json', sha(vendor / 'BUILD.json'))
    wasm = resolve_engine(app, record)
    for name, expected in record['files'].items():
        verified_file(wasm.parent if name == 'quickjs.wasm' else directory, name, expected)
    if {path.relative_to(directory).as_posix() for path in directory.rglob('*') if path.is_file()} != (FILES - {'quickjs.wasm'}) | {'BUILD.json', 'native-component.json'}:
        raise ValueError('Unexpected file in packaged QuickJS source/notices')
    if any((wasm.parent / 'extensions').glob('*/*.so')):
        raise ValueError('Unqualified QuickJS extensions remain in distribution')
    for path in wasm.parent.rglob('*'):
        if path.is_symlink():
            raise ValueError('Linked asset in QuickJS package')
        if not path.is_file():
            continue
        with path.open('rb') as stream:
            magic = stream.read(4)
        if path != wasm and (magic in (b'\x00asm', b'\x7fELF', b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf') or magic.startswith(b'MZ')):
            raise ValueError('Unreviewed native asset in QuickJS package')
    item = component(app, wasm, record)
    if json.loads((directory / 'native-component.json').read_text()) != item:
        raise ValueError('QuickJS native inventory differs from the reviewed bundle')
    return item
