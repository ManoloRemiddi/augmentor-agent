# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Independent offline UI probe of an already inspected Mac target bundle.

No normal application, provider readiness, update completion or replay. Caller
retains installation/startup admission and the exact verified artifact.
"""
import hashlib
from pathlib import Path
import subprocess
import sys

from .macos_payload import verify_bundle
from .payload_integrity import _json


def validate_report(output,release_bytes):
    release=_json(release_bytes,65536);report=_json(output,4096)
    if (not isinstance(release,dict) or not isinstance(report,dict) or set(report)!={
            'schema','releaseSHA256','version','sourceCommit','target','qtPlatform','rendered','width','height','fontCoverage'}
            or report['schema']!='augmentor-macos-health/1' or report['qtPlatform']!='offscreen'
            or report['releaseSHA256']!=hashlib.sha256(release_bytes).hexdigest()
            or any(report[key]!=release.get(key) for key in ('version','sourceCommit','target'))
            or report['target'] not in ('macos-arm64','macos-x64') or report['rendered'] is not True
            or report['fontCoverage'] is not True
            or any(type(report[key]) is not int or not 1<=report[key]<=32768 for key in ('width','height'))):
        raise ValueError('The offline UI report does not identify the independently verified Mac payload.')
    return report


def verify_local_health(bundle,release_bytes,payload,*,development=False,timeout=45):
    if sys.platform!='darwin':raise RuntimeError('Mac target health requires macOS.')
    if type(timeout) not in (int,float) or not 1<=timeout<=60:raise ValueError('Use a bounded offline health timeout.')
    before=verify_bundle(bundle,release_bytes,development=development)
    if before!=payload:raise ValueError('The target changed after independent inspection.')
    project=Path(bundle).absolute()/'Contents/Resources/app'
    result=subprocess.run([str(project/'python/bin/python3'),'-I','-B',str(project/'scripts/macos-local-health.py')],
        stdin=subprocess.DEVNULL,capture_output=True,timeout=timeout)
    if result.returncode or not result.stdout or len(result.stdout)>4096:
        raise RuntimeError('The fixed isolated target health action failed (exit '+str(result.returncode)+').')
    report=validate_report(result.stdout,release_bytes)
    if verify_bundle(bundle,release_bytes,development=development)!=payload:
        raise ValueError('The target changed during the isolated health probe.')
    return {**report,'payloadSHA256':payload['sha256'],'scope':'Offline shared UI render only; no provider, permission or normal app/reopen readiness.'}
