# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One resumable bundled-DSH setup transaction; OS adapters own service lifetime."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from platform_adapters import locks
from platform_adapters.paths import private_directory as create_directory, link_directory
from platform_adapters.private_files import require_directory as private_directory, read_json as private_json, atomic_json, descriptor

SCHEMA = 'augmentor-managed-dsh/1'
BUNDLES = ['@deepseek-ai/dsh-base', '@deepseek-ai/dsh-web-app',
           'dsh-model-picker-augmented', 'dsh-adaptive-reasoning', 'dsh-resonant-voice']


def runtime_paths(root):
    if sys.platform == 'win32':
        return root/'dsh/node_modules/@deepseek-ai/dsh/lib/bin.js', root/'node/node.exe'
    return root/'dsh/node_modules/.bin/dsh', root/'node/bin/node'


def initialize_voice(root, env):
    script = root/'dsh/node_modules/dsh-resonant-voice/bin/resonant-voice.js'
    if not script.is_file():
        raise ValueError('The bundled voice plugin is missing. Reinstall Augmentor before setup.')
    subprocess.run([str(runtime_paths(root)[1]), str(script), 'init'], env=env,
                   capture_output=True, check=True, timeout=30,
                   **({'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}))


def load_complete(root):
    spec = importlib.util.spec_from_file_location('managed_complete_setup', root/'scripts/setup-complete.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def model_configuration(root, request, *, complete=None):
    complete = complete or load_complete(root)
    url, model = request.get('url', ''), request.get('model', '')
    context = request.get('context', 32768)
    secret = request.get('apiKey', '')
    if not all(isinstance(v, str) for v in (url, model, secret)) or not isinstance(context, int):
        raise ValueError('Enter a model API address, model name and API key.')
    if len(url) > 2048 or len(model) > 256 or len(secret) > 8192 or not 4096 <= context <= 2000000:
        raise ValueError('The model settings exceed the supported limits.')
    complete.environment_value(secret)
    settings = complete.model_settings(url.strip(), model.strip(), context)
    return settings, secret or 'local'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('The model API redirected the request. Use its final HTTPS API address.')


def probe_model(settings, secret):
    provider = settings['llm-pi-ai']['providers']['augmentor-model']
    # One small, explicit connection test; provider error bodies may contain
    # sensitive details, so only status codes cross back to the GUI.
    request = urllib.request.Request(provider['baseURL']+'/chat/completions',
        data=json.dumps({'model': provider['models'][0]['id'],
                         'messages': [{'role': 'user', 'content': 'Reply with OK.'}],
                         'max_tokens': 8, 'stream': False}).encode(),
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer '+secret})
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(request, timeout=30) as response:
            raw = response.read(65537)
        payload = json.loads(raw) if len(raw) <= 65536 else None
        choices = payload.get('choices') if isinstance(payload, dict) else None
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict) or not isinstance(choices[0].get('message'), dict):
            raise ValueError('The model API did not return a compatible chat response.')
    except urllib.error.HTTPError as error:
        raise ValueError(f'The model rejected the connection test (HTTP {error.code}). Check the API address, model name and key.') from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise ValueError('The model API could not be reached or returned an invalid response. Check the address and connection.') from None


def provision(root, state, request, *, agent, manager_type, complete=None, voice_initializer=initialize_voice,
              probe=probe_model, progress=lambda phase: None):
    """A resumable first-run transaction; callers supply only their private roots."""
    complete = complete or load_complete(root)
    engine_only = request.get('action') == 'install-runtime'
    settings, secret = ({}, '') if engine_only else model_configuration(root, request, complete=complete)
    create_directory(state.parent)
    fresh = not state.exists() and not state.is_symlink()
    if fresh:
        create_directory(state)
    private_directory(state)
    lock = descriptor(state/'setup.lock', writable=True, create=True)
    try:
        try:
            locks.flock(lock, locks.LOCK_EX|locks.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Augmentor setup is already running. Wait for that window to finish.') from None
        sys.path.insert(0, str(root/'services'))
        from dsh.setup import Setup, configuration, current
        cli, node = runtime_paths(root)
        if not cli.is_file() or not node.is_file():
            raise ValueError('The bundled runtime is missing. Reinstall Augmentor before setup.')
        saved = current()
        home = state/'home'; marker = state/'setup.json'
        record = private_json(marker) if marker.exists() else None
        if record:
            if record.get('schema') != SCHEMA or record.get('appRoot') != str(root) or record.get('home') != str(home):
                raise ValueError('A different setup owns this data directory. Its data was preserved.')
        elif not fresh:
            raise ValueError('An incomplete unrecognized setup folder was preserved. It needs review before setup.')
        if saved and (not record or saved.get('home') != str(home) or saved.get('endpoint') != record.get('endpoint')):
            raise ValueError('A DSH connection already exists. Use the existing-DSH settings to manage it.')
        manager = {'type': manager_type, 'label': agent.label, 'state': str(state)}
        if record and record.get('status') == 'ready':
            if not saved:
                raise ValueError('Managed DSH settings were removed. Reconnect the preserved profile instead of replacing it.')
            return {'saved': True, 'endpoint': record['endpoint'], 'home': str(home)}
        owned = agent.owned()  # Refuse foreign files before model requests or configuration writes.
        if agent.loaded() and not owned:
            raise ValueError('A different DSH login service is already registered. It was preserved.')
        if record is None:
            with socket.socket() as port:
                port.bind(('127.0.0.1', 0)); number = port.getsockname()[1]
            record = {'schema': SCHEMA, 'appRoot': str(root), 'home': str(home),
                      'endpoint': 'http://127.0.0.1:'+str(number), 'port': number,
                      'status': 'preparing', 'label': agent.label}
            atomic_json(marker, record)
        if agent.loaded():
            progress('ready')
            # A worker can disappear after launchd starts but before the final
            # acknowledgement. Recheck and finish that exact configuration;
            # never stop a live host or rewrite its model settings to retry.
            runtime = private_json(state/'runtime.json')
            if not engine_only and (runtime.get('apiKey') != secret or json.loads((home/'settings.yaml').read_text()) != settings):
                raise ValueError('The previous setup is already running with different model settings. Finish it with those settings before changing models.')
            setup = Setup(); checked = setup.check({'endpoint': record['endpoint'], 'home': str(home)})
            if not checked['installed']:
                raise ValueError('The previous setup service is active but its integration is not ready. Its state was preserved.')
            if not saved:
                current_hash = hashlib.sha256(configuration().read_bytes()).hexdigest() if configuration().exists() else None
                if current_hash != record.get('configurationHash'):
                    raise ValueError('The connection settings changed during setup. Those settings were preserved.')
                setup.save(checked['token'], managed=manager)
            record['status'] = 'ready'; atomic_json(marker, record)
            return {'saved': True, 'endpoint': record['endpoint'], 'home': str(home)}
        if not engine_only:
            progress('model')
            probe(settings, secret)
        progress('runtime')
        record['status'] = 'preparing'
        # A concurrent external connection cannot be overwritten by setup.
        previous_config = configuration().read_bytes() if configuration().exists() else None
        record['configurationHash'] = hashlib.sha256(previous_config).hexdigest() if previous_config is not None else None
        atomic_json(marker, record)
        create_directory(home); private_directory(home)
        if not engine_only or not (home/'settings.yaml').exists():
            atomic_json(home/'settings.yaml', settings)  # JSON is a YAML subset.
        profile = home/'profiles/web'; create_directory(profile)
        private_directory(profile)
        modules = profile/'node_modules'; expected_modules = root/'dsh/node_modules'
        link_directory(modules, expected_modules)
        # First-party web bundles are already prepared inside the app; never
        # invoke npm or download a second DSH during customer installation.
        if not (profile/'package.json').exists():
            atomic_json(profile/'package.json', {'name': 'augmentor-managed-web', 'private': True, 'type': 'module',
                'dsh': {'profile': {'bundles': BUNDLES}}})
        for name in ('cordis.yml', 'cordis.patch.yml'):
            if not (profile/name).exists():
                atomic_json(profile/name, [])
        environment = {key: value for key, value in os.environ.items()
                       if key.startswith('XDG_') or key in ('AUGMENTOR_SHARED_CONFIG', 'AUGMENTOR_SHARED_DATA', 'AUGMENTOR_SHARED_STATE', 'RESONANT_VOICE_HOME', 'AUGMENTOR_PWSH', 'AUGMENTOR_DSH_CLI')}
        # Resuming runtime installation must preserve a previously supplied key.
        if engine_only and (state/'runtime.json').exists():
            secret = private_json(state/'runtime.json').get('apiKey', '')
        atomic_json(state/'runtime.json', {'schema': SCHEMA, 'appRoot': str(root), 'home': str(home),
            'port': record['port'], 'apiKey': secret, 'environment': environment})
        env = {**os.environ, **environment, 'DSH_HOME': str(home), 'DSH_TELEMETRY_MODE': 'DISABLED',
               'AUGMENTOR_MODEL_API_KEY': secret,
               'PATH': str(cli.parent)+os.pathsep+str(node.parent)+os.pathsep+os.environ.get('PATH', os.defpath)}
        env.pop('NODE_OPTIONS', None); env.pop('NODE_PATH', None)
        os.environ['PATH'] = env['PATH']  # The GUI runs setup in a separate process.
        try:
            progress('integration')
            voice_initializer(root, env)
            complete.configure_product(root, cli, home, record['endpoint'], env, state, save=False)
            record['status'] = 'starting'; atomic_json(marker, record)
            progress('service')
            agent.start()
            progress('ready')
            started = time.monotonic(); deadline = started+60
            setup = Setup(); checked = None; last_check_error = None; attempts = 0
            while time.monotonic() < deadline:
                attempts += 1
                try:
                    checked = setup.check({'endpoint': record['endpoint'], 'home': str(home)})
                    if checked['installed']:
                        break
                except (OSError, ValueError) as error:
                    last_check_error = (str(error).replace(secret, '[redacted]') if secret else str(error))[:2000]
                time.sleep(.25)
            # Private diagnostics on both outcomes expose intermittent startup
            # delays without exporting credentials or broad process state.
            atomic_json(state/'startup-check.json', {'lastError': last_check_error,
                'integrationInstalled': bool(checked and checked.get('installed')),
                'attempts': attempts, 'elapsedSeconds': round(time.monotonic()-started, 3)})
            if not checked or not checked['installed']:
                raise ValueError('The managed agent did not become ready. Setup can be retried without changing other DSH profiles.')
            observed = configuration().read_bytes() if configuration().exists() else None
            if observed != previous_config:
                raise ValueError('Another window changed the DSH connection during setup. Those settings were preserved.')
            setup.save(checked['token'], managed=manager)
            # The runtime is ready before any desktop/browser can select it.
            record['status'] = 'ready'; atomic_json(marker, record)
            return {'saved': True, 'endpoint': record['endpoint'], 'home': str(home)}
        except Exception:
            # Once save succeeded, preserve the running service even if writing
            # the final journal failed. Do not strand a now-selected connection.
            if current().get('home') != str(home):
                agent.stop_failed_setup()
                record['status'] = 'failed'; atomic_json(marker, record)
            raise
    finally:
        os.close(lock)
