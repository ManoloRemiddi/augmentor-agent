# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Open a URL in the user's installed browser, using the native app's session."""
import os
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlsplit


DESKTOP_KEYS = ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'XDG_RUNTIME_DIR',
                'DBUS_SESSION_BUS_ADDRESS', 'XDG_CURRENT_DESKTOP', 'XDG_SESSION_TYPE',
                'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_DATA_DIRS')


def desktop_environment():
    # DSH can run as a user service without the graphical session environment.
    # Resolve only our live singleton's PID; never harvest unrelated processes.
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
    lock = runtime / 'augmentor-linux-pi.lock'
    try:
        if lock.stat().st_uid != os.getuid():
            raise ValueError('The native app lock has another owner')
        pid = int(lock.read_text().splitlines()[0])
        process = Path('/proc') / str(pid)
        args = (process / 'cmdline').read_bytes().split(b'\0')
        if process.stat().st_uid != os.getuid() or not any(
                args[i:i+2] == [b'-m', b'augmentor_linux'] for i in range(len(args)-1)):
            raise ValueError('The native app lock is stale')
        values = dict(part.split('=', 1) for part in
                      (process / 'environ').read_text().split('\0') if '=' in part)
        env = {key: values[key] for key in DESKTOP_KEYS if values.get(key)}
    except (OSError, ValueError, IndexError) as exc:
        raise RuntimeError('Open the Augmentor Agent Desktop app to connect to the desktop session.') from exc
    if not (env.get('DISPLAY') or env.get('WAYLAND_DISPLAY')):
        raise RuntimeError('The native app has no graphical display connection.')
    env.update({key: os.environ[key] for key in ('HOME', 'PATH', 'LANG', 'LC_ALL') if key in os.environ})
    return env


def open_url(url, browser='chromium'):
    if browser != 'chromium':
        raise ValueError('This native browser adapter currently supports Chromium only.')
    if not isinstance(url, str) or len(url) > 8192 or any(ord(c) < 32 for c in url):
        raise ValueError('A valid HTTP(S) URL is required.')
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Use an HTTP(S) URL without embedded credentials.')
    executable = shutil.which('chromium') or shutil.which('chromium-browser')
    if not executable:
        raise RuntimeError('Chromium is not installed. No other browser was substituted.')
    env = desktop_environment()
    # Chromium's singleton forwards this request to its existing user profile.
    # Never create an automation profile or a remote-debugging/headless browser.
    child = subprocess.Popen([executable, '--new-tab', url], env=env,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        code = child.wait(timeout=1)
    except subprocess.TimeoutExpired:
        code = None  # A newly started browser remains running.
    if code not in (None, 0):
        return {'ok': False, 'dispatched': False, 'verified': False,
                'error': f'Chromium could not accept the request (exit {code}).'}
    return {'ok': True, 'dispatched': True, 'verified': False, 'browser': 'chromium',
            'requestedUrl': url, 'newTabRequested': True,
            'verification': 'Check browser_tabs_list for the matching active URL/title, or linux_desktop_observe for visible Chromium state. A launch alone does not verify page loading.'}
