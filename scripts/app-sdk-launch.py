#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Launch SDK components through the product environment and lifetime lease."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = {'native': 'apps/browser/native-host.mjs',
              'register': 'scripts/install-workspace-profile.mjs',
              'embed': 'apps/browser/embed/server.mjs'}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMPONENTS:
        raise SystemExit('Usage: app-sdk-launch.py native|register|embed [arguments]')
    spec = importlib.util.spec_from_file_location('augmentor_component_launch', ROOT/'scripts/launch-component.py')
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    launcher.configure()
    sys.path.insert(0, str(ROOT/'services/lifecycle'))
    from lease import hold
    if sys.platform=='win32':
        sys.path.insert(0,str(ROOT/'services'))
        from lifecycle.windows_startup import Startup
        from lifecycle.sdk_launch_lease import retain
        from platform_adapters.paths import runtime_directory
        # Reader covers lease registration. A maintenance writer cannot miss
        # a new SDK server between discovery and desktop shutdown.
        with Startup():
            hold('runtime')
            retain(runtime_directory(),ROOT,sys.argv[1])
    else:hold('runtime')
    node = os.environ.get('AUGMENTOR_PI_NODE')
    if not node:
        raise SystemExit('The selected managed Node runtime is required.')
    command = [node, str(ROOT/COMPONENTS[sys.argv[1]]), *sys.argv[2:]]
    if sys.platform == 'win32':
        # Keep the Python supervisor alive: Windows leases cannot survive exec.
        sys.path.insert(0, str(ROOT/'services'))
        from platform_adapters.processes import OwnedProcess
        child = OwnedProcess(command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
        raise SystemExit(child.wait_graceful())
    os.execv(node, command)


if __name__ == '__main__':
    main()
