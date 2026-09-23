#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Stage/activate the additive memory adapter for this Linux voice preview.

No system package files are changed. Activation refuses active DSH work or a
voice connection. Native files are picked up on the next natural app restart.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
import uuid
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services'))
from dsh.setup import current
from dsh.remote import client


def idle(remote):
    rows = remote.call('session.list')['items']
    if any(row.get('running') for row in rows):
        raise RuntimeError('DSH has active work; activation was not performed.')
    try:
        with urllib.request.urlopen('http://127.0.0.1:8877/health', timeout=3) as response:
            if json.load(response).get('active'):
                raise RuntimeError('A voice connection is open; activation was not performed.')
    except urllib.error.URLError:
        raise RuntimeError('Voice state could not be checked; activation was not performed.') from None


def atomic(path, value):
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temporary.write_bytes(value)
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    descriptor = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))/'augmentor/desktop.json'
    if args.activate and descriptor.exists() and json.loads(descriptor.read_text()).get('releaseId'):
        raise RuntimeError('This historical preview updater cannot change a managed desktop release. Follow docs/DESKTOP-DEPLOYMENTS.md and stage a separate candidate.')
    installed = Path('/usr/lib/augmentor')
    preview = Path.home() / '.local/share/resonant-voice/augmentor-preview'
    stamp = time.strftime('%Y%m%d-%H%M%S')
    base = Path.home() / '.local/share/augmentor-memory'
    release = base / 'releases' / stamp
    backup = base / 'backups' / stamp
    if json.loads((installed / 'node_modules/typebox/package.json').read_text())['version'] != '1.3.7':
        raise RuntimeError('The installed TypeBox version differs from the tested runtime.')
    config = current()
    remote = client(config['endpoint'], config['home'])
    presets = [Path(config['home']) / '.agent-presets' / ('augmentor-' + surface + '-product') / 'agent.cordis.yml' for surface in ('linux', 'browser')]
    old_presets = {path: path.read_bytes() for path in presets}
    active_file = base / 'active.json'
    old_root = Path(json.loads(active_file.read_text())['activated']) if active_file.exists() else installed
    old_entry = json.dumps(str(old_root / 'adapters/dsh-memory/index.mjs'))
    if any(text.decode().count(old_entry) != 1 for text in old_presets.values()):
        raise RuntimeError('The current memory binding differs; review it before activation.')
    native = ['apps/native/augmentor_linux/' + name for name in ('memory.py', 'prompt_client.py')]
    native_before = {name: (preview / name).read_bytes() for name in native}
    release.mkdir(parents=True, mode=0o700)
    for directory in ('adapters/dsh-memory', 'dist/memory', 'dist/prompt-library', 'dist/platform', 'services/memory', 'services/lifecycle'):
        shutil.copytree(ROOT / directory, release / directory, ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(ROOT / 'services/platform_support.py', release / 'services/platform_support.py')
    (release / 'services/prompt-library').symlink_to(installed / 'services/prompt-library', target_is_directory=True)
    (release / 'node_modules').mkdir()
    shutil.copytree(installed / 'node_modules/typebox', release / 'node_modules/typebox')
    (release / 'package.json').write_text(json.dumps({'name': 'augmentor-dual-memory-preview', 'version': '1.0.0', 'type': 'module', 'private': True, 'license': 'SEE LICENSE IN LICENSE'}) + '\n')
    shutil.copy2(ROOT / 'LICENSE', release / 'LICENSE')
    manifest = {str(p.relative_to(release)): hashlib.sha256(p.read_bytes()).hexdigest() for p in release.rglob('*') if p.is_file() and not p.is_symlink()}
    (release / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    if not args.activate:
        print(json.dumps({'staged': str(release)}))
        raise SystemExit(0)
    idle(remote)
    backup.mkdir(parents=True, mode=0o700)
    for path, content in old_presets.items():
        atomic(backup / (path.parent.name + '.yml'), content)
    native += ['apps/native/augmentor_linux/dual_memory.py', 'services/memory/dual.py', 'services/memory/service.py', 'services/memory/hindsight.py', 'services/memory/provider.py']
    for name in native:
        target = preview / name
        if target.exists():
            saved = backup / name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
    data = Path(os.environ.get('AUGMENTOR_SHARED_DATA', Path.home() / '.local/share/augmentor'))
    with sqlite3.connect(data / 'dual-memory.sqlite3') as source, sqlite3.connect(backup / 'dual-memory.sqlite3') as target:
        source.backup(target)
    # All reviewable files/backups exist before the final guarded cutover.
    idle(remote)
    if any(path.read_bytes() != content for path, content in old_presets.items()):
        raise RuntimeError('A preset changed during staging; no preset was replaced.')
    if any((preview / name).read_bytes() != content for name, content in native_before.items()):
        raise RuntimeError('Native memory controls changed while staging; no activation performed.')
    for path, content in old_presets.items():
        updated = content.decode().replace(old_entry, json.dumps(str(release / 'adapters/dsh-memory/index.mjs'))).encode()
        atomic(path, updated)
        assert path.read_bytes() == updated
    for name in native:
        target = preview / name
        target.parent.mkdir(parents=True, exist_ok=True)
        atomic(target, (ROOT / name).read_bytes())
    # Do not reload if work/voice became active during the bounded file cutover.
    idle(remote)
    state = Path(os.environ.get('AUGMENTOR_SHARED_STATE', Path.home() / '.local/state/augmentor'))
    endpoint = state / 'dual-memory.sock'
    if endpoint.exists():
        with socket.socket(socket.AF_UNIX) as connection:
            connection.settimeout(10); connection.connect(str(endpoint))
            connection.sendall((json.dumps({'protocol':'augmentor-prompts/1','id':'deployment','method':'memory.dual.describe','params':{}})+'\n').encode())
            response = json.loads(connection.makefile().readline())
        pid = response['result']['pid']
        if b'memory/service.py' not in Path('/proc/' + str(pid) + '/cmdline').read_bytes():
            raise RuntimeError('Memory process identity did not match.')
        os.kill(pid, signal.SIGTERM)
        for _ in range(100):
            if not endpoint.exists(): break
            time.sleep(.1)
        if endpoint.exists(): raise RuntimeError('Old memory companion did not stop.')
    subprocess.Popen([sys.executable, str(release / 'services/memory/service.py')],
                     start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['systemctl', '--user', 'restart', 'dsh-web.service'], check=True)
    result = {'activated': str(release), 'backup': str(backup), 'nativeControls': 'available after natural desktop restart', 'presets': [str(p) for p in presets]}
    (base / 'active.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
