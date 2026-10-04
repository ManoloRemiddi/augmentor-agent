#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Render the sealed public payload on a disposable native build runner."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--development', action='store_true', help='Inspect an unpublished CI candidate; never grant installation authority')
    args = parser.parse_args()
    from platform_adapters.windows_identity import local_app_data, private_directory
    from lifecycle.payload_integrity import verify_payload
    from lifecycle.windows_health import verify_local_health
    payload = args.root.resolve()
    metadata = (payload/'release.json').read_bytes()
    release = json.loads(metadata)
    profile = json.loads((ROOT/'release/windows/public-preview.json').read_text())
    if args.development:
        profile = {'qualificationStatus':'development-candidate','customerDistribution':False}
    if any(release.get(key) != value for key, value in profile.items()):
        raise ValueError('Use the explicit public preview payload.')
    base = private_directory(local_app_data()/'Augmentor')
    private_directory(base/'run')
    verify_payload(payload, metadata)
    report = verify_local_health(payload, metadata, timeout=60)
    verify_payload(payload, metadata)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
