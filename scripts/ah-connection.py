#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Non-secret installed Harness connection metadata for the Browser bridge."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'apps/native'))
from augmentor_linux.ah_connection import selection, ensure_running

try:
    value = selection()
    if '--start' in sys.argv:
        ensure_running(value)
    value.pop('start', None)
    print(json.dumps(value))
except Exception:
    print('Connect Augmentor Harness by installing/opening its normal launcher, then reconnect. No alternate Pi profile was created.', file=sys.stderr)
    raise SystemExit(1)
