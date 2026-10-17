#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Run actual Office providers with synthetic inputs and explicit kernel bounds.

No engine build, selected artifact modification, owner profile or public release.
The retained containers are diagnostic isolation, not an installed app sandbox.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
IMAGE = 'sha256:e5431b048e23385ae592a3a813e3b23d6ad3d8c6c0ee6b0028d9edaba88c2924'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def command(args, **kwargs):
    return subprocess.run(args, text=True, capture_output=True, check=True, **kwargs).stdout


def private_input(value):
    path = Path(value).absolute()
    if path.resolve() != path or not path.is_relative_to(ROOT / 'outputs') or not path.is_dir():
        raise ValueError('Use an existing unlinked private outputs/ input directory')
    return path


def trace_evidence(path, result):
    pending = {}
    canaries = {name: {'driver': 0, 'other': 0} for name in ['only-on-host.png', 'only-on-host.txt']}
    wasm = 0
    connects = []
    for line in path.read_text().splitlines():
        match = re.match(r'(\d+)\s+(.*)', line)
        if not match:
            continue
        pid, body = int(match[1]), match[2]
        if '<unfinished ...>' in body:
            pending[pid] = body.replace('<unfinished ...>', '')
            continue
        if '<... ' in body and 'resumed>' in body:
            previous = pending.pop(pid, None)
            if previous is None:
                raise ValueError('Unpaired resumed trace call')
            body = previous + body.split('resumed>', 1)[1]
        if body.startswith('connect('):
            connects.append((pid, body))
        if not body.startswith('openat(') or 'O_RDONLY' not in body or not re.search(r'= \d+$', body):
            continue
        if 'soffice.wasm' in body:
            wasm += 1
        for name, counts in canaries.items():
            if '/work/outside/' + name in body:
                counts['driver' if pid == result['driverPid'] else 'other'] += 1
    if pending:
        raise ValueError('Unresolved trace calls remain')
    assert wasm >= 8, wasm  # Six valid paths, real cancellation and recovery.
    assert all(c['driver'] == 2 and c['other'] == 0 for c in canaries.values()), canaries
    # glibc's parent-thread passwd lookup probes an absent container-local NSS
    # socket twice. Keep these failed Unix calls explicit, not IP traffic or an
    # unexplained ignore rule; any other destination/thread still fails.
    renderers = result.get('rendererProcesses', [])
    assert not renderers or result.get('diagnosticProcessBoundary') is True
    assert len(renderers) <= 20 and all(isinstance(r.get('pid'), int) and r['pid'] > 0 and r.get('closed') is True for r in renderers)
    renderer_pids = {row['pid'] for row in renderers}
    assert len(renderer_pids) == len(renderers) and result['driverPid'] not in renderer_pids
    nss = [(pid, call) for pid, call in connects if pid in {result['driverPid'], *renderer_pids} and
           re.fullmatch(r'connect\(\d+, \{sa_family=AF_UNIX, sun_path="/var/run/nscd/socket"\}, 110\) = -1 ENOENT \(No such file or directory\)', call)]
    ip = [(pid, call) for pid, call in connects if (pid, call) not in nss]
    driver_nss = sum(pid == result['driverPid'] for pid, _ in nss)
    assert (driver_nss in {0, 2} if result.get('diagnosticProcessBoundary') else driver_nss == 2) and len(ip) == 1, connects
    assert all(sum(pid == renderer for pid, _ in nss) <= 4 for renderer in renderer_pids)
    pid, call = ip[0]
    assert pid == result['driverPid'] and '127.0.0.1' in call and f'htons({result["canaryPort"]})' in call, connects
    return {'successfulWasmOpens': wasm, 'outsideCanaryReads': canaries,
            'connectCalls': len(connects), 'failedParentContainerNssSocketCalls': len(nss),
            'ownedRendererProcessesConfirmedClosed': len(renderers),
            'ipConnectCalls': 1, 'soleIpConnectIsDriverHttpPositiveControl': True,
            'unresolvedCalls': 0, 'traceSha256': sha(path),
            'scope': 'All traced processes/threads within this diagnostic container only'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', required=True)
    parser.add_argument('--thin-app', required=True)
    parser.add_argument('--fixtures', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--process-boundary', action='store_true', help='Explicit contained prototype; not installed/default behavior')
    args = parser.parse_args()
    os.umask(0o077)
    app, thin, fixtures = map(private_input, [args.app, args.thin_app, args.fixtures])
    output = Path(args.output).absolute()
    if output.parent != ROOT / 'outputs' or output.exists() or output.is_symlink():
        raise ValueError('Use a new direct child of outputs/')
    for base in [app, thin]:
        if (base / 'desktop-release.json').exists():
            raise ValueError('Use an unselected diagnostic app; no owner profiles')
    assert json.loads((fixtures / 'fixtures.json').read_text())['schema'] == 'augmentor-rich-office-fixtures/1'
    engine = thin / 'node_modules/@augmentor/office-engine-wasm'
    proof = json.loads((ROOT / 'release/office-rebuild/thin-engine-qualification.json').read_text())
    for name, record in proof['build']['assets'].items():
        assert sha(engine / 'assets' / name) == record['sha256'], name
    spec = importlib.util.spec_from_file_location('office_identity', ROOT / 'scripts/office_engine.py')
    identity_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(identity_module)
    identity_module.validate_inputs(app)
    engine_identities = {
        'baselineWasmSha256': sha(app / 'node_modules/@deepseek-ai/libreoffice-kit-wasm/assets/soffice.wasm'),
        'thinWasmSha256': sha(engine / 'assets/soffice.wasm'),
        'baselineEntrySourceManifestSha256': sha(app / 'dist/runtime/vendor/office-entry/SOURCE.json'),
        'thinEntrySourceManifestSha256': sha(thin / 'dist/runtime/vendor/office-entry/SOURCE.json'),
    }
    command(['docker', 'image', 'inspect', IMAGE])
    output.mkdir(mode=0o700)
    probe = output / 'probe'
    probe.mkdir()
    shutil.copy2(ROOT / 'release/office-rebuild/boundaries-probe.mjs', probe / 'boundaries-probe.mjs')
    if args.process_boundary:
        for name in ['process-converter.mjs', 'process-renderer.mjs']:
            shutil.copy2(ROOT / 'release/office-rebuild' / name, probe / name)
    operator_sha = sha(Path(__file__))
    trace_tools = output / 'trace-tools'
    trace_tools.mkdir()
    # Private diagnostic copies only. Use the matching system loader/libraries
    # because MX strace requires a newer glibc than the immutable builder image.
    libraries = re.findall(r'(?:=>\s*)?(/[^\s]+)', command(['ldd', '/usr/bin/strace']))
    for name in ['/usr/bin/strace', *libraries]:
        shutil.copy2(name, trace_tools / Path(name).name)
    shutil.copy2('/usr/share/doc/strace/copyright', trace_tools / 'strace-copyright')
    tools = {p.name: sha(p) for p in trace_tools.iterdir()}
    runs = []
    for mode in ['baseline', 'thin']:
        work = output / mode
        work.mkdir(mode=0o700)
        name = 'augmentor-office-boundaries-' + mode + '-' + secrets.token_hex(6)
        mounts = [(app, '/app'), (fixtures, '/fixtures'), (trace_tools, '/trace'),
                  (probe, '/probe'),
                  (Path('/usr/share/fonts/truetype/liberation'), '/usr/share/fonts/truetype/liberation')]
        if mode == 'thin':
            mounts += [(thin / 'node_modules', '/app/node_modules'),
                       (thin / 'dist/runtime/vendor/office-entry', '/app/dist/runtime/vendor/office-entry')]
        create = ['docker', 'create', '--name', name, '--read-only', '--network', 'none',
                  '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                  '--memory', '3g', '--memory-swap', '3g', '--cpus', '1', '--pids-limit', '128',
                  '--user', f'{os.getuid()}:{os.getgid()}', '--workdir', '/work',
                  '--env', 'HOME=/work/home', '--env', 'PROBE_ENGINE=' + mode,
                  '--env', 'PROBE_PROCESS_BOUNDARY=' + ('1' if args.process_boundary else '0'),
                  '--tmpfs', '/tmp:rw,nosuid,nodev,noexec,size=256m']
        for source, target in mounts:
            create += ['--mount', f'type=bind,src={source},dst={target},readonly']
        create += ['--mount', f'type=bind,src={work},dst=/work', IMAGE,
                   '/trace/ld-linux-x86-64.so.2', '--library-path', '/trace', '/trace/strace',
                   '-f', '-qq', '-e', 'trace=openat,connect', '-o', '/work/trace.log',
                   '/app/node/bin/node', '--max-old-space-size=1536', '/probe/boundaries-probe.mjs']
        identity = command(create).strip()
        (work / 'container.json').write_text(json.dumps({'id': identity, 'name': name, 'command': create}, indent=2) + '\n')
        try:
            run = subprocess.run(['docker', 'start', '-a', identity], text=True, capture_output=True, timeout=240)
        except subprocess.TimeoutExpired:
            command(['docker', 'kill', identity])
            raise
        (work / 'stdout.log').write_text(run.stdout)
        (work / 'stderr.log').write_text(run.stderr)
        inspected = json.loads(command(['docker', 'inspect', identity]))[0]
        (work / 'inspection.json').write_text(json.dumps(inspected, indent=2) + '\n')
        assert inspected['State']['Status'] == 'exited' and inspected['State']['ExitCode'] == 0 and not inspected['State']['OOMKilled'], run.stderr[-4000:]
        config = inspected['HostConfig']
        for key, value in {'Memory': 3*1024**3, 'MemorySwap': 3*1024**3, 'NanoCpus': 1_000_000_000,
                           'PidsLimit': 128, 'NetworkMode': 'none', 'ReadonlyRootfs': True}.items():
            assert config[key] == value, key
        result = json.loads((work / 'result.json').read_text())
        assert result['probeSha256'] == sha(probe / 'boundaries-probe.mjs')
        for case in result['cases']:
            if not case.get('pdf'):
                continue
            pdf = work / case['pdf']
            text = command(['/usr/bin/pdftotext', str(pdf), '-'])
            assert case['required'] in text, case['name']
            assert not any(marker in text for marker in case['forbidden']), case['name']
            images = command(['/usr/bin/pdfimages', '-list', str(pdf)])
            count = sum(bool(re.match(r'\s*\d+\s+\d+\s+image\b', row)) for row in images.splitlines())
            assert count == case['images'], (case['name'], count, case['images'])
            case['requiredAndExcludedPdfTextVerified'] = True
            case['actualPdfImageCount'] = count
        result['trace'] = trace_evidence(work / 'trace.log', result)
        result['containerId'] = identity
        result['containerImageId'] = inspected['Image']
        runs.append(result)
        (output / 'progress.json').write_text(json.dumps(runs, indent=2) + '\n')
    record = {'schema': 'augmentor-office-contained-boundaries-pair/1', 'runs': runs,
              'tracingToolFiles': tools, 'operatorSha256': operator_sha,
              'engineIdentities': engine_identities,
              'probeSha256': sha(probe / 'boundaries-probe.mjs'),
              'processBoundaryPrototype': args.process_boundary,
              'processPrototypeFilesSha256': {p.name: sha(p) for p in probe.iterdir() if p.name.startswith('process-')},
              'engineBuildsStarted': 0, 'installedChanges': 0,
              'ownerProfilesOrDocumentsUsed': False, 'installedSandboxQualified': False,
              'macroExecutionQualified': False, 'publicRedistributionQualified': False}
    (output / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'engines': len(runs), 'casesPerEngine': len(runs[0]['cases']),
                      'maxMemoryPeakBytes': max(int(r['cgroup']['memory.peak']) for r in runs),
                      'documentHttpCanaryRequests': sum(r['documentHttpCanaryRequests'] for r in runs)}))


if __name__ == '__main__':
    main()
