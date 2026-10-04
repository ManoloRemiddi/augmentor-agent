#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Finite published012/013 integration in the separately admitted ext4 HOME.

Root package transactions and independent ending audits remain separate. The
historical coordinator is imported unchanged for its preservation/lifecycle
helpers; its default and staged-failure entrypoints are never called here.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import threading
import time

COORDINATOR_SHA = 'dfe89a104202b5a493a39af181b56c6853300852378d4d190011b7037247ac76'
MANAGED_SHA = '6b91fbf0c2406923d8d634e90a0dc0badeebd540f24890ad4c447fee9973ba3a'
BASELINE_RUN_SHA = 'd8819753165675606b7e4833384e420ea5ab79a27f33d6d47ad69747ebb04036'
BASELINE_ENDING_SHA = 'cc83cccd0ee8eb93277279fde8aa13d01ba2157aa753293f024e272f691ac29c'
BASELINE_SELECTOR_SHA = 'ae245d2a56d1b25f5e4e77319d4de602900a161a29e56429fdf0d9ca20a15e3f'
ORIGINAL_SELECTOR_SHA = '44dc272924e44b613fed40c59dc9ec09647abe0fb05e02d74a574c7c55b87bae'
FRESH_MARKER_SHA = 'ecb9fe836059b24cfcce649144c11f17f909860e81d7f6bac7f7dd01a507a5f1'
BASELINE_ROOT = '/home/augmentor-version-proof/.local/share/augmentor/releases/20261004-130807-cfb9d9c4'
BASELINE_ARTIFACT = '9cda9c487524c472576be2fb86d70cfea8e370ecbe54ad9694e848d406a8c816'
CONTAINER = '400a7c83dd588c57b8fe59594b9683725c49eaac14e14532140b7fc03631ca7b'
IMAGE = '049bbe119edbe568a0575ce7516cc22ae4699fc71eb6c96540a2ec6dc9de438d'
VOLUME = 'augmentor-versioned-home-20261004'
HOME = Path('/home/augmentor-version-proof')
ROOT = Path('/opt/augmentor-freshhome-coordinated174')
MARKER = Path('/etc/augmentor-upgrade-fresh-home-fixture')
JOURNALS = {m: 'published-product-freshhome-coordinated-'+m+'174' for m in ('upgrade', 'rollback')}
SELECTOR = '.local/share/augmentor/desktop.json'
HARNESS = '.config/augmentor/harnesses.json'
SOURCES = {'0.2.12': 'e02731023153e3b2e1440e50b8c14b64ad0a82e5',
           '0.2.13': '0eb2ec112afa52b886b63606f80967198a7feb0c'}
SEED_PINS = {'seedMapSha256': '6bc718f01ba65a06a69c10d5e2531c205f8fe69b7072c68aebdf2ebddc2152a7',
             'seedAdmissionSha256': '57cbfb3ae647a0de944d471a39fc298d4cea20e16290ad5e3f6421efb36fa191',
             'reviewedBundleSha256': '9846097df138a8b903d4590832b69c964eb69a4c52747834b8470a1bcdcd270a'}
DELTA_SHA = 'cde654ce909a7c66fe6a29871d2e5cb0b9e7644f9d886e28a5505ada53a3802c'
ALIAS_TOPOLOGY_SHA = '0736ca638a0feb36b68cbc173ba15caaf64ddd800d167ae10578571aea1c9cf5'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def immutable_read(path, limit=1048576):
    """Check all root ancestors before opening a bounded non-linked input."""
    for parent in path.parents:
        value = parent.lstat()
        if not stat.S_ISDIR(value.st_mode) or value.st_uid != 0 or value.st_gid != 0 or value.st_mode & 0o022:
            raise ValueError('Fresh root authority traverses a mutable or linked ancestor.')
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
            or info.st_nlink != 1 or info.st_mode & 0o022 or info.st_size > limit):
        raise ValueError('Fresh root authority is foreign, linked, writable or oversized.')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        if identity(os.fstat(fd)) != identity(info): raise ValueError('Root input changed before reading.')
        chunks = []; count = 0
        while count <= limit:
            chunk = os.read(fd, min(65536, limit+1-count))
            if not chunk: break
            chunks.append(chunk); count += len(chunk)
        if count != info.st_size or count > limit or identity(os.fstat(fd)) != identity(info) or identity(path.lstat()) != identity(info):
            raise ValueError('Root input changed during reading.')
        return b''.join(chunks)
    finally:
        os.close(fd)


def pinned_module(path, name, expected):
    raw = immutable_read(path)
    if digest(raw) != expected: raise ValueError('An immutable reviewed helper source differs.')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # Execute the verified bytes, without a mutable second loader read.
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def ending_identity(ending):
    flags = ('nativeInventoryUnchanged', 'normalManagedInventoryVerified',
             'historicalJournalsAndHistoriesPreserved', 'foreignHomeAliasesPreserved',
             'wholeHomeDeltaReviewed', 'processesAbsent', 'socketAbsent', 'portsIdle', 'leasesIdle')
    if (ending.get('format') != 'augmentor-published-freshhome-baseline-ending/1'
            or ending.get('status') != 'pass' or ending.get('actualFreshRunSha256') != BASELINE_RUN_SHA
            or ending.get('wholeHomeDeltaSha256') != DELTA_SHA or ending.get('container') != CONTAINER
            or ending.get('image') != IMAGE or ending.get('volume') != VOLUME
            or ending.get('workerExitCode') != 0 or ending.get('modelRequests') != 0
            or ending.get('unknownOutcome') is not False or ending.get('pending', 'missing') is not None
            or any(ending.get(k) is not True for k in flags)):
        raise ValueError('A genuine completed fresh baseline and reviewed ending audit are required.')


def admission_identity(admission, ending_raw):
    expected = {'format': 'augmentor-published-freshhome-admission/1', 'container': CONTAINER,
                'image': IMAGE, 'volume': VOLUME, 'baselineRunSha256': BASELINE_RUN_SHA,
                'baselineSelectorSha256': BASELINE_SELECTOR_SHA, 'originalSelectorSha256': ORIGINAL_SELECTOR_SHA,
                'wholeHomeDeltaSha256': DELTA_SHA, 'coordinatorSha256': COORDINATOR_SHA,
                'managedProofSha256': MANAGED_SHA, 'freshMarkerSha256': FRESH_MARKER_SHA, **SEED_PINS}
    if (any(admission.get(k) != v for k, v in expected.items())
            or admission.get('baselineEndingAuditSha256') != BASELINE_ENDING_SHA
            or digest(ending_raw) != BASELINE_ENDING_SHA
            or not re.fullmatch('[0-9a-f]{64}', admission.get('freshMarkerSha256', ''))):
        raise ValueError('Only the actual fresh ext4 baseline authority is supported.')
    ending_identity(json.loads(ending_raw))
    selected = admission.get('baselineSelected', {})
    if (selected.get('root') != BASELINE_ROOT or selected.get('artifactSha256') != BASELINE_ARTIFACT
            or selected.get('version') != '0.2.12' or selected.get('sourceRef') != SOURCES['0.2.12']
            or selected != json.loads(ending_raw).get('selected')):
        raise ValueError('The root-bound managed012 selection differs.')
    groups = admission.get('foreignHomeAliasGroups', {})
    if (len(groups) != 127 or digest(json.dumps(groups, sort_keys=True, separators=(',', ':')).encode()) != ALIAS_TOPOLOGY_SHA):
        raise ValueError('The exact127 actual fresh foreign alias groups differ.')
    paths = [p for names in groups.values() for p in names]
    if len(paths) != 255 or set(admission.get('foreignHomeAliasRows', {})) != set(paths):
        raise ValueError('Every closed foreign alias needs an exact root row.')
    alias_rows_identity(groups, admission['foreignHomeAliasRows'])
    if not isinstance(admission.get('historicalJournals'), dict) or set(admission['historicalJournals']) != {
            'published-product-baseline-history154', 'published-product-first-use-history157',
            'published-product-cold-history158', 'published-product-managed-baseline160'}:
        raise ValueError('The four actually retained fresh journals must be root-bound.')


def alias_rows_identity(groups, rows):
    required = {'bytes', 'sha256', 'uid', 'gid', 'mode', 'mtimeNs', 'ctimeNs', 'device', 'inode', 'nlink'}
    for group, names in groups.items():
        device, inode = (int(v) for v in group.split(':'))
        for name in names:
            row = rows[name]
            if (set(row) != required or row.get('uid') != 1000 or row.get('gid') != 1000
                    or row.get('mode') not in (0o600, 0o755)
                    or (row.get('device'), row.get('inode'), row.get('nlink')) != (device, inode, len(names))
                    or len(names) not in (2, 3) or not re.fullmatch('[0-9a-f]{64}', row.get('sha256', ''))
                    or any(type(row.get(k)) is not int or row[k] < 0 for k in ('bytes', 'mtimeNs', 'ctimeNs'))
                    or row['bytes'] > 4194304):
                raise ValueError('Foreign alias authority lacks complete actual byte/time/inode metadata.')


def binding_identity(binding, mode, proof_sha, admission_sha, admission, now, coordinator):
    """Same finite native/300-second APT predicates, explicit new authority."""
    if mode not in JOURNALS: raise ValueError('Only upgrade and rollback are supported.')
    version = '0.2.13' if mode == 'upgrade' else '0.2.12'
    audit = binding.get('nativeAudit', {}); transaction = binding.get('packageTransaction', {})
    if (binding.get('format') != 'augmentor-published-freshhome-coordinated-binding/1'
            or binding.get('mode') != mode or binding.get('proofSha256') != proof_sha
            or binding.get('admissionSha256') != admission_sha or binding.get('coordinatorSha256') != COORDINATOR_SHA
            or not re.fullmatch('[0-9a-f]{64}', binding.get('runToken', ''))
            or not isinstance(binding.get('createdAt'), (int, float)) or not 0 <= now-binding['createdAt'] <= 300
            or binding.get('baselineRunSha256') != BASELINE_RUN_SHA
            or binding.get('baselineEndingAuditSha256') != admission['baselineEndingAuditSha256']
            or audit.get('status') != 'pass' or audit.get('version') != version or audit.get('source') != SOURCES[version]
            or audit.get('pending', 'missing') is not None or audit.get('unknownOutcome') is not False
            or any(audit.get(k) is not True for k in ('leasesIdle', 'processesAbsent', 'socketAbsent', 'portsIdle'))
            or not re.fullmatch('[0-9a-f]{64}', binding.get('nativeAuditSha256', ''))):
        raise ValueError('The fresh root binding or independently audited native phase differs.')
    if (transaction.get('phase') != 'pass' or transaction.get('exitCode') != 0
            or transaction.get('pending', 'missing') is not None or transaction.get('unknownOutcome') is not False
            or transaction.get('versions') != {'augmentor-runtime': version, 'augmentor-desktop': version}
            or sorted(transaction.get('addedDependencies', [])) != (sorted(coordinator.NEW_DEPENDENCIES) if mode == 'upgrade' else [])
            or transaction.get('removedPackages') != [] or transaction.get('unrelatedPackageChanges') is not False
            or not re.fullmatch('[0-9a-f]{64}', transaction.get('receiptSha256', ''))):
        raise ValueError('The normal separate package transaction is not the exact reviewed cohort.')
    if not isinstance(binding.get('foreignHardlinks'), dict) or not isinstance(binding.get('dshCli'), dict):
        raise ValueError('Fresh root profile and exact DSH command identities are required.')
    if mode == 'rollback' and not re.fullmatch('[0-9a-f]{64}', binding.get('upgradeRunSha256', '')):
        raise ValueError('Rollback requires this fresh entrypoint actual successful upgrade.')
    return version


def mount_identity(mountinfo):
    rows = []
    for line in mountinfo.splitlines():
        before, sep, after = line.partition(' - ')
        if not sep: raise ValueError('Malformed mountinfo.')
        fields = before.split(); fs = after.split()
        if len(fields) < 6 or len(fs) < 3: raise ValueError('Malformed mountinfo.')
        if fields[4] == str(HOME): rows.append((fields, fs))
    if (len(rows) != 1 or rows[0][1][0] != 'ext4'
            or not rows[0][0][3].endswith('/volumes/'+VOLUME+'/_data')
            or 'rw' not in rows[0][0][5].split(',')):
        raise ValueError('The dedicated named ext4 HOME volume differs.')


def namespace_identity(marker_raw, admission, nodename, pid1, mountinfo):
    marker = json.loads(marker_raw)
    expected = {'format': 'augmentor-fresh-home-root-admission/1',
                'sourceContainer': 'eb9127eb22ea22d3bf9f48977f55bce755ee4affc2f015384925a3038a3dbfb8',
                'destinationContainer': CONTAINER, 'image': IMAGE, 'volume': VOLUME, **SEED_PINS}
    if (marker != expected or digest(marker_raw) != admission['freshMarkerSha256']
            or nodename != CONTAINER[:12] or pid1 != b'/usr/bin/tini\0--\0sleep\0infinity\0'):
        raise ValueError('The actual fresh namespace/root marker differs.')
    mount_identity(mountinfo)


def aliases_snapshot(home, admission, coordinator, private_parents):
    """Read only the255 explicitly pinned alias paths; no cache scans/writes."""
    observed = {}; rows = admission['foreignHomeAliasRows']
    for group, names in admission['foreignHomeAliasGroups'].items():
        device, inode = (int(v) for v in group.split(':'))
        if len(names) not in (2, 3): raise ValueError('Foreign alias group is not closed.')
        for name in names:
            path = PurePosixPath(name)
            profile = '.local/share/augmentor/dsh-home/profiles/web/'
            if (path.is_absolute() or '..' in path.parts or str(path) != name
                    or not (name.startswith(profile) and coordinator.foreign_node_path(name[len(profile):])
                            or re.fullmatch(r'\.local/share/pnpm/store/v11/files/[0-9a-f]{2}/[0-9a-f]+', name))):
                raise ValueError('An alias path escaped the retained foreign dependency/cache scope.')
            file = home/name; private_parents(file.parent); info = file.lstat()
            if (not stat.S_ISREG(info.st_mode) or (info.st_dev, info.st_ino, info.st_nlink) != (device, inode, len(names))
                    or info.st_size > 4194304):
                raise ValueError('An actual foreign alias was replaced, opened or oversized.')
            value = coordinator.hardlink_row(file, info)
            value.update(uid=info.st_uid, gid=info.st_gid, mode=stat.S_IMODE(info.st_mode),
                         mtimeNs=info.st_mtime_ns, ctimeNs=info.st_ctime_ns)
            if value != rows[name]: raise ValueError('A pinned foreign alias byte/metadata row differs.')
            observed[name] = value
    return observed


def baseline_identity(record, admission, coordinator):
    coordinator.known_pass(record)
    if (record.get('format') != 'augmentor-published-managed-baseline/1'
            or record.get('proofSha256') != MANAGED_SHA or record.get('selected') != admission['baselineSelected']
            or record.get('fullManagedInventoryVerified') is not True or record.get('coldHistoryPreserved') is not True
            or record.get('persistencePreserved') is not True or record.get('coldBaselineJournalPreserved') is not True
            or record.get('modelRequests') != 0 or record.get('ownedDshExitCode') != 0
            or record.get('nativePackageOperation') is not False or record.get('integrationMutation') is not False
            or record.get('companionCleanup', {}).get('phase') != 'pass'):
        raise ValueError('Only the genuine actual fresh managed012 success is supported.')


def rollback_identity(record, binding, admission_sha, proof_sha, coordinator):
    coordinator.known_pass(record)
    if (record.get('format') != 'augmentor-published-freshhome-coordinated/1' or record.get('mode') != 'upgrade'
            or record.get('nativeVersion') != '0.2.13' or record.get('proofSha256') != proof_sha
            or record.get('admissionSha256') != admission_sha or record.get('coordinatorSha256') != COORDINATOR_SHA
            or record.get('baselineRunSha256') != BASELINE_RUN_SHA
            or record.get('integrationAndSelectionVerified') is not True or record.get('modelRequests') != 0
            or record.get('persistencePreserved') is not True or record.get('foreignHomeAliasesPreserved') is not True
            or record.get('runToken') == binding['runToken']
            or not re.fullmatch('[0-9a-f]{64}', record.get('runToken', ''))):
        raise ValueError('Historical, incomplete, unknown or foreign upgrade cannot admit rollback.')


def compact_stage(verified):
    # The normal verifier checks the complete inventory. Preserve a bounded
    # receipt of its identity instead of a second4.2MiB journal inventory.
    return {'deployment': verified['deployment'], 'artifactSha256': verified['artifactSha256'],
            'verifiedInventorySha256': digest(json.dumps(verified, sort_keys=True, separators=(',', ':')).encode()),
            'fullInventoryVerified': True}


def fresh_integration_preserved(before, after, cordis_before, cordis_after, coordinator):
    """Actual173 SDK changes only timestamps of the same cordis.yml inode."""
    immutable = lambda row: {k: v for k, v in row.items() if k not in ('mtimeNs', 'ctimeNs')}
    if immutable(cordis_before) != immutable(cordis_after):
        raise ValueError('Normal SDK movement changed cordis.yml bytes or inode identity.')
    for snapshot, row in ((before, cordis_before), (after, cordis_after)):
        sparse = snapshot['foreign'].get('cordis.yml')
        if sparse != {k: row[k] for k in ('bytes', 'sha256', 'uid', 'gid', 'mode', 'mtimeNs')}:
            raise ValueError('The stable cordis.yml read and profile snapshot disagree.')
    normalized = {**after, 'foreign': {**after['foreign'], 'cordis.yml': before['foreign']['cordis.yml']}}
    # All other rows, owned backups, foreign presets and patch content retain
    # the historical coordinator's exact preservation predicates.
    coordinator.integration_preserved(before, normalized)


def prove(mode):
    os.umask(0o077); sys.dont_write_bytecode = True
    here = Path(__file__).parent
    # All root authority, source and actual namespace checks precede imports
    # from HOME/native applications or any SDK/process/lifecycle operation.
    proof_sha = digest(immutable_read(Path(__file__)))
    admission_raw = immutable_read(ROOT/'admission.json')
    admission = json.loads(admission_raw); admission_sha = digest(admission_raw)
    admission_identity(admission, immutable_read(ROOT/'baseline-ending.json'))
    if os.getuid() != 1000 or os.getgid() != 1000 or Path.home() != HOME:
        raise ValueError('Only the fresh dedicated ordinary UID/GID1000 HOME is supported.')
    namespace_identity(immutable_read(MARKER), admission, os.uname().nodename,
                       Path('/proc/1/cmdline').read_bytes(), Path('/proc/self/mountinfo').read_text())
    coordinator = pinned_module(here/'prove-published-linux-coordinated-version.py', 'fresh_coordinator', COORDINATOR_SHA)
    managed = pinned_module(here/'prove-published-linux-managed-baseline.py', 'fresh_managed', MANAGED_SHA)
    cold = pinned_module(here/'prove-published-linux-cold-history.py', 'fresh_cold', managed.COLD_SHA)
    base = pinned_module(here/'prove-published-linux-baseline-history.py', 'published_base', cold.BASE_SHA)
    helper = pinned_module(here/'published-linux-legacy-companion.py', 'published_companion', cold.HELPER_SHA)
    sha = lambda p: digest(p.read_bytes())
    binding_path = ROOT/(mode+'-binding.json')
    binding_raw = immutable_read(binding_path); binding = json.loads(binding_raw)
    version = binding_identity(binding, mode, proof_sha, admission_sha, admission, time.time(), coordinator)
    if base.HOME != HOME: raise ValueError('Pinned helper HOME differs.')
    helper.root_input(Path('/etc/augmentor-upgrade-init-fixture'))
    if Path('/etc/augmentor-upgrade-init-fixture').read_text() != helper.MARKER:
        raise ValueError('The historical helper protocol marker differs.')
    dsh_path, dsh_cli = coordinator.verified_dsh_path(base.HOME, base.APP, helper.private_parents,
                                        binding['dshCli'])
    env = {'HOME': str(base.HOME), 'USER': 'augmentor-version-proof', 'LOGNAME': 'augmentor-version-proof',
           'PATH': dsh_path, 'LANG': 'C.UTF-8',
           'DSH_HOME': str(base.HOME/'.local/share/augmentor/dsh-home'), 'DSH_AUGMENTOR_URL': 'http://127.0.0.1:35599',
           'DSH_TELEMETRY_MODE': 'DISABLED', 'QT_QPA_PLATFORM': 'offscreen', 'PYTHONNOUSERSITE': '1',
           'PYTHONDONTWRITEBYTECODE': '1', 'AUGMENTOR_MODEL_API_KEY': 'published-upgrade-synthetic-fixture'}
    os.environ.clear(); os.environ.update(env)
    sys.path[:0] = [str(base.APP/'apps/native'), str(base.APP/'services')]
    from lifecycle.lease import hold
    hold('desktop')  # Both native SH leases remain held until this worker exits.
    helper.root_input(base.APP/'release.json'); native = json.loads((base.APP/'release.json').read_text())
    if (native['version'], native['source'], native['target']) != (version, {'commit': SOURCES[version], 'dirty': False}, 'debian13-amd64'):
        raise ValueError('Native packages do not match this explicit phase.')
    coordinator.native_audit(version)
    helper.root_input(base.APP/'services/dsh/setup.py')
    if sha(base.APP/'services/dsh/setup.py') != coordinator.SETUP_SHAS[version]:
        raise ValueError('The historical published Setup bytes differ; no installed overlay is accepted.')
    from dsh.setup import Setup, current
    from augmentor_linux.adapters.dsh import DshAdapter
    data = base.HOME/'.local/share/augmentor'; home = Path(env['DSH_HOME'])
    baseline_folder = base.HOME/'.local/state/published-product-managed-baseline160'
    baseline = managed.retained_json(baseline_folder/'run.json', binding['baselineRunSha256'], helper, sha)
    coordinator.known_pass(baseline)
    baseline_identity(baseline, admission, coordinator)
    incoming = baseline
    if mode == 'rollback':
        incoming = managed.retained_json(base.HOME/'.local/state'/JOURNALS['upgrade']/'run.json', binding['upgradeRunSha256'], helper, sha)
        rollback_identity(incoming, binding, admission_sha, proof_sha, coordinator)
    settings = base.capture_settings(helper)
    if settings != incoming['settingsAfter'] or settings != binding['settingsBefore']:
        raise ValueError('The exact admitted prior settings differ.')
    for path, expected_digest in ((base.HOME/'.local/bin/augmentor-update', managed.UPDATER_SHA), (data/'desktop-deployment.py', managed.VERIFIER_SHA)):
        helper.private_parents(path.parent); info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 1000 or info.st_nlink != 1 or info.st_mode & 0o022 or sha(path) != expected_digest:
            raise ValueError('The normal canonical updater differs.')
    spec = importlib.util.spec_from_file_location('deployment', data/'desktop-deployment.py')
    deployment = importlib.util.module_from_spec(spec); spec.loader.exec_module(deployment)
    baseline_manifest = deployment.verify(Path(baseline['selected']['root']))
    if baseline_manifest['deployment'] != baseline['selected']:
        raise ValueError('The immutable managed012 baseline differs.')
    selected_before = json.loads((data/'desktop.json').read_text())
    if selected_before != incoming['selected']:
        raise ValueError('The current selector is not the exact prior successful selection.')
    if deployment.verify(Path(selected_before['root']))['deployment'] != selected_before:
        raise ValueError('The current managed inventory differs.')
    original_previous = json.loads((data/'desktop.previous.json').read_text())
    if mode == 'rollback' and original_previous != baseline['selected']:
        raise ValueError('Normal rollback does not point at the exact managed012 predecessor.')
    if mode == 'upgrade' and (sha(data/'desktop.json') != BASELINE_SELECTOR_SHA or sha(data/'desktop.previous.json') != ORIGINAL_SELECTOR_SHA):
        raise ValueError('Actual fresh baseline selector bytes differ.')
    if mode == 'upgrade' and original_previous != managed.retained_json(baseline_folder/'original-desktop.json', baseline['settingsBefore'][SELECTOR], helper, sha):
        raise ValueError('The original legacy predecessor differs from actual baseline160.')
    prior_version = '0.2.12' if mode == 'upgrade' else '0.2.13'
    saved_before = json.loads((base.HOME/HARNESS).read_text())
    expected_saved_bytes = coordinator.saved_bytes((base.HOME/HARNESS).read_bytes(), version)
    if set(saved_before.get('dsh', {})) - {'endpoint', 'home', 'version', 'managed'}:
        raise ValueError('Normal historical save cannot preserve unknown DSH connection fields.')
    saved = current()
    if saved.get('version') != prior_version or saved.get('endpoint') != env['DSH_AUGMENTOR_URL'] or saved.get('home') != str(home):
        raise ValueError('The saved prior product connection differs.')
    persistence = cold.persisted(base, helper)
    if persistence != managed.retained_json(baseline_folder/'persistence-before.json', managed.COLD_PERSISTENCE_SHA, helper, sha):
        raise ValueError('The three compressed histories differ from the cold baseline.')
    expected = managed.retained_json(base.HOME/'.local/state/published-product-first-use-history157/history-before.json', cold.EXPECTED_SHA, helper, sha)
    foreign_hardlinks = binding.get('foreignHardlinks', {})
    profile_before = coordinator.integration_snapshot(home, prior_version, foreign_hardlinks=foreign_hardlinks)
    _, cordis_before = coordinator.stable_owned_read(home/'profiles/web/cordis.yml')
    token = home/'augmentor-product-token'; helper.private_parents(token.parent)
    token_info = token.lstat()
    if not stat.S_ISREG(token_info.st_mode) or token_info.st_uid != 1000 or token_info.st_nlink != 1 or token_info.st_mode & 0o077:
        raise ValueError('The existing product token is unsafe.')
    token_before = (sha(token), token_info.st_mode, token_info.st_mtime_ns,
                    token_info.st_uid, token_info.st_gid, token_info.st_nlink, token_info.st_dev, token_info.st_ino)
    protected_folders = ['published-product-baseline-history154', 'published-product-first-use-history157',
                         'published-product-cold-history158', 'published-product-managed-baseline160']
    protected_before = {n: coordinator.tree(base.HOME/'.local/state'/n) for n in protected_folders}
    if protected_before != admission['historicalJournals']:
        raise ValueError('A root-bound historical journal or fresh baseline changed.')
    if mode == 'rollback':
        protected_folders.append(JOURNALS['upgrade'])
        protected_before[JOURNALS['upgrade']] = coordinator.tree(base.HOME/'.local/state'/JOURNALS['upgrade'])
    aliases_before = aliases_snapshot(base.HOME, admission, coordinator, helper.private_parents)
    folder = base.HOME/'.local/state'/JOURNALS[mode]
    helper.private_parents(folder.parent); folder.mkdir(mode=0o700, exist_ok=False)
    record = {'format': 'augmentor-published-freshhome-coordinated/1', 'mode': mode, 'phase': 'admitted',
              'proofSha256': proof_sha, 'rootBindingSha256': sha(binding_path), 'nativeVersion': version,
              'nativeSource': SOURCES[version], 'baselineRunSha256': BASELINE_RUN_SHA,
              'baselineEndingAuditSha256': admission['baselineEndingAuditSha256'],
              'admissionSha256': admission_sha, 'coordinatorSha256': COORDINATOR_SHA,
              'container': CONTAINER, 'image': IMAGE, 'volume': VOLUME, 'runToken': binding['runToken'],
              'pendingRequest': None, 'pendingLifecycle': None, 'pendingDeployment': None, 'pendingAction': None,
              'settingsBefore': settings, 'nativePackageOperation': False, 'historyApi': 'session/page; no Follow',
              'upgradeRollbackQualified': False, 'dshCli': dsh_cli}
    base.atomic(folder/'run.json', record); base.atomic(folder/'integration-before.json', profile_before)
    companion = node = server = thread = log = None; requests = []; failure = None
    try:
        companion = helper.PublishedLegacyCompanion(folder, env); companion.ready()
        server = managed.reject_model_server(requests, base.MODEL_PORT)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        log = (folder/'dsh.log').open('xb'); node = base.OwnedNode(folder, record, env); adapter = node.start(DshAdapter, log)
        sessions = adapter.call('session.list')['items']
        if {r['sessionId'] for r in sessions} != cold.SESSIONS or any(r.get('running') for r in sessions):
            raise ValueError('The three known sessions differ.')
        base.atomic(folder/'history-before.json', {s: cold.page(adapter.remote, s, expected[s]) for s in sorted(cold.SESSIONS)})
        updater = str(base.HOME/'.local/bin/augmentor-update')
        if mode == 'upgrade':
            managed.transaction(base, folder, record, 'stage', [updater, 'stage', str(base.APP), '--source-ref', SOURCES[version],
                                '--python', selected_before['python'], '--node', str(base.APP/'node/bin/node')], env)
            staged_root = Path((folder/'stage.stdout').read_text().strip()); helper.private_parents(staged_root)
            if staged_root.parent != data/'releases':
                raise ValueError('The staged candidate escaped its owned store.')
            staged = deployment.verify(staged_root); chosen = staged['deployment']
            coordinator.candidate_identity(chosen, selected_before, staged_root, version)
            base.atomic(folder/'stage-verified.json', compact_stage(staged))
        else:
            chosen = baseline_manifest['deployment']; staged_root = Path(chosen['root'])
        coordinator.verified_dsh_path(base.HOME, base.APP, helper.private_parents, dsh_cli)
        setup = Setup(); checked = setup.check({'endpoint': env['DSH_AUGMENTOR_URL'], 'home': str(home)})
        record['historicalCheckReportedInstalled'] = checked['installed']; base.atomic(folder/'run.json', record)
        # Historical013 checks live identity, not copied ownership; always install.
        result = coordinator.action(base, folder, record, 'normal-setup-install', lambda: setup.install(checked['token']))
        if result.get('installed') is not True or result.get('restartRequired') is not True:
            raise ValueError('Normal integration install returned an unexpected outcome.')
        profile_after = coordinator.integration_snapshot(home, version, base.APP, foreign_hardlinks)
        _, cordis_after = coordinator.stable_owned_read(home/'profiles/web/cordis.yml')
        fresh_integration_preserved(profile_before, profile_after, cordis_before, cordis_after, coordinator)
        base.atomic(folder/'integration-after.json', profile_after)
        node.stop(); node = base.OwnedNode(folder, record, env); adapter = node.start(DshAdapter, log)
        coordinator.verified_dsh_path(base.HOME, base.APP, helper.private_parents, dsh_cli)
        checked = setup.check({'endpoint': env['DSH_AUGMENTOR_URL'], 'home': str(home)})
        if checked.get('installed') is not True:
            raise ValueError('The restarted matching integration is unavailable.')
        result = coordinator.action(base, folder, record, 'normal-setup-save',
                        lambda: setup.save(checked['token'], managed=saved_before['dsh'].get('managed')))
        if result.get('saved') is not True:
            raise ValueError('Normal product save refused.')
        coordinator.saved_transition(saved_before, json.loads((base.HOME/HARNESS).read_text()), version)
        if (base.HOME/HARNESS).read_bytes() != expected_saved_bytes:
            raise ValueError('Normal save changed bytes beyond the intended saved product version.')
        command = [updater, 'activate', str(staged_root)] if mode == 'upgrade' else [updater, 'rollback']
        managed.transaction(base, folder, record, mode+'-selection', command, env)
        if json.loads((data/'desktop.json').read_text()) != chosen or json.loads((data/'desktop.previous.json').read_text()) != selected_before:
            raise ValueError('The normal selected release or predecessor differs.')
        deployment.verify(staged_root)
        base.atomic(folder/'history-after.json', {s: cold.page(adapter.remote, s, expected[s]) for s in sorted(cold.SESSIONS)})
        record['selected'] = chosen; record['integrationAndSelectionVerified'] = True
    except BaseException as exc:
        failure = exc; record['error'] = type(exc).__name__+': '+str(exc)
    finally:
        # Attempt normal cleanup independently, without signalling twice.
        for label, cleanup in (('node', lambda: node.stop() if node is not None and not node.attempted else None),
                               ('companion', lambda: companion.finish() if companion is not None else None)):
            try:
                result = cleanup()
                if label == 'companion' and result is not None: record['companionCleanup'] = result
            except BaseException as exc:
                record[label+'CleanupError'] = type(exc).__name__+': '+str(exc)
                if failure is None: failure = exc
        if log is not None: log.close()
        if server is not None: server.shutdown(); server.server_close()
        if thread is not None: thread.join(timeout=5)
        record['unknownOutcome'] = any(record[k] is not None for k in ('pendingRequest', 'pendingLifecycle', 'pendingDeployment', 'pendingAction'))
        try:
            record.update(settingsAfter=base.capture_settings(helper), modelRequests=len(requests),
                          persistencePreserved=cold.persisted(base, helper) == persistence,
                          baselineJournalPreserved=sha(baseline_folder/'run.json') == binding['baselineRunSha256'])
            coordinator.preserve_settings(settings, record['settingsAfter'])
            if immutable_read(ROOT/'admission.json') != admission_raw or immutable_read(binding_path) != binding_raw:
                raise ValueError('Root admission or phase binding changed during the run.')
            namespace_identity(immutable_read(MARKER), admission, os.uname().nodename,
                               Path('/proc/1/cmdline').read_bytes(), Path('/proc/self/mountinfo').read_text())
            record['foreignHomeAliasesPreserved'] = aliases_snapshot(base.HOME, admission, coordinator, helper.private_parents) == aliases_before
            info = token.lstat()
            if (sha(token), info.st_mode, info.st_mtime_ns, info.st_uid, info.st_gid, info.st_nlink, info.st_dev, info.st_ino) != token_before:
                raise ValueError('The existing product token changed.')
            if protected_before != {n: coordinator.tree(base.HOME/'.local/state'/n)
                                    for n in protected_folders}:
                raise ValueError('A historical failure, baseline or prior upgrade file changed.')
            if record.get('integrationAndSelectionVerified'):
                profile_ending = coordinator.integration_snapshot(home, version, base.APP, foreign_hardlinks)
                _, cordis_ending = coordinator.stable_owned_read(home/'profiles/web/cordis.yml')
                fresh_integration_preserved(profile_before, profile_ending, cordis_before, cordis_ending, coordinator)
                record['cordisTimestampAllowance'] = {'before': cordis_before, 'after': cordis_ending,
                                                     'bytesAndInodePreserved': True}
                coordinator.saved_transition(saved_before, json.loads((base.HOME/HARNESS).read_text()), version)
                if (base.HOME/HARNESS).read_bytes() != expected_saved_bytes:
                    raise ValueError('Ending saved configuration formatting differs.')
            if requests or not record['persistencePreserved'] or not record['baselineJournalPreserved'] or record['unknownOutcome']:
                raise ValueError('Ending preservation or known outcome differs.')
        except BaseException as exc:
            if failure is None: failure = exc; record['error'] = type(exc).__name__+': '+str(exc)
        record['phase'] = 'pass' if failure is None else 'failed-do-not-resume'; base.atomic(folder/'run.json', record)
    print(json.dumps(record))
    if failure is not None: raise failure


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('upgrade', 'rollback'))
    prove(parser.parse_args().mode)
