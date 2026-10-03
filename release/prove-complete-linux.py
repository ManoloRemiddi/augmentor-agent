#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fresh-user complete-bundle qualification in a disposable Linux container.

Uses a deterministic localhost model with real installed DSH/plugins/adapters.
Offscreen rendering and adapter turns do not qualify a graphical browser/session.
"""
import argparse
import copy
import hashlib
import http.server
import importlib.util
import json
import os
from pathlib import Path
import signal
import secrets
import stat
import shutil
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit

PROOF_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
COMPANION_PROOF_SHA256 = '70543782f9d26bae72bf0a4396e649c646017de7ee55a7f9af84075daf29368b'


def run(command, **kwargs):
    return subprocess.run([str(v) for v in command], check=True, text=True, **kwargs)


def selected_python_environment(app, python):
    """Use the installed runtime's verified pre-exec contract for proof children."""
    env = {**os.environ, 'AUGMENTOR_PYTHON': str(python)}
    marker = app/'linux-python-runtime.json'
    if marker.exists() or marker.is_symlink():
        path = app/'scripts/linux-python-runtime.py'
        spec = importlib.util.spec_from_file_location('complete_proof_runtime', path)
        runtime = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runtime)
        env = runtime.environment(app, str(python), env)
    # Adapter workers inherit this process environment. Replace it completely so
    # alternate Qt module sources removed by the contract cannot survive.
    os.environ.clear()
    os.environ.update(env)
    return env


def memory_companion(app, python, home, dsh_home, env, journal_root):
    path = Path(__file__).with_name('owned-memory-companion-proof.py')
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or hashlib.sha256(path.read_bytes()).hexdigest() != COMPANION_PROOF_SHA256:
        raise ValueError('The maintained companion proof helper is missing or changed.')
    spec = importlib.util.spec_from_file_location('owned_memory_companion_proof', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.OwnedMemoryCompanion(app, python, home, dsh_home, env, journal_root)


def fixture_model_server(requests, port):
    class Model(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()
            for delta, reason in (({'role': 'assistant', 'content': 'LINUX DISTRO FIXTURE VERIFIED'}, None), ({}, 'stop')):
                value = {'id': 'qualification', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'fixture',
                         'choices': [{'index': 0, 'delta': delta, 'finish_reason': reason}]}
                self.wfile.write(('data: '+json.dumps(value)+'\n\n').encode())
            self.wfile.write(b'data: [DONE]\n\n')
    return http.server.ThreadingHTTPServer(('127.0.0.1', port), Model)


def user_proof(bundle, setup_script=None):
    assert os.geteuid() != 0
    requests = []
    server = fixture_model_server(requests, 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with socket.socket() as available:
        available.bind(('127.0.0.1', 0))
        port = available.getsockname()[1]
    home = Path.home()
    data = home/'.local/share/augmentor'
    config = home/'.config'
    state = home/'.local/state/augmentor-install'
    app = Path('/usr/lib/augmentor')
    node = app/'node/bin/node'
    os.environ.update(AUGMENTOR_FIXTURE_KEY='qualification-fixture', QT_QPA_PLATFORM='offscreen',
                      XDG_RUNTIME_DIR=str(home/'runtime'), PATH=str(node.parent)+':'+os.environ['PATH'])
    Path(os.environ['XDG_RUNTIME_DIR']).mkdir(mode=0o700, exist_ok=True)
    manifest=json.loads((bundle/'bundle.json').read_text())
    bootstrap='/usr/bin/python3.13' if manifest['target']=='opensuse-leap16.0-x86_64' else '/usr/bin/python3'
    setup_script=(setup_script or bundle/'setup.py').resolve()
    override_used=setup_script!=(bundle/'setup.py').resolve()
    setup_sha=hashlib.sha256(setup_script.read_bytes()).hexdigest()
    bundle_setup_sha=hashlib.sha256((bundle/'setup.py').read_bytes()).hexdigest()
    command = [bootstrap, '-B', setup_script, '--bundle', bundle, '--skip-packages', '--no-services',
               '--non-interactive', '--model-url', f'http://127.0.0.1:{server.server_port}/v1', '--model', 'fixture',
               '--api-key-env', 'AUGMENTOR_FIXTURE_KEY', '--port', str(port)]
    process = None
    companion = None
    log = (home/'qualification-dsh.log').open('w')
    try:
        run(command)
        manifest = json.loads((bundle/'bundle.json').read_text())
        receipt = json.loads((state/'installation.json').read_text())
        assert receipt['status'] == 'installed' and receipt['target'] == manifest['target']
        assert (state/'model.env').stat().st_mode & 0o077 == 0
        saved = config/'augmentor/harnesses.json'
        assert json.loads(saved.read_text())['dsh']['version'] == manifest['version']
        assert (config/'autostart/com.augmentor.Agent.desktop').is_file()
        assert (home/'.local/share/applications/com.augmentor.Agent.secondary.desktop').is_file()
        assert (data/'browser'/manifest['version']/'voice.mjs').is_file()
        assert (config/'chromium/NativeMessagingHosts/com.augmentor.agent.json').is_file()
        dsh_home = data/'dsh-home'
        for plugin in ('dsh-resonant-voice', 'dsh-adaptive-reasoning', 'dsh-model-picker-augmented'):
            assert (dsh_home/'profiles/web/node_modules'/plugin/'package.json').is_file()
        desktop = json.loads((data/'desktop.json').read_text())
        python = Path(desktop['python'])
        selected_env = selected_python_environment(app, python)
        run([python, '-m', 'augmentor_linux', '--preview', '--screenshot', home/'desktop.png'],
            env={**selected_env, 'PYTHONPATH': str(app/'apps/native')})
        assert (home/'desktop.png').stat().st_size > 10000
        first = saved.read_bytes()
        run(command)
        assert saved.read_bytes() == first
        sys.path.insert(0, str(app/'apps/native'))
        from augmentor_linux.adapters.dsh import DshAdapter
        cli = data/'dsh-runtime/node_modules/.bin/dsh'
        env = {**os.environ, 'DSH_HOME': str(dsh_home), 'DSH_TELEMETRY_MODE': 'DISABLED',
               'AUGMENTOR_MODEL_API_KEY': 'qualification-fixture'}
        companion = memory_companion(app, python, home, dsh_home, env, state)

        def stop():
            nonlocal process
            if process is not None and process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=15)
            process = None

        def start():
            nonlocal process
            process = subprocess.Popen([str(node), str(cli.resolve()), 'web', '--no-open', '--host', '127.0.0.1', '--port', str(port)],
                                       env=env, stdout=log, stderr=log, start_new_session=True)
            deadline = time.monotonic()+60
            while time.monotonic() < deadline:
                assert process.poll() is None, 'DSH stopped; inspect qualification-dsh.log'
                try:
                    adapter = DshAdapter()
                    adapter.call('host.describe')
                    assert adapter.product
                    return adapter
                except (OSError, ValueError, RuntimeError):
                    time.sleep(.2)
            raise AssertionError('Installed DSH did not become ready')

        adapter = start()
        histories = {}
        for role in ('linux', 'browser'):
            session = 'qualification-'+role
            adapter.call('session.create', {'sessionId': session, 'agentPreset': 'augmentor-'+role+'-product', 'cwd': str(home)})
            adapter.call('session.selectModel', {'sessionId': session, 'provider': 'augmentor-model', 'model': 'fixture'})
            adapter.call('session.prompt', {'sessionId': session, 'mode': 'queue',
                         'content': [{'type': 'text', 'text': 'Reply to the '+role+' qualification fixture.'}]})
            deadline = time.monotonic()+60
            while time.monotonic() < deadline:
                histories[session] = adapter.call('session.history', {'sessionId': session})
                row = next(v for v in adapter.call('session.list')['items'] if v['sessionId'] == session)
                if not row['running'] and 'LINUX DISTRO FIXTURE VERIFIED' in json.dumps(histories[session]):
                    break
                time.sleep(.1)
            else:
                raise AssertionError('Installed '+role+' role did not complete a fixture model turn')
        histories = {session: adapter.call('session.history', {'sessionId': session}) for session in histories}
        (home/'history-before.json').write_text(json.dumps(histories, indent=2)+'\n')
        count = len(requests)
        stop()
        adapter = start()
        reopened = {session: adapter.call('session.history', {'sessionId': session}) for session in histories}
        (home/'history-after.json').write_text(json.dumps(reopened, indent=2)+'\n')
        # Actual DSH initializes an omitted delegationDepth to zero when loading
        # its session header. Compare the documented default semantically; every
        # saved event and every other header field must remain exactly equal.
        for session in histories:
            for snapshot in (histories[session], reopened[session]):
                snapshot['header'].setdefault('delegationDepth', 0)
        assert reopened == histories, 'Restart history differs; inspect history-before.json and history-after.json'
        assert len(requests) == count, 'Restart replayed a model request'
        stop()
        companion_cleanup = companion.finish()
        report = {'target': manifest['target'], 'sourceCommit': manifest['sourceCommit'], 'bundle': manifest['artifactId'],
                  'proofScriptSha256': PROOF_SHA256,
                  'setupScriptSha256':setup_sha,'bundleSetupScriptSha256':bundle_setup_sha,
                  'setupScriptMatchesBundle':not override_used and setup_sha==bundle_setup_sha,
                  'installerOverlayUsed':override_used,
                  'ordinaryUserSetup': True, 'realInstalledDshAndPlugins': True, 'offscreenNativeRender': True,
                  'secondWindowEntry': True, 'nativeHostRegistered': True, 'repeatPreservesSettings': True,
                  'linuxAndBrowserRoleFixtureTurns': True, 'restartPreservesHistoryWithoutReplay': True,
                  'modelRequests': count, 'realDesktopSessionTested': False, 'graphicalBrowserTested': False,
                  'physicalVoiceTested': False, 'memoryEngineTested': False,
                  'companionProofSha256': COMPANION_PROOF_SHA256, 'companionCleanup': companion_cleanup}
        if manifest.get('pythonRuntime'):
            report.update(pythonRuntime=manifest['pythonRuntime'], selectedPython=str(python),
                          licenseReviewComplete=False, embeddedSourceCoverageComplete=False)
        (home/'complete-proof.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report))
    finally:
        try:
            if process is not None and process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=15)
            if companion is not None and not companion.attempted:
                companion.finish()
        finally:
            server.shutdown()
            server.server_close()
            log.close()


# This entry is deliberately scoped to one explicitly owned installed Mint VM.
POST_SOURCE = '2035af99b46bb013e81de9766216da820ab4a325'
POST_HOME = Path('/home/augmentor-complete-proof')
POST_APP = Path('/usr/lib/augmentor')
POST_MARKER = Path('/etc/augmentor-test-vm')
POST_MARKER_TEXT = 'Isolated Augmentor Linux Mint 22.3 Cinnamon ISO qualification VM\n'
POST_SETTINGS = frozenset(('.local/state/augmentor-install/installation.json',
    '.local/state/augmentor-install/model.env', '.config/augmentor/harnesses.json',
    '.local/share/augmentor/desktop.json', '.local/share/augmentor/dsh-home/settings.yaml'))


def proof_module(path):
    spec = importlib.util.spec_from_file_location('complete_post_'+path.stem.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def settings_snapshot(home, expected):
    from platform_adapters.private_files import descriptor
    if set(expected) != POST_SETTINGS:
        raise ValueError('The post-install proof needs all five explicit settings hashes.')
    result = {}
    for name, identity in expected.items():
        with os.fdopen(descriptor(home/name), 'rb') as stream:
            raw = stream.read(1024*1024+1)
        if len(raw) > 1024*1024:
            raise ValueError('Fixture settings exceed the bounded proof size.')
        actual = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        if actual != identity:
            raise ValueError('Saved fixture settings changed; no setup or configuration was replayed.')
        result[name] = actual
    return result


def post_account_idle(home, service):
    """Refuse owned application/setup activity; never stop or adopt a service."""
    if service != 'augmentor-dsh.service':
        raise ValueError('The recorded fixture DSH service differs.')
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            args = (proc/'cmdline').read_bytes(); environment = (proc/'environ').read_bytes()
            fragments = (str(POST_APP).encode()+b'/', str(home/'.local/share/augmentor').encode()+b'/',
                         b'/setup.py', b'--owned-vm-post-install-fixture')
            if any(part in args for part in fragments) or (b'DSH_HOME='+str(home/'.local/share/augmentor/dsh-home').encode()+b'\0') in environment:
                raise ValueError('An owned product/setup process is active; it was preserved.')
        except FileNotFoundError:
            continue
    units = home/'.config/systemd/user'
    for name in (service, 'augmentor-desktop.service'):
        if any(units.glob('*.wants/'+name)):
            raise ValueError('A fixture login service is enabled; it was preserved.')
    runtime_dir = Path('/run/user')/str(os.getuid())
    if runtime_dir.exists():
        bus = runtime_dir/'bus'
        if not bus.exists():
            raise ValueError('The fixture user service owner is uncertain.')
        env = {**os.environ, 'XDG_RUNTIME_DIR': str(runtime_dir), 'DBUS_SESSION_BUS_ADDRESS': 'unix:path='+str(bus)}
        for name in (service, 'augmentor-desktop.service'):
            result = subprocess.run(['systemctl', '--user', 'show', name, '--property=ActiveState', '--value'],
                                    env=env, capture_output=True, text=True, timeout=15)
            if result.returncode or result.stdout.strip() not in ('inactive', 'failed'):
                raise ValueError('The fixture login service is active or uncertain; it was preserved.')


def empty_workspace_guard(home, expected_digest):
    """This first fixture must have no persisted work that startup could resume."""
    directory = home/'storages'; path = directory/'workspace.json'
    if directory.is_symlink() or not directory.is_dir() or set(directory.iterdir()) != {path}:
        raise ValueError('Unexpected prior session storage was preserved; no runtime was started.')
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or
        info.st_nlink != 1 or info.st_mode & 0o022 or info.st_size > 1024*1024):
        raise ValueError('The fixture workspace storage identity differs.')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_digest:
        raise ValueError('The bound initial workspace changed; no work was resumed.')
    storage = json.loads(raw)
    if storage.get('tables') != {'workspaces': {}}:
        raise ValueError('Prior session/workspace data was preserved; this fixture does not adopt it.')


def require_ports_idle(ports):
    for number in ports:
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', number))


def validate_post_fixture(bundle, fixture):
    import pwd
    if (fixture.get('format') != 'augmentor-owned-mint-post-install/1' or
        fixture.get('sourceCommit') != POST_SOURCE or fixture.get('uid') != 1001 or
        fixture.get('user') != 'augmentor-complete-proof' or fixture.get('home') != str(POST_HOME) or
        fixture.get('target') != 'linuxmint22.3-amd64' or
        fixture.get('markerSha256') != hashlib.sha256(POST_MARKER_TEXT.encode()).hexdigest()):
        raise ValueError('This post-install entry requires the explicit owned clean2035 Mint fixture.')
    if os.getuid() != 1001 or os.geteuid() != 1001 or Path.home() != POST_HOME or os.environ.get('HOME') != str(POST_HOME):
        raise ValueError('Run only as the dedicated ordinary fixture account.')
    entry = pwd.getpwuid(1001)
    if entry.pw_name != fixture['user'] or entry.pw_dir != fixture['home']:
        raise ValueError('The fixture account identity changed.')
    info = POST_MARKER.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022 or
        info.st_nlink != 1 or POST_MARKER.read_text() != POST_MARKER_TEXT):
        raise ValueError('The root-owned fixture marker is missing or changed.')
    fields = dict(row.split('=', 1) for row in Path('/etc/os-release').read_text().splitlines() if '=' in row)
    if fields['ID'].strip('"') != 'linuxmint' or fields['VERSION_ID'].strip('"') != '22.3':
        raise ValueError('The post-install fixture distro differs.')
    for command, expected in ((['hostname'], 'augmentor-mint223-iso'), (['systemd-detect-virt'], 'qemu'),
                              (['findmnt', '--target', '/', '--noheadings', '--output', 'SOURCE,FSTYPE'], '/dev/vda2 ext4')):
        if subprocess.check_output(command, text=True).strip() != expected:
            raise ValueError('The owned VM/root identity differs.')
    if ('boot=casper' in Path('/proc/cmdline').read_text() or
        any(word in Path('/proc/mounts').read_text() for word in ('iso9660', 'squashfs')) or
        Path('/sys/module/apparmor/parameters/enabled').read_text().strip() != 'Y'):
        raise ValueError('The installed isolated fixture security/root state differs.')
    if any(key.startswith(('AUGMENTOR_', 'DSH_', 'XDG_', 'LD_', 'QT_', 'QML_', 'NODE_', 'RESONANT_')) for key in os.environ):
        raise ValueError('Use an explicit clean fixture environment; no inherited runtime overrides.')
    sys.path.insert(0, str(POST_APP/'services'))
    from platform_adapters.private_files import require_directory, read_json
    require_directory(POST_HOME)
    raw = (bundle/'bundle.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != fixture.get('bundleManifestSha256'):
        raise ValueError('The explicitly bound complete manifest differs.')
    manifest = json.loads(raw)
    if manifest['sourceCommit'] != POST_SOURCE or manifest['target'] != fixture['target'] or manifest['artifactId'] != fixture.get('artifactId'):
        raise ValueError('The installed proof cannot adopt another source/target/artifact.')
    for name, expected in manifest['sha256'].items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or hashlib.sha256((bundle/path).read_bytes()).hexdigest() != expected:
            raise ValueError('The bound complete bundle checksum differs.')
    info = (POST_APP/'release.json').lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError('The installed release is not an immutable root-owned artifact.')
    setup = proof_module(bundle/'setup.py')
    setup.verify_installed_payload(POST_APP, manifest, bundle)
    for command in (['dpkg', '--audit'], ['dpkg', '--verify', 'augmentor-runtime', 'augmentor-desktop']):
        if subprocess.check_output(command, text=True):
            raise ValueError('The installed native package audit differs.')
    settings_snapshot(POST_HOME, fixture['settings'])
    receipt = read_json(POST_HOME/'.local/state/augmentor-install/installation.json')
    if receipt.get('status') != 'installed' or receipt.get('bundle') != manifest['artifactId'] or receipt.get('target') != manifest['target']:
        raise ValueError('This proof needs the exact already installed receipt; no setup is replayed.')
    desktop = read_json(POST_HOME/'.local/share/augmentor/desktop.json')
    if desktop.get('root') != str(POST_APP) or desktop.get('node') != str(POST_APP/'node/bin/node') or desktop.get('dshService') != fixture.get('dshService'):
        raise ValueError('The actual saved startup selection differs; it was preserved.')
    for name, digest in desktop.get('files', {}).items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or hashlib.sha256((POST_APP/path).read_bytes()).hexdigest() != digest:
            raise ValueError('The selected desktop inventory differs.')
    saved = read_json(POST_HOME/'.config/augmentor/harnesses.json')['dsh']
    home = POST_HOME/'.local/share/augmentor/dsh-home'
    if saved.get('home') != str(home) or saved.get('version') != manifest['version'] or desktop.get('dshHome') != str(home) or desktop.get('dshEndpoint') != saved.get('endpoint'):
        raise ValueError('The saved DSH connection differs.')
    import yaml
    model = yaml.safe_load((home/'settings.yaml').read_text())
    provider = model['llm-pi-ai']['providers']['augmentor-model']
    if (provider.get('api') != 'openai-completions' or provider.get('apiKeyEnv') != 'AUGMENTOR_MODEL_API_KEY' or
        len(provider.get('models', [])) != 1 or provider['models'][0]['id'] != 'fixture' or
        model.get('agent-default-model') != {'provider': 'augmentor-model', 'model': 'fixture'} or
        (POST_HOME/'.local/state/augmentor-install/model.env').read_text() != 'AUGMENTOR_MODEL_API_KEY="qualification-fixture"\n'):
        raise ValueError('This entry can use only the existing deterministic synthetic fixture model.')
    api = urlsplit(provider['baseURL']); endpoint = urlsplit(saved['endpoint'])
    for url in (api, endpoint):
        if url.scheme != 'http' or url.hostname != '127.0.0.1' or not url.port or url.username or url.password or url.query or url.fragment:
            raise ValueError('The saved fixture endpoint is not plain IPv4 loopback.')
    if (api.path != '/v1' or endpoint.path not in ('', '/') or api.port != fixture.get('modelApiPort') or
        endpoint.port != fixture.get('dshPort') or api.port == endpoint.port):
        raise ValueError('The explicitly bound saved ports differ; no settings were rewritten.')
    post_account_idle(POST_HOME, desktop['dshService'])
    empty_workspace_guard(home, fixture.get('workspaceStorageSha256'))
    post_run_name(POST_HOME/'.local/state/augmentor-install', fixture)
    require_ports_idle((api.port, endpoint.port))  # Never stop an occupied port's owner.
    from lifecycle.lease import hold
    hold('runtime')
    env = selected_python_environment(POST_APP, Path(desktop['python']))
    return manifest, desktop, env


POST_PRIOR_FAILURE_SHA = 'cd7f502ff3d868257f81c9a248aa9f11223925dd91af57da37f12e23407418f2'
POST_PRIOR_PROOF_SHA = 'a1342ea000108c40c8138ca3439fb4eb6c2302c266af503401e500e2c250b766'


POST_V3_RUN = 'post-install-proof-emulated-startup-v3'
POST_V3_PRIOR_SHA = {
    'post-install-proof': POST_PRIOR_FAILURE_SHA,
    'post-install-proof-cwd-v2': '72531cd9a3276236d4374d48f6a9785e93d2fcb0d068f914e9812efef8b3c441',
    'post-install-readiness-only-180-v1': 'a31419c04e561ccbd677be72114332fd224947c9578faff37952f4d4f242ef2e',
    'post-install-full-adapter-readiness-v1': 'bbd56ffb699752d1f774a5353065dad0315070e1b3b7d6530d9bced6c611c8ab',
}


def post_startup_budget(fixture):
    expected = 120 if fixture.get('runDirectory') == POST_V3_RUN else 60
    value = fixture.get('startupBudgetSeconds', 60)
    if type(value) is not int or value != expected:
        raise ValueError('Only the explicit emulated Mint v3 fixture may use120second startup; default/turn budgets remain60.')
    return value


def v3_prior_guard(state, fixture):
    from platform_adapters.private_files import descriptor, require_directory
    if fixture.get('priorFailures') != POST_V3_PRIOR_SHA or 'priorFailure' in fixture:
        raise ValueError('The emulated v3 fixture requires all four exact immutable prior records.')
    for name, digest in POST_V3_PRIOR_SHA.items():
        root = state/name; require_directory(root)
        with os.fdopen(descriptor(root/'run.json'), 'rb') as stream:
            raw = stream.read(16385)
        if len(raw) > 16384 or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('A preserved prior qualification record changed; no v3 run is adopted.')
        record = json.loads(raw)
        if name in ('post-install-proof', 'post-install-proof-cwd-v2'):
            required = {'format': 'augmentor-owned-post-install-run/1', 'sourceCommit': POST_SOURCE,
                        'artifactId': fixture['artifactId'], 'bundleManifestSha256': fixture['bundleManifestSha256'],
                        'status': 'failed', 'phase': 'starting', 'pendingRequest': None,
                        'unknownRequestOutcome': False, 'settingsPreserved': True}
        else:
            required = {'installedSource': POST_SOURCE, 'SDKMutations': False,
                        'phase': 'observed', 'modelRequests': 0, 'providerHttpRequests': []}
            required['status'] = 'failed' if name == 'post-install-readiness-only-180-v1' else 'full-adapter-read-observed'
            if record.get('pendingRequest') is not None or record.get('unknownRequestOutcome', False):
                raise ValueError('An uncertain prior request was preserved; no v3 run is adopted.')
        if any(record.get(key) != value for key, value in required.items()):
            raise ValueError('A prior record has an unqualified or uncertain outcome; no v3 run is adopted.')


def post_run_name(state, fixture):
    """Allow only the explicitly recorded no-request failure's cwd correction."""
    name = fixture.get('runDirectory', 'post-install-proof')
    post_startup_budget(fixture)
    if name == POST_V3_RUN:
        v3_prior_guard(state, fixture)
        return name
    if 'priorFailures' in fixture:
        raise ValueError('Prior-record bindings are restricted to the exact emulated v3 fixture.')
    if name == 'post-install-proof' and 'priorFailure' not in fixture:
        return name
    if (name != 'post-install-proof-cwd-v2' or
        fixture.get('priorFailure') != {'sha256': POST_PRIOR_FAILURE_SHA}):
        raise ValueError('The explicit cwd-v2 prior failure binding differs; no run is adopted.')
    from platform_adapters.private_files import descriptor, require_directory
    prior = state/'post-install-proof'
    require_directory(prior)
    with os.fdopen(descriptor(prior/'run.json'), 'rb') as stream:
        raw = stream.read(4097)
    if len(raw) > 4096 or hashlib.sha256(raw).hexdigest() != POST_PRIOR_FAILURE_SHA:
        raise ValueError('The preserved initial failure record differs.')
    record = json.loads(raw)
    required = {'format': 'augmentor-owned-post-install-run/1',
                'run': '1b8cb2ae536d0e6d979e89d15acf5cb1',
                'artifactId': fixture['artifactId'], 'sourceCommit': POST_SOURCE,
                'bundleManifestSha256': fixture['bundleManifestSha256'],
                'proofScriptSha256': POST_PRIOR_PROOF_SHA,
                'status': 'failed', 'phase': 'starting', 'pendingRequest': None,
                'unknownRequestOutcome': False, 'settingsPreserved': True}
    if any(record.get(key) != value for key, value in required.items()):
        raise ValueError('The prior run is not the bound pre-request failure.')
    return name


def begin_post_run(state, fixture):
    from platform_adapters.private_files import require_directory, atomic_json
    require_directory(state)
    root = state/post_run_name(state, fixture)
    try:
        root.mkdir(mode=0o700)
    except FileExistsError:
        raise ValueError('A previous post-install proof exists. Its outcome/state was preserved; no run or request is replayed.') from None
    require_directory(root)
    record = {'format': 'augmentor-owned-post-install-run/1', 'run': secrets.token_hex(16),
              'artifactId': fixture['artifactId'], 'sourceCommit': fixture['sourceCommit'],
              'bundleManifestSha256': fixture['bundleManifestSha256'], 'proofScriptSha256': PROOF_SHA256,
              'fixtureSha256': hashlib.sha256(json.dumps(fixture, sort_keys=True).encode()).hexdigest(),
              'phase': 'prepared', 'pendingRequest': None, 'status': 'running',
              'startupBudgetSeconds': post_startup_budget(fixture), 'turnBudgetSeconds': 60,
              'emulatedStartupQualification': fixture.get('runDirectory') == POST_V3_RUN,
              'public60SecondStartupProofPass': False,
              'priorRecordHashes': fixture.get('priorFailures', {})}
    atomic_json(root/'run.json', record)
    return root, record


def journal_mutation(root, record, adapter, method, payload):
    from platform_adapters.private_files import atomic_json
    record['pendingRequest'] = {'method': method, 'sessionId': payload.get('sessionId')}
    atomic_json(root/'run.json', record)
    # There is exactly one dispatch. A missing response leaves pendingRequest;
    # neither this entry nor a later invocation retries or adopts that outcome.
    result = adapter.call(method, payload)
    record['pendingRequest'] = None
    atomic_json(root/'run.json', record)
    return result


def normalized_histories(histories):
    result = copy.deepcopy(histories)
    for snapshot in result.values():
        snapshot['header'].setdefault('delegationDepth', 0)
    return result


def post_install_proof(bundle, fixture):
    """One-shot post-install acceptance for the explicit existing synthetic VM."""
    manifest, desktop, env = validate_post_fixture(bundle, fixture)
    from platform_adapters.private_files import atomic_json, require_directory
    from platform_adapters.processes import OwnedProcess
    root, record = begin_post_run(POST_HOME/'.local/state/augmentor-install', fixture)
    requests = []; process = None; server = None; thread = None; log = None; companion = None
    startup_budget = post_startup_budget(fixture); startup_observations = []
    baseline = None; history_preserved = False
    home = POST_HOME/'.local/share/augmentor/dsh-home'
    cli = POST_HOME/'.local/share/augmentor/dsh-runtime/node_modules/.bin/dsh'
    runtime_dir = POST_HOME/'runtime'
    if not runtime_dir.exists():
        runtime_dir.mkdir(mode=0o700)
    require_directory(runtime_dir)
    env['PATH'] = str(POST_APP/'node/bin')+':'+str(Path(desktop['python']).parent)+':'+str(cli.parent)+':'+env['PATH']
    env.update(QT_QPA_PLATFORM='offscreen', XDG_RUNTIME_DIR=str(runtime_dir),
               DSH_HOME=str(home), DSH_TELEMETRY_MODE='DISABLED', AUGMENTOR_MODEL_API_KEY='qualification-fixture')
    # The selected immutable loader environment must also reach adapter workers.
    os.environ.clear(); os.environ.update(env)
    sys.path.insert(0, str(POST_APP/'apps/native'))
    from augmentor_linux.adapters.dsh import DshAdapter

    def stop():
        nonlocal process
        if process is not None:
            try:
                if process.poll() is None:
                    process.terminate()
                    try: process.wait(timeout=15)
                    except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=15)
            finally:
                process.close(); process = None

    def start():
        nonlocal process
        process = OwnedProcess([str(POST_APP/'node/bin/node'), str(cli.resolve()), 'web', '--no-open',
                                '--host', '127.0.0.1', '--port', str(fixture['dshPort'])],
                               env=env, cwd=str(POST_HOME), stdout=log, stderr=log)
        began = time.monotonic(); deadline = began+startup_budget
        while time.monotonic() < deadline:
            if process.poll() is not None:
                startup_observations.append({'ready': False, 'elapsedSeconds': time.monotonic()-began})
                raise RuntimeError('The owned post-install DSH process exited; no startup was retried.')
            try:
                adapter = DshAdapter(); adapter.call('host.describe')
                if not adapter.product: raise ValueError('The saved product connection differs.')
            except (OSError, ValueError, RuntimeError):
                time.sleep(.2)
                continue
            elapsed = time.monotonic()-began
            if fixture.get('runDirectory') == POST_V3_RUN and elapsed > startup_budget:
                startup_observations.append({'ready': False, 'elapsedSeconds': elapsed,
                                             'readinessObserved': True, 'withinBudget': False})
                # Outside the polling catch: a successful late read is terminal,
                # before session/model mutations, and is never polled again.
                raise RuntimeError('Emulated v3 readiness was observed after120seconds; no new role request was dispatched.')
            startup_observations.append({'ready': True, 'elapsedSeconds': elapsed,
                                         'withinBudget': elapsed <= startup_budget})
            record['startupObservations'] = startup_observations; atomic_json(root/'run.json', record)
            return adapter
        startup_observations.append({'ready': False, 'elapsedSeconds': time.monotonic()-began})
        raise RuntimeError(f'The owned post-install DSH did not become ready within{startup_budget}seconds.')

    def snapshot(adapter, sessions):
        return {session: adapter.call('session.history', {'sessionId': session}) for session in sessions}

    try:
        companion = memory_companion(POST_APP, desktop['python'], POST_HOME, home, env, root)
        server = fixture_model_server(requests, fixture['modelApiPort'])
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        log = (root/'dsh.log').open('x'); (root/'dsh.log').chmod(0o600)
        record['phase'] = 'preview'; atomic_json(root/'run.json', record)
        run([desktop['python'], '-m', 'augmentor_linux', '--preview', '--screenshot', root/'desktop.png'],
            env={**env, 'PYTHONPATH': str(POST_APP/'apps/native')}, cwd=str(POST_HOME), timeout=120)
        if (root/'desktop.png').stat().st_size <= 10000: raise ValueError('The installed preview is incomplete.')
        record['phase'] = 'starting'; atomic_json(root/'run.json', record)
        adapter = start()
        rows = adapter.call('session.list')['items']
        if any(row.get('running') for row in rows): raise ValueError('Existing DSH work is active; no task was adopted or cancelled.')
        prior = [row['sessionId'] for row in rows]; baseline = snapshot(adapter, prior)
        atomic_json(root/'history-prior.json', baseline)
        sessions = []
        for role in ('linux', 'browser'):
            settings_snapshot(POST_HOME, fixture['settings'])
            session = 'qualification-post-'+record['run']+'-'+role; sessions.append(session)
            for method, payload in (
                ('session.create', {'sessionId': session, 'agentPreset': 'augmentor-'+role+'-product', 'cwd': str(POST_HOME)}),
                ('session.selectModel', {'sessionId': session, 'provider': 'augmentor-model', 'model': 'fixture'}),
                ('session.prompt', {'sessionId': session, 'mode': 'queue', 'content': [{'type': 'text', 'text': 'Reply to the '+role+' qualification fixture.'}]})):
                journal_mutation(root, record, adapter, method, payload)
            deadline = time.monotonic()+60
            while time.monotonic() < deadline:
                history = adapter.call('session.history', {'sessionId': session})
                row = next(row for row in adapter.call('session.list')['items'] if row['sessionId'] == session)
                if not row['running'] and 'LINUX DISTRO FIXTURE VERIFIED' in json.dumps(history): break
                time.sleep(.1)
            else: raise RuntimeError('The owned '+role+' fixture turn did not finish within60seconds.')
        before = snapshot(adapter, prior+sessions); atomic_json(root/'history-before.json', before)
        if normalized_histories({key: before[key] for key in prior}) != normalized_histories(baseline):
            raise ValueError('A preexisting history changed during the fixture turns.')
        count = len(requests)
        if count < 2: raise ValueError('Both role turns must reach the deterministic fixture model.')
        stop()
        record['phase'] = 'restart'; atomic_json(root/'run.json', record)
        adapter = start(); after = snapshot(adapter, prior+sessions); atomic_json(root/'history-after.json', after)
        if normalized_histories(after) != normalized_histories(before): raise ValueError('Restart changed a preserved history.')
        if len(requests) != count: raise ValueError('Restart replayed a model request.')
        history_preserved = True; stop()
        companion_cleanup = companion.finish()
        settings_snapshot(POST_HOME, fixture['settings'])
        report = {'format': 'augmentor-owned-post-install-proof/1', 'status': 'pass', 'sourceCommit': POST_SOURCE,
                  'artifactId': manifest['artifactId'], 'proofScriptSha256': PROOF_SHA256,
                  'selectedPython': desktop['python'], 'dshService': desktop['dshService'],
                  'setupReplayed': False, 'savedSettingsPreserved': True, 'preexistingHistoriesPreserved': True,
                  'offscreenNativeRender': True, 'linuxAndBrowserRoleFixtureTurns': True,
                  'restartPreservesHistoryWithoutReplay': True, 'modelRequests': count,
                  'originalFreshFullProofPass': False, 'realDesktopSessionTested': False,
                  'startupBudgetSeconds': startup_budget, 'turnBudgetSeconds': 60,
                  'emulatedStartupQualification': fixture.get('runDirectory') == POST_V3_RUN,
                  'public60SecondStartupProofPass': startup_budget == 60 and len(startup_observations) == 2 and
                      all(row['ready'] and row['elapsedSeconds'] <= 60 for row in startup_observations),
                  'priorRecordHashes': fixture.get('priorFailures', {}), 'startupObservations': startup_observations,
                  'graphicalBrowserTested': False, 'physicalVoiceTested': False,
                  'companionProofSha256': COMPANION_PROOF_SHA256, 'companionCleanup': companion_cleanup,
                  'licenseReviewComplete': False, 'embeddedSourceCoverageComplete': False}
        atomic_json(root/'report.json', report); record.update(status='complete', phase='complete',
            public60SecondStartupProofPass=report['public60SecondStartupProofPass'])
        return report
    except BaseException:
        record['status'] = 'failed'; record['unknownRequestOutcome'] = record['pendingRequest'] is not None
        raise
    finally:
        try:
            stop()
            if companion is not None and not companion.attempted:
                record['companionCleanup'] = companion.finish()
            elif companion is not None:
                record['companionCleanup'] = dict(companion.record)
        except BaseException:
            record['status'] = 'failed'
            if companion is not None:
                record['companionCleanup'] = dict(companion.record)
            raise
        finally:
            if server is not None:
                if thread is not None: server.shutdown(); thread.join(timeout=5)
                server.server_close()
            if log is not None: log.close()
            try:
                settings_snapshot(POST_HOME, fixture['settings']); record['settingsPreserved'] = True
            except BaseException:
                record['status'] = 'failed'; record['settingsPreserved'] = False
                raise
            finally:
                record['historyPreservedVerified'] = history_preserved
                record['modelRequests'] = len(requests)
                record['startupObservations'] = startup_observations
                atomic_json(root/'run.json', record)


# This admission is intentionally fixed to the reviewed pristine Mint candidate.
FRESH_SOURCE = '16bcb797cc5e84b6a4807d1b88229afebed2c5bf'
FRESH_ARTIFACT = '0.2.13-linuxmint22.3-amd64-complete-preview.1-16bcb797cc5e'
FRESH_MANIFEST_SHA = '9d2bd9d5e1b4c6cd4aadbc0fca7689562ebac33d995f7dd93ebc379e609c59d9'
FRESH_SETUP_SHA = 'd19ae1ecc900f5f3f29610c99b417474ef9e776043e99cabc5c3978dfaf76b52'
FRESH_HOME = Path('/home/augmentor-corrected-proof')
FRESH_RUN_DIRECTORY = 'fresh-emulated-proof16bcb'
FRESH_BOOT_ARGV_SHA = '6f74a927368ad3f9ba3ff9f29ab1f44416e8e7b2036afe18b6fb9c9aadbc1a9e'


def fresh_binding(fixture):
    import re
    expected = {'format': 'augmentor-owned-mint-fresh-emulated/1', 'sourceCommit': FRESH_SOURCE,
                'artifactId': FRESH_ARTIFACT, 'bundleManifestSha256': FRESH_MANIFEST_SHA,
                'setupSha256': FRESH_SETUP_SHA, 'target': 'linuxmint22.3-amd64',
                'uid': 1002, 'gid': 1002, 'user': 'augmentor-corrected-proof', 'home': str(FRESH_HOME),
                'markerSha256': hashlib.sha256(POST_MARKER_TEXT.encode()).hexdigest(),
                'proofScriptSha256': PROOF_SHA256,
                'bootArgvSha256': FRESH_BOOT_ARGV_SHA,
                'startupBudgetSeconds': 120, 'turnBudgetSeconds': 60,
                'qemuName': 'augmentor-mint223-cinnamon-iso', 'qemuPid': 2494740}
    if any(type(fixture.get(key)) is not type(value) or fixture.get(key) != value for key, value in expected.items()):
        raise ValueError('Only the exact clean16bcb fresh ordinary Mint fixture is admitted.')
    if not re.fullmatch('[a-f0-9]{32}', fixture.get('runToken', '')):
        raise ValueError('The fresh proof needs one explicit shared run token.')
    startup = fixture.get('startupDirectory')
    if not isinstance(startup, str) or not Path(startup).is_absolute() or '..' in Path(startup).parts:
        raise ValueError('The fresh proof needs its explicit observed absolute startup directory.')
    ports = [fixture.get(key) for key in ('modelApiPort', 'dshPort')]
    if any(type(v) is not int or not 1024 <= v <= 65535 for v in ports) or len(set(ports)) != 2:
        raise ValueError('The fresh fixture needs distinct ordinary loopback ports.')
    if any(key in fixture for key in ('priorFailure', 'priorFailures', 'settings', 'runDirectory')):
        raise ValueError('A fresh fixture cannot adopt prior settings, journals or retries.')


def fresh_qemu_paths(args, fixture):
    """Resolve the reviewed launch paths, never a daemon's later current cwd."""
    startup = Path(fixture['startupDirectory']); disk = Path(fixture['qemuDisk']); qmp = Path(fixture['qmpSocket'])
    if (not startup.is_absolute() or startup.is_symlink() or not startup.is_dir() or
        startup.stat().st_uid != os.getuid() or startup.stat().st_mode & 0o022 or
        disk.parent != startup or qmp.parent != startup or disk.name != 'guest.qcow2' or qmp.name != 'qmp.sock'):
        raise ValueError('The explicit owned QEMU startup directory/path identity differs.')
    def options(flag):
        values = []
        for index, arg in enumerate(args):
            if arg == flag:
                if index+1 == len(args): raise ValueError('Missing QEMU path option value.')
                values.append(os.fsdecode(args[index+1]))
        return values
    def resolve(value, expected):
        if value not in (expected.name, str(expected)):
            raise ValueError('QEMU permits only the exact same-dir absolute path or plain owned basename.')
        return expected
    def fields(value):
        parts = value.split(','); result = {}
        for part in parts:
            if '=' not in part: raise ValueError('Ambiguous QEMU drive/QMP option.')
            key, item = part.split('=', 1)
            if key in result: raise ValueError('Duplicate QEMU drive/QMP option field.')
            result[key] = item
        return result
    drives = [fields(value) for value in options(b'-drive')]
    candidates = [row for row in drives if row.get('if') == 'virtio']
    if (len(candidates) != 1 or candidates[0].get('format') != 'qcow2' or
        set(candidates[0]) != {'file', 'format', 'if'}):
        raise ValueError('The owned QEMU disk drive is missing or ambiguous.')
    resolve(candidates[0]['file'], disk)
    addresses = options(b'-qmp')
    if len(addresses) != 1 or not addresses[0].startswith('unix:'):
        raise ValueError('The owned QEMU unix QMP address is missing or ambiguous.')
    parts = addresses[0][5:].split(',', 1); resolve(parts[0], qmp)
    if len(parts) != 2 or fields(parts[1]) != {'server': 'on', 'wait': 'off'}:
        raise ValueError('The owned QMP listening options differ.')
    if (disk.is_symlink() or not disk.is_file() or disk.stat().st_uid != os.getuid() or
        qmp.is_symlink() or not stat.S_ISSOCK(qmp.stat().st_mode) or qmp.stat().st_uid != os.getuid()):
        raise ValueError('The owned QEMU disk/QMP paths differ.')
    return disk, qmp, parts[0]


def fresh_qmp_peer(qmp, expected_pid):
    """Kernel peer attribution only: no greeting read, QMP writes or commands."""
    import struct
    qmp = Path(qmp); directory = None; peer = None
    def directory_identity(info):
        return info.st_dev, info.st_ino, info.st_uid, info.st_mode
    def socket_identity(info):
        return info.st_dev, info.st_ino, info.st_uid, info.st_mode, info.st_nlink
    try:
        if not qmp.is_absolute() or qmp.name != 'qmp.sock':
            raise ValueError('The peer attribution needs the exact absolute owned QMP path.')
        directory = os.open(qmp.parent, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        initial_directory = os.fstat(directory)
        if (not stat.S_ISDIR(initial_directory.st_mode) or initial_directory.st_uid != os.getuid() or
            initial_directory.st_mode & 0o022 or directory_identity(qmp.parent.lstat()) != directory_identity(initial_directory)):
            raise ValueError('The QMP startup directory is not the same owned immutable directory.')
        initial_socket = os.stat(qmp.name, dir_fd=directory, follow_symlinks=False)
        if (not stat.S_ISSOCK(initial_socket.st_mode) or initial_socket.st_uid != os.getuid() or
            initial_socket.st_nlink != 1 or socket_identity(qmp.lstat()) != socket_identity(initial_socket)):
            raise ValueError('The QMP socket is not the same owned ordinary endpoint.')
        def still_bound():
            if (directory_identity(os.fstat(directory)) != directory_identity(initial_directory) or
                directory_identity(qmp.parent.lstat()) != directory_identity(initial_directory)):
                raise ValueError('The QMP startup directory was replaced or changed.')
            if (socket_identity(os.stat(qmp.name, dir_fd=directory, follow_symlinks=False)) != socket_identity(initial_socket) or
                socket_identity(qmp.lstat()) != socket_identity(initial_socket)):
                raise ValueError('The QMP socket was replaced or changed.')
        still_bound()
        peer = socket.socket(socket.AF_UNIX)
        # A daemon can bind a relative address in a directory whose full path is
        # longer than sockaddr_un. This local descriptor refers to that same
        # pinned directory, without changing cwd or creating an alias file.
        peer.settimeout(3); peer.connect('/proc/self/fd/'+str(directory)+'/qmp.sock')
        pid, uid, gid = struct.unpack('3i', peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        if pid != expected_pid or uid != os.getuid():
            raise ValueError('The QMP filesystem endpoint has a foreign peer.')
        still_bound()
        return {'pid': pid, 'uid': uid, 'gid': gid, 'protocolBytesSent': 0}
    finally:
        try:
            if peer is not None: peer.close()
        finally:
            if directory is not None: os.close(directory)


def fresh_host_preflight(fixture):
    """Read-only host wrapper admission; stage this result root-owned in the guest."""
    fresh_binding(fixture)
    proc = Path('/proc')/str(fixture['qemuPid'])
    if proc.stat().st_uid != os.getuid():
        raise ValueError('The QEMU process has a foreign host owner.')
    args = (proc/'cmdline').read_bytes().split(b'\0')[:-1]
    start = (proc/'stat').read_text().rsplit(')', 1)[1].split()[19]
    forbidden = (b'vfio', b'virtfs', b'virtiofs', b'fsdev', b'usb-host', b'/dev/', b'-cdrom', b'hostpci')
    if (not args or not Path(os.fsdecode(args[0])).name.startswith('qemu-system-') or
        any(part in arg for arg in args for part in forbidden) or
        b'-name' not in args or args[args.index(b'-name')+1] != fixture['qemuName'].encode()):
        raise ValueError('The exact owned QEMU/no-host-device identity differs.')
    normalized = [os.fsdecode(value) for value in args]; normalized[0] = Path(normalized[0]).name
    if hashlib.sha256(json.dumps(normalized, separators=(',', ':')).encode()).hexdigest() != fixture['bootArgvSha256']:
        raise ValueError('The retained exact QEMU boot arguments differ.')
    disk, qmp, address = fresh_qemu_paths(args, fixture)
    opened = {}
    for path in (proc/'fd').iterdir():
        try: opened[os.readlink(path)] = path.stat()
        except FileNotFoundError: continue
    actual = disk.stat(); held = opened.get(str(disk))
    if (held is None or not stat.S_ISREG(held.st_mode) or held.st_uid != os.getuid() or
        (held.st_dev, held.st_ino) != (actual.st_dev, actual.st_ino)):
        raise ValueError('The owned QEMU process/disk changed during preflight.')
    listeners = []
    for line in (proc/'net/unix').read_text().splitlines()[1:]:
        row = line.split(maxsplit=7)
        if (len(row) == 8 and row[7] in (address, str(qmp)) and int(row[3], 16) & 0x10000 and
            row[4] == '0001' and row[5] == '01' and 'socket:['+row[6]+']' in opened):
            listeners.append(row[6])
    if len(listeners) != 1:
        raise ValueError('The QMP listening kernel socket is not uniquely owned by QEMU.')
    if (proc/'stat').read_text().rsplit(')', 1)[1].split()[19] != start:
        raise ValueError('The owned QEMU start identity changed before peer attribution.')
    peer = fresh_qmp_peer(qmp, fixture['qemuPid'])
    if proc.stat().st_uid != os.getuid() or (proc/'stat').read_text().rsplit(')', 1)[1].split()[19] != start:
        raise ValueError('The owned QEMU start/owner changed after peer attribution.')
    return {'format': 'augmentor-mint-fresh-host-preflight/1', 'runToken': fixture['runToken'],
            'sourceCommit': FRESH_SOURCE, 'proofScriptSha256': PROOF_SHA256,
            'qemuPid': fixture['qemuPid'], 'qemuName': fixture['qemuName'],
            'qemuStart': start, 'argvSha256': hashlib.sha256(b'\0'.join(args)+b'\0').hexdigest(),
            'bootArgvSha256': fixture['bootArgvSha256'], 'startupDirectory': fixture['startupDirectory'],
            'qmpListeningInode': listeners[0], 'qmpPeer': peer,
            'noHostDevicesOrMounts': True, 'guestBootId': fixture['guestBootId'], 'observedUnix': time.time()}


def fresh_vm_identity(fixture, *, ordinary=True):
    import pwd
    fresh_binding(fixture)
    if ordinary:
        if (os.getuid() != 1002 or os.geteuid() != 1002 or os.getgid() != 1002 or
            os.getgroups() != [1002] or Path.home() != FRESH_HOME or os.environ.get('HOME') != str(FRESH_HOME)):
            raise ValueError('Use only the locked dedicated ordinary fresh Mint account.')
        entry = pwd.getpwuid(1002)
        if entry.pw_name != fixture['user'] or entry.pw_dir != str(FRESH_HOME) or entry.pw_uid != 1002 or entry.pw_gid != 1002:
            raise ValueError('The fresh account identity differs.')
    elif os.geteuid() != 0:
        raise ValueError('The external native lease audit requires root after the proof exits.')
    info = POST_MARKER.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o022 or
        POST_MARKER.read_text() != POST_MARKER_TEXT):
        raise ValueError('The owned installed Mint marker differs.')
    fields = dict(row.split('=', 1) for row in Path('/etc/os-release').read_text().splitlines() if '=' in row)
    if fields.get('ID', '').strip('"') != 'linuxmint' or fields.get('VERSION_ID', '').strip('"') != '22.3':
        raise ValueError('The fresh fixture is not Linux Mint22.3.')
    for command, expected in ((['hostname'], 'augmentor-mint223-iso'), (['systemd-detect-virt'], 'qemu'),
                              (['findmnt', '--target', '/', '--noheadings', '--output', 'SOURCE,FSTYPE'], '/dev/vda2 ext4')):
        if subprocess.check_output(command, text=True, timeout=15).strip() != expected:
            raise ValueError('The fresh VM/root identity differs.')
    if ('boot=casper' in Path('/proc/cmdline').read_text() or
        any(v in Path('/proc/mounts').read_text() for v in ('iso9660', 'squashfs', 'virtiofs', '9p')) or
        Path('/sys/module/apparmor/parameters/enabled').read_text().strip() != 'Y' or
        Path('/proc/sys/kernel/random/boot_id').read_text().strip() != fixture.get('guestBootId')):
        raise ValueError('The fresh installed root/security/boot identity differs.')
    if ordinary:
        if any(key.startswith(('AUGMENTOR_', 'DSH_', 'XDG_', 'LD_', 'QT_', 'QML_', 'NODE_', 'RESONANT_')) for key in os.environ):
            raise ValueError('The fresh fixture requires a clean environment.')
        receipt = Path(fixture['hostPreflightPath']); info = receipt.lstat(); raw = receipt.read_bytes()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o022 or
            len(raw) > 8192 or hashlib.sha256(raw).hexdigest() != fixture.get('hostPreflightSha256')):
            raise ValueError('The root-staged host preflight receipt differs.')
        observed = json.loads(raw)
        required = {'format': 'augmentor-mint-fresh-host-preflight/1', 'runToken': fixture['runToken'],
                    'sourceCommit': FRESH_SOURCE, 'proofScriptSha256': PROOF_SHA256,
                    'bootArgvSha256': fixture['bootArgvSha256'], 'startupDirectory': fixture['startupDirectory'],
                    'qemuPid': 2494740, 'qemuName': fixture['qemuName'],
                    'noHostDevicesOrMounts': True, 'guestBootId': fixture['guestBootId']}
        if any(observed.get(k) != v for k, v in required.items()) or not 0 <= time.time()-observed.get('observedUnix', 0) <= 300:
            raise ValueError('The host preflight is stale or belongs to another run/VM.')


def fresh_native_bundle(bundle, fixture):
    raw = (bundle/'bundle.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != FRESH_MANIFEST_SHA:
        raise ValueError('The exact fresh complete manifest differs.')
    manifest = json.loads(raw)
    if (manifest['sourceCommit'] != FRESH_SOURCE or manifest['artifactId'] != FRESH_ARTIFACT or
        manifest['target'] != fixture['target'] or hashlib.sha256((bundle/'setup.py').read_bytes()).hexdigest() != FRESH_SETUP_SHA):
        raise ValueError('The exact fresh source/artifact/installer differs.')
    setup = proof_module(bundle/'setup.py'); setup.verify_bundle(bundle)
    info = (POST_APP/'release.json').lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o022:
        raise ValueError('The native fresh release is not immutable/root-owned.')
    setup.verify_installed_payload(POST_APP, manifest, bundle)
    for command in (['dpkg', '--audit'], ['dpkg', '--verify', 'augmentor-runtime', 'augmentor-desktop']):
        if subprocess.check_output(command, text=True, timeout=60):
            raise ValueError('The native fresh package audit differs.')
    runtime = proof_module(POST_APP/'scripts/linux-python-runtime.py')
    marker = POST_APP/'linux-python-runtime.json'; value = runtime.policy(marker)
    if runtime.contract(value, runtime.digest(marker)) != manifest['pythonRuntime']:
        raise ValueError('The fresh full runtime policy differs.')
    runtime.host(value); runtime.verify_wheels(value, POST_APP/'python-wheels')
    runtime.source_qt().inputs(value, POST_APP/'python-wheels')
    return manifest


def validate_fresh_fixture(bundle, fixture):
    fresh_vm_identity(fixture)
    sys.path.insert(0, str(POST_APP/'services'))
    from platform_adapters.private_files import require_directory
    require_directory(FRESH_HOME)
    # The proof journal is outside installer state. Nothing in a prior account is adopted.
    for name in ('.local/share/augmentor', '.config/augmentor', '.local/state/augmentor-install',
                 '.local/state/augmentor', '.dsh', FRESH_RUN_DIRECTORY):
        path = FRESH_HOME/name
        if path.exists() or path.is_symlink():
            raise ValueError('The fresh proof needs absent application/settings/workspace/journal state.')
    post_account_idle(FRESH_HOME, 'augmentor-dsh.service')
    require_ports_idle((fixture['modelApiPort'], fixture['dshPort']))
    return fresh_native_bundle(bundle, fixture)


def begin_fresh_run(fixture):
    from platform_adapters.private_files import require_directory, atomic_json
    root = FRESH_HOME/FRESH_RUN_DIRECTORY
    try: root.mkdir(mode=0o700)
    except FileExistsError: raise ValueError('The fresh one-shot journal exists; no run or action is adopted.') from None
    require_directory(root)
    fd = os.open(FRESH_HOME, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)
    record = {'format': 'augmentor-owned-fresh-emulated-run/1', 'run': fixture['runToken'],
              'sourceCommit': FRESH_SOURCE, 'artifactId': FRESH_ARTIFACT, 'bundleManifestSha256': FRESH_MANIFEST_SHA,
              'proofScriptSha256': PROOF_SHA256, 'fixtureSha256': hashlib.sha256(json.dumps(fixture, sort_keys=True).encode()).hexdigest(),
              'phase': 'admitted', 'status': 'running', 'pendingRequest': None, 'unknownRequestOutcome': False,
              'completedActions': [], 'startupBudgetSeconds': 120, 'turnBudgetSeconds': 60,
              'originalPublic60FullProofPass': False}
    atomic_json(root/'run.json', record)
    return root, record


def fresh_once(root, record, action, function):
    from platform_adapters.private_files import atomic_json
    if record['pendingRequest'] is not None or action in record['completedActions']:
        raise ValueError('A pending/uncertain/completed fresh action is never retried.')
    record['pendingRequest'] = {'action': action}; atomic_json(root/'run.json', record)
    result = function()  # Exactly one call. Exceptions retain the pending fence.
    record['pendingRequest'] = None; record['completedActions'].append(action); atomic_json(root/'run.json', record)
    return result


def capture_fresh_settings():
    from platform_adapters.private_files import descriptor
    result = {}
    for name in POST_SETTINGS:
        with os.fdopen(descriptor(FRESH_HOME/name), 'rb') as stream: raw = stream.read(1024*1024+1)
        if len(raw) > 1024*1024: raise ValueError('Fresh settings exceed the bounded size.')
        result[name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    return result


def fresh_installed_selection(manifest, fixture):
    from platform_adapters.private_files import read_json
    receipt = read_json(FRESH_HOME/'.local/state/augmentor-install/installation.json')
    if any(receipt.get(k) != v for k, v in {'status': 'installed', 'bundle': FRESH_ARTIFACT, 'target': manifest['target']}.items()):
        raise ValueError('A known successful exact receipt is required; setup is not retried.')
    desktop = read_json(FRESH_HOME/'.local/share/augmentor/desktop.json')
    dsh = read_json(FRESH_HOME/'.config/augmentor/harnesses.json')['dsh']
    home = FRESH_HOME/'.local/share/augmentor/dsh-home'
    if (desktop.get('root') != str(POST_APP) or desktop.get('node') != str(POST_APP/'node/bin/node') or
        desktop.get('dshService') != 'augmentor-dsh.service' or desktop.get('dshHome') != str(home) or
        dsh.get('home') != str(home) or dsh.get('version') != manifest['version'] or
        dsh.get('endpoint') != 'http://127.0.0.1:'+str(fixture['dshPort']) or desktop.get('dshEndpoint') != dsh.get('endpoint')):
        raise ValueError('The fresh installed selection/saved endpoint differs.')
    for name, digest in desktop.get('files', {}).items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or hashlib.sha256((POST_APP/path).read_bytes()).hexdigest() != digest:
            raise ValueError('The fresh selected desktop inventory differs.')
    import yaml
    model = yaml.safe_load((home/'settings.yaml').read_text()); provider = model['llm-pi-ai']['providers']['augmentor-model']
    if (provider.get('baseURL') != 'http://127.0.0.1:'+str(fixture['modelApiPort'])+'/v1' or
        provider.get('api') != 'openai-completions' or provider.get('apiKeyEnv') != 'AUGMENTOR_MODEL_API_KEY' or
        len(provider.get('models', [])) != 1 or provider['models'][0]['id'] != 'fixture' or
        model.get('agent-default-model') != {'provider': 'augmentor-model', 'model': 'fixture'} or
        (FRESH_HOME/'.local/state/augmentor-install/model.env').read_text() != 'AUGMENTOR_MODEL_API_KEY="qualification-fixture"\n'):
        raise ValueError('The fresh selection is not the dedicated deterministic localhost model.')
    post_account_idle(FRESH_HOME, desktop['dshService'])
    from lifecycle.lease import hold
    hold('runtime')
    return desktop, selected_python_environment(POST_APP, Path(desktop['python']))


def fresh_start(process_factory, adapter_factory, observations):
    process = process_factory(); began = time.monotonic()
    try:
        while time.monotonic()-began < 120:
            exit_code = process.poll()
            if exit_code is not None:
                observations.append({'ready': False, 'elapsedSeconds': time.monotonic()-began, 'processExit': exit_code})
                raise RuntimeError('The fresh owned DSH exited; no startup is retried.')
            try:
                adapter = adapter_factory(); adapter.call('host.describe')
                if not adapter.product: raise ValueError('The fresh product connection differs.')
            except (OSError, ValueError, RuntimeError):
                time.sleep(.2); continue
            elapsed = time.monotonic()-began
            observations.append({'ready': elapsed <= 120, 'readinessObserved': True, 'elapsedSeconds': elapsed, 'withinBudget': elapsed <= 120})
            if elapsed > 120: raise RuntimeError('Fresh authenticated readiness exceeded120seconds; no next SDK mutation is dispatched.')
            return process, adapter
        observations.append({'ready': False, 'elapsedSeconds': time.monotonic()-began})
        raise RuntimeError('Fresh authenticated readiness was not observed within120seconds.')
    except BaseException:
        # Caller must own this child even when startup refuses.
        fresh_stop(process)
        raise


def fresh_stop(process):
    if process is not None:
        try:
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=15)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=15)
        finally: process.close()


def fresh_emulated_proof(bundle, fixture):
    """New ordinary account; unchanged installer, explicit emulated startup only."""
    manifest = validate_fresh_fixture(bundle, fixture)
    from platform_adapters.private_files import atomic_json, require_directory
    from platform_adapters.processes import OwnedProcess
    root, record = begin_fresh_run(fixture)
    settings = None; server = None; thread = None; thread_started = False; process = None; companion = None; log = None
    requests = []; observations = []; turn_observations = []; history_preserved = False; report = None
    try:
        runtime_dir = FRESH_HOME/'runtime'
        if not runtime_dir.exists(): runtime_dir.mkdir(mode=0o700)
        require_directory(runtime_dir)
        env = {**os.environ, 'AUGMENTOR_FIXTURE_KEY': 'qualification-fixture', 'QT_QPA_PLATFORM': 'offscreen',
               'XDG_RUNTIME_DIR': str(runtime_dir), 'PATH': str(POST_APP/'node/bin')+':'+os.environ['PATH']}
        server = fixture_model_server(requests, fixture['modelApiPort'])
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start(); thread_started = True
        log = (root/'dsh.log').open('x'); (root/'dsh.log').chmod(0o600)
        command = ['/usr/bin/python3', '-B', bundle/'setup.py', '--bundle', bundle, '--skip-packages', '--no-services',
                   '--non-interactive', '--model-url', 'http://127.0.0.1:'+str(fixture['modelApiPort'])+'/v1',
                   '--model', 'fixture', '--api-key-env', 'AUGMENTOR_FIXTURE_KEY', '--port', str(fixture['dshPort'])]
        record['phase'] = 'setup'; atomic_json(root/'run.json', record)
        fresh_once(root, record, 'setup.initial', lambda: run(command, env=env, cwd=str(FRESH_HOME), stdout=log, stderr=log))
        desktop, selected = fresh_installed_selection(manifest, fixture)
        settings = capture_fresh_settings(); record['settings'] = settings; atomic_json(root/'run.json', record)
        # Only a verified installed receipt permits the documented idempotent call.
        fresh_once(root, record, 'setup.installed-idempotence', lambda: run(command, env=env, cwd=str(FRESH_HOME), stdout=log, stderr=log))
        settings_snapshot(FRESH_HOME, settings)
        data = FRESH_HOME/'.local/share/augmentor'; home = data/'dsh-home'
        for path in (FRESH_HOME/'.config/autostart/com.augmentor.Agent.desktop',
                     FRESH_HOME/'.local/share/applications/com.augmentor.Agent.secondary.desktop',
                     FRESH_HOME/'.config/chromium/NativeMessagingHosts/com.augmentor.agent.json',
                     data/'browser'/manifest['version']/'voice.mjs'):
            if not path.is_file(): raise ValueError('The fresh desktop/Browser setup is incomplete.')
        for plugin in ('dsh-resonant-voice', 'dsh-adaptive-reasoning', 'dsh-model-picker-augmented'):
            if not (home/'profiles/web/node_modules'/plugin/'package.json').is_file(): raise ValueError('The fresh installed plugin is absent.')
        workspace = home/'storages/workspace.json'
        empty_workspace_guard(home, hashlib.sha256(workspace.read_bytes()).hexdigest())
        env = {**selected, 'DSH_HOME': str(home), 'DSH_TELEMETRY_MODE': 'DISABLED',
               'AUGMENTOR_MODEL_API_KEY': 'qualification-fixture', 'QT_QPA_PLATFORM': 'offscreen', 'XDG_RUNTIME_DIR': str(runtime_dir)}
        os.environ.clear(); os.environ.update(env)
        companion = memory_companion(POST_APP, desktop['python'], FRESH_HOME, home, env, root)
        record['phase'] = 'preview'; atomic_json(root/'run.json', record)
        run([desktop['python'], '-m', 'augmentor_linux', '--preview', '--screenshot', root/'desktop.png'],
            env={**env, 'PYTHONPATH': str(POST_APP/'apps/native')}, cwd=str(FRESH_HOME), timeout=120)
        if (root/'desktop.png').stat().st_size <= 10000: raise ValueError('The fresh preview is incomplete.')
        sys.path.insert(0, str(POST_APP/'apps/native'))
        from augmentor_linux.adapters.dsh import DshAdapter
        cli = data/'dsh-runtime/node_modules/.bin/dsh'
        def start():
            return fresh_start(lambda: OwnedProcess([str(POST_APP/'node/bin/node'), str(cli.resolve()), 'web', '--no-open',
                '--host', '127.0.0.1', '--port', str(fixture['dshPort'])], env=env, cwd=str(FRESH_HOME), stdout=log, stderr=log), DshAdapter, observations)
        record['phase'] = 'starting'; atomic_json(root/'run.json', record)
        process, adapter = start()
        if adapter.call('session.list')['items']: raise ValueError('The fresh runtime has prior sessions; none are adopted.')
        sessions = []
        for role in ('linux', 'browser'):
            record['phase'] = role+'-role'; atomic_json(root/'run.json', record)
            settings_snapshot(FRESH_HOME, settings)
            session = 'qualification-fresh-'+record['run']+'-'+role; sessions.append(session)
            for method, payload in (
                ('session.create', {'sessionId': session, 'agentPreset': 'augmentor-'+role+'-product', 'cwd': str(FRESH_HOME)}),
                ('session.selectModel', {'sessionId': session, 'provider': 'augmentor-model', 'model': 'fixture'}),
                ('session.prompt', {'sessionId': session, 'mode': 'queue', 'content': [{'type': 'text', 'text': 'Reply to the '+role+' qualification fixture.'}]})):
                fresh_once(root, record, session+':'+method, lambda m=method, p=payload: adapter.call(m, p))
            began = time.monotonic()
            while time.monotonic()-began < 60:
                history = adapter.call('session.history', {'sessionId': session})
                row = next(v for v in adapter.call('session.list')['items'] if v['sessionId'] == session)
                elapsed = time.monotonic()-began
                completed = not row['running'] and 'LINUX DISTRO FIXTURE VERIFIED' in json.dumps(history)
                if completed or elapsed > 60:
                    turn_observations.append({'role': role, 'elapsedSeconds': elapsed,
                        'completionObserved': completed, 'withinBudget': elapsed <= 60})
                    record['turnObservations'] = turn_observations; atomic_json(root/'run.json', record)
                if elapsed > 60:
                    raise RuntimeError('The fresh '+role+' turn reads exceeded60seconds; no next SDK mutation is dispatched.')
                if completed: break
                time.sleep(.1)
            else: raise RuntimeError('The fresh '+role+' fixture turn did not finish within60seconds.')
            settings_snapshot(FRESH_HOME, settings)
        before = {sid: adapter.call('session.history', {'sessionId': sid}) for sid in sessions}
        atomic_json(root/'history-before.json', before); count = len(requests)
        if count < 2: raise ValueError('Both fresh roles must reach the counted model fixture.')
        fresh_stop(process); process = None
        record['phase'] = 'restart'; atomic_json(root/'run.json', record)
        process, adapter = start()
        after = {sid: adapter.call('session.history', {'sessionId': sid}) for sid in sessions}
        atomic_json(root/'history-after.json', after)
        if normalized_histories(after) != normalized_histories(before): raise ValueError('Fresh restart changed history.')
        if len(requests) != count: raise ValueError('Fresh restart replayed a model request.')
        history_preserved = True; fresh_stop(process); process = None
        cleanup = companion.finish(); settings_snapshot(FRESH_HOME, settings)
        report = {'format': 'augmentor-owned-fresh-emulated-proof/1', 'status': 'pass', 'sourceCommit': FRESH_SOURCE,
                  'artifactId': FRESH_ARTIFACT, 'proofScriptSha256': PROOF_SHA256, 'setupScriptSha256': FRESH_SETUP_SHA,
                  'installerOverlayUsed': False, 'ordinaryUserSetup': True, 'repeatPreservesSettings': True,
                  'savedSettingsPreserved': True, 'offscreenNativeRender': True, 'secondWindowEntry': True,
                  'nativeHostRegistered': True, 'linuxAndBrowserRoleFixtureTurns': True,
                  'restartPreservesHistoryWithoutReplay': True, 'selectedPython': desktop['python'],
                  'dshService': desktop['dshService'], 'modelRequests': count, 'startupObservations': observations,
                  'turnObservations': turn_observations,
                  'startupBudgetSeconds': 120, 'turnBudgetSeconds': 60, 'emulatedStartupQualification': True,
                  'originalPublic60FullProofPass': False, 'public60SecondStartupProofPass': False,
                  'realDesktopSessionTested': False, 'graphicalBrowserTested': False, 'physicalVoiceTested': False,
                  'licenseReviewComplete': False, 'embeddedSourceCoverageComplete': False,
                  'externalLeaseAuditRequired': True, 'companionProofSha256': COMPANION_PROOF_SHA256,
                  'companionCleanup': cleanup}
        record.update(status='complete', phase='complete')
        return report
    except BaseException:
        record['status'] = 'failed'; record['unknownRequestOutcome'] = record['pendingRequest'] is not None
        raise
    finally:
        try:
            fresh_stop(process)
            if companion is not None:
                if not companion.attempted: companion.finish()
                record['companionCleanup'] = dict(companion.record)
        except BaseException:
            record['status'] = 'failed'
            if companion is not None: record['companionCleanup'] = dict(companion.record)
            raise
        finally:
            try:
                if server is not None:
                    try:
                        if thread_started: server.shutdown(); thread.join(timeout=5)
                    finally: server.server_close()
            except BaseException:
                record['status'] = 'failed'; raise
            finally:
                if log is not None: log.close()
                try:
                    if settings is not None: settings_snapshot(FRESH_HOME, settings); record['settingsPreserved'] = True
                except BaseException:
                    record['status'] = 'failed'; record['settingsPreserved'] = False; raise
                finally:
                    record.update(modelRequests=len(requests), startupObservations=observations,
                                  turnObservations=turn_observations, historyPreservedVerified=history_preserved)
                    atomic_json(root/'run.json', record)
                    if report is not None and record['status'] == 'complete':
                        atomic_json(root/'report.json', report)


def fresh_audit_record(record, fixture):
    if (record.get('run') != fixture['runToken'] or record.get('sourceCommit') != FRESH_SOURCE or
        record.get('artifactId') != FRESH_ARTIFACT or record.get('bundleManifestSha256') != FRESH_MANIFEST_SHA or
        record.get('proofScriptSha256') != fixture['proofScriptSha256'] or
        record.get('fixtureSha256') != hashlib.sha256(json.dumps(fixture, sort_keys=True).encode()).hexdigest()):
        raise ValueError('The external audit cannot adopt another journal/tool/fixture.')


def fresh_external_audit(bundle, fixture):
    """Root wrapper readback after the proof exits; never stop any process."""
    fresh_vm_identity(fixture, ordinary=False); fresh_native_bundle(bundle, fixture)
    import fcntl
    root = FRESH_HOME/FRESH_RUN_DIRECTORY; info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 1002 or info.st_mode & 0o077:
        raise ValueError('The fresh audit journal root differs.')
    path = root/'run.json'; info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 1002 or info.st_mode & 0o077 or info.st_nlink != 1:
        raise ValueError('The fresh audit journal file differs.')
    record = json.loads(path.read_bytes())
    fresh_audit_record(record, fixture)
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid(): continue
        try:
            if proc.stat().st_uid != 1002: continue
            args = (proc/'cmdline').read_bytes(); env = (proc/'environ').read_bytes()
            if any(v in args for v in (str(POST_APP).encode(), b'/setup.py', b'--owned-vm-fresh-emulated-fixture')) or str(FRESH_HOME/'.local/share/augmentor').encode() in env:
                raise ValueError('The fresh proof/product child is still active; it is preserved.')
        except FileNotFoundError: continue
    for path in (Path('/var/lib/augmentor-package-maintenance/pending.json'),
                 Path('/run/augmentor/augmentor-runtime.pending'), Path('/run/augmentor/augmentor-desktop.pending')):
        if path.exists() or path.is_symlink(): raise ValueError('Native package maintenance is pending; it is preserved.')
    leases = []
    try:
        for component in ('runtime', 'desktop'):
            fd = os.open('/run/augmentor/augmentor-'+component+'.lock', os.O_RDONLY|os.O_NOFOLLOW)
            leases.append(fd); info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o022:
                raise ValueError('The native external lease identity differs.')
            fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
        require_ports_idle((fixture['modelApiPort'], fixture['dshPort']))
        memory = FRESH_HOME/'.local/state/augmentor/dual-memory.sock'
        if memory.exists() or memory.is_symlink():
            raise ValueError('A fresh memory socket remains; no daemon is adopted or stopped.')
        if record.get('settings'):
            if set(record['settings']) != POST_SETTINGS:
                raise ValueError('The external settings audit needs all five original hashes.')
            for name, expected in record['settings'].items():
                path = FRESH_HOME/name; info = path.lstat(); raw = path.read_bytes()
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != 1002 or info.st_nlink != 1 or info.st_mode & 0o077 or
                    {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)} != expected):
                    raise ValueError('The fresh external settings preservation audit differs.')
    finally:
        for fd in reversed(leases): os.close(fd)
    return {'format': 'augmentor-owned-fresh-emulated-external-audit/1', 'sourceCommit': FRESH_SOURCE,
            'run': fixture['runToken'], 'proofOutcome': record['status'], 'runSha256': hashlib.sha256((root/'run.json').read_bytes()).hexdigest(),
            'proofScriptSha256': record['proofScriptSha256'], 'fixtureSha256': record['fixtureSha256'],
            'nativeAudit': True, 'exclusiveLeasesIdle': True, 'noOwnedProcessOrListener': True,
            'settingsPreserved': bool(record.get('settings')), 'SDKPending': record['pendingRequest'],
            'protectedEarlierAccountsAuditRequired': True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--out', type=Path, default=Path('/tmp/complete-linux-proof.json'))
    p.add_argument('--user-phase', action='store_true', help=argparse.SUPPRESS)
    p.add_argument('--setup-script', type=Path,
                   help='Explicit diagnostic installer override; records its hash and cannot count as matching-bundle acceptance.')
    p.add_argument('--owned-vm-post-install-fixture', type=Path,
                   help='Explicit one-shot clean2035 Mint fixture; verifies saved state and never invokes setup.')
    p.add_argument('--owned-vm-fresh-emulated-fixture', type=Path,
                   help='One-shot pristine clean16bcb Mint account; separately labelled120-second emulated startup.')
    p.add_argument('--fresh-emulated-external-audit', action='store_true',
                   help='Read-only root audit after the fresh proof exits; requires its exact fixture.')
    a = p.parse_args()
    if a.owned_vm_fresh_emulated_fixture:
        if a.user_phase or a.setup_script or a.owned_vm_post_install_fixture:
            p.error('Fresh emulated fixture cannot use another proof phase or installer override.')
        sys.path.insert(0, str(POST_APP/'services'))
        raw = a.owned_vm_fresh_emulated_fixture.read_bytes()
        info = a.owned_vm_fresh_emulated_fixture.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o022 or len(raw) > 16384:
            p.error('The fresh fixture must be a bounded immutable root-staged ordinary file.')
        fixture = json.loads(raw)
        report = (fresh_external_audit if a.fresh_emulated_external_audit else fresh_emulated_proof)(a.bundle.resolve(), fixture)
        print(json.dumps(report))
        return
    if a.fresh_emulated_external_audit:
        p.error('External fresh audit requires its exact fresh fixture.')
    if a.owned_vm_post_install_fixture:
        if a.user_phase or a.setup_script:
            p.error('Post-install fixture cannot use user-phase or an installer override.')
        sys.path.insert(0, str(POST_APP/'services'))
        from platform_adapters.private_files import read_json
        report = post_install_proof(a.bundle.resolve(), read_json(a.owned_vm_post_install_fixture))
        print(json.dumps(report))
        return
    if not any(Path(marker).exists() for marker in ('/.dockerenv', '/run/.containerenv')):
        raise SystemExit('This proof requires a disposable Docker/Podman container.')
    bundle = a.bundle.resolve()
    if a.user_phase:
        user_proof(bundle, a.setup_script)
        return
    assert os.geteuid() == 0
    if Path('/usr/lib/augmentor/release.json').exists():
        raise ValueError('Use a fresh container without an installed Augmentor payload; equal package versions can mask another source revision.')
    manifest=json.loads((bundle/'bundle.json').read_text())
    bootstrap='/usr/bin/python3.13' if manifest['target']=='opensuse-leap16.0-x86_64' else '/usr/bin/python3'
    plan = json.loads(subprocess.check_output([bootstrap, '-B', str(bundle/'setup.py'), '--bundle', str(bundle), '--plan'], text=True))
    command = plan['system']['command']
    assert command[:2] in (['sudo', 'apt'], ['sudo', 'dnf'], ['sudo','pacman'],['sudo','zypper'])
    if command[1] == 'apt':
        run(['apt-get', 'update', '-qq'])
        run(['apt-get', 'install', '-y', '--no-install-recommends', 'passwd', 'util-linux'])
    elif command[1]=='dnf':
        run(['dnf', 'install', '-y', 'shadow-utils', 'util-linux'])
    elif not shutil.which('useradd') or not shutil.which('runuser'):
        helpers=(['pacman','-S','--needed','--noconfirm','shadow','util-linux'] if command[1]=='pacman'
                 else ['zypper','--non-interactive','install','--no-recommends','shadow','util-linux'])
        run(helpers)
    # The actual installer runs as a fresh ordinary user below; root performs
    # only the exact package plan, avoiding a sudo dependency in minimal images.
    for index,command in enumerate(plan['system']['commands']):
        if plan['system']['guardVerificationBeforeApplication'] and index==len(plan['system']['commands'])-1:
            spec=importlib.util.spec_from_file_location('fixture_independent_verifier',bundle/'linux-package-verification.py')
            verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
            verifier.verify_guard(manifest,bundle)
        native=command[1:]
        if native[0]=='zypper':
            # Own checksum-verified private candidate RPM only; upstream repo
            # signature policy remains intact. This flag is fixture-only.
            native=native[:3]+['--allow-unsigned-rpm']+native[3:]
        run(native)
    manifest = json.loads((bundle/'bundle.json').read_text())
    release = json.loads(Path('/usr/lib/augmentor/release.json').read_text())
    assert release['source'] == {'commit': manifest['sourceCommit'], 'dirty': False}
    assert release['version'] == manifest['version']
    run(['useradd', '-m', '-s', '/bin/sh', 'augmentor-complete-proof'])
    command=['runuser', '-u', 'augmentor-complete-proof', '--', bootstrap, '-B', Path(__file__).resolve(), '--bundle', bundle, '--user-phase']
    if a.setup_script:command+=['--setup-script',a.setup_script.resolve()]
    run(command)
    report = json.loads(Path('/home/augmentor-complete-proof/complete-proof.json').read_text())
    report['systemPlan'] = plan['system']
    a.out.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
