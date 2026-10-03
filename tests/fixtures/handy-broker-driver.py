# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Disposable no-model proof: retain startup stderr and RPC timing, never params."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

spawn = subprocess.Popen


def diagnostic_spawn(arguments, *args, **options):
    if isinstance(arguments, (list, tuple)) and arguments and Path(arguments[0]).name == 'handy.exe':
        options['stderr'] = sys.stderr
    return spawn(arguments, *args, **options)


subprocess.Popen = diagnostic_spawn
spec = importlib.util.spec_from_file_location('private_broker', sys.argv[1])
broker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(broker)
call = broker.Backend.call


def measured_call(self, method, params, **options):
    started = time.monotonic()
    outcome = 'completed'
    try:
        return call(self, method, params, **options)
    except Exception as error:
        outcome = type(error).__name__
        raise
    finally:
        print(json.dumps({'operation': method, 'seconds': round(time.monotonic()-started, 3),
                          'outcome': outcome}), file=sys.stderr, flush=True)


broker.Backend.call = measured_call
broker.main()
