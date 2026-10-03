#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Compare the known published012 histories without opening a Follow stream.

DSH's documented Follow promotes a cold Agent and may append end-seed. This
separate acceptance uses its cold Page API and preserves every event and every
compressed persistence byte. Historical Follow/formatting failures stay FAIL.
"""
import http.server
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import threading
import time

BASE_SHA = '119be053b8af0d6923276e570254f3a24ed8d30fedb64081f9c0928bd3988f86'
HELPER_SHA = '89a147101055f2efd4e7b852d94f72cd0d1864b5caad9458541ddb591c582ec9'
PRIOR_RUN_SHA = '1af362eb578102935e6c7bb4ef497859225a7ec57ea70e271c4b91d93098f621'
EXPECTED_SHA = '25666a93f06d81ba3d0824069208d717dc469e82b88122e70988756866a1d12e'
SESSIONS = frozenset(('published012-init154-linux', 'published012-first-use157-linux', 'published012-first-use157-browser'))


def load(path, name, digest, sha):
    if sha(path) != digest: raise ValueError('The reviewed '+name+' source differs.')
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o022:
        raise ValueError('A reviewed proof input is mutable or linked.')
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def page(remote, session, expected):
    if expected.get('hasMore') is not False or expected.get('sessionId') != session:
        raise ValueError('The retained fixture page is incomplete or foreign.')
    records = expected.get('events')
    if not isinstance(records, list) or not 1 <= len(records) <= 200:
        raise ValueError('The retained bounded complete event page is required.')
    for seq, record in enumerate(records):
        if record.get('type') != 'event' or record.get('event', {}).get('seq') != seq:
            raise ValueError('The known fixture must have every dense event from sequence0.')
    result = remote.invoke('session/page', {'request': {'address': {'kind': 'session', 'sessionId': session},
                           'throughSeq': len(records)-1, 'maxMessages': 200}})
    if result.get('hasMore') is not False or result.get('records') != records:
        raise ValueError('Cold SDK history lost, reordered, added or changed a preserved event.')
    return result


def persisted(base, helper):
    directory = base.HOME/'.local/share/augmentor/dsh-home/sessions/--home-augmentor-version-proof--'
    helper.private_parents(directory)
    if {p.name for p in directory.iterdir()} != SESSIONS:
        raise ValueError('The exact three synthetic session directories differ.')
    result = {}
    for session in sorted(SESSIONS):
        folder = directory/session; helper.private_parents(folder)
        if {p.name for p in folder.iterdir()} != {'session.v3.jsonl.zstd', 'session.lock'}:
            raise ValueError('An unexpected persistence generation or sidecar appeared.')
        for path in folder.iterdir():
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != 1000 or info.st_nlink != 1 or info.st_mode & 0o077:
                raise ValueError('A persistence member is unsafe or foreign.')
            if info.st_size > 1048576: raise ValueError('Fixture persistence exceeds its bounded size.')
            result[str(path.relative_to(directory))] = {'sha256': base.sha(path), 'bytes': info.st_size,
                  'uid': info.st_uid, 'gid': info.st_gid, 'mode': stat.S_IMODE(info.st_mode), 'mtimeNs': info.st_mtime_ns}
    return result


def prove():
    import hashlib
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    sys.dont_write_bytecode = True; os.umask(0o077)
    base = load(Path(__file__).with_name('prove-published-linux-baseline-history.py'), 'published_base', BASE_SHA, sha)
    helper = load(Path(__file__).with_name('published-linux-legacy-companion.py'), 'published_companion', HELPER_SHA, sha)
    if os.getuid() != 1000 or Path.home() != base.HOME: raise ValueError('Only the owned ordinary fixture is supported.')
    helper.root_input(Path(__file__)); helper.root_input(Path('/etc/augmentor-upgrade-init-fixture'))
    if Path('/etc/augmentor-upgrade-init-fixture').read_text() != helper.MARKER or Path('/proc/1/cmdline').read_bytes() != b'/usr/bin/tini\0--\0sleep\0infinity\0':
        raise ValueError('The admitted init154 namespace is required.')
    helper.root_input(base.APP/'release.json')
    release = json.loads((base.APP/'release.json').read_text())
    if (release['version'], release['source'], release['target']) != ('0.2.12', {'commit': base.SOURCE, 'dirty': False}, 'debian13-amd64'):
        raise ValueError('The exact published012 baseline is required.')
    prior = base.HOME/'.local/state/published-product-first-use-history157'
    helper.private_parents(prior)
    for path in (prior/'run.json', prior/'history-before.json'):
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 1000 or info.st_nlink != 1
                or info.st_mode & 0o077 or info.st_size > 1048576):
            raise ValueError('A retained fixture outcome is unsafe or foreign.')
    if sha(prior/'run.json') != PRIOR_RUN_SHA or sha(prior/'history-before.json') != EXPECTED_SHA:
        raise ValueError('The retained failed profile/outcome differs; it cannot be resumed.')
    old = json.loads((prior/'run.json').read_text())
    if (old['pendingRequest'] is not None or old['pendingLifecycle'] is not None or old['unknownOutcome']
            or old['modelRequests'] != 4 or old['settingsPreserved'] is not True or old['companionCleanup']['phase'] != 'pass'):
        raise ValueError('Only the exact known completed post-first-use state is supported.')
    expected = json.loads((prior/'history-before.json').read_text())
    if set(expected) != SESSIONS: raise ValueError('The retained complete session set differs.')
    settings = base.capture_settings(helper)
    if settings != base.FIRST_USE_SETTINGS: raise ValueError('Saved settings differ from the admitted baseline.')
    env = {'HOME': str(base.HOME), 'USER': 'augmentor-version-proof', 'LOGNAME': 'augmentor-version-proof',
           'PATH': str(base.APP/'node/bin')+':/usr/bin:/bin', 'LANG': 'C.UTF-8',
           'DSH_HOME': str(base.HOME/'.local/share/augmentor/dsh-home'), 'DSH_AUGMENTOR_URL': 'http://127.0.0.1:35599',
           'DSH_TELEMETRY_MODE': 'DISABLED', 'QT_QPA_PLATFORM': 'offscreen', 'PYTHONNOUSERSITE': '1',
           'PYTHONDONTWRITEBYTECODE': '1', 'AUGMENTOR_MODEL_API_KEY': 'published-upgrade-synthetic-fixture'}
    os.environ.clear(); os.environ.update(env); sys.path.insert(0, str(base.APP/'apps/native'))
    from augmentor_linux.adapters.dsh import DshAdapter
    from dsh.setup import current
    from lifecycle.lease import hold
    import yaml
    hold('desktop'); base.check_provider(yaml.safe_load((base.HOME/base.SETTINGS[-1]).read_text()), current())
    runtime = base.HOME/'.local/share/augmentor/dsh-runtime/node_modules/@deepseek-ai'
    for file,digest in (('dsh-session/lib/index.js','05e94f57d96e7979670a5b51024c8591572eb0051ce793613dbdec35cf2c47bf'),
                        ('dsh-api-session-controller/lib/index.js','16ecb48f33996efe72868f1603223214430634c5ac4c3e8fe9060bf240e990ff')):
        if sha(runtime/file) != digest: raise ValueError('The researched shipped cold-history contract differs.')
    folder = base.HOME/'.local/state/published-product-cold-history158'
    helper.private_parents(folder.parent); folder.mkdir(mode=0o700, exist_ok=False)
    record = {'format': 'augmentor-published-cold-history/1', 'phase': 'admitted', 'proofSha256': sha(Path(__file__)),
              'pendingRequest': None, 'pendingLifecycle': None, 'historicalFailuresRelabelled': False,
              'historyApi': 'session/page; no Follow/promotion', 'upgradeRollbackQualified': False, 'settings': settings}
    base.atomic(folder/'run.json', record)
    snapshot = persisted(base, helper); base.atomic(folder/'persistence-before.json', snapshot)
    requests = []; companion = None; node = None; server = None; thread = None; log = None; failure = None
    class Model(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_POST(self): requests.append(self.path); self.send_error(503, 'No model turn is authorized in cold-history proof.')
    try:
        companion = helper.PublishedLegacyCompanion(folder, env); companion.ready()
        server = http.server.ThreadingHTTPServer(('127.0.0.1', base.MODEL_PORT), Model)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        log = (folder/'dsh.log').open('xb')
        for phase in ('before', 'after-normal-restart'):
            node = base.OwnedNode(folder, record, env); adapter = node.start(DshAdapter, log)
            rows = adapter.call('session.list')['items']
            if {row['sessionId'] for row in rows} != SESSIONS or any(row['running'] for row in rows):
                raise ValueError('The exact known idle SDK sessions differ.')
            histories = {sid: page(adapter.remote, sid, expected[sid]) for sid in sorted(SESSIONS)}
            base.atomic(folder/('history-'+phase+'.json'), histories)
            if requests or persisted(base, helper) != snapshot or base.capture_settings(helper) != settings:
                raise ValueError('Cold observation changed persistence/settings or requested a model.')
            node.stop()
        record['coldHistoryAndPersistencePreserved'] = True
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
        record.update(modelRequests=len(requests), unknownOutcome=record['pendingLifecycle'] is not None,
                      settingsPreserved=base.capture_settings(helper) == settings,
                      persistedBytesAndMetadataPreserved=persisted(base, helper) == snapshot,
                      historicalFailureJournalsPreserved=sha(prior/'run.json') == PRIOR_RUN_SHA)
        if failure is None and (requests or record['unknownOutcome'] or not record['settingsPreserved']
                               or not record['persistedBytesAndMetadataPreserved'] or not record['historicalFailureJournalsPreserved']):
            failure = ValueError('Ending cold-history preservation or absence audit differs.')
            record['error'] = str(failure)
        record['phase'] = 'pass' if failure is None else 'failed-do-not-resume'
        base.atomic(folder/'run.json', record)
    print(json.dumps(record))
    if failure is not None: raise failure


if __name__ == '__main__': prove()
