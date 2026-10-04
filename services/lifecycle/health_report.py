# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Shared offline health-report validation, including independent recovery."""
import hashlib

from .payload_integrity import _json


def validate_health_report(output, release_bytes):
    """Match bounded native UI evidence to independently identified metadata.

    Callers must verify payload bytes, retain installation admission and observe
    the actual owned probe's successful complete exit. JSON alone proves none
    of those facts and cannot complete an update or authorize restoration.
    """
    release = _json(release_bytes, 65536)
    report = _json(output, 4096)
    if (not isinstance(release, dict) or not isinstance(report, dict) or
            set(report) != {'schema','releaseSHA256','version','sourceCommit','target',
                           'qtPlatform','rendered','width','height','fontCoverage'} or
            report['schema'] != 'augmentor-local-health/1' or report['qtPlatform'] != 'windows' or
            report['releaseSHA256'] != hashlib.sha256(release_bytes).hexdigest() or
            any(report[key] != release.get(key) for key in ('version','sourceCommit','target')) or
            report['target'] not in ('windows-x64','windows-arm64') or
            report['rendered'] is not True or report['fontCoverage'] is not True or
            any(type(report[key]) is not int or not 1 <= report[key] <= 32768 for key in ('width','height'))):
        raise ValueError('The local-health report does not identify the verified installed payload.')
    return report
