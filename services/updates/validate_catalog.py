# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""The release publisher uses the same eligibility schema as the installed client."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from updates.policy import validate_catalog


def validate(value):
    if not isinstance(value,dict) or set(value)!={'stable','preview'}:
        raise ValueError('Publish both supported channel catalogs together.')
    for channel,catalog in value.items():
        validate_catalog(catalog)
        if any(release['channel']!=channel for release in catalog['releases']):
            raise ValueError('A catalog contains a release for another channel.')
    return value


if __name__=='__main__':
    try:
        raw=sys.stdin.read(4*1024**2+1)
        if len(raw)>4*1024**2:raise ValueError('Update catalogs exceed the publisher limit.')
        print(json.dumps(validate(json.loads(raw)),sort_keys=True,separators=(',',':')))
    except Exception as error:
        print(str(error),file=sys.stderr);sys.exit(1)
