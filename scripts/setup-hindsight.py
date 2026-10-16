#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Install controlled Hindsight 0.10.0; preserve chat models and memory data."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import secrets
import tempfile
import uuid
import subprocess
import sys
import tarfile
import time
import urllib.request
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services'))
from memory.budget import CALL_SECONDS
from memory import hindsight_backport
from memory.engine_install import OWNER_LABEL, artifact_path, cache_inventory, checked, image_ready, inspect, materialize, same_container, verify_artifact

IMAGE = 'ghcr.io/vectorize-io/hindsight@sha256:3edcb6165cefdeaa6721dd0fce43cfd13b7a9c346ce0d2c5f4b4bf7bc3c8ac0b'
PROTOCOL = 'augmentor-memory-processing/1'


def environment(model, port, gateway_port, *, llama_cpp_thinking='default', postgres_port=None, offline=False):
    if llama_cpp_thinking not in ('default', 'off'):
        raise ValueError('Invalid memory-only llama.cpp thinking mode.')
    extra = json.dumps({'chat_template_kwargs': {'enable_thinking': False}}, separators=(',', ':')) if llama_cpp_thinking == 'off' else 'null'
    value = {'HINDSIGHT_API_LLM_MODEL': model, 'HINDSIGHT_API_LLM_BASE_URL': f'http://127.0.0.1:{gateway_port}/v1',
        'HINDSIGHT_API_PORT': str(port), 'HINDSIGHT_ENABLE_CP': 'false', 'HINDSIGHT_API_HOST': '127.0.0.1',
        'HINDSIGHT_API_LLM_PROVIDER': 'openai', 'HINDSIGHT_API_WORKER_ENABLED': 'false',
        # Hindsight 0.10.0 otherwise selects its shorter 30-second Reflect
        # default. All operation clients must honor our existing call ceiling.
        'HINDSIGHT_API_LLM_TIMEOUT': str(CALL_SECONDS),
        'HINDSIGHT_API_ENABLE_AUTO_CONSOLIDATION': 'false', 'HINDSIGHT_API_CONSOLIDATION_RECONCILE_INTERVAL_SECONDS': '0',
        'HINDSIGHT_API_MENTAL_MODEL_REFRESH_TICK_SECONDS': '0', 'HINDSIGHT_API_SKIP_LLM_VERIFICATION': 'true',
        'HINDSIGHT_API_LLM_MAX_RETRIES': '0', 'HINDSIGHT_API_WORKER_MAX_RETRIES': '0',
        'HINDSIGHT_API_RETAIN_LLM_MAX_RETRIES': '0', 'HINDSIGHT_API_REFLECT_LLM_MAX_RETRIES': '0',
        'HINDSIGHT_API_CONSOLIDATION_LLM_MAX_RETRIES': '0', 'HINDSIGHT_API_CONSOLIDATION_MAX_ATTEMPTS': '1',
        'HINDSIGHT_API_LLM_MAX_CONCURRENT': '1', 'HINDSIGHT_API_RETAIN_MAX_CONCURRENT': '1',
        'HINDSIGHT_API_CONSOLIDATION_LLM_PARALLELISM': '1',
        'HINDSIGHT_API_REFLECT_MAX_ITERATIONS': '2', 'HINDSIGHT_API_REFLECT_MAX_CONTEXT_TOKENS': '8000',
        'HINDSIGHT_API_REFLECT_SOURCE_FACTS_MAX_TOKENS': '1200', 'HINDSIGHT_API_REFLECT_MAX_COMPLETION_TOKENS': '4096',
        'HINDSIGHT_API_EMBEDDINGS_LOCAL_FORCE_CPU': 'true', 'HINDSIGHT_API_RERANKER_LOCAL_FORCE_CPU': 'true',
        'HINDSIGHT_API_RERANKER_LOCAL_MAX_CONCURRENT': '1',
        'HINDSIGHT_API_HTTP_EXTENSION': 'augmentor_memory:ControlledMemory',
        'HINDSIGHT_API_HTTP_GATEWAY': f'http://127.0.0.1:{gateway_port}', 'PYTHONPATH': '/augmentor'}
    value.update(HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1', OTEL_SDK_DISABLED='true', PYTHONDONTWRITEBYTECODE='1')
    if postgres_port is not None: value['HINDSIGHT_API_DATABASE_URL'] = f'pg0://hindsight:{postgres_port}'
    if offline: value.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    # Use the pinned engine's supported request-body configuration for every
    # operation. This affects only this memory client, never the model server.
    for operation in ('', 'RETAIN_', 'REFLECT_', 'CONSOLIDATION_'):
        value['HINDSIGHT_API_' + operation + 'LLM_EXTRA_BODY'] = extra
    return value


def environment_matches(actual, expected):
    # Missing extra-body settings are the pinned engine's JSON-null defaults.
    # A configured off mode must not be silently reused as default or vice versa.
    return all(actual.get(key, 'null' if key.endswith('_LLM_EXTRA_BODY') else None) == value
               for key, value in expected.items())


def atomic(path, value):
    fd, temporary = tempfile.mkstemp(prefix=path.name + '-', dir=path.parent)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, indent=2); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def mounts_match(container, artifact, volume, backport, cache):
    expected = {'/augmentor': ('bind', str(artifact), False), '/home/hindsight/.pg0': ('volume', volume, True)}
    if backport:
        expected[hindsight_backport.manifest()['containerPath']] = ('bind', str(artifact / 'source-backport/memory_engine.py'), False)
    if cache: expected['/home/hindsight/.cache/huggingface/hub'] = ('bind', str(cache), False)
    actual = {m['Destination']: (m.get('Type'), m.get('Name') if m.get('Type') == 'volume' else m.get('Source'), m.get('RW')) for m in container['Mounts']}
    return actual == expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-url', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--port', type=int)
    parser.add_argument('--gateway-port', type=int)
    parser.add_argument('--postgres-port', type=int, help='Explicit embedded PostgreSQL port for a separate local installation. Omission preserves a saved choice.')
    parser.add_argument('--name')
    parser.add_argument('--volume')
    parser.add_argument('--restart', choices=('no', 'unless-stopped'), help='Container restart policy. Omission preserves the saved choice; a fresh installation defaults to unless-stopped.')
    parser.add_argument('--public-model-cache', help='Optional read-only cache containing only the two declared public model roots; enables offline loading. Omission preserves the saved path.')
    parser.add_argument('--sudo-docker', action='store_true')
    parser.add_argument('--api-key-env')
    parser.add_argument('--llama-cpp-thinking', choices=('default', 'off'),
                        help='Memory requests only: server default or enable_thinking=false. Omission preserves the saved choice.')
    parser.add_argument('--refresh-budget-backport', action=argparse.BooleanOptionalAction, default=None,
                        help='Use the reviewed MIT refresh-default backport with the exact pinned image. Omission preserves the saved choice.')
    parser.add_argument('--replace-stopped', action='store_true', help='Back up and replace a deliberately stopped exact-version engine; never stop an active one.')
    parser.add_argument('--recover-pending', action='store_true', help='Confirm a previously created matching instance from its private receipt without replaying creation or replacement.')
    args = parser.parse_args()
    data = Path(os.environ.get('AUGMENTOR_SHARED_DATA', Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'augmentor')).absolute()
    path, receipt_path = data / 'hindsight.json', data / 'hindsight-installation.json'
    if path.is_symlink() or receipt_path.is_symlink(): raise ValueError('Memory configuration cannot be a symlink.')
    previous = json.loads(path.read_text()) if path.exists() else {}
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    if args.recover_pending:
        if receipt.get('phase') == 'ready' or not isinstance(receipt.get('configuration'), dict):
            raise ValueError('There is no recorded unfinished installation to recover.')
        previous = receipt['configuration']
    elif receipt.get('phase') in ('creating', 'checking', 'renaming') and receipt.get('configuration'):
        raise ValueError('An installation is unconfirmed. Inspect its private receipt, then explicitly use --recover-pending; nothing was replayed.')
    name = args.name or previous.get('containerName', 'augmentor-hindsight')
    volume = args.volume or previous.get('volumeName', 'augmentor-hindsight-data')
    if any(not isinstance(v, str) or not v or v[0] == '-' or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-' for c in v) for v in (name, volume)):
        parser.error('Use a simple Docker name and named data volume.')
    if previous.get('containerName', name) != name or previous.get('volumeName', volume) != volume:
        raise ValueError('The saved installation name/volume differs; use a separate profile.')
    port = args.port if args.port is not None else urlsplit(previous.get('endpoint', 'http://127.0.0.1:8889')).port
    gateway_port = args.gateway_port if args.gateway_port is not None else previous.get('gatewayPort', 8890)
    postgres_port = args.postgres_port if args.postgres_port is not None else previous.get('postgresPort')
    ports = [port, gateway_port] + ([] if postgres_port is None else [postgres_port])
    if any(type(p) is not int or not 1024 <= p <= 65535 for p in ports) or len(set(ports)) != len(ports):
        parser.error('Choose distinct nonprivileged API, gateway and optional database ports.')
    thinking = args.llama_cpp_thinking or previous.get('llamaCppThinking', 'default')
    if thinking not in ('default', 'off'): raise SystemExit('Saved memory thinking mode is invalid; configuration was not changed.')
    saved_backport = previous.get('refreshBudgetBackport', False)
    if type(saved_backport) is not bool: raise ValueError('Saved source-backport choice is invalid.')
    backport = args.refresh_budget_backport if args.refresh_budget_backport is not None else saved_backport
    reviewed = hindsight_backport.manifest() if backport else None
    if reviewed and reviewed['baseImage'] != IMAGE: raise ValueError('The source backport is not reviewed for this image.')
    restart = args.restart or previous.get('restartPolicy', 'unless-stopped')
    if restart not in ('no', 'unless-stopped'): raise ValueError('Saved engine restart policy is invalid.')
    cache_value = args.public_model_cache or previous.get('publicModelCache')
    cache = Path(cache_value).resolve() if cache_value else None
    cache_hash = hashlib.sha256(json.dumps(cache_inventory(cache), sort_keys=True).encode()).hexdigest() if cache else None
    if args.public_model_cache is None and previous.get('publicModelCacheSha256', cache_hash) != cache_hash:
        raise ValueError('The saved public model cache changed; no engine was modified.')
    url = urlsplit(args.model_url)
    try: local = ipaddress.ip_address(url.hostname or '').is_loopback
    except ValueError: local = False
    if url.scheme != 'http' or not local or url.username or url.password or url.query or url.fragment:
        parser.error('Use a numeric loopback HTTP model URL without embedded credentials.')
    endpoint = f'http://127.0.0.1:{port}'
    if previous and previous.get('endpoint') != endpoint: raise SystemExit('Refusing to silently change the memory destination.')
    docker = ['sudo', 'docker'] if args.sudo_docker else ['docker']
    key = previous.get('gatewayKey') or secrets.token_urlsafe(32)
    model_key = os.environ.get(args.api_key_env, '') if args.api_key_env else previous.get('modelKey', 'local')
    if not model_key: raise SystemExit('The model credential environment variable is empty.')
    content = (Path(__file__).resolve().parents[1] / 'services/memory/hindsight_extension.py').read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    artifact = artifact_path(data, content, backport)
    expected = environment(args.model, port, gateway_port, llama_cpp_thinking=thinking, postgres_port=postgres_port, offline=bool(cache))
    container = inspect(docker, name, missing=True)
    continuing = receipt.get('phase') != 'ready' and receipt.get('name') == name and receipt.get('volume') == volume and receipt.get('artifact') == str(artifact)
    owner = previous.get('installationId') or (receipt.get('installationId') if continuing else None) or uuid.uuid4().hex
    if container and previous.get('containerId') not in (None, container['Id']):
        if not (continuing and receipt.get('previousContainerId') == previous['containerId'] and container['Config'].get('Labels', {}).get(OWNER_LABEL) == owner):
            raise ValueError('Saved engine identity changed; no mutation was attempted.')
    if container and previous.get('installationId') and container['Config'].get('Labels', {}).get(OWNER_LABEL) != owner:
        raise ValueError('Saved engine ownership changed; no mutation was attempted.')
    matches = False
    if container:
        env = dict(e.split('=', 1) for e in container['Config']['Env'] if '=' in e)
        matches = (container['Config']['Image'] == IMAGE and environment_matches(env, expected) and env.get('HINDSIGHT_API_HTTP_KEY') == key and
                   container.get('HostConfig', {}).get('RestartPolicy', {}).get('Name') == restart and mounts_match(container, artifact, volume, backport, cache))
        if not matches:
            if not args.replace_stopped or container['State']['Running']:
                raise SystemExit('Existing engine differs. Stop it deliberately, then use --replace-stopped; data will be backed up.')
            if container['Config']['Image'] != IMAGE:
                raise ValueError('Only the pinned 0.10.0 image is qualified for stopped replacement.')
            if not any(m.get('Type') == 'volume' and m.get('Name') == volume and m.get('Destination') == '/home/hindsight/.pg0' for m in container['Mounts']):
                raise SystemExit('Existing memory data volume differs; no replacement was attempted.')
    if args.recover_pending and not (container and matches):
        raise ValueError('Pending recovery requires the recorded matching instance; no creation or replacement was attempted.')
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    if data.stat().st_mode & 0o077: raise ValueError('Use a private memory data directory (mode 0700).')
    plan = {'protocol': 'augmentor-memory-installation/1', 'phase': 'preparing', 'installationId': owner, 'name': name,
            'volume': volume, 'artifact': str(artifact), 'previousContainerId': container['Id'] if container else receipt.get('previousContainerId')}
    desired = {'endpoint': endpoint, 'version': '0.10.0', 'image': IMAGE, 'processingProtocol': PROTOCOL,
               'gatewayPort': gateway_port, 'gatewayKey': key, 'modelUrl': args.model_url.rstrip('/'), 'modelKey': model_key,
               'model': args.model, 'extensionSha256': digest, 'llamaCppThinking': thinking, 'refreshBudgetBackport': backport,
               'engineSourceSha256': reviewed['resultSha256'] if backport else None, 'postgresPort': postgres_port,
               'publicModelCache': str(cache) if cache else None, 'publicModelCacheSha256': cache_hash,
               'restartPolicy': restart, 'containerName': name, 'volumeName': volume,
               'containerId': container['Id'] if container and matches else None,
               'installationId': container['Config'].get('Labels', {}).get(OWNER_LABEL) if container and matches else owner}
    # Like hindsight.json, this is private credential-bearing state. Persist the
    # exact desired values before creation so a lost acknowledgement can be
    # confirmed without generating another credential or replaying Docker run.
    plan['configuration'] = desired
    if container and matches:
        verify_artifact(artifact, content, backport)
    else:
        image_ready(docker, IMAGE)
        materialize(docker, IMAGE, data, content, backport)
    backup = None
    if container and not matches:
        identity = container['Id']; same_container(docker, name, identity, stopped=True)
        stamp = time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
        backup = data / ('hindsight-before-controlled-' + stamp + '.tar')
        atomic(receipt_path, {**plan, 'phase': 'backing-up', 'backup': str(backup)})
        with backup.open('xb') as stream:
            backup.chmod(0o600); checked(docker, ['cp', identity + ':/home/hindsight/.pg0', '-'], stdout=stream, stderr=subprocess.PIPE)
            stream.flush(); os.fsync(stream.fileno())
        if backup.stat().st_size == 0: raise ValueError('The stopped database backup is empty; original instance remains unchanged.')
        with tarfile.open(backup, 'r:') as archive:
            members = archive.getmembers()
            if not any(m.isfile() for m in members) or any(m.offset_data + m.size > backup.stat().st_size for m in members):
                raise ValueError('The stopped database backup is incomplete; original instance remains unchanged.')
        with backup.open('rb') as stream: backup_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
        same_container(docker, name, identity, stopped=True)
        checked(docker, ['update', '--restart=no', identity], stdout=subprocess.DEVNULL)
        same_container(docker, name, identity, stopped=True)
        backup_name = name + '-before-controlled-' + stamp
        atomic(backup.with_suffix('.json'), {'protocol': 'augmentor-memory-backup/1', 'sourceContainerId': identity,
               'image': container['Config']['Image'], 'volume': volume, 'sha256': backup_hash,
               'bytes': backup.stat().st_size, 'plannedBackupContainer': backup_name})
        plan.update(backupContainer=backup_name, backupContainerId=identity, backupSha256=backup_hash)
        atomic(receipt_path, {**plan, 'phase': 'renaming', 'backup': str(backup), 'backupContainer': backup_name})
        checked(docker, ['rename', identity, backup_name], stdout=subprocess.DEVNULL)
        if inspect(docker, name, missing=True) is not None: raise ValueError('The previous name is still occupied; no replacement was started.')
        container = None
    if container is None:
        atomic(receipt_path, {**plan, 'phase': 'creating', 'backup': str(backup) if backup else None})
        command = ['run', '-d', '--pull=never', '--name', name, '--label', OWNER_LABEL + '=' + owner, '--restart', restart, '--network', 'host',
                   '--cpus', '4', '--memory', '8g', '-v', volume + ':/home/hindsight/.pg0', '-v', str(artifact) + ':/augmentor:ro']
        if cache: command += ['-v', str(cache) + ':/home/hindsight/.cache/huggingface/hub:ro']
        if backport: command += ['-v', str(artifact / 'source-backport/memory_engine.py') + ':' + reviewed['containerPath'] + ':ro']
        for field, value in expected.items(): command += ['-e', field + '=' + value]
        command += ['-e', 'HINDSIGHT_API_LLM_API_KEY', '-e', 'HINDSIGHT_API_HTTP_KEY', IMAGE]
        runner = docker[:]
        if args.sudo_docker: runner.insert(1, '--preserve-env=HINDSIGHT_API_LLM_API_KEY,HINDSIGHT_API_HTTP_KEY')
        checked(runner, command, env={**os.environ, 'HINDSIGHT_API_LLM_API_KEY': key, 'HINDSIGHT_API_HTTP_KEY': key}, capture_output=True, text=True)
        container = inspect(docker, name)
        same_container(docker, name, container['Id'], owner=owner)
    identity = container['Id']
    atomic(receipt_path, {**plan, 'phase': 'checking', 'containerId': identity, 'backup': str(backup) if backup else None})
    if not container['State']['Running']:
        same_container(docker, name, identity, owner=owner if container['Config'].get('Labels', {}).get(OWNER_LABEL) else None)
        checked(docker, ['start', identity], stdout=subprocess.DEVNULL)
    for _ in range(120):
        current = same_container(docker, name, identity)
        if not current['State']['Running']: raise ValueError('The engine exited; inspect its receipt/logs without replaying installation.')
        try:
            with urllib.request.urlopen(endpoint + '/openapi.json', timeout=3) as response: assert json.load(response)['info']['version'] == '0.10.0'
            with urllib.request.urlopen(endpoint + '/health', timeout=3) as response: assert json.load(response)['status'] == 'healthy'
            with urllib.request.urlopen(endpoint + '/ext/augmentor/policy', timeout=3) as response:
                assert json.load(response) == {'protocol': PROTOCOL, 'workerEnabled': False, 'reconcileSeconds': 0, 'llmRetries': 0}
            same_container(docker, name, identity); break
        except Exception: time.sleep(1)
    else:
        # Only the positively identified instance can be stopped; an unknown
        # replacement is never touched. Existing data/backup remain retained.
        same_container(docker, name, identity)
        checked(docker, ['stop', '-t', '30', identity], stdout=subprocess.DEVNULL)
        raise SystemExit('Controlled engine did not become ready. Configuration was not changed; exact engine stopped.')
    value = {**desired, 'containerId': identity, 'installationId': container['Config'].get('Labels', {}).get(OWNER_LABEL)}
    atomic(path, value)
    atomic(receipt_path, {**plan, 'phase': 'ready', 'containerId': identity, 'backup': str(backup) if backup else None})
    print('Controlled Hindsight ready. Restart the tested memory companion to load its gateway.')
    print('Cached memory remains readable. No archive processing or model request was authorized by installation.')


if __name__ == '__main__': main()
