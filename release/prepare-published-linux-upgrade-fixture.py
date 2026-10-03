#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One-shot initial setup for the explicitly owned Debian product-upgrade fixture.

This prepares the published0.2.12 baseline. It does not prove an upgrade, launch
model turns, provision speech/memory engines, or operate a customer installation.
Native packages must already be installed through the signed package manager.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import threading
import time
import http.server

HOME = Path('/home/augmentor-version-proof')
BUNDLE = Path('/opt/augmentor-version-proof150/augmentor-0.2.12-complete-preview.1')
APP = Path('/usr/lib/augmentor')
SOURCE = 'e02731023153e3b2e1440e50b8c14b64ad0a82e5'
MANIFEST_SHA = '753dd0136ebcfcb11b8c77f7c888db805f4a41f7a3cdb5efe884795747ad67dc'
SETUP_SHA = 'a5d3443bb6b284b2082ffe5f3571fc22faaf7f66700040876e540bbbb966e7a1'
MARKER = 'Isolated Augmentor published product-version Debian13 container150\n'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def root_file(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o022:
        raise ValueError('A public fixture input is not an ordinary immutable root-owned file.')
    for parent in path.parents:
        directory = parent.lstat()
        if not stat.S_ISDIR(directory.st_mode) or directory.st_uid != 0 or directory.st_mode & 0o022:
            raise ValueError('A fixture input ancestor is not an immutable root-owned directory.')


def admit():
    if os.getuid() != 1000 or Path.home() != HOME or HOME.is_symlink():
        raise ValueError('Only the dedicated ordinary fixture account is supported.')
    info = HOME.lstat()
    if info.st_uid != 1000 or info.st_mode & 0o077:
        raise ValueError('The dedicated fixture home must remain private.')
    marker = Path('/etc/augmentor-test-container'); root_file(marker)
    if marker.read_text() != MARKER:
        raise ValueError('This is not the explicitly owned isolated fixture.')
    root_file(BUNDLE/'bundle.json'); root_file(BUNDLE/'setup.py')
    if digest(BUNDLE/'bundle.json') != MANIFEST_SHA or digest(BUNDLE/'setup.py') != SETUP_SHA:
        raise ValueError('The published baseline inputs differ.')
    manifest = json.loads((BUNDLE/'bundle.json').read_text())
    if (manifest['sourceCommit'], manifest['target'], manifest['version']) != (SOURCE, 'debian13-amd64', '0.2.12'):
        raise ValueError('The published product/target identity differs.')
    for name, expected in manifest['sha256'].items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('A bundle member escapes its owned root.')
        path = BUNDLE/relative; root_file(path)
        if digest(path) != expected:
            raise ValueError('A public bundle member checksum differs.')
    metadata = json.loads((APP/'release.json').read_text())
    if (metadata['source']['commit'], metadata['source']['dirty'], metadata['target'], metadata['version']) != (SOURCE, False, 'debian13-amd64', '0.2.12'):
        raise ValueError('The installed native baseline differs.')
    for package in ('augmentor-runtime', 'augmentor-desktop'):
        check = subprocess.run(['dpkg', '-V', package], capture_output=True, text=True, check=True)
        if check.stdout.strip() or check.stderr.strip():
            raise ValueError('The installed native baseline audit differs.')
    for path in (HOME/'.local/share/augmentor', HOME/'.local/state/augmentor-install', HOME/'.config/augmentor', HOME/'.dsh'):
        if path.exists() or path.is_symlink():
            raise ValueError('Prior product state is preserved; preparation never resumes or adopts it.')
    return manifest


def atomic(path, value):
    temporary = path.with_name(path.name+'.new')
    with temporary.open('x') as stream:
        json.dump(value, stream, indent=2); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    temporary.replace(path)
    fd = os.open(path.parent, os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def prepare():
    os.umask(0o077); manifest = admit()
    folder = HOME/'.local/state/published-product-upgrade150'
    folder.mkdir(parents=True, mode=0o700, exist_ok=False)
    requests = []
    class Model(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_POST(self):
            requests.append({'path': self.path, 'time': time.time()})
            self.send_error(503, 'No model turn is authorized during initial preparation.')
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Model)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    import socket
    with socket.socket() as available:
        available.bind(('127.0.0.1', 0)); dsh_port = available.getsockname()[1]
    env = {**os.environ, 'AUGMENTOR_FIXTURE_KEY': 'published-upgrade-synthetic-fixture',
           'QT_QPA_PLATFORM': 'offscreen', 'DSH_TELEMETRY_MODE': 'DISABLED'}
    command = ['/usr/bin/python3', '-B', str(BUNDLE/'setup.py'), '--bundle', str(BUNDLE),
               '--skip-packages', '--no-services', '--non-interactive', '--model-url',
               f'http://127.0.0.1:{server.server_port}/v1', '--model', 'fixture',
               '--api-key-env', 'AUGMENTOR_FIXTURE_KEY', '--port', str(dsh_port)]
    record = {'format': 'augmentor-published-upgrade-baseline-preparation/1', 'phase': 'pending-one-installer',
              'source': SOURCE, 'artifactId': manifest['artifactId'], 'target': manifest['target'],
              'proofSha256': digest(Path(__file__)), 'bundleManifestSha256': MANIFEST_SHA,
              'setupSha256': SETUP_SHA, 'modelPort': server.server_port, 'dshPort': dsh_port,
              'argv': command, 'startedAt': time.time(), 'upgradeQualified': False}
    atomic(folder/'run.json', record)
    try:
        with (folder/'initial-setup.log').open('xb') as log:
            result = subprocess.run(command, env=env, cwd=HOME, stdout=log, stderr=subprocess.STDOUT)
        record.update(installerExitCode=result.returncode, modelRequests=requests, completedAt=time.time())
        if result.returncode or requests:
            raise ValueError('Initial preparation failed; preserve its state and never replay this installer.')
        stamp = json.loads((HOME/'.local/state/augmentor-install/installation.json').read_text())
        if stamp['bundle'] != manifest['artifactId'] or stamp['status'] != 'installed':
            raise ValueError('The initial installed receipt differs.')
        record.update(phase='prepared-published012-baseline', installerMatchesPublishedBundle=True,
                      ordinaryUser=True, modelTurnsExecuted=False, speechMemoryEnginesProvisioned=False,
                      graphicalSessionTested=False, upgradeQualified=False)
        atomic(folder/'run.json', record)
        print(json.dumps(record))
    except BaseException:
        record.update(phase='failed-do-not-resume', modelRequests=requests)
        atomic(folder/'run.json', record)
        raise
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


if __name__ == '__main__':
    prepare()
