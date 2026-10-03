#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Create SDK state with the product's owner-only OS filesystem adapter."""
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))
from platform_adapters.paths import private_directory
from platform_adapters.private_files import descriptor, require_directory


def prepare(action, path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError('An absolute private path is required.')
    if action == 'directory':
        private_directory(path)
        require_directory(path)
    elif action == 'token':
        private_directory(path.parent)
        require_directory(path.parent)
        try:
            fd = descriptor(path, writable=True, exclusive=True)
        except FileExistsError:
            os.close(descriptor(path))  # Validate without replacing an existing token.
            return
        with os.fdopen(fd, 'w', encoding='ascii') as stream:
            stream.write(secrets.token_hex(32)+'\n')
            stream.flush(); os.fsync(stream.fileno())
    else:
        raise ValueError('Unsupported private SDK action.')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('Usage: app-sdk-private.py directory|token /absolute/path')
    try:
        prepare(sys.argv[1], sys.argv[2])
    except Exception:
        raise SystemExit('The SDK private path could not be verified; existing files were preserved.')
