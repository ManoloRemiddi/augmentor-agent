# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""OS publisher trust in addition to fresh signed metadata and pinned bytes.

Public key pins come from the original inspected source payload, never a selected
catalog, environment, downloaded installer or display name. Missing/disabled
configuration defers automatic installation. Inspection never executes a target.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from lifecycle.payload_integrity import _read, _json


def policy(root):
    value = _json(_read(Path(root)/'release/windows/signing.json', 65536), 65536)
    if (not isinstance(value, dict) or set(value) != {'schema', 'enabled', 'publicKeySHA256'}
            or value['schema'] != 'augmentor-windows-signing/1'
            or type(value['enabled']) is not bool
            or not isinstance(value['publicKeySHA256'], list)
            or len(value['publicKeySHA256']) > 3
            or any(not isinstance(key, str) or not re.fullmatch('[a-f0-9]{64}', key)
                   for key in value['publicKeySHA256'])
            or len(set(value['publicKeySHA256'])) != len(value['publicKeySHA256'])):
        raise ValueError('The installed publisher signing policy is invalid.')
    if not value['enabled'] or not value['publicKeySHA256']:
        raise ValueError('This source has not provisioned Windows publisher signing for automatic installation.')
    return value


def inspect(root, target):
    """Read-only platform report; an unpinned report cannot authorize installation."""
    if sys.platform != 'win32':
        raise RuntimeError('Publisher inspection requires the native Windows trust provider.')
    root, target = Path(root), Path(target)
    executable = root/'powershell/pwsh.exe'
    script = root/'scripts/verify-windows-publisher.ps1'
    if not executable.is_file() or not script.is_file():
        raise ValueError('The inspected source lacks its fixed publisher verifier.')
    environment = {key:value for key,value in os.environ.items()
                   if not key.upper().startswith(('PS', 'POWERSHELL', 'NODE_', 'PYTHON'))}
    # Restore only the verified bundled module path; user module directories
    # must not resolve the module-qualified inspection command.
    environment['PSModulePath'] = str(executable.parent/'Modules')
    result = subprocess.run([str(executable), '-NoLogo', '-NoProfile', '-NonInteractive',
        '-File', str(script), '-LiteralPath', str(target)], env=environment,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    if result.returncode or len(result.stdout) > 4096:
        raise ValueError('Windows could not verify the installer publisher signature.')
    value = _json(result.stdout, 4096)
    if (not isinstance(value, dict) or set(value) != {'schema','trusted','timestamped','publicKeySHA256'}
            or value['schema'] != 'augmentor-windows-publisher/1'
            or value['trusted'] is not True or value['timestamped'] is not True
            or not isinstance(value['publicKeySHA256'], str)
            or not re.fullmatch('[a-f0-9]{64}', value['publicKeySHA256'])):
        raise ValueError('Windows did not report a valid timestamped installer publisher.')
    return value


def verify(root, target):
    original = policy(root)
    result = inspect(root, target)
    if policy(root) != original:
        raise ValueError('The source publisher policy changed during verification.')
    if result['publicKeySHA256'] not in original['publicKeySHA256']:
        raise ValueError('The installer signature belongs to another publisher key.')
    return True
