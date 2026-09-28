#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Compile the native private-Python launcher for a staged Windows payload."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def build_launcher(payload, arch, *, name='Augmentor.exe'):
    if sys.platform != 'win32' or arch not in ('x64','arm64') or name not in ('Augmentor.exe','AugmentorFixture.exe'):
        raise ValueError('Use a supported Windows launcher identity and architecture.')
    payload = Path(payload).resolve()
    vswhere = Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)'))/'Microsoft Visual Studio/Installer/vswhere.exe'
    install = subprocess.check_output([str(vswhere), '-latest', '-products', '*', '-property', 'installationPath'], text=True).strip()
    if not install:
        raise RuntimeError('Windows build tools are missing')
    vcvars = Path(install)/'VC/Auxiliary/Build/vcvarsall.bat'
    # Build paths originate in this controlled checkout. Do not accept shell
    # metacharacters: vcvarsall is the vendor's batch environment initializer.
    values = (str(vcvars), str(payload), str(ROOT))
    if any(any(c in value for c in '&|<>^%!\r\n') for value in values):
        raise ValueError('Unsupported shell character in the build path')
    include = payload/'python/include'
    if not (include/'Python.h').is_file():
        raise RuntimeError('Standalone Python must include its matching C headers')
    command = (f'call "{vcvars}" {"amd64_arm64" if arch == "arm64" else "amd64"} && '
        f'cl /nologo /O2 /W4 /MT /I"{include}" "{ROOT / "services/platform/windows-launcher.c"}" '
        f'/Fe:"{payload / name}" /Fo:"{payload / "launcher.obj"}" '
        '/link /SUBSYSTEM:WINDOWS user32.lib shell32.lib')
    # list2cmdline would backslash-escape embedded quotes, which cmd.exe does
    # not understand. This is an explicitly constructed, validated shell line.
    subprocess.run('cmd.exe /d /s /c "'+command+'"', check=True)
    (payload/'launcher.obj').unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--arch', choices=('x64','arm64'), required=True)
    args = parser.parse_args()
    build_launcher(args.root, args.arch)
