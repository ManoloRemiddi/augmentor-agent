#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Compare two distinct conversions in one process and two fresh processes.

Bounded diagnostic only. No new engine build, owner state, installed changes or
claim that process-per-conversion is an adopted/qualified production adapter.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('boundaries', ROOT / 'release/office-rebuild/contained-boundaries.py')
BOUNDARIES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOUNDARIES)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['app', 'thin-app', 'fixtures', 'output']:
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    app, thin, fixtures = map(BOUNDARIES.private_input, [args.app, args.thin_app, args.fixtures])
    out = Path(args.output).absolute()
    if out.parent != ROOT / 'outputs' or out.exists() or out.is_symlink():
        raise ValueError('Use a new direct outputs/ directory')
    for base in [app, thin]:
        assert not (base / 'desktop-release.json').exists()
    proof = json.loads((ROOT / 'release/office-rebuild/thin-engine-qualification.json').read_text())
    for name, record in proof['build']['assets'].items():
        assert BOUNDARIES.sha(thin / 'node_modules/@augmentor/office-engine-wasm/assets' / name) == record['sha256']
    spec = importlib.util.spec_from_file_location('office_identity', ROOT / 'scripts/office_engine.py')
    identity = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(identity)
    identity.validate_inputs(app)
    out.mkdir(mode=0o700)
    probe = out / 'probe'
    probe.mkdir()
    shutil.copy2(ROOT / 'release/office-rebuild/retention-probe.mjs', probe / 'retention-probe.mjs')
    runs = []
    for mode, style in [('baseline', 'same'), ('thin', 'same'), ('baseline', 'fresh'), ('thin', 'fresh')]:
        work = out / (mode + '-' + style)
        work.mkdir(mode=0o700)
        mounts = [(app, '/app'), (fixtures, '/fixtures'), (probe, '/probe'),
                  (Path('/usr/share/fonts/truetype/liberation'), '/usr/share/fonts/truetype/liberation')]
        if mode == 'thin':
            mounts += [(thin / 'node_modules', '/app/node_modules'),
                       (thin / 'dist/runtime/vendor/office-entry', '/app/dist/runtime/vendor/office-entry')]
        create = ['docker', 'create', '--name', 'augmentor-office-retention-' + mode + '-' + style + '-' + secrets.token_hex(6),
                  '--read-only', '--network', 'none', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                  '--memory', '3g', '--memory-swap', '3g', '--cpus', '1', '--pids-limit', '128',
                  '--user', f'{os.getuid()}:{os.getgid()}', '--workdir', '/work',
                  '--env', 'HOME=/work/home', '--env', 'PROBE_ENGINE=' + mode, '--env', 'RETENTION_STYLE=' + style,
                  '--tmpfs', '/tmp:rw,nosuid,nodev,noexec,size=256m']
        for source, target in mounts:
            create += ['--mount', f'type=bind,src={source},dst={target},readonly']
        create += ['--mount', f'type=bind,src={work},dst=/work', BOUNDARIES.IMAGE,
                   '/app/node/bin/node', '--expose-gc', '--max-old-space-size=1536', '/probe/retention-probe.mjs']
        container = BOUNDARIES.command(create).strip()
        (work / 'container.json').write_text(json.dumps({'id': container, 'command': create}, indent=2) + '\n')
        try:
            run = subprocess.run(['docker', 'start', '-a', container], text=True, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired:
            BOUNDARIES.command(['docker', 'kill', container])
            raise
        (work / 'stdout.log').write_text(run.stdout)
        (work / 'stderr.log').write_text(run.stderr)
        inspected = json.loads(BOUNDARIES.command(['docker', 'inspect', container]))[0]
        (work / 'inspection.json').write_text(json.dumps(inspected, indent=2) + '\n')
        assert inspected['State']['Status'] == 'exited' and inspected['State']['ExitCode'] == 0 and not inspected['State']['OOMKilled'], run.stderr[-3000:]
        for key, value in {'Memory': 3221225472, 'MemorySwap': 3221225472, 'NanoCpus': 1_000_000_000,
                           'PidsLimit': 128, 'NetworkMode': 'none', 'ReadonlyRootfs': True}.items():
            assert inspected['HostConfig'][key] == value
        result = json.loads((work / 'result.json').read_text())
        assert result['probeSha256'] == BOUNDARIES.sha(probe / 'retention-probe.mjs')
        for worker in result['runs']:
            for doc in worker['documents']:
                text = BOUNDARIES.command(['/usr/bin/pdftotext', str(work / doc['pdf']), '-'])
                assert 'RETENTION_DOCUMENT_' + str(doc['index']) in text
                assert BOUNDARIES.sha(work / doc['pdf']) == doc['pdfSha256']
                doc['actualPdfTextVerified'] = True
        runs.append(result)
        (out / 'progress.json').write_text(json.dumps(runs, indent=2) + '\n')
    result = {'schema': 'augmentor-office-retention-diagnostic/1', 'runs': runs,
              'operatorSha256': BOUNDARIES.sha(Path(__file__)),
              'probeSha256': BOUNDARIES.sha(probe / 'retention-probe.mjs'),
              'forcedGcIsDiagnosticOnly': True, 'processBoundaryIsDiagnosticOnly': True,
              'engineBuildsStarted': 0, 'installedChanges': 0, 'publicRedistributionQualified': False}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'containers': len(runs), 'pdfsVerified': 8,
                      'peaks': {r['engine'] + '-' + r['style']: int(r['cgroup']['memory.peak']) for r in runs}}))


if __name__ == '__main__':
    main()
