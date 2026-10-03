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
    parser.add_argument('--attempt',required=True)
    args=parser.parse_args()
    if sys.platform!='win32':parser.error('Requires the native Windows kernel.')
    from updates.windows_driver import run
    from lifecycle.observer_retention import retain
    from updates.attempt import attempt_id,write_result
    from lifecycle.windows_update_observer import CoordinatorObserver
    attempt_id(args.attempt)
    retain(ROOT)
    try:
        bootstrap=CoordinatorObserver(args.observer_endpoint,args.observer_parent,args.observer_nonce,allow_transfer=False)
    except Exception as error:
        from platform_adapters.paths import private_directory
        from platform_adapters.windows_identity import local_app_data
        directory=private_directory(local_app_data()/'Augmentor/updates')
        # The source bootstrap never released this parent; coordination was
        # not entered. Existing pending work still blocks through fresh guards.
        write_result(directory,args.attempt,'deferred',error=error)
        raise
    with bootstrap:
        run(ROOT,args.source_release_sha256,args.source_inventory_sha256,bootstrap=bootstrap,attempt=args.attempt)


if __name__=='__main__':main()
