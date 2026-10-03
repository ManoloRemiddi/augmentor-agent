#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fixed managed source launcher with only a fresh status identifier."""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from updates.linux_bootstrap import bootstrap

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--attempt',required=True)
    args=parser.parse_args();bootstrap(ROOT,args.attempt)
