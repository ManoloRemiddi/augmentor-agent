#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual installed package lifecycle proof in explicit disposable fixtures.

Root changes only the fixture's installed application package. The ordinary
synthetic user launches the real native preview and a leased bundled Node child.
This does not qualify a real login, version upgrade, installer or physical audio.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
APP = Path('/usr/lib/augmentor')
HOME = Path('/home/augmentor-package-proof')
MARKERS = {
    'Owned Augmentor arch complete package fixture; synthetic users only; no host devices or mounts\n':
        ('arch20261001-x86_64', 'pacman', '/usr/bin/python3'),
    'Owned Augmentor leap complete package fixture; synthetic users only; no host devices or mounts\n':
        ('opensuse-leap16.0-x86_64', 'rpm', '/usr/bin/python3.13'),
}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--guard', type=Path, required=True, help='Separately copied reviewed public guard.')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if os.geteuid() != 0 or not Path('/.dockerenv').exists():
        raise ValueError('Use only a root process inside the explicit disposable Docker fixture.')
    marker = Path('/etc/augmentor-full-package-fixture').read_text()
    if marker not in MARKERS or args.out.exists() or args.out.is_symlink():
        raise ValueError('Unknown fixture or existing results; preserve earlier evidence.')
    target, manager, bootstrap = MARKERS[marker]
    if args.artifact.is_symlink() or digest(args.artifact) != args.sha256:
        raise ValueError('The exact inspected native artifact is required.')
    guard = load(args.guard, 'independent_fixture_guard')
    if guard.host(target) != manager:
        raise ValueError('The fixture does not match the explicit artifact target.')
    # Offline means no default route, checked independently of external downloads.
    if any(row.split()[1] == '00000000' for row in Path('/proc/net/route').read_text().splitlines()[1:]):
        raise ValueError('Disconnect the disposable fixture from its Docker network first.')
    args.out.mkdir(mode=0o700)
    env = dict(os.environ, LC_ALL='C', PYTHONDONTWRITEBYTECODE='1')

    def run(name, command, expected=0):
        result = subprocess.run([str(item) for item in command], env=env, text=True,
                                capture_output=True, timeout=180)
        (args.out/(name+'.stdout')).write_text(result.stdout)
        (args.out/(name+'.stderr')).write_text(result.stderr)
        if (expected == 0 and result.returncode != 0) or (expected == 'refusal' and result.returncode == 0):
            raise RuntimeError(f'{name}: unexpected native transaction status {result.returncode}; logs preserved.')
        return {'exitCode': result.returncode, 'stdoutSha256': digest(args.out/(name+'.stdout')),
                'stderrSha256': digest(args.out/(name+'.stderr'))}

    def settled():
        for path in (guard.STATE/'pending.json', guard.RUN/'augmentor-runtime.pending',
                     guard.RUN/'augmentor-desktop.pending'):
            assert not path.exists() and not path.is_symlink(), str(path)

    initial = guard.receipt(target, manager)
    initial_bytes = (APP/'linux-package.json').read_bytes()
    release_bytes = (APP/'release.json').read_bytes()
    settled()
    runtime = load(APP/'scripts/linux-python-runtime.py', 'installed_fixture_runtime')
    policy = runtime.policy(APP/'linux-python-runtime.json')
    stack = runtime.system_qt()
    stack.verify(policy, APP/'python-wheels'/stack.MANIFEST)
    # Read only synthetic user's own immutable receipt; never discover other homes.
    selected = next((HOME/'.local/share/augmentor/python-runtimes').glob(policy['profile']+'-*'))
    saved = (selected/runtime.RECEIPT).read_bytes()
    receipt = json.loads(saved)
    assert receipt['target'] == target
    sentinel = HOME/'package-lifecycle-sentinel.txt'
    if sentinel.exists() or sentinel.is_symlink():
        raise ValueError('Use a new synthetic sentinel path.')
    sentinel.write_text('Owned package lifecycle fixture; preserve this synthetic user file.\n')
    os.chown(sentinel, 1002, 1002)
    sentinel_hash = digest(sentinel)
    replace = ['pacman', '-U', '--noconfirm', args.artifact] if manager == 'pacman' else ['rpm', '-Uvh', '--replacepkgs', args.artifact]
    remove = ['pacman', '-R', '--noconfirm', 'augmentor-agent'] if manager == 'pacman' else ['rpm', '-e', 'augmentor-agent']
    common = ['runuser', '-u', 'augmentor-package-proof', '--', 'env', 'QT_QPA_PLATFORM=offscreen',
              'PYTHONDONTWRITEBYTECODE=1']
    outcomes = {}
    for component in ('runtime', 'desktop'):
        command = ([bootstrap, '-B', APP/'scripts/run-component.py', 'runtime', APP/'node/bin/node',
                    '-e', "setInterval(()=>{},1000)"] if component == 'runtime' else ['augmentor-agent', '--preview'])
        with (args.out/(component+'-live.stdout')).open('w') as stdout, (args.out/(component+'-live.stderr')).open('w') as stderr:
            process = subprocess.Popen([str(item) for item in common+command], env=env,
                                       stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                deadline = time.monotonic()+30
                while True:
                    assert process.poll() is None, 'The real component stopped before acquiring its lease.'
                    with (guard.RUN/('augmentor-'+component+'.lock')).open('r') as lock:
                        try:
                            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        except BlockingIOError:
                            break
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Real component did not acquire its package lease.')
                    time.sleep(.1)
                for operation, transaction in [('replace', replace), ('remove', remove)]:
                    result = run(component+'-busy-'+operation, transaction, 'refusal')
                    log = (args.out/(component+'-busy-'+operation+'.stdout')).read_text()+(args.out/(component+'-busy-'+operation+'.stderr')).read_text()
                    assert 'Augmentor is still open' in log, 'A manager error alone is not busy refusal proof.'
                    assert guard.installed(manager) == initial['package']
                    assert guard.receipt(target, manager) == initial
                    assert (APP/'linux-package.json').read_bytes() == initial_bytes
                    assert (APP/'release.json').read_bytes() == release_bytes
                    assert process.poll() is None
                    settled()
                    outcomes[component+'Busy'+operation.title()] = result
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=15)
    outcomes['idleSameArtifactReinstall'] = run('idle-reinstall', replace)
    assert guard.receipt(target, manager) == initial
    settled()
    audit = ['pacman', '-Qkk', 'augmentor-agent'] if manager == 'pacman' else ['rpm', '-V', 'augmentor-agent']
    outcomes['nativeAuditAfterReinstall'] = run('reinstall-native-audit', audit)
    outcomes['idleRemove'] = run('idle-remove', remove)
    assert guard.installed(manager) is None and not APP.exists() and not guard.DESKTOP.exists()
    settled()
    assert digest(sentinel) == sentinel_hash and (selected/runtime.RECEIPT).read_bytes() == saved
    outcomes['reinstallAfterRemoval'] = run('after-removal-reinstall', replace)
    assert guard.receipt(target, manager) == initial
    assert (APP/'linux-package.json').read_bytes() == initial_bytes
    assert (APP/'release.json').read_bytes() == release_bytes
    settled()
    stack.verify(policy, APP/'python-wheels'/stack.MANIFEST)
    outcomes['finalNativeAudit'] = run('final-native-audit', audit)
    outcomes['coldNativeRender'] = run('final-render', common+['augmentor-agent', '--preview', '--screenshot', HOME/'lifecycle-window.png'])
    assert digest(sentinel) == sentinel_hash and (selected/runtime.RECEIPT).read_bytes() == saved
    report = {'format': 'augmentor-system-qt-installed-package-proof/1', 'target': target,
              'package': initial['package'], 'source': initial['source'], 'artifactSha256': args.sha256,
              'artifactBytes': args.artifact.stat().st_size, 'receiptSha256': hashlib.sha256(initial_bytes).hexdigest(),
              'appInventoryMembers': len(initial['files']), 'runtimeReceiptSha256': hashlib.sha256(saved).hexdigest(),
              'runtimeArtifactSha256': receipt['artifactSha256'], 'systemQtStack': policy['systemQtStack'],
              'proofSha256': digest(__file__), 'independentGuardSha256': digest(args.guard),
              'outcomes': outcomes, 'offline': True, 'realNativePreviewLease': True, 'realBundledNodeLease': True,
              'pendingAbsent': True, 'completeApplicationInventoryPassed': True, 'nativePackageAuditPassed': True,
              'syntheticUserSentinelPreserved': True, 'immutableRuntimeReceiptPreserved': True,
              'versionUpgradeTested': False, 'rollbackTested': False, 'completeInstallerTested': False,
              'realDesktopSessionTested': False, 'graphicalBrowserTested': False, 'physicalAudioTested': False,
              'liveInputPermissionTested': False, 'licenseReviewComplete': False,
              'embeddedSourceCoverageComplete': False, 'publicReleaseQualified': False, 'ownerStateChanged': False}
    (args.out/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'target': target, 'passed': True, 'report': str(args.out/'result.json')}))


if __name__ == '__main__':
    main()
