# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Apply the reviewed, version/hash-gated local DSH 0.2 history compatibility patch."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

UPSTREAM = '382a3f28b95e0b9504969ac6f407f909aef0ba4699c3175d36c0ef91b31cfde2'
PATCHED = 'a2d392dcc2a7701975419905e3c72e315fb24d84d9c488c5e039eb43540ee643'

def apply(package):
    package = package.resolve()
    metadata = json.loads((package / 'package.json').read_text())
    if metadata['name'] != '@deepseek-ai/dsh-session-format-v3-to-v4' or metadata['version'] != '0.2.0-rc.2':
        raise ValueError('Refusing an unqualified DSH package/version')
    target = package / 'lib/index.js'
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    if digest == PATCHED:
        print('DSH 0.2 history compatibility patch already verified')
        return
    if digest != UPSTREAM:
        raise ValueError('Refusing an unknown or modified upstream file')
    patch = Path(__file__).resolve().parents[1] / 'release/dsh/patches/dsh-session-format-v3-to-v4-0.2.0-rc.2.patch'
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'lib').mkdir()
        output = root / 'lib/index.js'
        output.write_bytes(target.read_bytes())
        subprocess.run(['patch', '--batch', '-p1', '-i', str(patch)], cwd=root, check=True, capture_output=True)
        if hashlib.sha256(output.read_bytes()).hexdigest() != PATCHED:
            raise ValueError('Patched output does not match the reviewed artifact')
        # New inode: never mutate a shared pnpm-store hardlink.
        temporary = target.with_suffix('.augmentor-compat.tmp')
        temporary.write_bytes(output.read_bytes())
        temporary.chmod(target.stat().st_mode)
        temporary.replace(target)
    print('Verified local DSH 0.2 history compatibility patch applied')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path, help='Installed dsh-session-format-v3-to-v4 package directory')
    apply(parser.parse_args().package)
