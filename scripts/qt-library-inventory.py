#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Record the Qt binaries actually shipped, without claiming license coverage."""
import argparse
import hashlib
import json
from pathlib import Path
import PySide6
from PySide6.QtCore import qVersion


def inventory():
    root=Path(PySide6.__file__).resolve().parent
    binaries=set(root.rglob('*.dylib'))
    frameworks=sorted(root.rglob('*.framework'))
    for framework in frameworks:
        candidates=[framework/framework.stem,*framework.glob('Versions/*/'+framework.stem)]
        found={p.resolve() for p in candidates if p.is_file()}
        if not found:raise RuntimeError('Framework executable missing: '+str(framework))
        binaries.update(found)
    rows=[]
    for file in sorted(binaries):
        if file.is_file():
            with file.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            rows.append({'path':str(file.relative_to(root)),'bytes':file.stat().st_size,'sha256':digest})
    return {'qtVersion':qVersion(),'pysideVersion':PySide6.__version__,
            'frameworks':[str(p.relative_to(root)) for p in frameworks],
            'binaries':rows,'embeddedThirdPartyNoticeReviewComplete':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--qt-version',required=True)
    args=parser.parse_args()
    report=inventory()
    if report['qtVersion']!=args.qt_version:parser.error('Qt version differs from the release configuration')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n')
