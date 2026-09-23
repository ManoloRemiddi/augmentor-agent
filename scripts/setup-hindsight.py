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
import subprocess
import time
import urllib.request
from urllib.parse import urlsplit

IMAGE = 'ghcr.io/vectorize-io/hindsight@sha256:3edcb6165cefdeaa6721dd0fce43cfd13b7a9c346ce0d2c5f4b4bf7bc3c8ac0b'
PROTOCOL = 'augmentor-memory-processing/1'


def environment(model, port, gateway_port):
    return {'HINDSIGHT_API_LLM_MODEL': model, 'HINDSIGHT_API_LLM_BASE_URL': f'http://127.0.0.1:{gateway_port}/v1',
        'HINDSIGHT_API_PORT': str(port), 'HINDSIGHT_ENABLE_CP': 'false', 'HINDSIGHT_API_HOST': '127.0.0.1',
        'HINDSIGHT_API_LLM_PROVIDER': 'openai', 'HINDSIGHT_API_WORKER_ENABLED': 'false',
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-url', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--port', type=int, default=8889)
    parser.add_argument('--gateway-port', type=int, default=8890)
    parser.add_argument('--name', default='augmentor-hindsight')
    parser.add_argument('--volume', default='augmentor-hindsight-data')
    parser.add_argument('--sudo-docker', action='store_true')
    parser.add_argument('--api-key-env')
    parser.add_argument('--replace-stopped', action='store_true', help='Back up and replace a stopped older engine; never stop an active one.')
    args = parser.parse_args()
    if not all(1024 <= p <= 65535 for p in (args.port, args.gateway_port)) or args.port == args.gateway_port:
        parser.error('Choose distinct nonprivileged API and gateway ports.')
    url = urlsplit(args.model_url)
    try: local = ipaddress.ip_address(url.hostname or '').is_loopback
    except ValueError: local = False
    if url.scheme != 'http' or not local or url.username or url.password or url.query or url.fragment:
        parser.error('Use a numeric loopback HTTP model URL without embedded credentials.')
    docker = ['sudo', 'docker'] if args.sudo_docker else ['docker']
    data = Path(os.environ.get('AUGMENTOR_SHARED_DATA', Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'augmentor'))
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = data / 'hindsight.json'
    previous = json.loads(path.read_text()) if path.exists() else {}
    endpoint = f'http://127.0.0.1:{args.port}'
    if previous and previous.get('endpoint') != endpoint:
        raise SystemExit('Refusing to silently change the memory destination.')
    key = previous.get('gatewayKey') or secrets.token_urlsafe(32)
    model_key = os.environ.get(args.api_key_env, '') if args.api_key_env else previous.get('modelKey', 'local')
    if not model_key: raise SystemExit('The model credential environment variable is empty.')
    source = Path(__file__).resolve().parents[1] / 'services/memory/hindsight_extension.py'
    content = source.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    artifact = data / 'memory-engine' / digest
    artifact.mkdir(parents=True, exist_ok=True, mode=0o755)
    extension = artifact / 'augmentor_memory.py'
    if extension.exists() and extension.read_bytes() != content:
        raise SystemExit('Controlled memory artifact differs from its recorded hash.')
    if not extension.exists():
        extension.write_bytes(content); extension.chmod(0o444)
    expected = environment(args.model, args.port, args.gateway_port)
    existing = subprocess.run(docker + ['inspect', args.name], capture_output=True, text=True)
    create = existing.returncode != 0
    if not create:
        container = json.loads(existing.stdout)[0]
        env = dict(e.split('=', 1) for e in container['Config']['Env'])
        matches = (container['Config']['Image'] == IMAGE and all(env.get(k) == v for k, v in expected.items()) and
                   env.get('HINDSIGHT_API_HTTP_KEY') == key and
                   any(m.get('Source') == str(artifact) and m.get('Destination') == '/augmentor' for m in container['Mounts']))
        if not matches:
            if not args.replace_stopped or container['State']['Running']:
                raise SystemExit('Existing engine differs. Stop it deliberately, then use --replace-stopped; data will be backed up.')
            if not any(m.get('Name') == args.volume and m.get('Destination') == '/home/hindsight/.pg0' for m in container['Mounts']):
                raise SystemExit('Existing memory data volume differs; no replacement was attempted.')
            stamp = time.strftime('%Y%m%d-%H%M%S')
            backup = data / ('hindsight-before-controlled-' + stamp + '.tar')
            with backup.open('xb') as stream:
                backup.chmod(0o600)
                subprocess.run(docker + ['cp', args.name + ':/home/hindsight/.pg0', '-'], stdout=stream, check=True)
                stream.flush(); os.fsync(stream.fileno())
            subprocess.run(docker + ['update', '--restart=no', args.name], check=True, stdout=subprocess.DEVNULL)
            subprocess.run(docker + ['rename', args.name, args.name + '-before-controlled-' + stamp], check=True)
            create = True
    if create:
        subprocess.run(docker + ['pull', IMAGE], check=True)
        command = docker + ['run', '-d', '--name', args.name, '--restart', 'unless-stopped', '--network', 'host',
                   '--cpus', '4', '--memory', '8g', '-v', args.volume + ':/home/hindsight/.pg0',
                   '-v', str(artifact) + ':/augmentor:ro']
        for name, value in expected.items(): command += ['-e', name + '=' + value]
        command += ['-e', 'HINDSIGHT_API_LLM_API_KEY', '-e', 'HINDSIGHT_API_HTTP_KEY']
        if args.sudo_docker: command.insert(1, '--preserve-env=HINDSIGHT_API_LLM_API_KEY,HINDSIGHT_API_HTTP_KEY')
        subprocess.run(command + [IMAGE], check=True, env={**os.environ, 'HINDSIGHT_API_LLM_API_KEY': key, 'HINDSIGHT_API_HTTP_KEY': key})
    else:
        subprocess.run(docker + ['start', args.name], check=True, stdout=subprocess.DEVNULL)
    for _ in range(120):
        try:
            with urllib.request.urlopen(endpoint + '/openapi.json', timeout=3) as response:
                assert json.load(response)['info']['version'] == '0.10.0'
            with urllib.request.urlopen(endpoint + '/health', timeout=3) as response:
                assert json.load(response)['status'] == 'healthy'
            with urllib.request.urlopen(endpoint + '/ext/augmentor/policy', timeout=3) as response:
                policy = json.load(response)
                assert policy['protocol'] == PROTOCOL and policy['workerEnabled'] is False and policy['reconcileSeconds'] == 0
            break
        except Exception: time.sleep(1)
    else:
        subprocess.run(docker + ['stop', '-t', '30', args.name], check=False, stdout=subprocess.DEVNULL)
        raise SystemExit('Controlled engine did not become ready. Configuration was not changed; engine stopped.')
    value = {'endpoint': endpoint, 'version': '0.10.0', 'image': IMAGE, 'processingProtocol': PROTOCOL,
             'gatewayPort': args.gateway_port, 'gatewayKey': key, 'modelUrl': args.model_url.rstrip('/'),
             'modelKey': model_key, 'extensionSha256': digest}
    temporary = path.with_suffix('.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(json.dumps(value, indent=2) + '\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)
    print('Controlled Hindsight ready. Restart the tested memory companion to load its gateway.')
    print('Cached memory remains readable. No archive processing or model request was authorized by installation.')


if __name__ == '__main__': main()
