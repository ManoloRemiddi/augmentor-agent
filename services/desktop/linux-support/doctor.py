#!/usr/bin/env python3
# Augmentor Desktop — Linux compatibility discovery
# Copyright © 2026 Manolo Remiddi
# SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# License: MIT with Augmentor Resale Restriction — see LICENSE.

"""Read-only discovery. No screenshots, app contents, input, or network calls."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


def read_release(root=Path('/etc')):
    values = {}
    for name in ('os-release', 'lsb-release'):
        try:
            for line in (root / name).read_text().splitlines():
                key, sep, value = line.partition('=')
                if sep:
                    values[key] = value.strip('"\'')
        except OSError:
            pass
    try:
        mx = (root / 'mx-version').read_text().strip()
    except OSError:
        mx = None
    return {
        'name': values.get('DISTRIB_DESCRIPTION', values.get('PRETTY_NAME', 'unknown')),
        'base_id': values.get('ID', 'unknown'),
        'mx_release': mx,
    }


def parse_portals(text):
    interfaces = {}
    for name, body in re.findall(r'interface (org\.freedesktop\.portal\.\w+)\s*\{(.*?)\n\s*\};', text, re.S):
        properties = {}
        for prop in ('version', 'AvailableDeviceTypes', 'AvailableSourceTypes', 'SupportedCapabilities'):
            match = re.search(r'\b' + prop + r'\s*=\s*(\d+)', body)
            if match:
                properties[prop] = int(match.group(1))
        interfaces[name.rsplit('.', 1)[-1]] = properties
    return interfaces


def inspect_portals():
    if not shutil.which('gdbus'):
        return {'status': 'unavailable', 'reason': 'gdbus is not installed'}
    try:
        result = subprocess.run([
            'gdbus', 'introspect', '--session', '--dest', 'org.freedesktop.portal.Desktop',
            '--object-path', '/org/freedesktop/portal/desktop', '--only-properties',
        ], capture_output=True, text=True, timeout=10, check=False)
    except subprocess.TimeoutExpired:
        return {'status': 'unknown', 'reason': 'Desktop portal query timed out'}
    except OSError:
        return {'status': 'unknown', 'reason': 'Could not run desktop portal query'}
    if result.returncode:
        # Avoid returning arbitrary subprocess output, paths or bus addresses.
        return {'status': 'unknown', 'reason': 'Session bus inaccessible or portal query failed'}
    interfaces = parse_portals(result.stdout)
    return {'status': 'observed', 'interfaces': interfaces}


def recommendation(session, portal):
    if session == 'wayland':
        if portal['status'] != 'observed':
            return 'Wayland: portal support is unverified. Run this checker in the logged-in desktop session.'
        interfaces = portal['interfaces']
        devices = interfaces.get('RemoteDesktop', {}).get('AvailableDeviceTypes', 0)
        if devices & 3 == 3 and 'ScreenCast' in interfaces:
            return 'Wayland portal candidate: keyboard, pointer and screencast advertised. Live consent, capture and input tests still required.'
        return 'Wayland portal capabilities are incomplete for full desktop control; inspect the installed portal backend.'
    if session == 'x11':
        return 'X11 backend candidate. Validate accessibility, capture and XTest in an isolated test desktop.'
    return 'Unknown session type. No desktop-control backend selected.'


def report(probe=False, environment=None):
    environment = os.environ if environment is None else environment
    session = environment.get('XDG_SESSION_TYPE', 'unknown').lower()
    portal = inspect_portals() if probe else {'status': 'not_probed'}
    return {
        'schema_version': 1,
        'os': read_release(),
        'desktop': environment.get('XDG_CURRENT_DESKTOP', 'unknown'),
        'session_type': session,
        'python_gi_installed': importlib.util.find_spec('gi') is not None,
        'commands': {name: shutil.which(name) is not None for name in ('gdbus', 'xdotool', 'wmctrl', 'Xvfb')},
        'portals': portal,
        'assessment': recommendation(session, portal),
        'limitations': [
            'Package/interface presence is not a functional control test.',
            'Python GI presence does not establish AT-SPI accessibility coverage.',
            'X11 tools do not establish native Wayland control, even when DISPLAY exists.',
        ],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe-portals', action='store_true', help='Read interface properties via the local session bus; may activate the portal service.')
    args = parser.parse_args()
    print(json.dumps(report(args.probe_portals), indent=2))
