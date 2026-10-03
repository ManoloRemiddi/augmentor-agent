#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fixed forward-update worker launched by the independent verified observer.

There is no arbitrary installer, command, target or recovery PID argument. All
apply inputs come from live user consent and fresh installed-root TUF verification.
The app's launch integration and target-health completion must qualify before the
automatic-install flag can be enabled; this entrypoint alone does not qualify it.
"""
import argparse
import hashlib
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observer-endpoint',type=Path,required=True)
    parser.add_argument('--observer-parent',type=int,required=True)
    parser.add_argument('--observer-nonce',required=True)
    parser.add_argument('--source-release-sha256',required=True)
    parser.add_argument('--source-inventory-sha256',required=True)
    args=parser.parse_args()
    if sys.platform!='win32':parser.error('Requires the native Windows kernel.')
    from lifecycle.observer_runtime import verify_observer_runtime
    from lifecycle.payload_integrity import _read,MAX_INVENTORY
    from lifecycle.windows_update_observer import CoordinatorObserver
    from platform_adapters.paths import windows_environment,private_directory
    from platform_adapters.private_files import require_directory
    from platform_adapters.windows_identity import local_app_data
    from updates.windows_coordinator import coordinate
    environment=windows_environment();os.environ.update(environment)
    base=local_app_data()/'Augmentor'
    root=local_app_data()/'Programs/Augmentor Agent/current'
    if ROOT==root or ROOT.is_relative_to(root) or root.is_relative_to(ROOT):
        raise ValueError('The independent coordinator must execute outside the replaceable installation.')
    release=_read(root/'release.json',65536);inventory=_read(root/'payload-integrity.json',MAX_INVENTORY)
    for expected,raw in ((args.source_release_sha256,release),(args.source_inventory_sha256,inventory)):
        if not re.fullmatch('[a-f0-9]{64}',expected) or hashlib.sha256(raw).hexdigest()!=expected:
            raise ValueError('The source changed after independent observer launch.')
    verify_observer_runtime(ROOT,release,inventory)
    shared=Path(environment['AUGMENTOR_SHARED_STATE'])
    data=Path(os.environ.get('AUGMENTOR_SHARED_DATA',Path(environment['XDG_DATA_HOME'])/'augmentor'))
    # Shared update settings/cache are distinct from the native install journal.
    updates=require_directory(data/'updates')
    private_directory(base/'updates')
    with CoordinatorObserver(args.observer_endpoint,args.observer_parent,args.observer_nonce) as peer:
        coordinate(root,base,updates,shared,Path(environment['XDG_DATA_HOME'])/'augmentor/managed-dsh',peer,release,inventory)
    # The native installer waits for this real process exit before placement.


if __name__=='__main__':main()
