#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Compare early/late Qt portal identity in the marked full Fedora test guest.

Uses standalone fixture windows, never patches the installed product. Private
logs contain only fixture Qt output and filtered portal identity/settings calls.
This does not qualify the separate desktop-control process's consent identity.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

assert os.geteuid() != 0 and os.environ.get('USER') == 'augmentor-proof'
assert Path('/etc/augmentor-test-vm').read_text() == 'Isolated Augmentor Fedora GNOME qualification VM\n'
assert subprocess.check_output(['systemd-detect-virt'], text=True).strip() == 'qemu'
environment = dict(row.split('=', 1) for row in subprocess.check_output(
    ['systemctl', '--user', 'show-environment'], text=True).splitlines() if '=' in row)
for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'XDG_CURRENT_DESKTOP',
            'XDG_RUNTIME_DIR', 'XDG_SESSION_TYPE', 'DBUS_SESSION_BUS_ADDRESS'):
    if key in environment:
        os.environ[key] = environment[key]
assert environment['XDG_SESSION_TYPE'] == 'wayland' and environment['XDG_CURRENT_DESKTOP'] == 'GNOME'
program = '''import sys
from PySide6.QtCore import QTimer,qVersion
from PySide6.QtWidgets import QApplication,QLabel
from PySide6.QtDBus import QDBusConnection
assert qVersion()=='6.11.2'
early=sys.argv[1]=='early'
if early:
 QApplication.setDesktopFileName('com.augmentor.Agent')
app=QApplication(['augmentor-portal-identity-fixture'])
app.setApplicationName('Augmentor Agent')
if not early:
 app.setDesktopFileName('com.augmentor.Agent')
print('QT_DBUS_SENDER='+QDBusConnection.sessionBus().baseService(),flush=True)
window=QLabel('Owned Qt portal identity fixture: '+sys.argv[1]);window.resize(350,100);window.show()
QTimer.singleShot(5000,app.quit)
app.exec()
'''
out = Path.home()/'qt-portal-identity-proof'
out.mkdir(mode=0o700, exist_ok=True)
results = []
for platform in ('xcb', 'wayland'):
    for order in ('late', 'early'):
        prefix = platform+'-'+order
        with (out/(prefix+'-bus.log')).open('w') as buslog:
            monitor = subprocess.Popen(['dbus-monitor', '--session',
                "type='method_call',interface='org.freedesktop.host.portal.Registry'",
                "type='method_call',interface='org.freedesktop.portal.Settings'",
                "type='method_return',sender='org.freedesktop.portal.Desktop'",
                "type='error',sender='org.freedesktop.portal.Desktop'"],
                stdout=buslog, stderr=subprocess.PIPE, text=True)
            try:
                time.sleep(.5)
                assert monitor.poll() is None, 'Fixture bus monitor failed to start.'
                result = subprocess.run(['/usr/bin/python3', '-c', program, order],
                    env={**os.environ, 'QT_QPA_PLATFORM': platform,
                         'QT_LOGGING_RULES': 'qt.qpa.services=true'},
                    text=True, capture_output=True, timeout=40)
                assert result.returncode == 0, result.stderr
            finally:
                monitor.terminate()
                monitor.wait(timeout=10)
        text = result.stdout+result.stderr
        (out/(prefix+'-qt.log')).write_text(text)
        raw_trace = (out/(prefix+'-bus.log')).read_text()
        sender = re.search(r'^QT_DBUS_SENDER=(:\d+\.\d+)$', result.stdout, re.M)
        assert sender, 'Fixture Qt sender was not identified.'
        trace = '\n'.join(block for block in re.split(r'(?=^method call )', raw_trace, flags=re.M)
                          if 'sender='+sender.group(1)+' ->' in block)
        register = trace.find('interface=org.freedesktop.host.portal.Registry; member=Register')
        settings = trace.find('interface=org.freedesktop.portal.Settings;')
        headers = re.findall(r'^method call [^\n]+', trace, re.M)
        registration_serials = [re.search(r' serial=(\d+) ', header).group(1)
            for header in headers if 'interface=org.freedesktop.host.portal.Registry; member=Register' in header]
        replies = re.findall(r'^(?:method return|error) [^\n]+', raw_trace, re.M)
        successful = sum(any(header.startswith('method return ') and
            'destination='+sender.group(1)+' ' in header and
            re.search(r' reply_serial='+serial+r'(?:\s|$)', header)
            for header in replies) for serial in registration_serials)
        failed = sum(any(header.startswith('error ') and
            'destination='+sender.group(1)+' ' in header and
            re.search(r' reply_serial='+serial+r'(?:\s|$)', header)
            for header in replies) for serial in registration_serials)
        cached_identity_errors = sum(block.startswith('error ') and
            'destination='+sender.group(1)+' ' in block.splitlines()[0] and
            any(re.search(r' reply_serial='+serial+r'(?:\s|$)', block.splitlines()[0])
                for serial in registration_serials) and
            'Connection already associated with an application ID' in block
            for block in re.split(r'(?=^(?:method call|method return|error|signal) )', raw_trace, flags=re.M))
        results.append({'platform': platform, 'order': order,
            'lateRegistrationWarningCount': text.count('Connection already associated with an application ID'),
            'portalRegistrationFailureCount': text.count('Failed to register with host portal'),
            'registerCallObserved': register >= 0,
            'registerSuccessfulReplies': successful,
            'registerErrorReplies': failed,
            'registerCachedIdentityErrors': cached_identity_errors,
            'registerBeforeFirstSettingsCall': register >= 0 and (settings < 0 or register < settings),
            'qtLogSha256': hashlib.sha256(text.encode()).hexdigest(),
            'busLogSha256': hashlib.sha256(raw_trace.encode()).hexdigest(),
            'qtSenderCallsSha256': hashlib.sha256(trace.encode()).hexdigest()})
        if order == 'early':
            assert register >= 0 and successful > 0 and failed == 0 and (settings < 0 or register < settings)
        else:
            assert successful == 0 and cached_identity_errors > 0
report = {'format': 'augmentor-gnome-qt-portal-identity/1',
    'proofSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'qtVersion': '6.11.2', 'results': results,
    'actualAugmentorLaunchTested': False, 'controlHelperConsentIdentityTested': False,
    'portalRestartReregistrationTested': False, 'modelTurnTested': False}
(out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
