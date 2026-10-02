# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Explicit build-tool launchers; never run npm's Windows shim through a shell."""
from pathlib import Path
import shutil
import sys


def npm_command():
    if sys.platform != 'win32':
        return ['npm']
    node = shutil.which('node')
    if not node:
        raise RuntimeError('A build-time Node installation is required.')
    cli = Path(node).parent/'node_modules/npm/bin/npm-cli.js'
    if not cli.is_file():
        raise RuntimeError('The build-time Node installation must include npm.')
    return [node, str(cli)]
