#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Opt-in Linux proof engine; separate database/gateway, existing public model cache only."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import time
import urllib.request
from urllib.parse import urlsplit
import uuid

CACHE_MODELS = ('models--BAAI--bge-small-en-v1.5', 'models--cross-encoder--ms-marco-MiniLM-L-6-v2')


def provider(value):
    if not isinstance(value, dict) or set(value) != {'api', 'baseUrl', 'models'} or value['api'] != 'openai-completions':
        raise ValueError('Supply only the local provider api, baseUrl and one model; credentials are not accepted.')
    url = urlsplit(value['baseUrl'])
    if url.scheme != 'http' or url.hostname != '127.0.0.1' or url.username or url.password or url.query or url.fragment or url.path.rstrip('/') != '/v1':
        raise ValueError('Use an unauthenticated numeric-loopback /v1 model endpoint.')
    models = value['models']
    allowed = {'id', 'name', 'reasoning', 'input', 'contextWindow', 'maxTokens', 'cost'}
    if not isinstance(models, list) or len(models) != 1 or not isinstance(models[0], dict) or set(models[0]) - allowed:
        raise ValueError('Supply one explicit public model declaration.')
    model = models[0]
    if not isinstance(model.get('id'), str) or model.get('contextWindow') != 262144 or model.get('maxTokens') != 8192:
        raise ValueError('Preserve the qualified local 262144 context and 8192 output declaration.')
    return model


def cache_inventory(root):
    """Only public model-cache directories, no hub credential or escaping link."""
    root = root.resolve()
    result = {}
    if {p.name for p in root.iterdir()} != set(CACHE_MODELS):
        raise ValueError('The proof cache must contain exactly the two declared public models.')
    for path in sorted(root.rglob('*')):
        if path.name in ('token', 'stored_tokens', '.env'):
            raise ValueError('Credentials do not belong in the public model proof cache.')
        if path.is_symlink():
            if not path.resolve().is_relative_to(root):
                raise ValueError('A cached model link escapes the isolated public cache.')
            result[path.relative_to(root).as_posix()] = ['link', os.readlink(path)]
        elif path.is_file():
            result[path.relative_to(root).as_posix()] = ['file', path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()]
        elif not path.is_dir():
            raise ValueError('Unsupported model cache input.')
    return result


def run(args, **kwargs):
    return subprocess.check_output(args, text=True, timeout=kwargs.pop('timeout', 45), **kwargs).strip()


def inspect(name):
    return json.loads(run(['docker', 'inspect', name]))[0]


def identity(value):
    # Includes environment in the digest, never in a public result or console.
    return hashlib.sha256(json.dumps({k: value[k] for k in ('Id', 'Image', 'Config', 'HostConfig', 'Mounts')}, sort_keys=True).encode()).hexdigest()


def same_instance(value, expected_id):
    if value['Id'] != expected_id:
        raise ValueError('Container identity changed; refuse to manage this instance.')


def write(path, value):
    with path.open('x') as stream:
        path.chmod(0o600)
        json.dump(value, stream, indent=2)
        stream.write('\n')


def free_port():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        return listener.getsockname()[1]


def prepare(args):
    if os.name != 'posix' or not Path('/proc/meminfo').exists():
        raise ValueError('This isolated Docker proof is currently Linux-only.')
    root = Path(args.root).resolve()
    if root.stat().st_mode & 0o077 or not (root / 'proof-owner.json').is_file() or (root / 'engine.json').exists():
        raise ValueError('Use a fresh private proof directory with its ownership marker.')
    declaration = json.loads(Path(args.provider_json).read_text()); model = provider(declaration)
    spec = importlib.util.spec_from_file_location('proof_setup_hindsight', Path(__file__).with_name('setup-hindsight.py'))
    setup = importlib.util.module_from_spec(spec); spec.loader.exec_module(setup)
    baseline = inspect(args.cache_container)
    if not baseline['State']['Running'] or baseline['Image'] != 'sha256:' + setup.IMAGE.split('sha256:')[1]:
        raise ValueError('The existing cache container must run the exact pinned Hindsight image.')
    env = dict(row.split('=', 1) for row in baseline['Config']['Env'] if '=' in row)
    if env.get('HINDSIGHT_API_LLM_MODEL') != model['id']:
        raise ValueError('The proof model differs from the configured memory engine; no setting was changed.')
    extras = [json.loads(env.get('HINDSIGHT_API_' + op + 'LLM_EXTRA_BODY', 'null')) for op in ('', 'RETAIN_', 'REFLECT_', 'CONSOLIDATION_')]
    if all(value is None for value in extras): thinking = 'default'
    elif all(value == {'chat_template_kwargs': {'enable_thinking': False}} for value in extras): thinking = 'off'
    else: raise ValueError('The existing memory request policy is not the supported uniform default/off choice.')
    available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))
    if available < 10 * 1024 * 1024:
        raise ValueError('Insufficient free host memory for a separate bounded proof engine; existing workloads remain untouched.')
    cache = root / 'model-cache'; cache.mkdir(mode=0o755)
    for name in CACHE_MODELS:
        run(['docker', 'cp', args.cache_container + ':/home/hindsight/.cache/huggingface/hub/' + name, str(cache / name)])
    inventory = cache_inventory(cache)
    extension = root / 'engine-extension'; extension.mkdir(mode=0o755)
    source = Path(__file__).resolve().parents[1] / 'services/memory/hindsight_extension.py'
    shutil.copyfile(source, extension / 'augmentor_memory.py'); (extension / 'augmentor_memory.py').chmod(0o444)
    port, gateway, postgres = free_port(), free_port(), free_port()
    if len({port, gateway, postgres}) != 3: raise ValueError('Port reservation collision; preserve this preparation for inspection.')
    key = secrets.token_urlsafe(32); name = 'augmentor-pi-memory-proof-' + uuid.uuid4().hex
    configuration = {**setup.environment(model['id'], port, gateway, llama_cpp_thinking=thinking),
                     'HINDSIGHT_API_LLM_API_KEY': key, 'HINDSIGHT_API_HTTP_KEY': key,
                     'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'HF_HUB_DISABLE_TELEMETRY': '1',
                     'DO_NOT_TRACK': '1', 'OTEL_SDK_DISABLED': 'true', 'PYTHONDONTWRITEBYTECODE': '1'}
    configuration['HINDSIGHT_API_DATABASE_URL'] = 'pg0://hindsight:' + str(postgres)
    envfile = root / 'engine.env'
    with envfile.open('x') as stream:
        envfile.chmod(0o600)
        for label, value in configuration.items():
            if '\n' in value or '\r' in value: raise ValueError('Invalid engine environment value.')
            stream.write(label + '=' + value + '\n')
    record = {'name': name, 'volume': name + '-data', 'port': port, 'gatewayPort': gateway, 'postgresPort': postgres,
              'image': setup.IMAGE, 'baselineContainer': args.cache_container, 'baselineId': baseline['Id'],
              'baselineIdentity': identity(baseline), 'cacheManifest': inventory,
              'extensionSha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'llamaCppThinking': thinking,
              'model': model['id'], 'created': False}
    write(root / 'engine.json', record)
    run(['docker', 'volume', 'create', record['volume']])
    container_id = run(['docker', 'run', '-d', '--pull=never', '--name', name, '--label', 'org.augmentor.proof=' + name,
         '--restart=no', '--network=host', '--cpus=4', '--memory=8g',
         '-v', record['volume'] + ':/home/hindsight/.pg0', '-v', str(extension) + ':/augmentor:ro',
         '-v', str(cache) + ':/home/hindsight/.cache/huggingface/hub:ro', '--env-file', str(envfile), setup.IMAGE])
    record.update(created=True, containerId=container_id)
    (root / 'engine.json').write_text(json.dumps(record, indent=2) + '\n')
    endpoint = 'http://127.0.0.1:' + str(port)
    shared = root / 'shared-data'; shared.mkdir(mode=0o700, exist_ok=True)
    write(shared / 'hindsight.json', {'endpoint': endpoint, 'version': '0.10.0', 'image': setup.IMAGE,
          'processingProtocol': setup.PROTOCOL, 'gatewayPort': gateway, 'gatewayKey': key,
          'modelUrl': declaration['baseUrl'].rstrip('/'), 'modelKey': 'not-required', 'llamaCppThinking': thinking})
    print(json.dumps({'phase': 'isolated-engine-created', 'port': port, 'gatewayPort': gateway, 'newWeightsDownloaded': False}), flush=True)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        current = inspect(name); same_instance(current, record['containerId'])
        if not current['State']['Running']: raise ValueError('The isolated engine exited; inspect its private logs without restarting it.')
        try:
            with urllib.request.urlopen(endpoint + '/health', timeout=2) as response: healthy = json.load(response)['status'] == 'healthy'
            with urllib.request.urlopen(endpoint + '/ext/augmentor/policy', timeout=2) as response: policy = json.load(response)
            if healthy and policy == {'protocol': setup.PROTOCOL, 'workerEnabled': False, 'reconcileSeconds': 0, 'llmRetries': 0}: break
        except Exception: pass
        time.sleep(.25)
    else: raise ValueError('The isolated engine did not become healthy within its proof preparation bound.')
    if identity(inspect(args.cache_container)) != record['baselineIdentity']: raise ValueError('The original engine identity/configuration changed during preparation.')
    print(json.dumps({'phase': 'isolated-engine-ready', 'port': port, 'gatewayPort': gateway, 'cacheFiles': len(inventory), 'originalEngineUnchanged': True}), flush=True)


def stop(args):
    root = Path(args.root).resolve(); record = json.loads((root / 'engine.json').read_text())
    if not record['name'].startswith('augmentor-pi-memory-proof-'): raise ValueError('Not a proof-owned container.')
    found = subprocess.run(['docker', 'inspect', record['name']], capture_output=True, text=True, timeout=10)
    if found.returncode:
        if record.get('created'): raise ValueError('The recorded proof container disappeared; preserve its evidence.')
        return
    current = json.loads(found.stdout)[0]
    if current['Config'].get('Labels', {}).get('org.augmentor.proof') != record['name']:
        raise ValueError('The container is not owned by this proof.')
    if record.get('containerId'): same_instance(current, record['containerId'])
    if current['State']['Running']: run(['docker', 'stop', '--time', '30', record['name']])
    assert not inspect(record['name'])['State']['Running']
    if identity(inspect(record['baselineContainer'])) != record['baselineIdentity']: raise ValueError('The original memory engine changed; preserve evidence for inspection.')
    if cache_inventory(root / 'model-cache') != record['cacheManifest']: raise ValueError('The read-only public model cache changed.')
    print(json.dumps({'phase': 'isolated-engine-stopped', 'originalEngineUnchanged': True, 'cacheUnchanged': True, 'privateDatabasePreserved': True}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('action', choices=['prepare', 'stop']); parser.add_argument('--root', required=True)
    parser.add_argument('--provider-json'); parser.add_argument('--cache-container', default='augmentor-hindsight')
    options = parser.parse_args()
    if options.action == 'prepare':
        if not options.provider_json: parser.error('prepare requires --provider-json')
        prepare(options)
    else: stop(options)
