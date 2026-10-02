#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Read the installed app and compositor in the owned full Fedora test guest.

Run through the dedicated guest user's SSH session. Prints private fixture
metadata; a successful inspection is not connected-harness or input acceptance.
"""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys


def output(command):
    return subprocess.check_output(command, text=True, timeout=15).strip()


def properties(command):
    return dict(line.split('=', 1) for line in output(command).splitlines() if '=' in line)


if (os.geteuid() == 0 or os.environ.get('USER') != 'augmentor-proof'
        or Path('/etc/augmentor-test-vm').read_text() != 'Isolated Augmentor Fedora GNOME qualification VM\n'
        or output(['systemd-detect-virt']) != 'qemu'):
    raise SystemExit('Run only as the dedicated ordinary user in the owned Fedora GNOME guest.')

root = Path('/usr/lib/augmentor')
release = json.loads((root/'release.json').read_text())
subprocess.run(['rpm', '-V', 'augmentor-agent'], check=True, timeout=30)
environment = properties(['systemctl', '--user', 'show-environment'])
for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'XDG_CURRENT_DESKTOP',
             'XDG_RUNTIME_DIR', 'XDG_SESSION_TYPE', 'DBUS_SESSION_BUS_ADDRESS'):
    if name in environment:
        os.environ[name] = environment[name]
assert environment['XDG_CURRENT_DESKTOP'] == 'GNOME'
assert environment['XDG_SESSION_TYPE'] == 'wayland'
assert output(['getenforce']) == 'Enforcing'
sessions = []
for row in output(['loginctl', 'list-sessions', '--no-legend']).splitlines():
    fields = row.split()
    if len(fields) > 3 and fields[2] == 'augmentor-proof' and fields[3] == 'seat0':
        sessions.append(properties(['loginctl', 'show-session', fields[0], '-p', 'Type',
            '-p', 'Class', '-p', 'State', '-p', 'Active', '-p', 'Seat']))
assert len(sessions) == 1 and sessions[0] == {
    'Type': 'wayland', 'Class': 'user', 'State': 'active', 'Active': 'yes', 'Seat': 'seat0'}
service = properties(['systemctl', '--user', 'show', 'augmentor-desktop.service',
                      '-p', 'ActiveState', '-p', 'SubState', '-p', 'MainPID'])
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
    client.settimeout(5)
    client.connect(str(Path(os.environ['XDG_RUNTIME_DIR'])/'augmentor-linux-pi.sock'))
    client.sendall(b'maintenance.status')
    with client.makefile('rb') as stream:
        desktop = json.loads(stream.readline(16384))
assert service['ActiveState'] == 'active' and service['SubState'] == 'running'
assert int(service['MainPID']) == desktop['pid'] and desktop['buildRoot'] == str(root)
command = Path('/proc')/str(desktop['pid'])/'cmdline'
arguments = command.read_bytes().split(b'\0')
assert b'--ensure-running' in arguments and b'--preview' not in arguments
selection = json.loads((Path.home()/'.local/share/augmentor/desktop.json').read_text())
assert selection['root'] == str(root)
sys.path.insert(0, str(root/'services/desktop'))
from gnome import GnomeObserver
from gi.repository import Gio
scene = GnomeObserver(Gio.bus_get_sync(Gio.BusType.SESSION, None)).read()
assert scene['guards']['screenShieldAvailable'] is True
report = {'format': 'augmentor-gnome-full-vm-inspection/1',
    'source': release['source'], 'version': release['version'],
    'inspectionSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'packageVerified': True, 'selinuxEnforcing': True, 'graphicalSessions': sessions,
    'service': service, 'desktop': desktop, 'scene': scene,
    'canonicalSelection': True, 'serviceOwnsActualApplication': True,
    'previewLaunch': False, 'harnessConnectionTested': False, 'modelTurnTested': False,
    'gnomeInputToolsEnabled': False}
print(json.dumps(report, indent=2))
