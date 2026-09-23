#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Take a package lifetime lease, then replace this process with the component."""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/lifecycle'))
from lease import hold

if len(sys.argv) < 3 or sys.argv[1] not in ('runtime', 'desktop'):
    raise SystemExit('Usage: run-component.py runtime|desktop COMMAND [ARG...]')
try:
    hold(sys.argv[1])
except RuntimeError as error:
    raise SystemExit(str(error))
os.execvp(sys.argv[2], sys.argv[2:])
