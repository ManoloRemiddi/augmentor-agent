#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Provision a private, bundled DSH runtime for a fresh macOS desktop user.

The GUI sends model configuration through stdin. Secrets never appear in process
arguments, launchd plists or progress output. Existing external DSH connections
are never adopted or modified by this first-run path.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LABEL = 'com.augmentor.Agent.DSH'
SCHEMA = 'augmentor-managed-dsh/1'


def load_complete(root):
    spec = importlib.util.spec_from_file_location('mac_complete_setup', root/'scripts/setup-complete.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def private_json(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1:
        raise ValueError('Setup needs an ordinary private file owned by this user.')
    return json.loads(path.read_text())


def atomic_json(path, value):
    import tempfile
    with tempfile.NamedTemporaryFile(dir=path.parent, mode='w', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(value, stream, indent=2); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
            temporary.chmod(0o600); temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def private_directory(path):
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Setup needs a private data directory owned by this user.')


def installed_location(root):
    app = root.parents[2]
    if root != app/'Contents/Resources/app' or app.parent not in (Path('/Applications'), Path.home()/'Applications'):
        raise ValueError('Drag Augmentor into Applications, then open that copy to set it up.')
    info = plistlib.loads((app/'Contents/Info.plist').read_bytes())
    if info.get('CFBundleIdentifier') != 'com.augmentor.Agent':
        raise ValueError('Use the installed Augmentor desktop application.')


def model_configuration(root, request):
    complete = load_complete(root)
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


def provision(root, state, request, *, agent=None, probe=probe_model):
    """A resumable first-run transaction; callers supply only their private roots."""
    complete = load_complete(root)
    settings, secret = model_configuration(root, request)
    state.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fresh = not state.exists() and not state.is_symlink()
    if fresh:
        state.mkdir(mode=0o700)
    private_directory(state)
    lock = os.open(state/'setup.lock', os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(lock).st_mode) or os.fstat(lock).st_nlink != 1:
            raise ValueError('Invalid setup lock.')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Augmentor setup is already running. Wait for that window to finish.') from None
        sys.path.insert(0, str(root/'services'))
        from dsh.setup import Setup, configuration, current
        cli = root/'dsh/node_modules/.bin/dsh'; node = root/'node/bin/node'
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
        agent = agent or LaunchAgent(root, state)
        manager = {'type': 'launchd', 'label': agent.label, 'state': str(state)}
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
            # A worker can disappear after launchd starts but before the final
            # acknowledgement. Recheck and finish that exact configuration;
            # never stop a live host or rewrite its model settings to retry.
            runtime = private_json(state/'runtime.json')
            if runtime.get('apiKey') != secret or json.loads((home/'settings.yaml').read_text()) != settings:
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
        probe(settings, secret)
        record['status'] = 'preparing'
        # A concurrent external connection cannot be overwritten by setup.
        previous_config = configuration().read_bytes() if configuration().exists() else None
        record['configurationHash'] = hashlib.sha256(previous_config).hexdigest() if previous_config is not None else None
        atomic_json(marker, record)
        home.mkdir(parents=True, exist_ok=True, mode=0o700); private_directory(home)
        atomic_json(home/'settings.yaml', settings)  # JSON is a YAML subset.
        profile = home/'profiles/web'; profile.mkdir(parents=True, exist_ok=True, mode=0o700)
        private_directory(profile)
        modules = profile/'node_modules'; expected_modules = root/'dsh/node_modules'
        if modules.is_symlink():
            if modules.resolve() != expected_modules.resolve():
                raise ValueError('The managed profile runtime link changed. It was preserved.')
        elif modules.exists():
            raise ValueError('The managed profile has an unexpected runtime directory. It was preserved.')
        else:
            modules.symlink_to(expected_modules, target_is_directory=True)
        # First-party web bundles are already prepared inside the app; never
        # invoke npm or download a second DSH during customer installation.
        if not (profile/'package.json').exists():
            atomic_json(profile/'package.json', {'name': 'augmentor-managed-web', 'private': True, 'type': 'module',
                'dsh': {'profile': {'bundles': ['@deepseek-ai/dsh-base', '@deepseek-ai/dsh-web-app']}}})
        for name in ('cordis.yml', 'cordis.patch.yml'):
            if not (profile/name).exists():
                atomic_json(profile/name, [])
        environment = {key: value for key, value in os.environ.items()
                       if key.startswith('XDG_') or key in ('AUGMENTOR_SHARED_CONFIG', 'AUGMENTOR_SHARED_DATA', 'AUGMENTOR_SHARED_STATE')}
        atomic_json(state/'runtime.json', {'schema': SCHEMA, 'appRoot': str(root), 'home': str(home),
            'port': record['port'], 'apiKey': secret, 'environment': environment})
        env = {**os.environ, **environment, 'DSH_HOME': str(home), 'DSH_TELEMETRY_MODE': 'DISABLED',
               'AUGMENTOR_MODEL_API_KEY': secret,
               'PATH': str(cli.parent)+os.pathsep+str(node.parent)+os.pathsep+os.environ.get('PATH', os.defpath)}
        env.pop('NODE_OPTIONS', None); env.pop('NODE_PATH', None)
        os.environ['PATH'] = env['PATH']  # The GUI runs setup in a separate process.
        try:
            complete.configure_product(root, cli, home, record['endpoint'], env, state, save=False)
            record['status'] = 'starting'; atomic_json(marker, record)
            agent.start()
            started = time.monotonic(); deadline = started+60
            setup = Setup(); checked = None; last_check_error = None; attempts = 0
            while time.monotonic() < deadline:
                attempts += 1
                try:
                    checked = setup.check({'endpoint': record['endpoint'], 'home': str(home)})
                    if checked['installed']:
                        break
                except (OSError, ValueError) as error:
                    last_check_error = str(error).replace(secret, '[redacted]')[:2000]
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
        result = provision(ROOT, base/'augmentor/managed-dsh', request)
        print(json.dumps({'ok': True, **result}))
    except Exception as error:
        # Never include provider response bodies or the input request here.
        print(json.dumps({'ok': False, 'error': str(error) if isinstance(error, ValueError)
                          else 'Setup could not finish. Its private data was retained for diagnosis and retry.'}))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
