#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Inventory installed Python notices; file presence is not a compliance finding."""
import argparse
import hashlib
from importlib.metadata import distributions
import json
from pathlib import Path


def inventory():
    rows=[]
    for distribution in sorted(distributions(),key=lambda d:d.metadata.get('Name','')):
        notices=[]
        for file in distribution.files or []:
            if not any(word in Path(str(file)).name.lower() for word in ('license','copying','notice')):continue
            path=Path(distribution.locate_file(file))
            if path.is_file():
                notices.append({'path':str(file),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        rows.append({'name':distribution.metadata.get('Name'),'version':distribution.version,'notices':notices})
    return {'scope':'Python distribution metadata; excludes embedded native-library source obligations',
            'packages':rows,'missingRecordedNotices':[row['name'] for row in rows if not row['notices']],
            'licenseReviewComplete':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(inventory(),indent=2)+'\n')
