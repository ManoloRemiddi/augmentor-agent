#!/usr/bin/python3 -I
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Keep the independently installed ALPM guard through app removal/recovery."""
import os
from pathlib import Path
import subprocess


def main():
    if os.geteuid()!=0:raise RuntimeError('Only the package manager may remove this guard.')
    pending=Path('/var/lib/augmentor-package-maintenance/pending.json')
    if pending.exists() or pending.is_symlink():
        raise RuntimeError('Complete verified Augmentor package recovery before removing its guard.')
    result=subprocess.run(['pacman','-Q','augmentor-agent'],capture_output=True,text=True,
                          timeout=15,env={**os.environ,'LC_ALL':'C'})
    if result.returncode==0:
        raise RuntimeError('Remove Augmentor in its own completed transaction before removing the guard.')
    if result.returncode!=1 or "package 'augmentor-agent' was not found" not in result.stdout+result.stderr:
        raise RuntimeError('Cannot establish that Augmentor is absent; the guard remains installed.')


if __name__=='__main__':
    try:main()
    except (OSError,RuntimeError) as error:raise SystemExit(str(error)) from None
