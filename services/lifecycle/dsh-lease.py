#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Hold installed runtime files for the lifetime of DSH's product integration."""
import sys
from pathlib import Path
from lease import hold
if sys.platform in ('linux','darwin') and (Path(__file__).resolve().parents[2]/'release.json').is_file():
    from posix_startup import Startup
    with Startup() as startup:
        hold('runtime')
        print('READY',flush=True)
        if sys.stdin.buffer.readline()!=b'READY\n':raise SystemExit(0)
        startup.ready()
        sys.stdin.buffer.read()
else:
    hold('runtime')
    print('READY',flush=True)
    sys.stdin.buffer.read()
