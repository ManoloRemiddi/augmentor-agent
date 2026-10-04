#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fresh integration163 only: consume the exact verified staged013 from failed161.

No native transaction, staging, installer replay or SDK mutation is dispatched.
This source candidate needs a separately reviewed fresh immutable root binding.
The original failed161 worker, journals and conservative host failure persist.
"""
import hashlib
import importlib.util
from pathlib import Path
import stat
import sys

COORDINATOR_SHA = '2c2e66353766e11bec58217832636e2699afd1012a694c4bf3bb89114354ab7a'


def prove():
    sys.dont_write_bytecode = True
    source = Path(__file__).parent/'prove-published-linux-coordinated-version.py'
    for path in (Path(__file__), source):
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o022:
            raise ValueError('The fresh reviewed163 sources must be immutable root-owned files.')
        for parent in path.parents:
            info = parent.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
                raise ValueError('The fresh163 source traverses a mutable ancestor.')
    if hashlib.sha256(source.read_bytes()).hexdigest() != COORDINATOR_SHA:
        raise ValueError('The reviewed finite orchestration source differs.')
    spec = importlib.util.spec_from_file_location('staged_coordinator', source)
    coordinator = importlib.util.module_from_spec(spec); spec.loader.exec_module(coordinator)
    coordinator.prove('upgrade', integration_after_stage=True, proof_path=Path(__file__))


if __name__ == '__main__':
    prove()
