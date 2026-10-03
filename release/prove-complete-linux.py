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


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--out', type=Path, default=Path('/tmp/complete-linux-proof.json'))
    p.add_argument('--user-phase', action='store_true', help=argparse.SUPPRESS)
    p.add_argument('--setup-script', type=Path,
                   help='Explicit diagnostic installer override; records its hash and cannot count as matching-bundle acceptance.')
    p.add_argument('--owned-vm-post-install-fixture', type=Path,
                   help='Explicit one-shot clean2035 Mint fixture; verifies saved state and never invokes setup.')
    a = p.parse_args()
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
