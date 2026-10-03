#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fixed external Windows update parent; no caller-supplied installer or command."""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-release-sha256',required=True)
    parser.add_argument('--source-inventory-sha256',required=True)
    parser.add_argument('--observer-endpoint',type=Path,required=True)
    parser.add_argument('--observer-parent',type=int,required=True)
    parser.add_argument('--observer-nonce',required=True)
    args=parser.parse_args()
    if sys.platform!='win32':parser.error('Requires the native Windows kernel.')
    from updates.windows_driver import run
    from lifecycle.windows_update_observer import CoordinatorObserver
    with CoordinatorObserver(args.observer_endpoint,args.observer_parent,args.observer_nonce,
                             allow_transfer=False) as bootstrap:
        run(ROOT,args.source_release_sha256,args.source_inventory_sha256,bootstrap=bootstrap)


if __name__=='__main__':main()
