#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Launch bundled components with the same runtime and per-user environment."""
import os
from pathlib import Path
import runpy
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]


def configure():
    sys.dont_write_bytecode = True
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    python = ROOT/'python/bin/python3'
    node = ROOT/'node/bin/node'
    os.environ.setdefault('AUGMENTOR_PYTHON', str(python) if python.exists() else sys.executable)
    if node.exists():os.environ.setdefault('AUGMENTOR_PI_NODE', str(node))
    bins = [str(Path(os.environ['AUGMENTOR_PYTHON']).parent)]
    if node.exists():bins.insert(0, str(node.parent))
    dsh = ROOT/'dsh/node_modules/.bin'
    if (dsh/'dsh').exists():bins.append(str(dsh))
    os.environ['PATH'] = os.pathsep.join([*bins, os.environ.get('PATH', os.defpath)])
    os.environ.setdefault('PI_TELEMETRY', '0')
    os.environ.setdefault('PI_SKIP_VERSION_CHECK', '1')
    if sys.platform == 'darwin':
        base = Path.home()/'Library/Application Support/Augmentor'
        for key, child in [('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_STATE_HOME','state')]:
            os.environ.setdefault(key, str(base/child))
        # macOS Unix socket paths are short. Keep sockets separate from durable
        # Application Support records; reject an occupied foreign/symlink path.
        runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/tmp/augmentor-{os.getuid()}'))
        runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = runtime.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise RuntimeError('Augmentor needs a private runtime directory owned by this user.')
        os.environ['XDG_RUNTIME_DIR'] = str(runtime)
        os.environ.setdefault('AUGMENTOR_PI_SOCKET', str(runtime/'pi.sock'))
        os.environ.setdefault('AUGMENTOR_SHARED_STATE', str(runtime/'shared'))


def main():
    if len(sys.argv)<2 or sys.argv[1] not in ('desktop','browser','runtime','shortcut-service'):
        raise SystemExit('Usage: launch-component.py desktop|browser|runtime|shortcut-service [arguments]')
    component = sys.argv[1]
    configure()
    sys.path.insert(0, str(ROOT/'services/lifecycle'))
    from lease import hold
    hold('desktop' if component in ('desktop','shortcut-service') else 'runtime')
    if component in ('desktop','shortcut-service'):
        sys.path.insert(0, str(ROOT/'apps/native'))
        sys.argv = ['augmentor-desktop', *sys.argv[2:]]
        runpy.run_module('augmentor_linux' if component=='desktop' else
                        'augmentor_linux.macos_shortcut_service', run_name='__main__')
    else:
        import shutil
        node = os.environ.get('AUGMENTOR_PI_NODE') or shutil.which('node')
        if not node:raise RuntimeError('The bundled Node runtime is missing.')
        script = ROOT/('apps/browser/native-host.mjs' if component=='browser' else 'dist/runtime/src/main.js')
        os.execv(node, [node, str(script), *sys.argv[2:]])


if __name__=='__main__':main()
