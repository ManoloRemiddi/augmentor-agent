# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Pinned engine installation inputs and exact Docker ownership, without inference."""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import uuid

from memory import hindsight_backport

CACHE_MODELS = ('models--BAAI--bge-small-en-v1.5', 'models--cross-encoder--ms-marco-MiniLM-L-6-v2')
OWNER_LABEL = 'org.augmentor.memory.installation'


def cache_inventory(folder):
    folder = Path(folder).resolve()
    if {p.name for p in folder.iterdir()} != set(CACHE_MODELS):
        raise ValueError('The public cache must contain exactly the two declared model roots.')
    result = {}
    for path in sorted(folder.rglob('*')):
        if path.name in ('token', 'stored_tokens', '.env'):
            raise ValueError('Credentials do not belong in the public model cache.')
        if path.is_symlink():
            if not path.resolve().is_relative_to(folder):
                raise ValueError('A public model-cache link escapes its root.')
            result[path.relative_to(folder).as_posix()] = ['link', os.readlink(path)]
        elif path.is_file():
            result[path.relative_to(folder).as_posix()] = ['file', path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()]
        elif not path.is_dir():
            raise ValueError('Unsupported public model-cache input.')
    return result


def inspect(docker, name, *, missing=False):
    result = subprocess.run(docker + ['inspect', name], capture_output=True, text=True, timeout=20)
    if result.returncode:
        if missing and any(message in result.stderr.lower() for message in ('no such object', 'no such container')):
            return None
        raise ValueError('Docker inspection could not be confirmed; no mutation was authorized.')
    values = json.loads(result.stdout)
    if len(values) != 1 or not isinstance(values[0].get('Id'), str):
        raise ValueError('Docker returned an invalid container identity.')
    return values[0]


def checked(docker, args, **options):
    result = subprocess.run(docker + args, check=False, timeout=120, **options)
    if result.returncode:
        raise ValueError('Docker ' + args[0] + ' did not confirm success; nothing was replayed.')
    return result


def same_container(docker, name, identity, *, stopped=False, owner=None):
    current = inspect(docker, name)
    if current['Id'] != identity:
        raise ValueError('Container identity changed; refuse to manage it.')
    if stopped and current['State']['Running']:
        raise ValueError('The engine is running; stop it deliberately before replacement.')
    if owner is not None and current['Config'].get('Labels', {}).get(OWNER_LABEL) != owner:
        raise ValueError('Container ownership changed; refuse to manage it.')
    return current


def image_ready(docker, image):
    result = subprocess.run(docker + ['image', 'inspect', image], capture_output=True, text=True, timeout=20)
    if result.returncode:
        if not any(message in result.stderr.lower() for message in ('no such image', 'no such object')):
            raise ValueError('Pinned image inspection failed; no download was attempted.')
        checked(docker, ['pull', image], stdout=subprocess.DEVNULL)
        result = subprocess.run(docker + ['image', 'inspect', image], capture_output=True, text=True, timeout=20)
    if result.returncode or json.loads(result.stdout)[0]['Id'] != 'sha256:' + image.split('sha256:')[1]:
        raise ValueError('The local engine image differs from its pinned digest.')


def public_engine_source(docker, image, record):
    """Read only the exact public file from a never-started, uniquely owned image instance."""
    token = uuid.uuid4().hex
    name = 'augmentor-memory-source-' + token
    label = 'org.augmentor.memory.source'
    owner = {'name': name, 'token': token, 'terminal': False}
    record.write_text(json.dumps(owner) + '\n'); record.chmod(0o600)
    identity = None
    try:
        checked(docker, ['create', '--name', name, '--network', 'none', '--label', label + '=' + token,
                         '--entrypoint', '/bin/true', image], capture_output=True, text=True)
        current = inspect(docker, name)
        if current['Config'].get('Labels', {}).get(label) != token or current['State']['Running']:
            raise ValueError('The public source container is not the owned stopped instance.')
        identity = current['Id']; owner['containerId'] = identity
        record.write_text(json.dumps(owner) + '\n')
        value = checked(docker, ['cp', identity + ':' + hindsight_backport.manifest()['containerPath'], '-'], capture_output=True)
        if len(value.stdout) > 2 * 1024 * 1024:
            raise ValueError('The pinned public source exceeds its extraction bound.')
        with tarfile.open(fileobj=io.BytesIO(value.stdout)) as archive:
            files = archive.getmembers()
            if len(files) != 1 or not files[0].isfile() or files[0].size > 2 * 1024 * 1024:
                raise ValueError('The pinned source archive is not one regular public file.')
            return archive.extractfile(files[0]).read()
    finally:
        current = inspect(docker, name, missing=True)
        if current is not None:
            if (identity is not None and current['Id'] != identity or current['State']['Running'] or
                    current['Config'].get('Labels', {}).get(label) != token):
                raise ValueError('Source-container ownership changed; cleanup was refused.')
            checked(docker, ['rm', '-v', current['Id']], stdout=subprocess.DEVNULL)
            if inspect(docker, name, missing=True) is not None:
                raise ValueError('Owned source-container removal was not confirmed.')
        owner['terminal'] = True
        record.write_text(json.dumps(owner) + '\n')


def artifact_path(data, extension, backport):
    digest = hashlib.sha256(extension).hexdigest()
    if backport:
        value = hindsight_backport.manifest()
        digest = hashlib.sha256((digest + ':' + value['resultSha256'] + ':' + value['patchSha256']).encode()).hexdigest()
    return Path(data) / 'memory-engine' / digest


def verify_artifact(folder, extension, backport):
    folder = Path(folder)
    if folder.is_symlink() or folder.parent.is_symlink():
        raise ValueError('Controlled memory artifacts cannot follow a symlink.')
    expected = {'augmentor_memory.py': extension}
    if backport:
        for name in ('LICENSE', 'SOURCE.json', 'refresh-budget.patch'):
            expected[name] = (hindsight_backport.VENDOR / name).read_bytes()
    for name, content in expected.items():
        target = folder / name
        if target.is_symlink() or not target.is_file() or target.read_bytes() != content:
            raise ValueError('Controlled memory artifact differs from its recorded source: ' + name)
    if backport:
        value = hindsight_backport.manifest()
        for name, key in [('original.py', 'baseSha256'), ('memory_engine.py', 'resultSha256')]:
            target = folder / 'source-backport' / name
            if target.is_symlink() or not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != value[key]:
                raise ValueError('Controlled memory backport artifact changed: ' + name)
    allowed = set(expected) | ({'source-owner.json', 'source-backport/original.py', 'source-backport/memory_engine.py'} if backport else set())
    actual = set()
    for file in folder.rglob('*'):
        if file.is_symlink(): raise ValueError('Controlled memory artifact contains a symlink.')
        if file.is_file(): actual.add(file.relative_to(folder).as_posix())
    if actual != allowed:
        raise ValueError('Controlled memory artifact contains unexpected or missing inputs.')
    if backport and json.loads((folder / 'source-owner.json').read_text()).get('terminal') is not True:
        raise ValueError('Public source-container cleanup is not confirmed.')
    return folder


def materialize(docker, image, data, extension, backport):
    target = artifact_path(data, extension, backport)
    if target.is_symlink() or target.parent.is_symlink():
        raise ValueError('Controlled memory artifacts cannot follow a symlink.')
    if target.exists():
        return verify_artifact(target, extension, backport)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    staging = Path(tempfile.mkdtemp(prefix='preparing-', dir=target.parent))
    try:
        file = staging / 'augmentor_memory.py'; file.write_bytes(extension); file.chmod(0o444)
        if backport:
            source = public_engine_source(docker, image, staging / 'source-owner.json')
            hindsight_backport.prepare(source, staging / 'source-backport')
            for name in ('LICENSE', 'SOURCE.json', 'refresh-budget.patch'):
                file = staging / name; shutil.copyfile(hindsight_backport.VENDOR / name, file); file.chmod(0o444)
        verify_artifact(staging, extension, backport)
        staging.chmod(0o755); staging.rename(target)
    except Exception:
        # Keep incomplete source/ownership evidence. Never overwrite or repair a
        # recorded artifact to obtain an installation pass.
        raise
    return verify_artifact(target, extension, backport)
