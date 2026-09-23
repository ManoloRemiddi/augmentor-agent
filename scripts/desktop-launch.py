#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One installed build for login, menu, shortcuts, secondary windows and recovery."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

SERVICE = 'augmentor-desktop.service'


def configuration():
    data = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))
    return json.loads((data/'augmentor/desktop.json').read_text())


def exchange(command, suffix=''):
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(3)
        try: client.connect(str(runtime/('augmentor-linux-pi'+suffix+'.sock')))
        except (FileNotFoundError, ConnectionRefusedError): return None
        try:
            client.sendall(command.encode())
            with client.makefile('rb') as stream:
                raw = stream.readline(16384)
                return json.loads(raw) if raw else None
        except (ConnectionResetError, BrokenPipeError): return None


def start_service():
    subprocess.run(['systemctl', '--user', 'start', SERVICE], check=True, timeout=20)


def recover():
    start_service()
    deadline = time.monotonic()+60
    while time.monotonic() < deadline:
        status = exchange('maintenance.status')
        # A selected update may be pending while this window finishes its work.
        # Recovery must still operate on that running window.
        if status: break
        time.sleep(.25)
    else: raise RuntimeError('The desktop did not start. Check: journalctl --user -u '+SERVICE)
    status = exchange('maintenance.recover')
    if not status or not status.get('accepted'):
        raise RuntimeError('Recovery was not started. Finish the current action or open dialog, then retry.')
    print('Checking the runtime and reopening the saved conversation…', flush=True)
    deadline = time.monotonic()+120
    while time.monotonic() < deadline:
        status = exchange('maintenance.status')
        if status and not status.get('repairing'):
            if status.get('online') and not status.get('sessionRestoreError'):
                print('Connected. Desktop build: '+status['buildRoot']); return
            raise RuntimeError(status.get('lastError') or status.get('sessionRestoreError') or 'Recovery did not reconnect.')
        time.sleep(.5)
    raise RuntimeError('Recovery is still running. Open Settings → Recover connection for details.')


def main(args):
    if args == ['--autostart']:
        start_service(); return 0
    if args in (['--recover'], ['--recover-window']):
        result = 0
        try: recover()
        except Exception as error: print(str(error), file=sys.stderr); result = 1
        if args == ['--recover-window']: input('Press Enter to close. ')
        return result
    service_run = args == ['--service-run']
    # The primary process always belongs to the user service. Further menu or
    # shortcut invocations use the normal singleton activation protocol.
    if not service_run and '--instance' not in args and not any(a.startswith('--instance=') for a in args):
        if exchange('maintenance.status') is None:
            start_service()
            if not args: return 0
            deadline = time.monotonic()+30
            while exchange('maintenance.status') is None:
                if time.monotonic() >= deadline: raise RuntimeError('Desktop startup timed out.')
                time.sleep(.25)
    config = configuration()
    root = Path(config['root'])
    if not (root/'apps/native/augmentor_linux/window.py').is_file():
        raise RuntimeError('The configured desktop build is missing. Reinstall its deployment; the build will not be silently changed.')
    if service_run:
        # KDE session restore can race login and resurrect an old executable.
        # A busy restored window keeps its work; an idle obsolete build is
        # replaced through its own guarded close protocol. A matching external
        # window is watched until it exits, then the service assumes ownership.
        while existing := exchange('maintenance.status'):
            config = configuration()
            root = Path(config['root'])
            if existing.get('buildRoot') != str(root) and existing.get('accepted'):
                response = exchange('maintenance.close')
                if not response or not response.get('accepted'):
                    raise RuntimeError('The restored desktop could not be closed safely.')
            time.sleep(.5)
        # Selection may have changed while a restored external window was busy.
        config = configuration()
        root = Path(config['root'])
        if not (root/'apps/native/augmentor_linux/window.py').is_file():
            raise RuntimeError('The selected desktop release is missing.')
    env = {**os.environ, 'PYTHONPATH':str(root/'apps/native'), 'AUGMENTOR_PI_NODE':config['node'],
           'PI_TELEMETRY':'0', 'PI_SKIP_VERSION_CHECK':'1'}
    if config.get('dshService'): env['AUGMENTOR_DSH_SERVICE'] = config['dshService']
    if not env.get('QT_QPA_PLATFORM') and env.get('XDG_SESSION_TYPE') == 'wayland' and env.get('DISPLAY'):
        env['QT_QPA_PLATFORM'] = 'xcb'
    os.execve(config['python'], [config['python'], '-m', 'augmentor_linux', *(['--ensure-running'] if service_run else args)], env)


if __name__ == '__main__':
    try: raise SystemExit(main(sys.argv[1:]))
    except Exception as error:
        print('Augmentor startup failed: '+str(error), file=sys.stderr); raise SystemExit(1)
