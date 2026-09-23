#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Hold installed runtime files for the lifetime of DSH's product integration."""
import sys
from lease import hold
hold('runtime')
print('READY',flush=True)
sys.stdin.buffer.read()
