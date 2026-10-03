#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Adopt the known published012 native baseline through its normal updater.

This preserves an immutable managed012 artifact before a future native package
upgrade can replace /usr/lib/augmentor. No package, integration, model/session
mutation, installer replay, cold launch or rollback is performed here.
"""
import hashlib
import http.server
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import threading

COLD_SHA = 'c3ce83bf4cb3b77eb21fb1306e0c11535d3e7e74f2b2049587bacb985d64484d'
COLD_RUN_SHA = '6ef8c759e6769f0bcc5a97bbbe4cafd0daf71c41625ef46d873d71c412fcb69f'
COLD_PERSISTENCE_SHA = 'a999f72d4791610f535541695592e14ccdcbe806f3e426936e31717037054a8d'
VERIFIER_SHA = 'bac64490fbb570e3d55171b7cd99e663b3c3ab0eecbc929976a23c2d1baebd35'
UPDATER_SHA = '3bf6f45d51f2e8d23b61db40dc8d952668c48e990c7d8cfb8fe91bfed9914001'


def immutable_source(path):
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o022:
        raise ValueError('Reviewed proof source must be an immutable root-owned regular file.')
    for parent in path.parents:
        info=parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError('Reviewed proof source traverses a mutable or linked directory.')


def retained_json(path, digest, helper, sha):
    helper.private_parents(path.parent); info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 1000 or info.st_nlink != 1
            or info.st_mode & 0o077 or info.st_size > 1048576 or sha(path) != digest):
        raise ValueError('A retained baseline input is foreign, linked, changed or unsafe.')
    return json.loads(path.read_text())


def native_identity(metadata, source):
    if (metadata['version'], metadata['source'], metadata['target']) != ('0.2.12', {'commit': source, 'dirty': False}, 'debian13-amd64'):
        raise ValueError('The exact published012 native baseline is required.')


def transaction(base, folder, record, label, argv, env, invoke=subprocess.run):
    if record.get('pendingDeployment') is not None:
        raise ValueError('Unknown deployment outcome is terminal; never replay it.')
    record['pendingDeployment'] = {'label': label, 'argv': argv}
    base.atomic(folder/'run.json', record)
    with (folder/(label+'.stdout')).open('xb') as out, (folder/(label+'.stderr')).open('xb') as err:
        result = invoke(argv, env=env, cwd=base.HOME, stdout=out, stderr=err, timeout=600)
    record.setdefault('completedDeployments', []).append({'label': label, 'exitCode': result.returncode})
    record['pendingDeployment'] = None; base.atomic(folder/'run.json', record)
    if result.returncode: raise ValueError('Normal '+label+' refused; no dependent phase may run.')


def settings_unchanged_except_selection(before, after):
    key = '.local/share/augmentor/desktop.json'
    if set(before) != set(after) or any(before[n] != after[n] for n in before if n != key):
        raise ValueError('Managed adoption changed an unrelated saved setting.')


def reject_model_server(requests, port):
    class Model(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_POST(self):
            requests.append(self.path)
            self.send_error(503, 'No model turn is authorized during managed baseline adoption.')
    return http.server.ThreadingHTTPServer(('127.0.0.1', port), Model)


def prove():
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    sys.dont_write_bytecode = True; os.umask(0o077)
    here = Path(__file__).parent
    immutable_source(Path(__file__))
    immutable_source(here/'prove-published-linux-cold-history.py')
    spec = importlib.util.spec_from_file_location('cold', here/'prove-published-linux-cold-history.py')
    if sha(Path(spec.origin)) != COLD_SHA: raise ValueError('The reviewed cold-history source differs.')
    cold = importlib.util.module_from_spec(spec); spec.loader.exec_module(cold)
    base = cold.load(here/'prove-published-linux-baseline-history.py', 'published_base', cold.BASE_SHA, sha)
    helper = cold.load(here/'published-linux-legacy-companion.py', 'published_companion', cold.HELPER_SHA, sha)
    if os.getuid() != 1000 or Path.home() != base.HOME: raise ValueError('Only the owned ordinary init154 fixture is supported.')
    for path in (Path(__file__), Path(spec.origin), Path('/etc/augmentor-upgrade-init-fixture')): helper.root_input(path)
    if Path('/etc/augmentor-upgrade-init-fixture').read_text() != helper.MARKER or Path('/proc/1/cmdline').read_bytes() != b'/usr/bin/tini\0--\0sleep\0infinity\0':
        raise ValueError('The admitted init154 namespace differs.')
    native = json.loads((base.APP/'release.json').read_text()); helper.root_input(base.APP/'release.json')
    native_identity(native,base.SOURCE)
    prior = base.HOME/'.local/state/published-product-cold-history158/run.json'
    old = retained_json(prior,COLD_RUN_SHA,helper,sha)
    if old['phase'] != 'pass' or old['modelRequests'] or old['unknownOutcome'] or old['pendingLifecycle'] is not None:
        raise ValueError('Only the exact known idle cold-history state is supported.')
    data = base.HOME/'.local/share/augmentor'; updater = base.HOME/'.local/bin/augmentor-update'
    verifier = data/'desktop-deployment.py'
    for path, expected in ((updater, UPDATER_SHA), (verifier, VERIFIER_SHA)):
        helper.private_parents(path.parent); info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 1000 or info.st_nlink != 1 or info.st_mode & 0o022 or sha(path) != expected:
            raise ValueError('The original canonical updater input differs.')
    settings = base.capture_settings(helper)
    if settings != base.FIRST_USE_SETTINGS: raise ValueError('The exact five baseline settings differ.')
    selection_bytes = (data/'desktop.json').read_bytes(); selection = json.loads(selection_bytes)
    if selection.get('root') != str(base.APP) or selection.get('version') != '0.2.12' or selection.get('sourceRef') is not None or (data/'desktop.previous.json').exists() or (data/'desktop.previous.json').is_symlink():
        raise ValueError('Only the retained original legacy native selection can be adopted.')
    helper.private_parents(data/'releases')
    env = {'HOME': str(base.HOME), 'USER': 'augmentor-version-proof', 'LOGNAME': 'augmentor-version-proof',
           'PATH': str(base.APP/'node/bin')+':/usr/bin:/bin', 'LANG': 'C.UTF-8',
           'DSH_HOME': str(base.HOME/'.local/share/augmentor/dsh-home'), 'DSH_AUGMENTOR_URL': 'http://127.0.0.1:35599',
           'DSH_TELEMETRY_MODE': 'DISABLED', 'QT_QPA_PLATFORM': 'offscreen', 'PYTHONNOUSERSITE': '1',
           'PYTHONDONTWRITEBYTECODE': '1', 'AUGMENTOR_MODEL_API_KEY': 'published-upgrade-synthetic-fixture'}
    os.environ.clear(); os.environ.update(env); sys.path.insert(0, str(base.APP/'apps/native'))
    from augmentor_linux.adapters.dsh import DshAdapter
    from lifecycle.lease import hold
    hold('desktop')
    helper.root_input(base.APP/'release.json')
    native_identity(json.loads((base.APP/'release.json').read_text()),base.SOURCE)
    from dsh.setup import current
    import yaml
    base.check_provider(yaml.safe_load((base.HOME/base.SETTINGS[-1]).read_text()), current())
    verifier_spec = importlib.util.spec_from_file_location('original_updater', verifier)
    deployment = importlib.util.module_from_spec(verifier_spec); verifier_spec.loader.exec_module(deployment)
    expected = retained_json(base.HOME/'.local/state/published-product-first-use-history157/history-before.json',cold.EXPECTED_SHA,helper,sha)
    persistence = cold.persisted(base, helper)
    if persistence != retained_json(prior.with_name('persistence-before.json'),COLD_PERSISTENCE_SHA,helper,sha):
        raise ValueError('The exact completed cold baseline persistence differs.')
    folder = base.HOME/'.local/state/published-product-managed-baseline160'
    helper.private_parents(folder.parent); folder.mkdir(mode=0o700, exist_ok=False)
    with (folder/'original-desktop.json').open('xb') as original:
        original.write(selection_bytes); original.flush(); os.fsync(original.fileno())
    record = {'format': 'augmentor-published-managed-baseline/1', 'phase': 'admitted', 'proofSha256': sha(Path(__file__)),
              'pendingRequest': None, 'pendingLifecycle': None, 'pendingDeployment': None,
              'settingsBefore': settings, 'nativePackageOperation': False, 'integrationMutation': False,
              'upgradeRollbackQualified': False}
    base.atomic(folder/'run.json', record); base.atomic(folder/'persistence-before.json', persistence)
    companion = node = server = thread = log = None; requests = []; failure = None
    try:
        companion = helper.PublishedLegacyCompanion(folder, env); companion.ready()
        # Zero POSTs are required, even if a connection/import starts a model unexpectedly.
        server = reject_model_server(requests,base.MODEL_PORT); thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        log = (folder/'dsh.log').open('xb'); node = base.OwnedNode(folder, record, env); adapter = node.start(DshAdapter, log)
        base.atomic(folder/'history-before.json', {sid:cold.page(adapter.remote,sid,expected[sid]) for sid in sorted(cold.SESSIONS)})
        transaction(base,folder,record,'stage',[str(updater),'stage',str(base.APP),'--source-ref',base.SOURCE,
                    '--python',selection['python'],'--node',str(base.APP/'node/bin/node')],env)
        root = Path((folder/'stage.stdout').read_text().strip())
        if root.parent != data/'releases' or root.is_symlink(): raise ValueError('The normal staged release escaped its store.')
        helper.private_parents(root)
        staged = deployment.verify(root); chosen = staged['deployment']
        if chosen['sourceRef'] != base.SOURCE or chosen['version'] != '0.2.12' or chosen['root'] != str(root) or chosen['node'] != str(root/'node/bin/node'):
            raise ValueError('The normal managed012 identity differs.')
        if (data/'desktop.json').read_bytes() != selection_bytes: raise ValueError('Staging changed the selected release.')
        base.atomic(folder/'stage-verified.json', staged)
        transaction(base,folder,record,'activate',[str(updater),'activate',str(root)],env)
        if json.loads((data/'desktop.json').read_bytes()) != chosen or json.loads((data/'desktop.previous.json').read_bytes()) != selection:
            raise ValueError('The normal activation selected an unexpected artifact or predecessor.')
        deployment.verify(root)
        settings_unchanged_except_selection(settings,base.capture_settings(helper))
        base.atomic(folder/'history-after.json',{sid:cold.page(adapter.remote,sid,expected[sid]) for sid in sorted(cold.SESSIONS)})
        if requests or cold.persisted(base,helper) != persistence: raise ValueError('Adoption changed a history or requested a model.')
        record.update(selected=chosen, fullManagedInventoryVerified=True, coldHistoryPreserved=True)
    except BaseException as exc: failure = exc; record['error'] = type(exc).__name__+': '+str(exc)
    finally:
        try:
            if node is not None and not node.attempted: node.stop()
            if companion is not None: record['companionCleanup'] = companion.finish()
        except BaseException as exc:
            record['cleanupError'] = type(exc).__name__+': '+str(exc)
            if failure is None: failure = exc
        finally:
            if log is not None: log.close()
            if server is not None: server.shutdown(); server.server_close()
            if thread is not None: thread.join(timeout=5)
        record.update(settingsAfter=base.capture_settings(helper),modelRequests=len(requests),
                      persistencePreserved=cold.persisted(base,helper)==persistence,
                      coldBaselineJournalPreserved=sha(prior)==COLD_RUN_SHA,
                      unknownOutcome=record['pendingLifecycle'] is not None or record['pendingDeployment'] is not None)
        try: settings_unchanged_except_selection(settings,record['settingsAfter'])
        except ValueError as exc:
            if failure is None: failure = exc; record['error'] = str(exc)
        if failure is None and (requests or not record['persistencePreserved'] or not record['coldBaselineJournalPreserved'] or record['unknownOutcome']):
            failure = ValueError('Ending preservation or absence audit differs.'); record['error'] = str(failure)
        record['phase'] = 'pass' if failure is None else 'failed-do-not-resume'; base.atomic(folder/'run.json', record)
    print(json.dumps(record))
    if failure is not None: raise failure


if __name__ == '__main__': prove()
