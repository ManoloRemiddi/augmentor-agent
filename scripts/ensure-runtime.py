#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'apps/native'))
from augmentor_linux.runtime_start import ensure_running
if '--harness' in sys.argv:
    harness=sys.argv[sys.argv.index('--harness')+1]
else:
    from augmentor_linux.preferences import Preferences
    harness=Preferences().values['harness']
if harness in ('pi','codex'):ensure_running(harness)
elif harness=='ah':
    from augmentor_linux.ah_connection import selection,ensure_running as ensure_harness
    ensure_harness(selection())
elif harness!='dsh':raise SystemExit('Choose Augmentor Harness, DSH, Pi or Codex.')
