#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Stage, select and inspect recorded desktop releases without interrupting work."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import uuid

DATA = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))/'augmentor'
MANIFEST = 'desktop-release.json'


def read(path):
    return json.loads(path.read_text())


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix='.'+path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, indent=2); stream.write('\n')
            stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(descriptor)
        finally: os.close(descriptor)
    finally:
        if os.path.exists(name): os.unlink(name)


@contextmanager
def locked():
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (DATA/'deployment.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if '__pycache__' in relative.parts or path.suffix == '.pyc' or str(relative) == MANIFEST:
            continue
        if path.is_symlink():
            # External links would let a subsequent source edit change a release.
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError('Release contains an external symlink: '+str(relative))
            result[str(relative)] = 'link:'+os.readlink(path)
        elif path.is_file():
            result[str(relative)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def verify(root):
    value = read(root/MANIFEST)
    actual = inventory(root)
    if value['files'] != actual:
        raise ValueError('Release files changed after staging; stage a new release.')
    digest = hashlib.sha256(json.dumps(actual, sort_keys=True).encode()).hexdigest()
    if value['artifactSha256'] != digest:
        raise ValueError('Release inventory identity does not match.')
    return value


def check(config, connected=False):
    root = Path(config['root'])
    if '--ensure-running' not in (root/'apps/native/augmentor_linux/window.py').read_text():
        raise ValueError('This build lacks the supervised startup protocol.')
    env = {**os.environ, 'PYTHONPATH':str(root/'apps/native'),
           'PYTHONDONTWRITEBYTECODE':'1', 'QT_QPA_PLATFORM':'offscreen',
           'AUGMENTOR_PI_NODE':config['node']}
    code = 'from augmentor_linux import window, controller\n'
    if connected and config.get('dshService'):
        # This reads the matching product identity and model catalog. No prompts,
        # new chats, runtime restarts or configuration writes are involved.
        code += 'from augmentor_linux.adapters.dsh import DshAdapter\nadapter = DshAdapter()\n'
        code += 'if not adapter.product: raise RuntimeError("The candidate is not connected to the product integration.")\n'
        if config.get('dshEndpoint') and config.get('dshHome'):
            code += ('if adapter.base != '+repr(config['dshEndpoint'])+' or str(adapter.home) != '+repr(config['dshHome'])+
                     ': raise RuntimeError("The runtime configuration changed; refresh the startup registry before staging.")\n')
        code += 'adapter.call("host.describe")\n'
    result = subprocess.run([config['python'], '-c', code], cwd=root, env=env,
                            capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError('Candidate import/connection check failed:\n'+result.stderr[-3000:])
    subprocess.run([config['node'], '--version'], check=True, capture_output=True, timeout=10)


def stage(source, source_ref, python=None, node=None):
    source = Path(source).resolve()
    current = read(DATA/'desktop.json')
    releases = DATA/'releases'; releases.mkdir(parents=True, exist_ok=True)
    if releases.resolve().is_relative_to(source):
        raise ValueError('The candidate source cannot contain the release store.')
    name = time.strftime('%Y%m%d-%H%M%S-')+uuid.uuid4().hex[:8]
    temporary = releases/('.staging-'+name)
    final = releases/name
    temporary.mkdir(mode=0o700)
    try:
        # Copy the runnable artifact, never an entire checkout or user data.
        for part in ('apps', 'services', 'adapters', 'dist', 'config', 'licenses', 'scripts', 'node', 'node_modules', 'release', 'docs'):
            if (source/part).is_dir():
                shutil.copytree(source/part, temporary/part, symlinks=True,
                                ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.git', '.env', 'outputs'))
        for part in ('package.json', 'package-lock.json', 'release.json', 'LICENSE', 'README.md', 'distribution-exclusions.json', 'distribution-overrides.json'):
            if (source/part).is_file():
                target = temporary/part; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source/part, target)
        config = dict(current, root=str(temporary), python=str(Path(python or current['python']).absolute()),
                      node=str(Path(node or current['node']).absolute()))
        # A bundled interpreter follows the copy; venv symlinks must not resolve.
        for key in ('python', 'node'):
            path = Path(config[key])
            if path.is_relative_to(source): config[key] = str(temporary/path.relative_to(source))
        config['version'] = read(temporary/'release/product.json')['version']
        check(config)
        files = inventory(temporary)
        digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
        config.update(root=str(final), releaseId=name, sourceRef=source_ref, artifactSha256=digest)
        for key in ('python', 'node'):
            if Path(config[key]).is_relative_to(temporary):
                config[key] = str(final/Path(config[key]).relative_to(temporary))
        # Remove inherited partial hashes; the complete inventory owns identity.
        config.pop('files', None); config.pop('windowSha256', None)
        atomic(temporary/MANIFEST, {'deployment':config, 'files':files, 'artifactSha256':digest})
        temporary.rename(final)
        return final
    finally:
        if temporary.exists(): shutil.rmtree(temporary)


def activate(root):
    root = Path(root).resolve()
    release = verify(root)
    config = release['deployment']
    if Path(config['root']) != root:
        raise ValueError('Release moved after staging; stage it again at its final location.')
    check(config, connected=True)
    # Preflight is allowed to import modules but cannot alter staged files.
    verify(root)
    previous = read(DATA/'desktop.json')
    if previous == config: return config
    atomic(DATA/'desktop.previous.json', previous)
    # The only commit point: interruption before this keeps the old selection;
    # interruption after it leaves a complete, validated new selection.
    atomic(DATA/'desktop.json', config)
    return config


def rollback():
    previous = read(DATA/'desktop.previous.json')
    if (Path(previous['root'])/MANIFEST).exists(): verify(Path(previous['root']))
    check(previous, connected=True)
    current = read(DATA/'desktop.json')
    atomic(DATA/'desktop.json', previous)
    atomic(DATA/'desktop.previous.json', current)
    return previous


def status():
    config = read(DATA/'desktop.json')
    spec = importlib.util.spec_from_file_location('desktop_launch', Path(__file__).with_name('desktop-launch.py'))
    launch = importlib.util.module_from_spec(spec); spec.loader.exec_module(launch)
    running = {name:launch.exchange('maintenance.status', suffix) for name, suffix in
               (('desktop',''), ('mobile','-mobile'), ('secondary','-secondary'))}
    return {'selected':{key:config.get(key) for key in ('root','version','releaseId','sourceRef','artifactSha256')},
            'running':{key:({'buildRoot':value.get('buildRoot'), 'online':value.get('online'),
                'voiceAvailable':value.get('voiceAvailable'), 'updatePending':value.get('buildRoot') != config['root']} if value else None)
                for key,value in running.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    staging = commands.add_parser('stage'); staging.add_argument('root', type=Path)
    staging.add_argument('--source-ref', required=True, help='Tested commit or explicit mixed-artifact provenance.')
    staging.add_argument('--python', type=Path); staging.add_argument('--node', type=Path)
    activation = commands.add_parser('activate'); activation.add_argument('root', type=Path)
    commands.add_parser('rollback'); commands.add_parser('status')
    args = parser.parse_args()
    if args.command == 'status': print(json.dumps(status(), indent=2)); return
    with locked():
        if args.command == 'stage':
            print(stage(args.root, args.source_ref, args.python, args.node)); return
        result = activate(args.root) if args.command == 'activate' else rollback()
        print('Selected '+result['root']+'\nExisting windows keep their current build until closed or the next login.')


if __name__ == '__main__':
    try: main()
    except Exception as error: raise SystemExit('Desktop deployment failed: '+str(error))
