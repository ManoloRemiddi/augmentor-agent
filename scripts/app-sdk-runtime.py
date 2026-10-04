#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Read-only application discovery; no service start, credentials or state writes."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).absolute().parents[1]


def describe(root=ROOT, *, platform=None, environ=None):
    platform = platform or sys.platform
    env = os.environ if environ is None else environ
    root = Path(root).absolute()
    if platform == 'linux':
        data = Path(env.get('XDG_DATA_HOME', Path.home()/'.local/share'))
        selected = json.loads((data/'augmentor/desktop.json').read_text())
        if Path(selected['root']).resolve() != root.resolve():
            raise ValueError('Use the selected managed Augmentor release.')
        return {**selected, 'platform': platform}
    if platform not in ('darwin', 'win32'):
        raise ValueError('Unsupported Augmentor application platform.')
    release = json.loads((root/'release.json').read_text())
    target = 'windows-' if platform == 'win32' else 'macos-'
    if not release.get('target', '').startswith(target):
        raise ValueError('The Augmentor artifact does not match this platform.')
    if platform == 'win32':
        if sys.platform != 'win32':
            raise ValueError('Windows runtime discovery requires Windows identity verification.')
        sys.path.insert(0, str(root/'services'))
        from platform_adapters.windows_identity import local_app_data
        base = local_app_data()/'Augmentor'
    else:
        base = Path.home()/'Library/Application Support/Augmentor'
    node = root/('node/node.exe' if platform == 'win32' else 'node/bin/node')
    python = root/('python/python.exe' if platform == 'win32' else 'python/bin/python3')
    for file in (node, python, root/'apps/browser/native-host.mjs', root/'services/workspaces/sdk.json'):
        if not file.is_file():
            raise ValueError('The installed Augmentor application SDK runtime is incomplete.')
    environment = {key: str(base/child) if platform == 'win32' else env.get(key, str(base/child))
                   for key, child in [('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'), ('XDG_STATE_HOME', 'state')]}
    return {'root': str(root), 'node': str(node), 'python': str(python),
            'version': release['version'], 'platform': platform, 'environment': environment}


if __name__ == '__main__':
    if sys.argv[1:] != ['--describe']:
        raise SystemExit('Usage: app-sdk-runtime.py --describe')
    try:
        print(json.dumps(describe()))
    except Exception:
        raise SystemExit('The installed Augmentor SDK runtime could not be verified; no services were started.')
