#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Install a locked production tree and assemble its npm license inventory."""
import argparse
import json
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    target = args.out.resolve()
    if target.exists() and any(target.iterdir()):
        parser.error('Choose an empty staging directory.')
    target.mkdir(parents=True, exist_ok=True)
    node_target = json.loads(subprocess.check_output(['node','-p',
        'JSON.stringify({os:process.platform,cpu:process.arch})'],text=True))
    for name in ('package.json', 'package-lock.json'):
        shutil.copy2(ROOT / name, target / name)
    subprocess.run(['npm', 'ci', '--ignore-scripts', '--omit=dev', '--no-audit', '--no-fund'], cwd=target, check=True)
    subprocess.run(['node', str(ROOT / 'scripts/prepare-ws.mjs'), str(target)], check=True)
    sdk = target / 'node_modules/@earendil-works/pi-coding-agent'
    metadata = json.loads((sdk / 'package.json').read_text())
    if metadata.get('optionalDependencies', {}).get('@mariozechner/clipboard') != '0.3.9':
        raise SystemExit('Pi optional clipboard dependency changed; review the distribution exclusion.')
    # Pi's public loader handles absence. Augmentor uses its own Qt/browser
    # clipboard bindings; do not ship unused native terminal clipboard binaries.
    excluded = [{'name': 'ws', 'version': '8.21.0',
                 'path': 'node_modules/@earendil-works/pi-coding-agent/node_modules/ws',
                 'reason': 'CVE-2026-62389; Pi resolves the locked root ws 8.21.3 instead'},
                {'name': '@earendil-works/pi-coding-agent', 'version': '0.85.1',
                 'path': 'dist/bundle',
                 'reason': 'unused standalone CLI/RPC bundles embed ws 8.21.0; Augmentor uses the unbundled SDK'}]
    # msgpackr's optional string accelerator is not required: its public Node
    # loader catches absence and retains the JavaScript implementation. Ship
    # that portable path instead of ABI-specific prebuilt native addons.
    msgpackr = target / 'node_modules/msgpackr'
    if msgpackr.exists():
        meta = json.loads((msgpackr / 'package.json').read_text())
        if meta['version'] != '2.1.0' or meta.get('optionalDependencies', {}).get('msgpackr-extract') != '^3.0.4':
            raise SystemExit('msgpackr optional accelerator changed; review the distribution exclusion.')
        paths = [target / 'node_modules/msgpackr-extract']
        paths.extend((target / 'node_modules/@msgpackr-extract').glob('*'))
        for item in paths:
            if not item.exists(): continue
            accelerator = json.loads((item / 'package.json').read_text())
            if accelerator['version'] != '3.0.4':
                raise SystemExit('Unexpected msgpackr accelerator version.')
            excluded.append({'name': accelerator['name'], 'version': accelerator['version'],
                             'reason': 'optional native accelerator; public JavaScript fallback is used'})
            shutil.rmtree(item)
        subprocess.run(['node', '--input-type=module', '-e',
                        "import {pack,unpack,isNativeAccelerationEnabled} from 'msgpackr'; "
                        "const v={text:'Augmentor ©',items:[1,true,null]}; "
                        "if(isNativeAccelerationEnabled || JSON.stringify(unpack(pack(v)))!==JSON.stringify(v)) process.exit(1)"],
                       cwd=target, check=True)
    # The SDK ships sample applications, including a compiled Doom WASM demo.
    # They are not SDK runtime code and have separate licensing obligations.
    examples = sdk / 'examples'
    if examples.exists():
        excluded.append({'name': metadata['name'], 'version': metadata['version'], 'path': 'examples',
                         'reason': 'sample applications are not part of Augmentor; separate licenses'})
        shutil.rmtree(examples)
    for modules in (target / 'node_modules', sdk / 'node_modules'):
        tui = modules / '@earendil-works/pi-tui'
        for platform in ('darwin', 'win32'):
            helper = tui / 'native' / platform
            if helper.exists():
                excluded.append({'name': '@earendil-works/pi-tui', 'version': metadata['version'],
                                 'path': 'native/' + platform, 'reason': 'foreign platform keyboard helper'})
                shutil.rmtree(helper)
    for modules in (target / 'node_modules', sdk / 'node_modules'):
        scope = modules / '@mariozechner'
        if not scope.exists():
            continue
        for item in sorted(scope.glob('clipboard*')):
            meta = json.loads((item / 'package.json').read_text())
            if meta['version'] != '0.3.9' or not (meta['name'] == '@mariozechner/clipboard' or meta['name'].startswith('@mariozechner/clipboard-')):
                raise SystemExit('Unexpected clipboard package; review exclusion: ' + str(item))
            excluded.append({'name': meta['name'], 'version': meta['version']})
            shutil.rmtree(item)
    # The published Pi tarball also includes esbuild binaries for foreign
    # operating systems. Keep only the build host's OS/architecture binary.
    for modules in (target / 'node_modules', sdk / 'node_modules'):
        scope = modules / '@esbuild'
        if not scope.exists():
            continue
        owner = json.loads((modules / 'esbuild/package.json').read_text())
        for item in sorted(scope.iterdir()):
            meta = json.loads((item / 'package.json').read_text())
            if owner.get('optionalDependencies', {}).get(meta['name']) != meta['version']:
                raise SystemExit('Unexpected esbuild platform dependency: ' + str(item))
            if meta.get('os') == [node_target['os']] and meta.get('cpu') == [node_target['cpu']]:
                continue
            excluded.append({'name': meta['name'], 'version': meta['version'], 'reason': 'foreign platform'})
            shutil.rmtree(item)
    vendor = ROOT / 'vendor/photon-node'
    if not (vendor / 'BUILD.json').exists():
        raise SystemExit('The reviewed Photon image module is missing. Run scripts/build-photon.py.')
    record = json.loads((vendor / 'BUILD.json').read_text())
    config = json.loads((ROOT / 'release/photon/build.json').read_text())
    if any(record.get(key) != value for key, value in config.items()):
        raise SystemExit('Photon source/toolchain configuration changed. Rebuild and review its notices.')
    if hashlib.sha256((ROOT / 'release/photon/Cargo.lock').read_bytes()).hexdigest() != record['cargoLockSha256']:
        raise SystemExit('Photon dependency lock changed. Rebuild and review its notices.')
    for name, expected in record['files'].items():
        if hashlib.sha256((vendor / name).read_bytes()).hexdigest() != expected:
            raise SystemExit('Photon artifact differs from its build record: ' + name)
    photon = sdk / 'node_modules/@silvia-odwyer/photon-node'
    if json.loads((photon / 'package.json').read_text())['version'] != record['npmVersion']:
        raise SystemExit('Pi Photon version changed; review compatibility before packaging.')
    shutil.rmtree(photon); shutil.copytree(vendor, photon)
    shutil.copytree(vendor / 'third-party', target / 'licenses/photon')
    shutil.copyfile(vendor / 'BUILD.json', target / 'licenses/photon/BUILD.json')
    (target / 'distribution-overrides.json').write_text(json.dumps({'photon': {
        'npmVersion': record['npmVersion'], 'source': record['source'], 'changes': record['changes'],
        'wasmSha256': record['files']['photon_rs_bg.wasm']}}, indent=2) + '\n')
    (target / 'distribution-exclusions.json').write_text(json.dumps(excluded, indent=2) + '\n')
    subprocess.run([sys.executable, str(ROOT / 'scripts/third-party-notices.py'), '--tree', str(target),
                    '--out', str(target / 'licenses/npm')], check=True)
    print(target)


if __name__ == '__main__':
    main()
