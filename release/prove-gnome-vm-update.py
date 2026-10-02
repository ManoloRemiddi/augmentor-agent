#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Stage/select a verified candidate and adopt it in the marked idle GNOME guest.

The package baseline remains immutable. Only the dedicated guest's canonical
updater changes selection, and one accepted idle close precedes one cold launch.
Private output records exact selected/running identities and portal bus replies.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time


def command(args, timeout=30):
    return subprocess.check_output(args, text=True, timeout=timeout).strip()


def wait(predicate, label, seconds=90):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(.2)
    raise RuntimeError('Timed out waiting for ' + label)


assert os.geteuid() != 0 and os.environ.get('USER') == 'augmentor-proof'
assert Path('/etc/augmentor-test-vm').read_text() == 'Isolated Augmentor Fedora GNOME qualification VM\n'
assert command(['systemd-detect-virt']) == 'qemu'
assert command(['getenforce']) == 'Enforcing'
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--candidate', type=Path, required=True)
p.add_argument('--source', required=True)
p.add_argument('--previous-source', required=True)
p.add_argument('--window-sha256', required=True)
a = p.parse_args()
assert re.fullmatch('[0-9a-f]{40}', a.source)
assert re.fullmatch('[0-9a-f]{40}', a.previous_source)
assert re.fullmatch('[0-9a-f]{64}', a.window_sha256)
candidate = a.candidate.resolve()
assert candidate.is_relative_to(Path.home()/'managed-update-candidates')
release = json.loads((candidate/'release.json').read_text())
assert release['source'] == {'commit': a.source, 'dirty': False}
assert release['version'] == '0.2.13'
assert hashlib.sha256((candidate/'apps/native/augmentor_linux/window.py').read_bytes()).hexdigest() == a.window_sha256
subprocess.run(['rpm', '-V', 'augmentor-agent'], check=True, timeout=30)
environment = dict(row.split('=', 1) for row in command(
    ['systemctl', '--user', 'show-environment']).splitlines() if '=' in row)
for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'XDG_CURRENT_DESKTOP',
            'XDG_RUNTIME_DIR', 'XDG_SESSION_TYPE', 'DBUS_SESSION_BUS_ADDRESS'):
    if key in environment:
        os.environ[key] = environment[key]
assert environment['XDG_SESSION_TYPE'] == 'wayland' and environment['XDG_CURRENT_DESKTOP'] == 'GNOME'
sessions = [row.split()[0] for row in command(['loginctl', 'list-sessions', '--no-legend']).splitlines()
            if len(row.split()) > 3 and row.split()[2:4] == ['augmentor-proof', 'seat0']]
assert len(sessions) == 1
session = dict(row.split('=', 1) for row in command(['loginctl', 'show-session', sessions[0],
               '-p', 'Type', '-p', 'Class', '-p', 'Active', '-p', 'State', '-p', 'Seat']).splitlines())
assert session == {'Type': 'wayland', 'Class': 'user', 'Active': 'yes', 'State': 'active', 'Seat': 'seat0'}
data = Path.home()/'.local/share/augmentor'
initial_selection = json.loads((data/'desktop.json').read_text())
previous_root = Path(initial_selection['root'])
assert previous_root == Path('/usr/lib/augmentor') or previous_root.is_relative_to(data/'releases')
assert json.loads((previous_root/'release.json').read_text())['source'] == {'commit': a.previous_source, 'dirty': False}
if previous_root != Path('/usr/lib/augmentor'):
    assert initial_selection['sourceRef'] == a.previous_source
    import importlib.util
    spec = importlib.util.spec_from_file_location('owned_previous_deployment', data/'desktop-deployment.py')
    deployment = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(deployment)
    deployment.verify(previous_root)
assert initial_selection['dshService'] is None
updater = Path.home()/'.local/bin/augmentor-update'
launcher = Path.home()/'.local/bin/augmentor-agent'


def exchange(action='maintenance.status'):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(3)
        try:
            client.connect(str(Path(os.environ['XDG_RUNTIME_DIR'])/'augmentor-linux-pi.sock'))
            client.sendall(action.encode())
            with client.makefile('rb') as stream:
                raw = stream.readline(16384)
                return json.loads(raw) if raw else None
        except (FileNotFoundError, ConnectionRefusedError, ConnectionResetError, TimeoutError):
            if action != 'maintenance.status':
                raise  # Never treat an unknown action outcome as safe to replay.
            return None


def owned(status):
    return int(command(['systemctl', '--user', 'show', 'augmentor-desktop.service',
                        '--value', '-p', 'MainPID'])) == status['pid']


initial = exchange()
assert initial and initial['accepted'] and not initial['busy'] and not initial['running']
assert not initial['draftPresent'] and not initial['online'] and owned(initial)
assert initial['buildRoot'] == initial_selection['root']
staged = Path(command([str(updater), 'stage', str(candidate), '--source-ref', a.source,
                      '--node', str(candidate/'node/bin/node')], timeout=90)).resolve()
assert staged.is_relative_to(data/'releases')
assert json.loads((data/'desktop.json').read_text()) == initial_selection
assert exchange() == initial and owned(initial)
assert (staged/'fedora-package.json').read_bytes() == (candidate/'fedora-package.json').read_bytes()
assert command([initial_selection['python'], str(staged/'scripts/run-component.py'),
                'runtime', str(staged/'node/bin/node'), '--version']) == 'v24.19.0'
command([str(updater), 'activate', str(staged)], timeout=90)
selected = json.loads((data/'desktop.json').read_text())
assert selected['root'] == str(staged) and selected['sourceRef'] == a.source
assert selected['python'] == initial_selection['python']
assert selected['node'] == str(staged/'node/bin/node')
assert json.loads((data/'desktop.previous.json').read_text()) == initial_selection
assert exchange() == initial and owned(initial)
pending = json.loads(command([str(updater), 'status']))
assert pending['running']['desktop']['updatePending'] is True
assert pending['running']['desktop']['buildRoot'] == initial_selection['root']
out = Path.home()/'gnome-managed-update-proof'
out.mkdir(mode=0o700, exist_ok=True)
buslog_path = out/'portal-registration.log'
with buslog_path.open('w') as buslog:
    monitor = subprocess.Popen(['dbus-monitor', '--session',
        "type='method_call',interface='org.freedesktop.host.portal.Registry'",
        "type='method_call',interface='org.freedesktop.portal.Settings'",
        "type='method_return',sender='org.freedesktop.portal.Desktop'",
        "type='error',sender='org.freedesktop.portal.Desktop'"],
        stdout=buslog, stderr=subprocess.PIPE, text=True)
    try:
        time.sleep(.5)
        assert monitor.poll() is None
        assert exchange('maintenance.close')['accepted'] is True
        wait(lambda: exchange() is None, 'accepted idle close')
        wait(lambda: command(['systemctl', '--user', 'show', 'augmentor-desktop.service',
                             '--value', '-p', 'ActiveState']) == 'inactive', 'clean service exit')
        command([str(launcher)])
        reopened = wait(exchange, 'canonical new-release launch')
        assert reopened['pid'] != initial['pid'] and owned(reopened)
        assert reopened['buildRoot'] == str(staged) and not reopened['running'] and not reopened['draftPresent']
        assert not reopened['online']
    finally:
        monitor.terminate()
        monitor.wait(timeout=10)

# Identify the actual app's portal sender by the bus daemon's process ID.
# Other fixture or desktop clients can make concurrent Settings calls.
from gi.repository import Gio, GLib
bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
trace = buslog_path.read_text()
candidates = set(re.findall(r'^method call .*?sender=(:\d+\.\d+) ', trace, re.M))
senders = []
for sender in candidates:
    try:
        pid = bus.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus',
            'org.freedesktop.DBus', 'GetConnectionUnixProcessID', GLib.Variant('(s)', (sender,)),
            None, 0, 3000, None).unpack()[0]
    except GLib.Error:
        continue  # Unrelated short-lived desktop clients can disappear.
    if pid == reopened['pid']:
        senders.append(sender)
assert len(senders) == 1, 'Actual Qt portal sender was not uniquely identified.'
qt_sender = senders[0]
calls = [header for header in re.findall(r'^method call [^\n]+', trace, re.M)
         if 'sender='+qt_sender+' ->' in header]
registrations = [header for header in calls if 'interface=org.freedesktop.host.portal.Registry; member=Register' in header]
assert len(registrations) == 1
settings = [header for header in calls if 'interface=org.freedesktop.portal.Settings;' in header]
assert not settings or calls.index(registrations[0]) < calls.index(settings[0])
serial = re.search(r' serial=(\d+) ', registrations[0]).group(1)
replies = [header for header in re.findall(r'^(?:method return|error) [^\n]+', trace, re.M)
           if 'destination='+qt_sender+' ' in header and re.search(r' reply_serial='+serial+r'(?:\s|$)', header)]
assert len(replies) == 1 and replies[0].startswith('method return '), 'Actual Qt registration did not succeed.'
adopted = json.loads(command([str(updater), 'status']))
assert adopted['running']['desktop']['updatePending'] is False
assert adopted['running']['desktop']['buildRoot'] == str(staged)
sys.path.insert(0, str(staged/'services/desktop'))
from gnome import GnomeObserver
scene = GnomeObserver(bus).read()
assert scene['guards']['screenShieldAvailable'] is True and not scene['guards']['locked']
subprocess.run(['rpm', '-V', 'augmentor-agent'], check=True, timeout=30)
report = {'format': 'augmentor-gnome-full-vm-managed-update/1',
    'source': release['source'], 'version': release['version'],
    'previousSource': a.previous_source,
    'proofSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'registeredUpdaterSha256': hashlib.sha256((data/'desktop-deployment.py').read_bytes()).hexdigest(),
    'selectedArtifactContainsRegisteredUpdater': (staged/'scripts/desktop-deployment.py').read_bytes() == (data/'desktop-deployment.py').read_bytes(),
    'canonicalLauncherSha256': hashlib.sha256((data/'desktop-launch.py').read_bytes()).hexdigest(),
    'windowSha256': a.window_sha256, 'selected': selected,
    'previous': initial_selection, 'initial': initial, 'reopened': reopened,
    'stagingPreservesSelectionAndRunningProcess': True,
    'stagedPackageBackendPreserved': True, 'stagedActualRuntimeLeasePassed': True,
    'activationPreservesRunningProcess': True, 'selectedVsRunningPendingReported': True,
    'previousSelectionRetained': True, 'idleCloseAccepted': True,
    'cleanServiceExit': True, 'canonicalServiceOwnsNewRelease': True,
    'adoptionClearsPending': True, 'actualQtRegistrationSucceeded': True,
    'actualQtRegisterBeforeSettings': True,
    'portalTraceSha256': hashlib.sha256(trace.encode()).hexdigest(),
    'graphicalSession': session, 'scene': scene,
    'originalPackageVerified': True, 'selinuxEnforcing': command(['getenforce']) == 'Enforcing',
    'connectedHarnessTested': False, 'modelTurnTested': False,
    'newReleaseLoginRebootTested': False, 'gnomeInputToolsEnabled': False}
(out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
