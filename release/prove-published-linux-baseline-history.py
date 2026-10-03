#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One-shot SDK history acceptance for the published012 init154 fixture.

No installer, integration update, package operation, real provider, speech device
or memory engine is used. A failure is retained and must never be resumed.
"""
import copy
import argparse
import hashlib
import http.server
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import stat
import subprocess
import sys
import threading
import time

HOME = Path('/home/augmentor-version-proof')
APP = Path('/usr/lib/augmentor')
SOURCE = 'e02731023153e3b2e1440e50b8c14b64ad0a82e5'
HELPER_SHA = '89a147101055f2efd4e7b852d94f72cd0d1864b5caad9458541ddb591c582ec9'
DSH_PORT = 35599
MODEL_PORT = 43907
SETTINGS = ('.config/augmentor/harnesses.json', '.local/state/augmentor-install/installation.json',
            '.local/state/augmentor-install/model.env', '.local/share/augmentor/desktop.json',
            '.local/share/augmentor/dsh-home/settings.yaml')
ANSWER = 'PUBLISHED LINUX BASELINE FIXTURE VERIFIED'
FIRST_USE_JOURNAL_SHA = 'a5f4250e098a084aecf560d13bf18a8069a2168ed38a5a3f0e01bbbe30105557'
FIRST_USE_SETTINGS = {
    '.config/augmentor/harnesses.json': '55f6dcaa34c3aae24bc79a8650d9df9b456489151bef6f0d1e7154c3f92075a6',
    '.local/state/augmentor-install/installation.json': 'ca01b57f3209c6558b516af04c24df33ee4572c4e0eeb03bdf115a1100c40565',
    '.local/state/augmentor-install/model.env': 'f20487bf2a4fe61323ed0c0216e2efa2a7d2bd7fe17beb5892d001b0f32c4e46',
    '.local/share/augmentor/desktop.json': '44dc272924e44b613fed40c59dc9ec09647abe0fb05e02d74a574c7c55b87bae',
    '.local/share/augmentor/dsh-home/settings.yaml': 'aad67c7c9bc29ae310cbb4c9eea2e420805e5bf8c2d66b038bee77909d2c365b',
}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def atomic(path, value):
    temporary = path.with_name(path.name+'.new')
    with temporary.open('x') as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(value, stream, indent=2); stream.write('\n')
        stream.flush(); os.fsync(stream.fileno())
    temporary.replace(path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)


def normalized(histories):
    result = copy.deepcopy(histories)
    for history in result.values():
        history['header'].setdefault('delegationDepth', 0)
    return result


def mutate(folder, record, adapter, method, payload):
    if record.get('pendingRequest') is not None:
        raise ValueError('An unknown SDK outcome is terminal; never replay it.')
    record['pendingRequest'] = {'method': method, 'payload': payload}
    atomic(folder/'run.json', record)
    result = adapter.call(method, payload)
    record.setdefault('completedRequests', []).append(record['pendingRequest'])
    record['pendingRequest'] = None
    atomic(folder/'run.json', record)
    return result


def capture_settings(helper):
    found = {}
    for name in SETTINGS:
        path = HOME/name; helper.private_parents(path.parent)
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 1000 or info.st_nlink != 1
                or info.st_mode & 0o022 or info.st_size > 1048576):
            raise ValueError('A saved fixture setting has unsafe metadata or size.')
        found[name] = sha(path)
    return found


def check_provider(settings, saved):
    provider = settings['llm-pi-ai']['providers']['augmentor-model']
    if (provider.get('api') != 'openai-completions'
            or provider.get('apiKeyEnv') != 'AUGMENTOR_MODEL_API_KEY'
            or provider.get('baseURL') != 'http://127.0.0.1:43907/v1'
            or [row.get('id') for row in provider.get('models', [])] != ['fixture']
            or saved.get('endpoint') != 'http://127.0.0.1:35599'
            or saved.get('home') != str(HOME/'.local/share/augmentor/dsh-home')
            or saved.get('version') != '0.2.12'):
        raise ValueError('The saved numeric loopback fixture model or product connection differs.')


def check_first_use_record(record):
    methods = [row['method'] for row in record.get('completedRequests', [])]
    if (record.get('phase') != 'failed-do-not-resume' or record.get('sourceCommit') != SOURCE
            or record.get('pendingRequest') is not None or record.get('pendingLifecycle') is not None
            or record.get('unknownOutcome') is not False or record.get('modelRequests') != 2
            or record.get('companionCleanup', {}).get('phase') != 'pass'
            or methods != ['session.create', 'session.selectModel', 'session.prompt']
            or any(row.get('payload', {}).get('sessionId') != 'published012-init154-linux' for row in record.get('completedRequests', []))):
        raise ValueError('The historical first-use outcome is not the exact known completed fixture turn.')


def admit_first_use(helper, yaml):
    path = HOME/'.local/state/published-product-baseline-history154/run.json'
    helper.private_parents(path.parent); info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 1000 or info.st_nlink != 1
            or info.st_mode & 0o077 or info.st_size > 1048576 or sha(path) != FIRST_USE_JOURNAL_SHA):
        raise ValueError('The retained initial first-use failure differs; it cannot be resumed.')
    record = json.loads(path.read_text()); check_first_use_record(record)
    if capture_settings(helper) != FIRST_USE_SETTINGS:
        raise ValueError('The exact retained post-first-use settings differ.')
    original = Path('/opt/augmentor-version-proof150/published012-initial-settings.yaml')
    helper.root_input(original)
    if sha(original) != '8ddd40e97c20d225c90cbbe80658826083e3da0b5ccf123c03427c60ec167add':
        raise ValueError('The immutable original public fixture YAML differs.')
    if yaml.safe_load(original.read_text()) != yaml.safe_load((HOME/SETTINGS[-1]).read_text()):
        raise ValueError('A semantic setting changed during first use.')
    return {'historicalInitialProof': 'FAIL-settings-formatting', 'historicalJournalSha256': FIRST_USE_JOURNAL_SHA,
            'historicalKnownCompletedLinuxTurn': True, 'historicalOriginalSettingsSemanticallyEqual': True,
            'historicalFailureRelabelled': False, 'historicalActionReplayed': False}


class OwnedNode:
    def __init__(self, folder, record, env):
        self.folder = folder; self.record = record; self.env = env
        self.process = None; self.bound = None; self.attempted = False
        self.argv = [str(APP/'node/bin/node'), str((HOME/'.local/share/augmentor/dsh-runtime/node_modules/.bin/dsh').resolve()),
                     'web', '--no-open', '--host', '127.0.0.1', '--port', str(DSH_PORT)]

    def identity(self):
        if self.process is None or self.process.poll() is not None:
            raise ValueError('The original fixture DSH process is absent.')
        proc = Path('/proc')/str(self.process.pid)
        fields = (proc/'stat').read_text().rsplit(')', 1)[1].split()
        identity = {'pid': self.process.pid, 'uid': proc.stat().st_uid,
                    'startTicks': int(fields[19]), 'argv': [x.decode() for x in (proc/'cmdline').read_bytes().split(b'\0') if x]}
        if (identity['uid'] != 1000 or identity['argv'] != self.argv
                or ('DSH_HOME='+self.env['DSH_HOME']).encode() not in (proc/'environ').read_bytes().split(b'\0')
                or (self.bound is not None and identity != self.bound)
                or os.getpgid(self.process.pid) != self.process.pid):
            raise ValueError('The original fixture DSH identity or process group changed.')
        return identity

    def start(self, adapter_class, log):
        if self.process is not None:
            raise ValueError('A DSH spawn cannot be repeated or adopted.')
        self.record['pendingLifecycle'] = 'spawn-owned-dsh'; atomic(self.folder/'run.json', self.record)
        self.process = subprocess.Popen(self.argv, env=self.env, cwd=HOME, stdout=log, stderr=log, start_new_session=True)
        self.bound = self.identity()
        self.record.update(pendingLifecycle=None, ownedDsh=self.bound); atomic(self.folder/'run.json', self.record)
        began = time.monotonic(); deadline = began+60
        while time.monotonic() < deadline:
            self.identity()
            try:
                adapter = adapter_class(); adapter.call('host.describe')
                if not adapter.product: raise ValueError('The fixture product connection differs.')
            except (OSError, ValueError, RuntimeError):
                time.sleep(.2); continue
            elapsed = time.monotonic()-began
            self.record.setdefault('startupSeconds', []).append(elapsed); atomic(self.folder/'run.json', self.record)
            if elapsed > 60: raise RuntimeError('Readiness arrived outside the unchanged60second budget.')
            return adapter
        raise RuntimeError('The owned DSH host did not become ready within60seconds.')

    def stop(self):
        if self.attempted: raise ValueError('A normal DSH stop is one-shot; never retry it.')
        self.attempted = True
        if self.process is None: return
        self.identity()
        self.record['pendingLifecycle'] = 'SIGTERM-owned-dsh'; atomic(self.folder/'run.json', self.record)
        os.killpg(self.process.pid, signal.SIGTERM)
        code = self.process.wait(timeout=15)
        if code not in (0, -signal.SIGTERM): raise ValueError('Owned DSH normal stop failed.')
        self.record.update(pendingLifecycle=None, ownedDshExitCode=code); atomic(self.folder/'run.json', self.record)


def model_server(requests):
    class Model(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_POST(self):
            count = int(self.headers.get('Content-Length', '0'))
            if not 0 < count <= 1048576:
                self.send_error(413); return
            requests.append({'path': self.path, 'body': json.loads(self.rfile.read(count))})
            self.send_response(200); self.send_header('Content-Type', 'text/event-stream'); self.end_headers()
            for delta, reason in (({'role': 'assistant', 'content': ANSWER}, None), ({}, 'stop')):
                value = {'id': 'published-baseline', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'fixture',
                         'choices': [{'index': 0, 'delta': delta, 'finish_reason': reason}]}
                self.wfile.write(('data: '+json.dumps(value)+'\n\n').encode())
            self.wfile.write(b'data: [DONE]\n\n')
    return http.server.ThreadingHTTPServer(('127.0.0.1', MODEL_PORT), Model)


def prove(*, first_use=False):
    os.umask(0o077)
    if os.getuid() != 1000 or Path.home() != HOME:
        raise ValueError('Only the dedicated ordinary published fixture is supported.')
    path = Path(__file__).with_name('published-linux-legacy-companion.py')
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o022 or sha(path) != HELPER_SHA:
        raise ValueError('The reviewed immutable legacy helper differs.')
    spec = importlib.util.spec_from_file_location('published_legacy', path)
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    helper.root_input(path); helper.root_input(Path(__file__)); helper.private_parents(HOME)
    marker = Path('/etc/augmentor-upgrade-init-fixture'); helper.root_input(marker)
    if marker.read_text() != helper.MARKER or Path('/proc/1/cmdline').read_bytes() != b'/usr/bin/tini\0--\0sleep\0infinity\0':
        raise ValueError('The independently admitted init154 namespace is required.')
    helper.root_input(APP/'release.json')
    native = json.loads((APP/'release.json').read_text())
    if (native['version'], native['source'], native['target']) != ('0.2.12', {'commit': SOURCE, 'dirty': False}, 'debian13-amd64'):
        raise ValueError('The published baseline native identity differs.')
    prepared = HOME/'.local/state/published-product-upgrade150/run.json'
    helper.private_parents(prepared.parent)
    pinfo = prepared.lstat()
    if not stat.S_ISREG(pinfo.st_mode) or pinfo.st_uid != 1000 or pinfo.st_nlink != 1 or pinfo.st_mode & 0o077:
        raise ValueError('The original preparation journal differs.')
    preparation = json.loads(prepared.read_text())
    if (preparation['phase'], preparation['source'], preparation['dshPort'], preparation['modelPort']) != ('prepared-published012-baseline', SOURCE, DSH_PORT, MODEL_PORT):
        raise ValueError('Only the already prepared exact baseline/ports are supported.')
    for port in (DSH_PORT, MODEL_PORT):
        with socket.socket() as available: available.bind(('127.0.0.1', port))
    env = dict(os.environ)
    for name in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP', 'PYTHONUSERBASE', 'LD_PRELOAD', 'LD_LIBRARY_PATH'):
        env.pop(name, None); os.environ.pop(name, None)
    env.update(DSH_HOME=str(HOME/'.local/share/augmentor/dsh-home'), DSH_TELEMETRY_MODE='DISABLED',
               QT_QPA_PLATFORM='offscreen', AUGMENTOR_MODEL_API_KEY='published-upgrade-synthetic-fixture',
               AUGMENTOR_FIXTURE_KEY='published-upgrade-synthetic-fixture', PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1')
    os.environ.update(env); sys.dont_write_bytecode = True
    sys.path.insert(0, str(APP/'apps/native'))
    from augmentor_linux.adapters.dsh import DshAdapter
    from lifecycle.lease import hold
    hold('desktop')
    from dsh.setup import current
    import yaml
    check_provider(yaml.safe_load((HOME/'.local/share/augmentor/dsh-home/settings.yaml').read_text()), current())
    first_use_admission = admit_first_use(helper, yaml) if first_use else None
    env.update(DSH_AUGMENTOR_URL='http://127.0.0.1:35599',
               PATH=str(APP/'node/bin')+':/usr/bin:/bin')
    os.environ.update(env)
    run_name = 'published-product-first-use-history157' if first_use else 'published-product-baseline-history154'
    session_prefix = 'published012-first-use157-' if first_use else 'published012-init154-'
    folder = HOME/'.local/state'/run_name
    helper.private_parents(folder.parent); folder.mkdir(mode=0o700, exist_ok=False)
    record = {'format': 'augmentor-published-baseline-history/1', 'phase': 'admitted', 'sourceCommit': SOURCE,
              'proofSha256': sha(Path(__file__)), 'helperSha256': HELPER_SHA, 'pendingRequest': None,
              'pendingLifecycle': None, 'upgradeRollbackQualified': False, 'startedAt': time.time()}
    if first_use: record['firstUseAdmission'] = first_use_admission
    atomic(folder/'run.json', record)
    settings = capture_settings(helper); record['settings'] = settings; atomic(folder/'run.json', record)
    companion = None; node = None; server = None; thread = None; log = None; requests = []; failure = None
    try:
        companion = helper.PublishedLegacyCompanion(folder, env); companion.ready()
        server = model_server(requests); thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        log = (folder/'dsh.log').open('xb'); node = OwnedNode(folder, record, env); adapter = node.start(DshAdapter, log)
        rows = adapter.call('session.list')['items']
        if any(row.get('running') for row in rows): raise ValueError('A preexisting SDK task is active.')
        prior = [row['sessionId'] for row in rows]
        original = {sid: adapter.call('session.history', {'sessionId': sid}) for sid in prior}
        atomic(folder/'history-prior.json', original)
        sessions = []
        for role in ('linux', 'browser'):
            if capture_settings(helper) != settings: raise ValueError('Saved settings changed before a role turn.')
            session = session_prefix+role
            if session in prior: raise ValueError('A fixture session already exists; it cannot be resumed.')
            sessions.append(session)
            for method, payload in (
                ('session.create', {'sessionId': session, 'agentPreset': 'augmentor-'+role+'-product', 'cwd': str(HOME)}),
                ('session.selectModel', {'sessionId': session, 'provider': 'augmentor-model', 'model': 'fixture'}),
                ('session.prompt', {'sessionId': session, 'mode': 'queue', 'content': [{'type': 'text', 'text': 'Reply to the '+role+' baseline fixture.'}]})):
                mutate(folder, record, adapter, method, payload)
            deadline = time.monotonic()+60
            while time.monotonic() < deadline:
                history = adapter.call('session.history', {'sessionId': session})
                row = next(row for row in adapter.call('session.list')['items'] if row['sessionId'] == session)
                if not row['running'] and ANSWER in json.dumps(history):
                    if time.monotonic() > deadline: raise RuntimeError('The role completion arrived outside60seconds.')
                    break
                time.sleep(.1)
            else: raise RuntimeError('The fixture role did not finish within60seconds.')
        before = {sid: adapter.call('session.history', {'sessionId': sid}) for sid in prior+sessions}
        atomic(folder/'history-before.json', before)
        if normalized({sid: before[sid] for sid in prior}) != normalized(original): raise ValueError('A prior history changed.')
        count = len(requests)
        if count < 2: raise ValueError('Both roles must reach the synthetic model.')
        node.stop(); node = OwnedNode(folder, record, env); adapter = node.start(DshAdapter, log)
        after = {sid: adapter.call('session.history', {'sessionId': sid}) for sid in prior+sessions}
        atomic(folder/'history-after.json', after)
        if normalized(after) != normalized(before): raise ValueError('Restart changed saved history events.')
        if len(requests) != count: raise ValueError('Restart replayed a model request.')
        record['historyPreservedVerified'] = True
        if capture_settings(helper) != settings: raise ValueError('Saved settings changed.')
    except BaseException as exc:
        failure = exc; record.update(phase='failed-do-not-resume', error=type(exc).__name__+': '+str(exc))
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
        record.update(modelRequests=len(requests), modelRequestTrace=requests, completedAt=time.time(),
                      unknownOutcome=record['pendingRequest'] is not None or record['pendingLifecycle'] is not None)
        try:
            record['settingsPreserved'] = capture_settings(helper) == settings
            if not record['settingsPreserved']: raise ValueError('Ending saved settings differ.')
        except BaseException as exc:
            record['settingsPreserved'] = False
            if failure is None: failure = exc
        record['phase'] = 'pass' if failure is None else 'failed-do-not-resume'
        atomic(folder/'run.json', record)
    print(json.dumps({key: value for key, value in record.items() if key != 'modelRequestTrace'}))
    if failure is not None: raise failure


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owned-published-first-use-history', action='store_true',
                        help='Separate known post-first-use fixture; preserves the initial formatting failure.')
    prove(first_use=parser.parse_args().owned_published_first_use_history)
