#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Mount/copy/launch a development DMG and exercise its sealed runtime in isolation.

Retains the isolated copy and logs under --out, including on failure. Does not
register browser/login integration, use a live model or bypass Gatekeeper.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(command, log, **kwargs):
    with log.open('w') as stream:
        subprocess.run([str(item) for item in command], stdout=stream,
            stderr=subprocess.STDOUT, check=True, timeout=kwargs.pop('timeout', 180), **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('Run on macOS with an ordinary graphical login session')
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error('Use a new, empty evidence directory')
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    artifacts = args.artifacts.resolve()
    report = json.loads((artifacts/'artifacts.json').read_text())
    if report['component'] != 'desktop':
        parser.error('This proof currently qualifies the desktop bundle')
    image = report['diskImage']
    if Path(image['artifact']).name != image['artifact']:
        raise ValueError('Disk image must be a basename')
    disk = artifacts/image['artifact']
    with disk.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != image['sha256']:
            raise ValueError('Disk image checksum mismatch')
    run([sys.executable, ROOT/'scripts/verify-macos-application-inventory.py', artifacts], out/'inventory.json')
    mount = out/'mount';mount.mkdir()
    subprocess.run(['hdiutil', 'attach', '-quiet', '-readonly', '-nobrowse',
        '-mountpoint', str(mount), str(disk)], check=True, timeout=60)
    app = out/'Installed ü'/'Augmentor Agent Desktop.app'
    try:
        app.parent.mkdir()
        run(['ditto', mount/app.name, app], out/'copy.log')
    finally:
        subprocess.run(['hdiutil', 'detach', '-quiet', str(mount)], check=True, timeout=60)
        mount.rmdir()
    run(['codesign', '--verify', '--deep', '--strict', app], out/'seal-before.log')
    project = app/'Contents/Resources/app'
    # Darwin socket names cannot live under the long app/evidence paths.
    state = Path(tempfile.mkdtemp(prefix='ag-mac-proof-', dir='/tmp'))
    env = {**os.environ, 'PATH':os.pathsep.join([str(project/'dsh/node_modules/.bin'),
        str(project/'node/bin'), '/usr/bin', '/bin', '/usr/sbin', '/sbin']),
        'XDG_CONFIG_HOME':str(state/'config'), 'XDG_DATA_HOME':str(state/'data'),
        'XDG_STATE_HOME':str(state/'state'), 'XDG_RUNTIME_DIR':str(state/'run'),
        'AUGMENTOR_SHARED_CONFIG':str(state/'shared-config'),
        'AUGMENTOR_SHARED_DATA':str(state/'shared-data'), 'AUGMENTOR_SHARED_STATE':str(state/'shared-state'),
        'AUGMENTOR_PI_CONFIG':str(state/'pi-config'), 'AUGMENTOR_PI_STATE':str(state/'pi-state'),
        'AUGMENTOR_PYTHON':str(project/'python/bin/python3'), 'AUGMENTOR_PI_NODE':str(project/'node/bin/node')}
    launch = ['open', '-n', '-W', '--stdout', str(out/'launch.stdout'), '--stderr', str(out/'launch.stderr')]
    for key in env:
        if key.startswith(('XDG_', 'AUGMENTOR_')):
            launch.extend(['--env', key+'='+env[key]])
    launch.extend([str(app), '--args', '--preview', '--screenshot', str(out/'window.png')])
    run(launch, out/'launch.log', env=env, timeout=45)
    if not (out/'window.png').is_file():
        raise ValueError('Application launch did not produce its window screenshot')
    run([project/'node/bin/node', ROOT/'scripts/dsh-payload-proof.mjs', project/'dsh'], out/'payload.json', env=env)
    run(['codesign', '--verify', '--deep', '--strict', app], out/'seal-after-launch.log')
    env.update(AUGMENTOR_PROOF_APP_ROOT=str(project), DSH_TEST_MODULES=str(project/'dsh/node_modules'),
        AUGMENTOR_PROOF_QT_PLATFORM='cocoa', AUGMENTOR_PROOF_APPROVALS='1', AUGMENTOR_PROOF_INTERACTIONS='1',
        AUGMENTOR_PROOF_EXACT_FORK='1', AUGMENTOR_PROOF_EXISTING_PROMPTS='1', PYTHONDONTWRITEBYTECODE='0')
    run([project/'python/bin/python3', '-I', '-B', ROOT/'scripts/dsh-setup-proof.py'], out/'dsh-integration.log', env=env)
    run(['codesign', '--verify', '--deep', '--strict', app], out/'seal-after-integration.log')
    result = {'schema':'augmentor-macos-bundle-proof/1', 'artifactSha256':image['sha256'],
        'appInventorySha256':report['applicationInventorySha256'], 'installedCopy':str(app),
        'isolatedState':str(state), 'model':'local deterministic fixture', 'launchServices':True,
        'relocatedUnicodePath':True, 'nativeRuntime':True, 'dshIntegration':True, 'sealedAfterUse':True,
        'productionSigningQualified':False, 'permissionsQualified':False}
    (out/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
