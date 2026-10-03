#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Source-side updater launcher with no caller-supplied installation inputs."""
from pathlib import Path
import argparse
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))


def main():
    from updates.attempt import attempt_id
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt',type=attempt_id,required=True)
    args=parser.parse_args()
    from updates.windows_bootstrap import bootstrap
    bootstrap(ROOT,args.attempt)


if __name__=='__main__':main()
