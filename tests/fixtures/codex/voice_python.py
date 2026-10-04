# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Run the unmodified Browser voice worker with synthetic device callbacks."""
import fake_audio  # noqa: F401
import runpy
import sys
args = sys.argv[1:]
if args and args[0] == '-u': args.pop(0)
sys.argv = args
runpy.run_path(args[0], run_name='__main__')
