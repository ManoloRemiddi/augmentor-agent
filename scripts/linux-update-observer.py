#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fixed retained Linux observer; no development or external-command mode."""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from updates.linux_driver import run

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('attempt','source-root','source-release-sha256','source-payload-sha256'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--bootstrap-fd',required=True,type=int)
    args=parser.parse_args()
    run(ROOT,args.source_root,args.source_release_sha256,args.source_payload_sha256,args.attempt,args.bootstrap_fd)
