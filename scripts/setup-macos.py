#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Provision a private, bundled DSH runtime for a fresh macOS desktop user.

The GUI can install the engine before a model is configured. Optional model
configuration arrives through stdin. Secrets never appear in process
arguments, launchd plists or progress output. Existing external DSH connections
are never adopted or modified by this first-run path.
"""
import argparse
import json
import os
from pathlib import Path
import plistlib
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LABEL = 'com.augmentor.Agent.DSH'
sys.path.insert(0, str(ROOT/'services'))
from dsh import managed as common
from dsh.managed import SCHEMA, BUNDLES, load_complete, initialize_voice, probe_model
from platform_adapters.private_files import require_directory as private_directory, read_json as private_json, atomic_json


def model_configuration(root, request):
    return common.model_configuration(root, request, complete=load_complete(root))


def provision(root, state, request, *, agent=None, probe=probe_model, progress=lambda phase: None):
    return common.provision(root, state, request, agent=agent or LaunchAgent(root, state),
        manager_type='launchd', complete=load_complete(root), voice_initializer=initialize_voice,
        probe=probe, progress=progress)


def installed_location(root):
    app = root.parents[2]
    if root != app/'Contents/Resources/app' or app.parent not in (Path('/Applications'), Path.home()/'Applications'):
        raise ValueError('Drag Augmentor into Applications, then open that copy to set it up.')
    info = plistlib.loads((app/'Contents/Info.plist').read_bytes())
    if info.get('CFBundleIdentifier') != 'com.augmentor.Agent':
        raise ValueError('Use the installed Augmentor desktop application.')


def service_plist(root, state, label=LABEL):
    return plistlib.dumps({'Label': label,
        'ProgramArguments': [str(root/'python/bin/python3'), '-I', '-B', str(root/'scripts/setup-macos.py'),
                             '--run-service', str(state)],
        'RunAtLoad': True, 'KeepAlive': True, 'ThrottleInterval': 10, 'Umask': 0o077,
        # This host serves foreground chat and tools. Background applies
        # launchd's restrictive CPU/I/O limits to work the user is waiting for.
        'ProcessType': 'Interactive', 'WorkingDirectory': str(state/'home'),
        'StandardOutPath': str(state/'runtime.log'), 'StandardErrorPath': str(state/'runtime.log')})


class LaunchAgent:
    def __init__(self, root, state, directory=None, label=LABEL):
        self.label = label; self.state = state
        self.path = (directory or Path.home()/'Library/LaunchAgents')/(label+'.plist')
        self.content = service_plist(root, state, label)
        self.target = f'gui/{os.getuid()}/{label}'

    def loaded(self):
        return subprocess.run(['launchctl', 'print', self.target], capture_output=True, timeout=10).returncode == 0

    def owned(self):
        if not self.path.exists() and not self.path.is_symlink():
            return False
        info = self.path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1 or self.path.read_bytes() != self.content:
            raise ValueError('An existing DSH login service differs. It was preserved.')
        return True

    def start(self):
        owned = self.owned()
        if self.loaded():
            if not owned:
                raise ValueError('A different DSH login service is already registered. It was preserved.')
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not owned:
            descriptor = os.open(self.path, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(self.content); stream.flush(); os.fsync(stream.fileno())
        result = subprocess.run(['launchctl', 'bootstrap', f'gui/{os.getuid()}', str(self.path)], capture_output=True, timeout=20)
        if result.returncode:
            raise ValueError('The Augmentor background service could not start. Its private setup data was retained for retry.')

    def stop_failed_setup(self):
        # Only used before the connection is offered to any Augmentor surface.
        if not self.owned():
            return
        if self.loaded():
            result = subprocess.run(['launchctl', 'bootout', self.target], capture_output=True, timeout=20)
            # bootout acknowledges removal before launchd has finished draining
            # the job. Do not delete files or start a replacement during that gap.
            deadline = time.monotonic()+35
            while time.monotonic() < deadline:
                if not self.loaded(): return
                time.sleep(.2)
            raise ValueError('The setup service is still active. Its files were preserved.')


def run_service(state):
    private_directory(state)
    config = private_json(state/'runtime.json')
    if config.get('schema') != SCHEMA or config.get('appRoot') != str(ROOT) or config.get('home') != str(state/'home'):
        raise ValueError('The managed service configuration does not match this application.')
    if not isinstance(config.get('port'), int) or not 1024 <= config['port'] <= 65535:
        raise ValueError('Invalid managed service port.')
    sys.path.insert(0, str(ROOT/'services/lifecycle'))
    from lease import hold
    env = {**os.environ, **config['environment'], 'DSH_HOME': config['home'],
           'DSH_TELEMETRY_MODE': 'DISABLED', 'AUGMENTOR_MODEL_API_KEY': config['apiKey'],
           'PYTHONDONTWRITEBYTECODE': '1'}
    env.pop('NODE_OPTIONS', None); env.pop('NODE_PATH', None)
    env['PATH'] = os.pathsep.join([str(ROOT/'node/bin'), str(ROOT/'python/bin'),
                                 str(ROOT/'dsh/node_modules/.bin'), env.get('PATH', os.defpath)])
    os.environ.update(config['environment'])
    hold('runtime')
    node = ROOT/'node/bin/node'
    cli = (ROOT/'dsh/node_modules/.bin/dsh').resolve(strict=True)
    os.execve(node, [str(node), str(cli), 'web', '--no-open', '--host', '127.0.0.1', '--port', str(config['port'])], env)


def start_saved(saved):
    """Recovery must restart the registered owner with its provider credentials."""
    manager = saved.get('managed', {})
    if manager.get('type') != 'launchd' or manager.get('label') != LABEL:
        raise ValueError('Unrecognized managed DSH service.')
    state = Path(manager['state']); private_directory(state)
    record = private_json(state/'setup.json')
    if (record.get('schema') != SCHEMA or record.get('status') != 'ready' or
            record.get('appRoot') != str(ROOT) or record.get('home') != saved.get('home') or
            record.get('endpoint') != saved.get('endpoint')):
        raise ValueError('The managed DSH ownership record does not match this connection.')
    agent = LaunchAgent(ROOT, state)
    if not agent.owned():
        raise ValueError('The managed DSH login service was removed. Its data was preserved.')
    agent.start()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-service', type=Path)
    parser.add_argument('--progress', action='store_true', help='Emit fixed setup phases as JSON lines for the app')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('This setup is for macOS.')
    os.umask(0o077)
    if args.run_service:
        run_service(args.run_service); return
    try:
        installed_location(ROOT)
        raw = sys.stdin.buffer.read(16385)
        if len(raw) > 16384:
            raise ValueError('Setup request exceeds its size limit.')
        request = json.loads(raw)
        base = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'Library/Application Support/Augmentor/data'))
        def progress(phase):
            if args.progress: print(json.dumps({'phase': phase}), flush=True)
        result = provision(ROOT, base/'augmentor/managed-dsh', request, progress=progress)
        print(json.dumps({'ok': True, **result}))
    except Exception as error:
        # Never include provider response bodies or the input request here.
        print(json.dumps({'ok': False, 'error': str(error) if isinstance(error, ValueError)
                          else 'Setup could not finish. Its private data was retained for diagnosis and retry.'}))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
