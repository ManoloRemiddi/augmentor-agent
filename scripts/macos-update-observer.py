#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fixed retained observer; no development mode or external commands."""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from updates.macos_driver import run

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('attempt','source-bundle','source-release-sha256','source-payload-sha256'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--bootstrap-fd',required=True,type=int)
    args=parser.parse_args()
    run(ROOT.parents[2],args.source_bundle,args.source_release_sha256,args.source_payload_sha256,args.attempt,args.bootstrap_fd)
