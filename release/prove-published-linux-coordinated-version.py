#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One-shot ordinary integration/selection phase after a separate native transaction.

Only the owned published012/013 init154 namespace is supported. This worker
never changes packages, installs a DSH runtime, creates sessions or sends prompts.
Each mode needs a fresh immutable root binding and an exclusive new journal.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import threading
import time

MANAGED_SHA = '6b91fbf0c2406923d8d634e90a0dc0badeebd540f24890ad4c447fee9973ba3a'
BASELINE_RUN_SHA = '3ddeb2d07cf6ee04f1062c20c01489098e657311a8686bdb4daf36f3a90f3e0c'
BASELINE_ENDING_SHA = '08fb21320493910aaa290f4cfd107fe63d32d9f410fa4563df811a86219516ef'
SOURCES = {'0.2.12': 'e02731023153e3b2e1440e50b8c14b64ad0a82e5',
           '0.2.13': '0eb2ec112afa52b886b63606f80967198a7feb0c'}
SETUP_SHAS = {'0.2.12': '12adf6d8be5b1659504164425fb56d8366e867254b2fe5d8019d0fcd0efe2cdc',
              '0.2.13': '18058dd0e072e780b82533b650f938d8809fab66bd3352c1111f66796f4843c9'}
PRESETS = ('augmentor-linux-product', 'augmentor-browser-product')
NEW_DEPENDENCIES = frozenset(('libqt6quickwidgets6', 'python3-pyside6.qtopengl', 'python3-pyside6.qtqml',
    'python3-pyside6.qtquick', 'python3-pyside6.qtquickwidgets', 'qml6-module-qtqml',
    'qml6-module-qtqml-models', 'qml6-module-qtqml-workerscript', 'qml6-module-qtquick'))
SELECTOR = '.local/share/augmentor/desktop.json'
HARNESS = '.config/augmentor/harnesses.json'
FOREIGN_NODE_ROOTS = ('ws', 'schemastery', 'cosmokit', '@standard-schema/spec',
                      'dsh-resonant-voice', 'dsh-adaptive-reasoning', 'dsh-model-picker-augmented')
EXECUTED_161_SHA = '75abecb7cb97ad87200d0c0c3bfdbe262ffce64d59dd7905a391955ad61e3c78'
FAILED_161_SHA = '5687a06d774861343cc6a728c459a1dcf3c815130a9f2d7b382c133761fe1e70'
STAGE_161_SHA = '78b90a68cada95b43d16b0ed77802011d0a0a66d3f425b0a49219228875fb271'
STAGE_161_ROOT = '20261004-100439-2c7a1562'
STAGE_161_ARTIFACT = '93fea0548f044762c168523b2405f9a2c884d975888239bff8fe66b5307bd3f3'
PRIOR_BINDING_SHA = '63e8a983b24fd63c0a7eea848d6d67e5192a26fbd8e4f588adcfd3a5cc1995af'
READONLY_162B_SHA = 'e7187744a4e2fc08365a21724dd7349c12076c952cb5c36d2c5cb2c2c5877140'
HOST_FAILURE_161_SHA = 'f96f1ae8fd38ab95992510d50d1d08da85346a18d2b2d3a347c02d1230ecde64'
ENDING_161_SHA = 'd27391c0a439927dab599d07be379ae55d0b6b9ee4cb2e392fdf4111dc37feb3'
APT_161_SHA = 'b4f5f4b81074feef61ba1434ac90f568533ec380910d83b0f86201b466204ab2'
DSH_CLI_SHA = '0ff7f1d72c4e0cbe14001709c81e20a04b70464118a7f78568952988e28f2ac5'
DSH_PACKAGE_SHA = '8da881a5aa7d371dc1244ebb7acb8dfa9ac5fafce50404b31185d89cf152763a'


def file_identity(info):
    # Reading can change atime; all content/topology metadata stays fenced.
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def stable_owned_read(path, limit=1048576):
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 1000 or info.st_gid != 1000
            or info.st_nlink != 1 or info.st_mode & 0o022 or info.st_size > limit):
        raise ValueError('An admitted ordinary input is linked, foreign or unsafe.')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        if file_identity(os.fstat(fd)) != file_identity(info):
            raise ValueError('An admitted ordinary input changed before reading.')
        chunks = []; count = 0
        while count <= limit:
            chunk = os.read(fd, min(65536, limit+1-count))
            if not chunk: break
            chunks.append(chunk); count += len(chunk)
        if (count != info.st_size or count > limit or file_identity(os.fstat(fd)) != file_identity(info)
                or file_identity(path.lstat()) != file_identity(info)):
            raise ValueError('An admitted ordinary input changed during reading.')
        raw = b''.join(chunks)
        row = {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': count,
               'uid': info.st_uid, 'gid': info.st_gid, 'mode': stat.S_IMODE(info.st_mode),
               'mtimeNs': info.st_mtime_ns, 'ctimeNs': info.st_ctime_ns,
               'device': info.st_dev, 'inode': info.st_ino, 'nlink': info.st_nlink}
        return raw, row
    finally:
        os.close(fd)


def verified_dsh_path(home, app, private_parents, bound=None):
    """Expose only the existing pinned npm command to historical Setup.check."""
    runtime = home/'.local/share/augmentor/dsh-runtime/node_modules'
    shim = runtime/'.bin/dsh'; target = runtime/'@deepseek-ai/dsh/lib/bin.js'
    package = target.parent.parent/'package.json'
    for parent in (shim.parent, target.parent, package.parent): private_parents(parent)
    info = shim.lstat()
    if (not stat.S_ISLNK(info.st_mode) or info.st_uid != 1000 or info.st_gid != 1000
            or info.st_nlink != 1 or os.readlink(shim) != '../@deepseek-ai/dsh/lib/bin.js'
            or shim.resolve(strict=True) != target):
        raise ValueError('The installed npm DSH command has foreign topology.')
    cli_raw, cli_row = stable_owned_read(target)
    package_raw, package_row = stable_owned_read(package)
    metadata = json.loads(package_raw)
    if (cli_row['sha256'] != DSH_CLI_SHA or package_row['sha256'] != DSH_PACKAGE_SHA
            or not cli_row['mode'] & 0o100 or metadata.get('name') != '@deepseek-ai/dsh'
            or metadata.get('version') != '0.1.5-rc.1' or file_identity(shim.lstat()) != file_identity(info)
            or os.readlink(shim) != '../@deepseek-ai/dsh/lib/bin.js'):
        raise ValueError('The pinned installed DSH command changed.')
    observed = {'shim': {'path': str(shim), 'link': os.readlink(shim), 'uid': info.st_uid,
                        'gid': info.st_gid, 'mode': stat.S_IMODE(info.st_mode), 'device': info.st_dev,
                        'inode': info.st_ino, 'nlink': info.st_nlink, 'bytes': info.st_size,
                        'mtimeNs': info.st_mtime_ns, 'ctimeNs': info.st_ctime_ns},
                'target': cli_row, 'package': package_row}
    if bound is not None and observed != bound:
        raise ValueError('The exact root-admitted DSH command identity differs.')
    path = str(shim.parent)+':'+str(app/'node/bin')+':/usr/bin:/bin'
    if shutil.which('dsh', path=path) != str(shim):
        raise ValueError('The admitted clean PATH cannot find exactly the installed DSH command.')
    return path, observed


def staged_binding_identity(binding, proof_sha, coordinator_sha, now):
    pins = {'priorFailedRunSha256': FAILED_161_SHA, 'priorRootBindingSha256': PRIOR_BINDING_SHA,
            'stageVerifiedSha256': STAGE_161_SHA, 'readOnly162bSha256': READONLY_162B_SHA,
            'originalHostFailureSha256': HOST_FAILURE_161_SHA, 'priorIndependentEndingAuditSha256': ENDING_161_SHA}
    if (binding.get('format') != 'augmentor-published-staged-integration-binding/1'
            or binding.get('mode') != 'upgrade-after-known-stage'
            or binding.get('coordinatorSha256') != coordinator_sha
            or not re.fullmatch('[0-9a-f]{64}', binding.get('runToken', ''))
            or any(binding.get(k) != v for k, v in pins.items())
            or binding.get('packageTransaction', {}).get('receiptSha256') != APT_161_SHA
            or not isinstance(binding.get('dshCli'), dict)):
        raise ValueError('Only the exact known staged161 failure may admit integration163.')
    normalized = {**binding, 'format': 'augmentor-published-coordinated-binding/1', 'mode': 'upgrade'}
    return binding_identity(normalized, 'upgrade', proof_sha, now)


def known_staged_failure(record, settings):
    cleanup = record.get('companionCleanup', {})
    if (record.get('format') != 'augmentor-published-coordinated/1' or record.get('mode') != 'upgrade'
            or record.get('phase') != 'failed-do-not-resume' or record.get('proofSha256') != EXECUTED_161_SHA
            or record.get('rootBindingSha256') != PRIOR_BINDING_SHA
            or record.get('nativeVersion') != '0.2.13' or record.get('nativeSource') != SOURCES['0.2.13']
            or record.get('baselineRunSha256') != BASELINE_RUN_SHA
            or record.get('error') != 'ValueError: Make the installed DSH command available on PATH before connecting it.'
            or record.get('unknownOutcome') is not False
            or any(record.get(k, 'missing') is not None for k in ('pendingRequest', 'pendingLifecycle', 'pendingDeployment', 'pendingAction'))
            or record.get('completedActions', []) != [] or record.get('completedDeployments') != [{'label': 'stage', 'exitCode': 0}]
            or record.get('integrationAndSelectionVerified', False) is not False or 'selected' in record
            or record.get('settingsBefore') != settings or record.get('settingsAfter') != settings
            or record.get('ownedDshExitCode') != 0 or record.get('modelRequests') != 0
            or record.get('persistencePreserved') is not True or record.get('baselineJournalPreserved') is not True
            or cleanup.get('phase') != 'pass' or cleanup.get('pending', 'missing') is not None
            or cleanup.get('unknownOutcome') is not False or cleanup.get('exitCode') != 0 or cleanup.get('normalExit') is not True):
        raise ValueError('The prior failure has an action, uncertainty or changed state; no continuation is allowed.')


def known_pass(record):
    if (record.get('phase') != 'pass' or record.get('unknownOutcome') is not False
            or record.get('pendingAction') is not None
            or any(record.get(k, 'missing') is not None for k in ('pendingRequest', 'pendingLifecycle', 'pendingDeployment'))):
        raise ValueError('Only a known successful prior outcome can admit a new phase.')


def binding_identity(binding, mode, proof_sha, now):
    if mode not in ('upgrade', 'rollback'):
        raise ValueError('Only the two explicit coordinated phases are supported.')
    version = '0.2.13' if mode == 'upgrade' else '0.2.12'
    audit = binding.get('nativeAudit', {})
    transaction = binding.get('packageTransaction', {})
    added = sorted(NEW_DEPENDENCIES) if mode == 'upgrade' else []
    if (binding.get('format') != 'augmentor-published-coordinated-binding/1'
            or binding.get('mode') != mode or binding.get('proofSha256') != proof_sha
            or not 0 <= now-binding.get('createdAt', 0) <= 300
            or audit.get('status') != 'pass' or audit.get('version') != version
            or audit.get('source') != SOURCES[version] or audit.get('pending', 'missing') is not None
            or audit.get('unknownOutcome') is not False
            or any(audit.get(k) is not True for k in ('leasesIdle', 'processesAbsent', 'socketAbsent', 'portsIdle'))):
        raise ValueError('The fresh root binding or separate known native transaction differs.')
    if (transaction.get('phase') != 'pass' or transaction.get('exitCode') != 0
            or transaction.get('pending', 'missing') is not None or transaction.get('unknownOutcome') is not False
            or transaction.get('versions') != {'augmentor-runtime': version, 'augmentor-desktop': version}
            or sorted(transaction.get('addedDependencies', [])) != added or transaction.get('removedPackages') != []
            or transaction.get('unrelatedPackageChanges') is not False
            or not re.fullmatch('[0-9a-f]{64}', transaction.get('receiptSha256', ''))):
        raise ValueError('The separately audited normal APT transaction is not the exact finite cohort.')
    for key in ('baselineRunSha256', 'baselineEndingAuditSha256', 'nativeAuditSha256'):
        if not re.fullmatch('[0-9a-f]{64}', binding.get(key, '')):
            raise ValueError('The immutable root binding lacks an exact prior receipt identity.')
    if binding['baselineRunSha256'] != BASELINE_RUN_SHA or binding['baselineEndingAuditSha256'] != BASELINE_ENDING_SHA:
        raise ValueError('Only the actually qualified baseline160 may be used.')
    if mode == 'rollback' and not re.fullmatch('[0-9a-f]{64}', binding.get('upgradeRunSha256', '')):
        raise ValueError('Rollback requires the exact successful upgrade outcome.')
    return version


def action(base, folder, record, label, invoke):
    if record.get('pendingAction') is not None or label in record.get('completedActions', []):
        raise ValueError('An integration action cannot be adopted or replayed.')
    record['pendingAction'] = label; base.atomic(folder/'run.json', record)
    result = invoke()  # An exception keeps pendingAction: its outcome is unknown.
    record.setdefault('completedActions', []).append(label)
    record['pendingAction'] = None; base.atomic(folder/'run.json', record)
    return result


def foreign_node_path(name):
    return any(name.startswith('node_modules/'+root+'/') for root in FOREIGN_NODE_ROOTS)


def hardlink_row(file, info):
    """Read a known foreign dependency without writing any inode or alias."""
    if (info.st_uid != 1000 or info.st_gid != 1000 or info.st_nlink not in (2, 3)
            or stat.S_IMODE(info.st_mode) not in (0o600, 0o755)):
        raise ValueError('The foreign dependency hardlink metadata differs.')
    def identity(value):
        return (value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid,
                value.st_nlink, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    fd = os.open(file, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        if identity(os.fstat(fd)) != identity(info):
            raise ValueError('A foreign dependency changed before its read.')
        chunks = []; count = 0
        while count <= 4194304:
            chunk = os.read(fd, min(65536, 4194305-count))
            if not chunk:
                break
            chunks.append(chunk); count += len(chunk)
        if (count != info.st_size or count > 4194304 or identity(os.fstat(fd)) != identity(info)
                or identity(file.lstat()) != identity(info)):
            raise ValueError('A foreign dependency changed during its read.')
        return {'bytes': count, 'sha256': hashlib.sha256(b''.join(chunks)).hexdigest(),
                'device': info.st_dev, 'inode': info.st_ino, 'nlink': info.st_nlink}
    finally:
        os.close(fd)


def tree(path, foreign_node_modules=False):
    """Bounded byte/metadata snapshot; preserve link strings without following them."""
    if path.is_symlink() or not path.is_dir():
        raise ValueError('A profile snapshot root is missing or linked.')
    result = {}; total = 0
    for file in sorted(path.rglob('*')):
        if len(result) >= 10000:
            raise ValueError('Profile snapshot exceeds its bounded fixture scope.')
        info = file.lstat(); name = str(file.relative_to(path))
        if stat.S_ISDIR(info.st_mode):
            result[name] = {'directory': True, 'uid': info.st_uid, 'gid': info.st_gid, 'mode': stat.S_IMODE(info.st_mode)}
            continue
        row = {'uid': info.st_uid, 'gid': info.st_gid, 'mode': stat.S_IMODE(info.st_mode), 'mtimeNs': info.st_mtime_ns}
        if stat.S_ISLNK(info.st_mode):
            row['link'] = os.readlink(file)
        elif stat.S_ISREG(info.st_mode) and info.st_size <= 4194304:
            if info.st_nlink == 1:
                row.update(bytes=info.st_size, sha256=hashlib.sha256(file.read_bytes()).hexdigest())
            elif foreign_node_modules and foreign_node_path(name):
                row.update(hardlink_row(file, info))
            else:
                raise ValueError('A profile hardlink is outside the known foreign dependency scope.')
            total += info.st_size
        else:
            raise ValueError('A profile member is linked, unsupported or oversized.')
        result[name] = row
        if len(result) > 10000 or total > 67108864:
            raise ValueError('Profile snapshot exceeds its bounded fixture scope.')
    return result


def integration_snapshot(home, version, app=None, foreign_hardlinks=None):
    profile = home/'profiles/web'; target = profile/'augmentor-product'; presets = home/'.agent-presets'
    owned = json.loads((target/'ownership.json').read_text())
    if (owned.get('version') != version or set(owned.get('files', {})) != {'browser/dist/index.js', 'browser/package.json'}
            or set(owned.get('presets', {})) != set(PRESETS)):
        raise ValueError('The known owned integration version or file set differs.')
    target_rows = tree(target); preset_rows = tree(presets); profile_rows = tree(profile, foreign_node_modules=True)
    actual_hardlinks = {name: row for name, row in profile_rows.items() if 'nlink' in row}
    if actual_hardlinks != (foreign_hardlinks or {}):
        raise ValueError('The foreign hardlink topology differs from the immutable root snapshot.')
    for name, digest in owned['files'].items():
        if target_rows.get(name, {}).get('sha256') != digest:
            raise ValueError('An owned plugin was edited.')
        if app is not None and hashlib.sha256((app/'apps/browser/plugin'/name.removeprefix('browser/')).read_bytes()).hexdigest() != digest:
            raise ValueError('The generated plugin does not match the selected native source.')
    for name, files in owned['presets'].items():
        if set(files) != {'preset.yml', 'agent.cordis.yml'}:
            raise ValueError('The known preset ownership is incomplete.')
        for filename, digest in files.items():
            if preset_rows.get(name+'/'+filename, {}).get('sha256') != digest:
                raise ValueError('An owned preset was edited.')
    patch = (profile/'cordis.patch.yml').read_text(); entry = owned.get('patchEntry')
    if not isinstance(entry, str) or not entry or patch.count(entry) != 1:
        raise ValueError('The exact single owned patch entry differs.')
    if app is not None:
        rows = json.loads(entry.removeprefix('- insert: '))
        product = [r for r in rows if r.get('id') == 'augmentor-product']
        if len(product) != 1 or product[0].get('name') != str(app/'adapters/dsh-product/index.mjs'):
            raise ValueError('The generated product entry targets another source root.')
    foreign = {k: v for k, v in profile_rows.items() if not k.startswith('augmentor-product/') and k not in ('augmentor-product', 'cordis.patch.yml')}
    foreign_presets = {k: v for k, v in preset_rows.items() if k.split('/')[0] not in PRESETS}
    return {'owned': owned, 'target': target_rows, 'presets': preset_rows, 'foreign': foreign,
            'foreignPresets': foreign_presets, 'patchForeignText': patch.replace(entry, ''),
            'patch': profile_rows['cordis.patch.yml']}


def integration_preserved(before, after):
    if before['patchForeignText'] != after['patchForeignText'] or before['foreignPresets'] != after['foreignPresets']:
        raise ValueError('Foreign composition or preset content changed.')
    added = set(after['foreign'])-set(before['foreign'])
    targets = {p.split('/')[0] for p in added if p.startswith('augmentor-product.before-')}
    patches = {p for p in added if re.fullmatch(r'cordis\.patch\.yml\.before-augmentor-[0-9a-f]{32}', p)}
    if len(targets) != 1 or len(patches) != 1 or any(not re.fullmatch(r'augmentor-product\.before-[0-9a-f]{32}', p) for p in targets):
        raise ValueError('Normal integration backup generation differs.')
    prefix = next(iter(targets))+'/'
    backups = {k.removeprefix(prefix): v for k, v in after['foreign'].items() if k.startswith(prefix)}
    old_presets = {k: v for k, v in before['presets'].items() if k.split('/')[0] in PRESETS}
    if set(backups) != set(before['target']) | {'presets/'+k for k in old_presets} | {'presets'}:
        raise ValueError('The normal owned backup contains an unexpected file set.')
    for key, value in before['target'].items():
        if backups[key] != value:
            raise ValueError('The old integration backup lost bytes or metadata.')
    for key, value in old_presets.items():
        restored = backups['presets/'+key]
        if (value.get('directory') and restored != value) or (not value.get('directory') and restored.get('sha256') != value.get('sha256')):
            raise ValueError('The normal preset backup lost the old bytes.')
    if not backups['presets'].get('directory') or not after['foreign'][next(iter(targets))].get('directory'):
        raise ValueError('The normal backup directory topology differs.')
    if after['foreign'][next(iter(patches))] != before['patch']:
        raise ValueError('The normal patch backup lost bytes or metadata.')
    expected = dict(before['foreign']); expected.update({k: after['foreign'][k] for k in added})
    if after['foreign'] != expected:
        raise ValueError('An unrelated profile file changed.')


def saved_transition(before, after, version):
    expected = json.loads(json.dumps(before)); expected['dsh']['version'] = version
    if after != expected:
        raise ValueError('Normal save changed a provider, endpoint or unrelated saved key.')


def saved_bytes(before, version):
    document = json.loads(before)
    if (json.dumps(document, indent=2)+'\n').encode() != before:
        raise ValueError('Historical save would normalize unrelated JSON formatting; preserve it instead.')
    document['dsh']['version'] = version
    return (json.dumps(document, indent=2)+'\n').encode()


def candidate_identity(chosen, prior, root, version):
    changed = {'root', 'node', 'version', 'sourceRef', 'artifactSha256', 'releaseId'}
    if (set(chosen) != set(prior) or any(chosen[k] != prior[k] for k in prior if k not in changed)
            or chosen.get('root') != str(root) or chosen.get('node') != str(root/'node/bin/node')
            or chosen.get('version') != version or chosen.get('sourceRef') != SOURCES[version]):
        raise ValueError('The managed candidate changed an unrelated connection or runtime identity.')


def preserve_settings(before, after):
    if set(before) != set(after) or any(before[k] != after[k] for k in before if k not in (SELECTOR, HARNESS)):
        raise ValueError('An unrelated saved setting changed.')


def native_audit(version, invoke=subprocess.run):
    for package in ('augmentor-runtime', 'augmentor-desktop'):
        registered = invoke(['dpkg-query', '-W', '-f=${Version}', package], text=True, capture_output=True, timeout=30)
        audited = invoke(['dpkg', '-V', package], text=True, capture_output=True, timeout=30)
        if (registered.returncode or registered.stdout != version or registered.stderr
                or audited.returncode or audited.stdout or audited.stderr):
            raise ValueError('The registered native cohort or package byte audit differs.')


def verified_existing_stage(deployment, home, helper, binding, settings):
    """Read the exact old outcome; verify existing files without dispatching stage."""
    prior = home/'.local/state/published-product-coordinated-upgrade161'
    helper.private_parents(prior)
    raw, row = stable_owned_read(prior/'run.json')
    if row['sha256'] != FAILED_161_SHA or row['mode'] & 0o077:
        raise ValueError('The exact known pre-installation failure changed.')
    known_staged_failure(json.loads(raw), settings)
    raw, row = stable_owned_read(prior/'stage-verified.json', 8*1024*1024)
    if row['sha256'] != STAGE_161_SHA or row['mode'] & 0o077:
        raise ValueError('The retained stage verification changed.')
    retained = json.loads(raw)
    root = home/'.local/share/augmentor/releases'/STAGE_161_ROOT
    helper.private_parents(root)
    verified = deployment.verify(root)
    if (verified != retained or verified['deployment'] != binding.get('stagedDeployment')
            or verified['deployment'].get('root') != str(root)
            or verified.get('artifactSha256') != STAGE_161_ARTIFACT
            or verified['deployment'].get('artifactSha256') != STAGE_161_ARTIFACT):
        raise ValueError('The full existing staged013 inventory differs.')
    return verified


def prove(mode, *, integration_after_stage=False, proof_path=None):
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    os.umask(0o077); sys.dont_write_bytecode = True
    here = Path(__file__).parent
    proof_path = Path(__file__) if proof_path is None else Path(proof_path)
    if integration_after_stage and (mode != 'upgrade' or proof_path != here/'prove-published-linux-staged-integration.py'):
        raise ValueError('Only the fixed fresh163 integration entrypoint is supported.')
    if not integration_after_stage and proof_path != Path(__file__):
        raise ValueError('Default phases cannot override their reviewed proof identity.')
    # Root topology is checked before importing any proof helper.
    spec = importlib.util.spec_from_file_location('managed', here/'prove-published-linux-managed-baseline.py')
    for path in (proof_path, Path(__file__), Path(spec.origin)):
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o022:
            raise ValueError('Reviewed worker sources must be immutable root-owned files.')
        for parent in path.parents:
            info = parent.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
                raise ValueError('Reviewed worker sources traverse a mutable ancestor.')
    if sha(Path(spec.origin)) != MANAGED_SHA:
        raise ValueError('The reviewed managed-baseline helper differs.')
    managed = importlib.util.module_from_spec(spec); spec.loader.exec_module(managed)
    cold = importlib.util.module_from_spec(importlib.util.spec_from_file_location('cold', here/'prove-published-linux-cold-history.py'))
    managed.immutable_source(Path(cold.__spec__.origin))
    if sha(Path(cold.__spec__.origin)) != managed.COLD_SHA:
        raise ValueError('The reviewed cold Page helper differs.')
    cold.__spec__.loader.exec_module(cold)
    base = cold.load(here/'prove-published-linux-baseline-history.py', 'published_base', cold.BASE_SHA, sha)
    helper = cold.load(here/'published-linux-legacy-companion.py', 'published_companion', cold.HELPER_SHA, sha)
    if os.getuid() != 1000 or Path.home() != base.HOME:
        raise ValueError('Only the dedicated ordinary init154 fixture account is supported.')
    binding_path = (Path('/opt/augmentor-version-proof150/integration163/binding.json') if integration_after_stage
                    else Path('/opt/augmentor-version-proof150/coordinated161')/(mode+'-binding.json'))
    managed.immutable_source(binding_path)
    binding = json.loads(binding_path.read_text())
    proof_sha = sha(proof_path)
    version = (staged_binding_identity(binding, proof_sha, sha(Path(__file__)), time.time()) if integration_after_stage
               else binding_identity(binding, mode, proof_sha, time.time()))
    helper.root_input(Path('/etc/augmentor-upgrade-init-fixture'))
    if Path('/etc/augmentor-upgrade-init-fixture').read_text() != helper.MARKER or Path('/proc/1/cmdline').read_bytes() != b'/usr/bin/tini\0--\0sleep\0infinity\0':
        raise ValueError('The owned init154 namespace differs.')
    dsh_path, dsh_cli = verified_dsh_path(base.HOME, base.APP, helper.private_parents,
                                        binding['dshCli'] if integration_after_stage else None)
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
    native_audit(version)
    helper.root_input(base.APP/'services/dsh/setup.py')
    if sha(base.APP/'services/dsh/setup.py') != SETUP_SHAS[version]:
        raise ValueError('The historical published Setup bytes differ; no installed overlay is accepted.')
    from dsh.setup import Setup, current
    from augmentor_linux.adapters.dsh import DshAdapter
    data = base.HOME/'.local/share/augmentor'; home = Path(env['DSH_HOME'])
    baseline_folder = base.HOME/'.local/state/published-product-managed-baseline160'
    baseline = managed.retained_json(baseline_folder/'run.json', binding['baselineRunSha256'], helper, sha)
    known_pass(baseline)
    if baseline.get('proofSha256') != MANAGED_SHA or baseline.get('fullManagedInventoryVerified') is not True:
        raise ValueError('The actual baseline160 managed adoption is not qualified.')
    incoming = baseline
    if mode == 'rollback':
        incoming = managed.retained_json(base.HOME/'.local/state/published-product-coordinated-upgrade161/run.json', binding['upgradeRunSha256'], helper, sha)
        known_pass(incoming)
        if (incoming.get('format') != 'augmentor-published-coordinated/1' or incoming.get('mode') != 'upgrade'
                or incoming.get('nativeVersion') != '0.2.13' or incoming.get('proofSha256') != sha(Path(__file__))
                or incoming.get('integrationAndSelectionVerified') is not True
                or incoming.get('modelRequests') != 0 or incoming.get('persistencePreserved') is not True):
            raise ValueError('Rollback cannot adopt another mode or incomplete upgrade.')
    settings = base.capture_settings(helper)
    if settings != incoming['settingsAfter'] or settings != binding['settingsBefore']:
        raise ValueError('The exact admitted prior settings differ.')
    for path, digest in ((base.HOME/'.local/bin/augmentor-update', managed.UPDATER_SHA), (data/'desktop-deployment.py', managed.VERIFIER_SHA)):
        helper.private_parents(path.parent); info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 1000 or info.st_nlink != 1 or info.st_mode & 0o022 or sha(path) != digest:
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
    if mode == 'upgrade' and original_previous != managed.retained_json(baseline_folder/'original-desktop.json', baseline['settingsBefore'][SELECTOR], helper, sha):
        raise ValueError('The original legacy predecessor differs from actual baseline160.')
    staged_existing = None
    if integration_after_stage:
        if (sha(data/'desktop.json') != binding.get('expectedCurrentSelectorSha256')
                or sha(data/'desktop.previous.json') != binding.get('expectedPreviousSelectorSha256')):
            raise ValueError('The exact incoming selector bytes differ.')
        staged_existing = verified_existing_stage(deployment, base.HOME, helper, binding, settings)
        candidate_identity(staged_existing['deployment'], selected_before,
                           Path(staged_existing['deployment']['root']), version)
    prior_version = '0.2.12' if mode == 'upgrade' else '0.2.13'
    saved_before = json.loads((base.HOME/HARNESS).read_text())
    expected_saved_bytes = saved_bytes((base.HOME/HARNESS).read_bytes(), version)
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
    profile_before = integration_snapshot(home, prior_version, foreign_hardlinks=foreign_hardlinks)
    token = home/'augmentor-product-token'; helper.private_parents(token.parent)
    token_info = token.lstat()
    if not stat.S_ISREG(token_info.st_mode) or token_info.st_uid != 1000 or token_info.st_nlink != 1 or token_info.st_mode & 0o077:
        raise ValueError('The existing product token is unsafe.')
    token_before = (sha(token), token_info.st_mode, token_info.st_mtime_ns,
                    token_info.st_uid, token_info.st_gid, token_info.st_nlink, token_info.st_dev, token_info.st_ino)
    protected_folders = ['published-product-baseline-history154', 'published-product-first-use-history157',
                         'published-product-cold-history158', 'published-product-managed-baseline160']
    if mode == 'rollback': protected_folders.append('published-product-coordinated-upgrade161')
    if integration_after_stage: protected_folders.append('published-product-coordinated-upgrade161')
    protected_before = {n: tree(base.HOME/'.local/state'/n) for n in protected_folders}
    folder = base.HOME/'.local/state'/('published-product-staged-integration163' if integration_after_stage
                                      else 'published-product-coordinated-'+mode+'161')
    helper.private_parents(folder.parent); folder.mkdir(mode=0o700, exist_ok=False)
    record = {'format': 'augmentor-published-coordinated/1', 'mode': mode, 'phase': 'admitted',
              'proofSha256': proof_sha, 'rootBindingSha256': sha(binding_path), 'nativeVersion': version,
              'nativeSource': SOURCES[version], 'baselineRunSha256': binding['baselineRunSha256'],
              'pendingRequest': None, 'pendingLifecycle': None, 'pendingDeployment': None, 'pendingAction': None,
              'settingsBefore': settings, 'nativePackageOperation': False, 'historyApi': 'session/page; no Follow',
              'upgradeRollbackQualified': False}
    if integration_after_stage:
        record.update(format='augmentor-published-staged-integration/1', mode='upgrade-after-known-stage',
                      coordinatorSha256=sha(Path(__file__)), runToken=binding['runToken'],
                      priorFailedRunSha256=FAILED_161_SHA, stageVerifiedSha256=STAGE_161_SHA,
                      readOnly162bSha256=READONLY_162B_SHA, originalHostFailureSha256=HOST_FAILURE_161_SHA,
                      priorIndependentEndingAuditSha256=ENDING_161_SHA, reusedVerifiedStage=True, dshCli=dsh_cli)
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
        if integration_after_stage:
            chosen = staged_existing['deployment']; staged_root = Path(chosen['root'])
            # The prior inventory was verified before lifecycle dispatch; check it
            # again immediately before installation without invoking stage.
            if deployment.verify(staged_root) != staged_existing:
                raise ValueError('The existing stage changed before integration.')
            base.atomic(folder/'reused-stage-verified.json', staged_existing)
        elif mode == 'upgrade':
            managed.transaction(base, folder, record, 'stage', [updater, 'stage', str(base.APP), '--source-ref', SOURCES[version],
                                '--python', selected_before['python'], '--node', str(base.APP/'node/bin/node')], env)
            staged_root = Path((folder/'stage.stdout').read_text().strip()); helper.private_parents(staged_root)
            if staged_root.parent != data/'releases':
                raise ValueError('The staged candidate escaped its owned store.')
            staged = deployment.verify(staged_root); chosen = staged['deployment']
            candidate_identity(chosen, selected_before, staged_root, version)
            base.atomic(folder/'stage-verified.json', staged)
        else:
            chosen = baseline_manifest['deployment']; staged_root = Path(chosen['root'])
        verified_dsh_path(base.HOME, base.APP, helper.private_parents, dsh_cli)
        setup = Setup(); checked = setup.check({'endpoint': env['DSH_AUGMENTOR_URL'], 'home': str(home)})
        record['historicalCheckReportedInstalled'] = checked['installed']; base.atomic(folder/'run.json', record)
        # Historical013 checks live identity, not copied ownership; always install.
        result = action(base, folder, record, 'normal-setup-install', lambda: setup.install(checked['token']))
        if result.get('installed') is not True or result.get('restartRequired') is not True:
            raise ValueError('Normal integration install returned an unexpected outcome.')
        profile_after = integration_snapshot(home, version, base.APP, foreign_hardlinks); integration_preserved(profile_before, profile_after)
        base.atomic(folder/'integration-after.json', profile_after)
        node.stop(); node = base.OwnedNode(folder, record, env); adapter = node.start(DshAdapter, log)
        verified_dsh_path(base.HOME, base.APP, helper.private_parents, dsh_cli)
        checked = setup.check({'endpoint': env['DSH_AUGMENTOR_URL'], 'home': str(home)})
        if checked.get('installed') is not True:
            raise ValueError('The restarted matching integration is unavailable.')
        result = action(base, folder, record, 'normal-setup-save',
                        lambda: setup.save(checked['token'], managed=saved_before['dsh'].get('managed')))
        if result.get('saved') is not True:
            raise ValueError('Normal product save refused.')
        saved_transition(saved_before, json.loads((base.HOME/HARNESS).read_text()), version)
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
            preserve_settings(settings, record['settingsAfter'])
            info = token.lstat()
            if (sha(token), info.st_mode, info.st_mtime_ns, info.st_uid, info.st_gid, info.st_nlink, info.st_dev, info.st_ino) != token_before:
                raise ValueError('The existing product token changed.')
            if protected_before != {n: tree(base.HOME/'.local/state'/n) for n in protected_folders}:
                raise ValueError('A historical failure, baseline or prior upgrade file changed.')
            if record.get('integrationAndSelectionVerified'):
                integration_preserved(profile_before, integration_snapshot(home, version, base.APP, foreign_hardlinks))
                saved_transition(saved_before, json.loads((base.HOME/HARNESS).read_text()), version)
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
