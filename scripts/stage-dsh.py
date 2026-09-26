#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Stage the exact DSH graph and prepare reviewed native helpers before signing.

No consumer-machine npm install or arbitrary lifecycle-script execution is needed.
The inventory records provenance; it does not certify third-party licensing.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PREPARE_SCRIPT = 'node_modules/@deepseek-ai/dsh-subprocess-local/scripts/ensure-spawn-helper.mjs'
PREPARE_SHA256 = 'ca5509febf1e6ec1356df121835ebe5ed2f9cace4bdc2ba6d83d41c7e45e0f1b'


def inventory(target):
    spec = importlib.util.spec_from_file_location('npm_notices', ROOT/'scripts/third-party-notices.py')
    notices = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(notices)
    lock = json.loads((target/'package-lock.json').read_text())['packages']
    packages = []
    for path in notices.package_dirs(target/'node_modules'):
        relative = path.relative_to(target).as_posix()
        meta = json.loads((path/'package.json').read_text())
        entry = lock.get(relative, {})
        if entry.get('version') != meta.get('version') or entry.get('dev'):
            raise ValueError('DSH dependency differs from production lock: '+relative)
        if meta['name'].startswith('@deepseek-ai/dsh') and meta['version'] != '0.1.5-rc.1':
            raise ValueError('Mixed DSH suite: '+relative)
        packages.append({'path':relative, 'name':meta['name'], 'version':meta['version'],
            'integrity':entry.get('integrity'), 'license':meta.get('license'),
            'noticeFiles':[p.relative_to(target).as_posix() for p in path.iterdir()
                if p.is_file() and (notices.LICENSE_NAME.match(p.name) or notices.NOTICE_NAME.match(p.name))]})
    if not any(p['name'] == '@deepseek-ai/dsh' for p in packages):
        raise ValueError('Locked DSH CLI is missing')
    return packages


def prepare(target, node):
    script = target/PREPARE_SCRIPT
    if hashlib.sha256(script.read_bytes()).hexdigest() != PREPARE_SHA256:
        raise ValueError('DSH spawn-helper preparation changed; review before executing')
    packages = inventory(target)
    subprocess.run([node, str(script)], check=True, cwd=target)
    report = {'schema':'augmentor-dsh-payload/1',
        'lockSha256':hashlib.sha256((target/'package-lock.json').read_bytes()).hexdigest(),
        'preparedScripts':{PREPARE_SCRIPT:PREPARE_SHA256}, 'packages':packages,
        'licenseReviewComplete':False}
    (target/'payload.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--node', default='node')
    args = parser.parse_args()
    target = args.out.resolve()
    if target.exists() and any(target.iterdir()):
        parser.error('Choose a new, empty DSH output directory')
    target.mkdir(parents=True, exist_ok=True)
    for name in ('package.json', 'package-lock.json'):
        shutil.copy2(ROOT/'release/dsh'/name, target/name)
    shutil.copytree(ROOT/'release/dsh/plugins', target/'plugins')
    subprocess.run(['npm', 'ci', '--ignore-scripts', '--omit=dev', '--no-audit', '--no-fund'],
        cwd=target, check=True)
    # The ARM64 Mac uses the native sharp/libvips pair qualified below. npm also
    # installs the optional wasm fallback there; it contains a separate native
    # source graph and is not a dependency of this target's working image path.
    if sys.platform == 'darwin':
        fallback = target/'node_modules/@img/sharp-wasm32'
        if fallback.exists():shutil.rmtree(fallback)
    report = prepare(target, args.node)
    subprocess.run([sys.executable, str(ROOT/'scripts/third-party-notices.py'),
        '--tree', str(target), '--out', str(target/'licenses')], check=True)
    subprocess.run([args.node, str(ROOT/'scripts/dsh-payload-proof.mjs'), str(target)], check=True, timeout=90)
    print(json.dumps({'staged':str(target), 'packages':len(report['packages']), 'licenseReviewComplete':False}))


if __name__ == '__main__':
    main()
