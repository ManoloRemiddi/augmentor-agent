#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Rebuild the minimal codemode engine with pinned sources, tools and notices.

Build on Linux x64. Normal platform packagers verify the retained artifact; they
do not download this toolchain or build optional QuickJS extensions.
"""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def download(item, path):
    if not path.exists():
        pending = path.with_suffix('.download')
        with urllib.request.urlopen(item['url'], timeout=60) as source, pending.open('wb') as target:
            shutil.copyfileobj(source, target)
        pending.replace(path)
    if sha(path) != item['sha256']:
        raise ValueError('Source/tool checksum differs: ' + path.name)
    return path


def extract(archive, target):
    target.mkdir()
    with tarfile.open(archive) as source:
        source.extractall(target, filter='data')
    entries = list(target.iterdir())
    if len(entries) != 1 or not entries[0].is_dir():
        raise ValueError('Expected one source directory: ' + archive.name)
    return entries[0]


def export_llvm(checkout, commit, paths, target):
    rows = subprocess.check_output(['git', '-C', str(checkout), 'ls-tree', '-rz', commit, '--', *paths])
    with target.open('wb') as output, gzip.GzipFile(filename='', fileobj=output, mode='wb', mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w') as archive:
            for row in rows.split(b'\0'):
                if not row:
                    continue
                metadata, name = row.split(b'\t', 1)
                mode, kind, oid = metadata.split()
                path = checkout / name.decode()
                if kind != b'blob' or mode not in (b'100644', b'100755', b'120000'):
                    raise ValueError('Unexpected LLVM source tree member')
                data = os.readlink(path).encode() if mode == b'120000' else path.read_bytes()
                identity = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
                if identity != oid.decode():
                    raise ValueError('LLVM source differs from pinned Git blob: ' + name.decode())
                info = tarfile.TarInfo(name.decode()); info.mode = int(mode, 8) & 0o777
                if mode == b'120000':
                    info.type = tarfile.SYMTYPE; info.linkname = data.decode()
                    archive.addfile(info)
                else:
                    info.size = len(data); archive.addfile(info, io.BytesIO(data))


def llvm_archive(config, cache):
    item = config['llvmBuiltins']; checkout = cache / 'llvm-project'
    if not checkout.exists():
        subprocess.run(['git', 'init', str(checkout)], check=True)
        subprocess.run(['git', '-C', str(checkout), 'remote', 'add', 'origin', item['repository']], check=True)
        subprocess.run(['git', '-C', str(checkout), 'fetch', '--depth=1', '--filter=blob:none', 'origin', item['commit']], check=True)
        subprocess.run(['git', '-C', str(checkout), 'sparse-checkout', 'init', '--cone'], check=True)
        subprocess.run(['git', '-C', str(checkout), 'sparse-checkout', 'set', 'compiler-rt/lib/builtins'], check=True)
        subprocess.run(['git', '-C', str(checkout), 'checkout', '--detach', item['commit']], check=True)
    if subprocess.check_output(['git', '-C', str(checkout), 'remote', 'get-url', 'origin'], text=True).strip() != item['repository']:
        raise ValueError('LLVM cache origin differs')
    if subprocess.check_output(['git', '-C', str(checkout), 'status', '--porcelain'], text=True).strip():
        raise ValueError('LLVM source cache must be clean')
    # Git archive can fetch every blob in a partial clone. Instead export only
    # selected tracked files, verifying each against the pinned Git tree.
    path = cache / 'llvm-builtins-source.tar.gz'
    pending = path.with_suffix('.download')
    export_llvm(checkout, item['commit'], item['paths'], pending)
    if sha(pending) != item['archiveSha256']:
        raise ValueError('LLVM source archive differs from its reviewed tree export')
    pending.replace(path)
    return path


def collect(source, libc, llvm, sdk, log, config, stage, archives):
    notices = stage / 'third-party'; notices.mkdir()
    selected = {
        'quickjs-wasi-MIT.txt': source / 'LICENSE',
        'quickjs-ng-MIT.txt': source / 'quickjs-ng/LICENSE',
        'wasi-libc-LICENSE.txt': libc / 'LICENSE',
        'wasi-libc-APACHE.txt': libc / 'LICENSE-APACHE',
        'wasi-libc-APACHE-LLVM.txt': libc / 'LICENSE-APACHE-LLVM',
        'wasi-libc-MIT.txt': libc / 'LICENSE-MIT',
        'musl-COPYRIGHT.txt': libc / 'libc-top-half/musl/COPYRIGHT',
        'cloudlibc-BSD-2.txt': libc / 'libc-bottom-half/cloudlibc/LICENSE',
        'dlmalloc-malloc.c': libc / 'dlmalloc/src/malloc.c',
        'emmalloc.c': libc / 'emmalloc/emmalloc.c',
        'musl-fts-BSD-3.txt': libc / 'fts/musl-fts/COPYING',
        'LLVM-LICENSE.txt': llvm / 'LICENSE.TXT',
        'compiler-rt-LICENSE.txt': llvm / 'compiler-rt/LICENSE.TXT',
    }
    for name, path in selected.items():
        shutil.copyfile(path, notices / name)
    sources = stage / 'sources'; sources.mkdir()
    for name, archive in archives.items():
        shutil.copyfile(archive, sources / (name + '.tar.gz'))

    def normalize(text):
        for path, label in [(sdk, '$SDK'), (sdk.resolve(), '$SDK'), (source, '$SOURCE'), (source.parent, '$BUILD')]:
            text = text.replace(str(path), label)
        return text

    raw = (source / 'quickjs-extract.tsv').read_text()
    (notices / 'link-extraction.tsv').write_text(normalize(raw))
    members = {}; inputs = {}
    for line in raw.splitlines()[1:]:
        reference, extracted, symbol = line.split('\t')
        match = re.fullmatch(r'(.*\.a)\(([^)]+)\)', extracted)
        if not match:
            raise ValueError('Unexpected linker extraction: ' + extracted)
        archive, member = Path(match[1]), match[2]
        if not archive.resolve().is_relative_to(sdk.resolve()):
            raise ValueError('Linker used an unowned SDK archive')
        relative = archive.resolve().relative_to(sdk.resolve()).as_posix()
        inputs[relative] = sha(archive)
        members.setdefault(relative, set()).add(member)
    # --trace also records the direct reactor input omitted by --why-extract.
    for line in log.read_text().splitlines():
        if not line.startswith(str(sdk) + '/') or ' ' in line:
            continue
        path = Path(line.split('(', 1)[0])
        if path.suffix in ('.o', '.a') and path.is_file() and path.resolve().is_relative_to(sdk.resolve()):
            inputs[path.resolve().relative_to(sdk.resolve()).as_posix()] = sha(path)
    if not any(path.endswith('/crt1-reactor.o') for path in inputs):
        raise ValueError('Link trace is missing the reactor startup input')
    if not any(path.endswith('/libc.a') for path in members) or not any(path.endswith('/libclang_rt.builtins.a') for path in members):
        raise ValueError('Link extraction no longer has the reviewed libc/builtins shape')
    builtins = [name for path, names in members.items() if path.endswith('/libclang_rt.builtins.a') for name in sorted(names)]
    origins = {}
    for member in builtins:
        if member == 'math-builtins.c.obj':
            origin = libc / 'libc-bottom-half/sources/math/math-builtins.c'
            origins[member] = {'component': 'wasi-libc', 'path': origin.relative_to(libc).as_posix(), 'sha256': sha(origin)}
        else:
            origin = llvm / 'compiler-rt/lib/builtins' / member.removesuffix('.obj')
            origins[member] = {'component': 'compiler-rt', 'path': origin.relative_to(llvm).as_posix(), 'sha256': sha(origin)}
    components = {
        'schema': 'augmentor-quickjs-static-sources/1',
        'sdkInputs': inputs,
        'extractedMembers': {path: sorted(names) for path, names in sorted(members.items())},
        'builtinsSourceOrigins': origins,
        'sources': config['sources'], 'llvmBuiltins': config['llvmBuiltins'],
        'notices': sorted(selected),
        'coverage': 'Complete pinned QuickJS/QuickJS-NG/wasi-libc source archives, LLVM builtins subtree and original notices. Extraction is pre-LTO evidence, not proof every extracted function survives optimization. musl, cloudlibc and dlmalloc notices cover libc; emmalloc/fts notices conservatively accompany the complete wasi-libc source archive. SDK libraries are verified release inputs, not independently rebuilt here.',
    }
    (notices / 'components.json').write_text(json.dumps(components, indent=2) + '\n')
    (notices / 'build-log.txt').write_text(normalize(log.read_text()))


def build(out, cache):
    if sys.platform != 'linux' or os.uname().machine != 'x86_64':
        raise ValueError('The reviewed source-build toolchain is Linux x64; packaging the retained WASM is portable')
    config = json.loads((ROOT / 'release/quickjs/build.json').read_text())
    cache.mkdir(parents=True, exist_ok=True)
    archives = {name: download(item, cache / (name + '.tar.gz')) for name, item in config['sources'].items()}
    sdk_archive = download(config['wasiSdk'], cache / 'wasi-sdk.tar.gz')
    binaryen_archive = download(config['binaryen'], cache / 'binaryen-130.0.0.tgz')
    archives['llvm-builtins'] = llvm_archive(config, cache)
    with tempfile.TemporaryDirectory(prefix='augmentor-quickjs-') as temporary:
        workspace = Path(temporary)
        source = extract(archives['quickjs-wasi'], workspace / 'source')
        ng = extract(archives['quickjs-ng'], workspace / 'ng')
        if (source / 'quickjs-ng').exists():
            (source / 'quickjs-ng').rmdir()
        shutil.move(str(ng), str(source / 'quickjs-ng'))
        sdk = extract(sdk_archive, workspace / 'sdk')
        binaryen = extract(binaryen_archive, workspace / 'binaryen')
        libc = extract(archives['wasi-libc'], workspace / 'libc')
        llvm = workspace / 'llvm'; llvm.mkdir()
        with tarfile.open(archives['llvm-builtins']) as archive:
            archive.extractall(llvm, filter='data')
        if json.loads((source / 'package.json').read_text())['version'] != config['npmVersion']:
            raise ValueError('QuickJS source version changed')
        compiler = subprocess.check_output([str(sdk / 'bin/clang'), '--version'], text=True).splitlines()[0]
        if config['llvmBuiltins']['commit'] not in compiler or '22.1.0-wasi-sdk' not in compiler:
            raise ValueError('SDK compiler/source identity changed')
        audit = source / 'augmentor-audit.mk'
        audit.write_text('LDFLAGS += -Wl,-Map,quickjs-link.map -Wl,--why-extract=quickjs-extract.tsv -Wl,--trace\n')
        log = workspace / 'build.log'
        with log.open('w') as output:
            subprocess.run(['make', '-f', 'Makefile', '-f', audit.name, 'check-wasi-sdk', 'quickjs.wasm', '-j2',
                            'WASI_SDK=' + str(sdk), 'WASM_OPT=' + str(binaryen / 'bin/wasm-opt')],
                           cwd=source, env={**os.environ, 'LC_ALL': 'C'}, stdout=output, stderr=subprocess.STDOUT, check=True)
        wasm = source / 'quickjs.wasm'
        if sha(wasm) != config['expectedWasmSha256']:
            raise ValueError('QuickJS rebuild differs from reviewed bytes; inspect before changing the pin')
        if str(workspace).encode() in wasm.read_bytes() or str(Path.home()).encode() in wasm.read_bytes():
            raise ValueError('QuickJS binary contains a build/private directory')
        stage = workspace / 'artifact'; stage.mkdir()
        shutil.copyfile(wasm, stage / 'quickjs.wasm')
        collect(source, libc, llvm, sdk, log, config, stage, archives)
        abi = json.loads(subprocess.check_output(['node', '--input-type=module', '-e',
            'import {readFileSync} from "node:fs"; const m=new WebAssembly.Module(readFileSync(process.argv[1]));'
            'console.log(JSON.stringify({imports:WebAssembly.Module.imports(m),exports:WebAssembly.Module.exports(m)}));', str(wasm)], text=True))
        (stage / 'third-party/wasm-abi.json').write_text(json.dumps(abi, indent=2) + '\n')
        record = {**config, 'compiler': compiler,
                  'changes': 'Unmodified pinned engine/interface source rebuilt with WASI SDK 32 and Binaryen 130. npm JavaScript remains unchanged; the recorded npm WASM is replaced. Optional extension binaries are not built or distributed.',
                  'files': {path.relative_to(stage).as_posix(): sha(path) for path in sorted(stage.rglob('*')) if path.is_file()}}
        (stage / 'BUILD.json').write_text(json.dumps(record, indent=2) + '\n')
        if out.exists():
            raise ValueError('Choose a new artifact directory: ' + str(out))
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(stage, out)
        print(json.dumps({'artifact': str(out), 'wasmSha256': sha(out / 'quickjs.wasm'), 'bytes': wasm.stat().st_size, 'noticesAndSources': len(record['files']) - 1}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'vendor/quickjs-engine')
    parser.add_argument('--cache', type=Path, default=ROOT / 'outputs/quickjs-source-cache')
    args = parser.parse_args()
    build(args.out.resolve(), args.cache.resolve())
