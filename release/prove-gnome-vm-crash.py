#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Kill only an idle, PID-fenced app in the owned guest and verify service restart.

No owner session, active work, draft, connected harness or model turn is touched.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time


assert os.geteuid() != 0 and os.environ.get('USER') == 'augmentor-proof'
assert Path('/etc/augmentor-test-vm').read_text() == 'Isolated Augmentor Fedora GNOME qualification VM\n'
assert subprocess.check_output(['systemd-detect-virt'], text=True).strip() == 'qemu'
assert subprocess.check_output(['getenforce'], text=True).strip() == 'Enforcing'
root = Path('/usr/lib/augmentor')
release = json.loads((root/'release.json').read_text())
assert release['source']['dirty'] is False
subprocess.run(['rpm', '-V', 'augmentor-agent'], check=True, timeout=30)
runtime = Path('/run/user')/str(os.getuid())


def exchange():
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(3)
        try:
            client.connect(str(runtime/'augmentor-linux-pi.sock'))
            client.sendall(b'maintenance.status')
            with client.makefile('rb') as stream:
                raw = stream.readline(16384)
                return json.loads(raw) if raw else None
        except (FileNotFoundError, ConnectionRefusedError, ConnectionResetError, TimeoutError):
            return None


def service():
    rows = subprocess.check_output(['systemctl', '--user', 'show', 'augmentor-desktop.service',
        '-p', 'MainPID', '-p', 'NRestarts', '-p', 'ActiveState', '-p', 'SubState'],
        text=True, timeout=10).splitlines()
    return dict(row.split('=', 1) for row in rows if '=' in row)


initial = exchange()
assert initial and initial['accepted'] and not initial['busy'] and not initial['running']
assert not initial['draftPresent'] and not initial['online'] and initial['buildRoot'] == str(root)
before = service()
assert int(before['MainPID']) == initial['pid'] and before['ActiveState'] == 'active'
# pidfd prevents accidentally killing a recycled process. Recheck the actual
# program and final maintenance state while holding that process reference.
fd = os.pidfd_open(initial['pid'])
try:
    program = Path('/proc')/str(initial['pid'])/'cmdline'
    arguments = program.read_bytes().split(b'\0')
    assert b'augmentor_linux' in arguments and b'--ensure-running' in arguments
    assert exchange() == initial and int(service()['MainPID']) == initial['pid']
    signal.pidfd_send_signal(fd, signal.SIGKILL)
finally:
    os.close(fd)
deadline = time.monotonic() + 90
restarted = None
while time.monotonic() < deadline:
    candidate = exchange()
    if candidate and candidate['pid'] != initial['pid']:
        restarted = candidate
        break
    time.sleep(.2)
assert restarted, 'The user service did not recover its idle application.'
after = service()
assert int(after['MainPID']) == restarted['pid'] and after['ActiveState'] == 'active'
assert after['SubState'] == 'running' and int(after['NRestarts']) == int(before['NRestarts']) + 1
assert restarted['buildRoot'] == str(root) and not restarted['running'] and not restarted['draftPresent']
assert not restarted['online']
subprocess.run(['rpm', '-V', 'augmentor-agent'], check=True, timeout=30)
report = {'format': 'augmentor-gnome-full-vm-idle-crash/1', 'source': release['source'],
    'version': release['version'], 'proofSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'initial': initial, 'restarted': restarted, 'serviceBefore': before, 'serviceAfter': after,
    'idleDraftFreePreflight': True, 'pidfdFencedSingleKill': True,
    'automaticServiceRestart': True, 'serviceRestartCountIncreasedOnce': True,
    'serviceOwnsNewProcess': True, 'sameInstalledRoot': True,
    'packageVerifiedAfterRestart': True, 'selinuxEnforcing': True,
    'connectedHarnessRecoveryTested': False, 'modelTurnTested': False,
    'busyTaskCrashTested': False, 'rebootTested': False, 'gnomeInputToolsEnabled': False}
print(json.dumps(report, indent=2))
