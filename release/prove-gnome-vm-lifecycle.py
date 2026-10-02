#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise duplicate autostart, lock fencing and idle cold launch in the owned VM.

This test changes only its marked QEMU guest session. It requires an idle main
window, refuses active work, and makes no model or portal input request.
"""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time


def command(args):
    return subprocess.check_output(args, text=True, timeout=20).strip()


def wait(predicate, label, seconds=30):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(.1)
    raise RuntimeError('Timed out waiting for ' + label)


assert os.geteuid() != 0 and os.environ.get('USER') == 'augmentor-proof'
assert Path('/etc/augmentor-test-vm').read_text() == 'Isolated Augmentor Fedora GNOME qualification VM\n'
assert command(['systemd-detect-virt']) == 'qemu'
assert command(['getenforce']) == 'Enforcing'
root = Path('/usr/lib/augmentor')
release = json.loads((root/'release.json').read_text())
assert release['source']['dirty'] is False
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
session = sessions[0]
launcher = Path.home()/'.local/bin/augmentor-agent'


def exchange(action='maintenance.status'):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(3)
        try:
            client.connect(str(Path(os.environ['XDG_RUNTIME_DIR'])/'augmentor-linux-pi.sock'))
        except (FileNotFoundError, ConnectionRefusedError):
            return None
        try:
            client.sendall(action.encode())
            with client.makefile('rb') as stream:
                raw = stream.readline(16384)
                return json.loads(raw) if raw else None
        except (ConnectionResetError, BrokenPipeError):
            return None


def owner(status):
    return int(command(['systemctl', '--user', 'show', 'augmentor-desktop.service',
                        '--value', '-p', 'MainPID'])) == status['pid']


initial = exchange()
assert initial and initial['accepted'] and not initial['busy'] and not initial['running']
assert not initial['draftPresent'] and initial['buildRoot'] == str(root) and owner(initial)
# Repeated production autostart requests must preserve this exact process and
# its maintenance state, not replace it or toggle its visible window.
for _ in range(3):
    subprocess.run([str(launcher), '--autostart'], check=True, timeout=25)
    assert exchange() == initial and owner(initial)

sys.path.insert(0, str(root/'services/desktop'))
from gnome import GnomeObserver
from gi.repository import Gio, GLib
bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
observer = GnomeObserver(bus)
before = observer.read()
assert not before['guards']['locked'] and before['guards']['screenShieldAvailable']
locked_error = None


def unavailable():
    global locked_error
    try:
        observer.read()
    except GLib.Error as error:
        # A timed-out call does not establish GNOME extension suspension.
        if 'UnknownMethod' not in str(error):
            raise
        locked_error = str(error)
        return True
    return False


try:
    subprocess.run(['sudo', 'loginctl', 'lock-session', session], check=True, timeout=15)
    wait(unavailable, 'user-only observer suspension while locked')
finally:
    subprocess.run(['sudo', 'loginctl', 'unlock-session', session], check=True, timeout=15)


def restored():
    try:
        candidate = GnomeObserver(bus)
        scene = candidate.read()
    except GLib.Error:
        return None
    if scene['guards']['locked'] or scene['guards']['screenShieldActive']:
        return None
    return scene


after = wait(restored, 'observer returning after fixture unlock')
assert before['compositorOwner'] == after['compositorOwner'] and before['epoch'] != after['epoch']
try:
    observer.read()
except RuntimeError as error:
    assert 'restarted' in str(error)
else:
    raise AssertionError('Old observer survived its enable epoch change.')
assert exchange() == initial and owner(initial)
# Only the idle, draft-free process accepted above may be closed. Never retry
# an action after an unknown outcome; wait for the known close to finish.
assert exchange('maintenance.close')['accepted'] is True
wait(lambda: exchange() is None, 'accepted idle close')
wait(lambda: command(['systemctl', '--user', 'show', 'augmentor-desktop.service',
                     '--value', '-p', 'ActiveState']) == 'inactive', 'clean service exit')
subprocess.run([str(launcher)], check=True, timeout=30)
reopened = wait(exchange, 'canonical closed-app launch', seconds=60)
assert reopened['pid'] != initial['pid'] and owner(reopened)
assert reopened['buildRoot'] == str(root) and not reopened['running'] and not reopened['draftPresent']
subprocess.run(['rpm', '-V', 'augmentor-agent'], check=True, timeout=30)
report = {'format': 'augmentor-gnome-full-vm-lifecycle/1', 'source': release['source'],
    'version': release['version'], 'proofSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'duplicateAutostartPreservesProcessAndState': True, 'duplicateAutostartCount': 3,
    'lockSuspendsUserObserver': True, 'lockedError': locked_error,
    'sameCompositorOwnerAfterUnlock': True, 'freshEpochAfterUnlock': True,
    'oldObserverRefusedAfterUnlock': True, 'lockPreservesApplicationProcessAndState': True,
    'idleCloseAccepted': True, 'cleanServiceExit': True, 'canonicalClosedLaunch': True,
    'reopenedServiceOwnsNewProcess': True, 'packageVerifiedAfterLifecycle': True,
    'selinuxEnforcing': command(['getenforce']) == 'Enforcing',
    'initial': initial, 'reopened': reopened, 'before': before, 'after': after,
    'positiveLockedSceneTested': False, 'loginAuthenticationTested': False,
    'harnessConnectionTested': False, 'modelTurnTested': False, 'crashRecoveryTested': False,
    'rebootTested': False, 'gnomeInputToolsEnabled': False}
print(json.dumps(report, indent=2))
