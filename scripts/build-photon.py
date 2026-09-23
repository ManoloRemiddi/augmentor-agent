#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Rebuild the required Photon image module with a locked, licensed Rust graph.

Requires the pinned Rust toolchain and wasm32 target. Output is a reviewed vendor
artifact; normal package builds verify its hashes instead of compiling Rust.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'MIT', 'Apache-2.0', 'BSD-3-Clause', 'Zlib', 'MIT OR Apache-2.0', 'Apache-2.0 OR MIT',
           'MIT/Apache-2.0', 'Apache-2.0/MIT', 'MIT / Apache-2.0', '0BSD OR MIT OR Apache-2.0',
           'Zlib OR Apache-2.0 OR MIT', 'Unlicense OR MIT', 'MIT OR Zlib OR Apache-2.0',
           '(MIT OR Apache-2.0) AND Unicode-3.0', 'BSD-2-Clause OR Apache-2.0 OR MIT'}


def sha(path):
    with path.open('rb') as source: return hashlib.file_digest(source, 'sha256').hexdigest()


def download(item, target):
    if not target.exists():
        temporary = target.with_suffix('.download')
        with urllib.request.urlopen(item['url'], timeout=60) as source, temporary.open('wb') as out:
            shutil.copyfileobj(source, out)
        temporary.replace(target)
    if sha(target) != item['sha256']: raise ValueError('Unverified download: ' + str(target))
    return target


def collect_licenses(metadata, source, sysroot, out, configuration):
    nodes = {row['id']: row for row in metadata['resolve']['nodes']}
    packages = {row['id']: row for row in metadata['packages']}
    todo = [key for key, row in packages.items() if row['name'] == 'photon-rs']; seen = set()
    while todo:
        key = todo.pop()
        if key in seen: continue
        seen.add(key)
        for edge in nodes[key]['deps']:
            if any(kind['kind'] in (None, 'build') for kind in edge['dep_kinds']): todo.append(edge['pkg'])
    directory = out / 'third-party'; directory.mkdir()
    components = []
    for key in sorted(seen, key=lambda value: (packages[value]['name'], packages[value]['version'])):
        row = packages[key]
        if row['license'] not in ALLOWED: raise ValueError('Unreviewed Rust license: ' + row['name'] + ' ' + str(row['license']))
        package = Path(row['manifest_path']).parent
        files = [path for path in sorted(package.iterdir()) if path.is_file() and re.match(r'(licen[sc]e|copying|unlicense|notice)', path.name, re.I)]
        if not files: raise ValueError('Missing Rust license text: ' + row['name'])
        notices = []
        for file in files:
            name = sha(file) + '.txt'; shutil.copyfile(file, directory / name)
            notices.append(name)
        components.append({'name': row['name'], 'version': row['version'], 'license': row['license'],
                           'source': configuration['source']['url'] if row['name'] == 'photon-rs' else f'https://crates.io/api/v1/crates/{row["name"]}/{row["version"]}/download',
                           'notices': notices})
    shutil.copyfile(sysroot / 'share/doc/rust/COPYRIGHT-library.html', directory / 'rust-standard-library.html')
    shutil.copyfile(source / 'crate/fonts/Apache License.txt', directory / 'roboto-license.txt')
    (directory / 'roboto-copyright.txt').write_text('Roboto-Regular.ttf\nCopyright 2011 Google Inc. All Rights Reserved.\nLicensed under the Apache License, Version 2.0\nhttp://www.apache.org/licenses/LICENSE-2.0\n')
    (directory / 'components.json').write_text(json.dumps({'rust': configuration['rust'], 'components': components,
        'standardLibraryNotices': 'rust-standard-library.html',
        'font': {'name': 'Roboto-Regular.ttf', 'sha256': sha(source / 'crate/fonts/Roboto-Regular.ttf'),
                 'notices': ['roboto-copyright.txt', 'roboto-license.txt']}}, indent=2) + '\n')
    return len(components)


def build(out):
    config = json.loads((ROOT / 'release/photon/build.json').read_text())
    compiler = subprocess.check_output(['rustc', '+' + config['rust'], '--version'], text=True).strip()
    if not compiler.startswith('rustc ' + config['rust'] + ' '): raise ValueError('Unexpected Rust compiler')
    sysroot = Path(subprocess.check_output(['rustc', '+' + config['rust'], '--print', 'sysroot'], text=True).strip())
    cache = ROOT / 'outputs/photon-build-cache'; cache.mkdir(parents=True, exist_ok=True)
    archive = download(config['source'], cache / 'source.tar.gz')
    cli_archive = download(config['wasmBindgen'], cache / 'wasm-bindgen.tar.gz')
    with tempfile.TemporaryDirectory(prefix='photon-build-') as temporary:
        workspace = Path(temporary); source = workspace / 'source'; source.mkdir()
        with tarfile.open(archive) as bundle:
            prefix = bundle.getmembers()[0].name + '/'
            for member in bundle.getmembers():
                if not member.name.startswith(prefix): continue
                member.name = member.name[len(prefix):]
                if member.name: bundle.extract(member, source, filter='data')
        manifest = source / 'crate/Cargo.toml'; text = manifest.read_text()
        changes = [('wasm-bindgen = { version = "0.2.92"', 'wasm-bindgen = { version = "=0.2.100"'),
                   ('js-sys = { version = "0.3.62"', 'js-sys = { version = "=0.3.77"'),
                   ('[dependencies.web-sys]\nversion = "0.3"', '[dependencies.web-sys]\nversion = "=0.3.77"')]
        for before, after in changes:
            if text.count(before) != 1: raise ValueError('Photon source changed at binding constraints')
            text = text.replace(before, after)
        manifest.write_text(text); shutil.copyfile(ROOT / 'release/photon/Cargo.lock', source / 'Cargo.lock')
        with tarfile.open(cli_archive) as bundle: bundle.extractall(workspace / 'cli', filter='data')
        cli = next((workspace / 'cli').glob('*/wasm-bindgen'))
        env = {**os.environ, 'CARGO_BUILD_JOBS': '2', 'CARGO_TARGET_DIR': str(cache / 'target'),
               'RUSTFLAGS': f'--remap-path-prefix={source}=/photon --remap-path-prefix={Path.home() / ".cargo"}=/cargo'}
        cargo = ['cargo', '+' + config['rust']]
        subprocess.run(cargo + ['build', '--manifest-path', str(manifest), '--target', 'wasm32-unknown-unknown', '--release', '--lib', '--locked'], env=env, check=True)
        metadata = json.loads(subprocess.check_output(cargo + ['metadata', '--manifest-path', str(manifest), '--locked', '--filter-platform', 'wasm32-unknown-unknown', '--format-version', '1'], env=env, text=True))
        stage = workspace / 'module'
        subprocess.run([str(cli), str(cache / 'target/wasm32-unknown-unknown/release/photon_rs.wasm'), '--target', 'nodejs', '--out-name', 'photon_rs', '--out-dir', str(stage)], check=True)
        for file in stage.glob('*.js'):
            file.write_text('// Photon by Silvia O\'Dwyer, Apache-2.0; see LICENSE.md.\n// Rebuilt by Augmentor; source, changes and dependencies are recorded in BUILD.json.\n' + file.read_text())
        upstream = ROOT / 'node_modules/@earendil-works/pi-coding-agent/node_modules/@silvia-odwyer/photon-node'
        for name in ('package.json', 'LICENSE.md'): shutil.copyfile(upstream / name, stage / name)
        count = collect_licenses(metadata, source, sysroot, stage, config)
        record = {**config, 'compiler': compiler, 'cargoLockSha256': sha(source / 'Cargo.lock'),
                  'changes': 'Pinned binding versions; generated paired Node.js glue/WASM with locked dependencies and normalized source paths.',
                  'files': {p.relative_to(stage).as_posix(): sha(p) for p in sorted(stage.rglob('*')) if p.is_file()}}
        (stage / 'BUILD.json').write_text(json.dumps(record, indent=2) + '\n')
        if out.exists():
            if not (out / 'BUILD.json').exists(): raise ValueError('Refusing to replace an unrelated directory: ' + str(out))
            shutil.rmtree(out)
        out.parent.mkdir(parents=True, exist_ok=True); shutil.copytree(stage, out)
        print(f'Rebuilt Photon with notices for {count} Rust packages: {out}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'vendor/photon-node')
    args = parser.parse_args(); build(args.out.resolve())
