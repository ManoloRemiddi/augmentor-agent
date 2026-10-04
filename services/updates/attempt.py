# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bounded local launch results, never publisher/install/recovery authority."""
from pathlib import Path
import re

SCHEMA='augmentor-update-attempt-result/1'


def attempt_id(value):
    if not isinstance(value,str) or not re.fullmatch('[a-f0-9]{48}',value):
        raise ValueError('Use the fresh update launch identifier.')
    return value


def release_id(candidate):
    return ':'.join(str(candidate[key]) for key in ('channel','target','version','build'))


def validate_result(value, expected):
    attempt_id(expected)
    if (not isinstance(value,dict) or set(value)!={'schema','attempt','outcome','error','releaseId','transactionId','reopenRequested'} or
            value['schema']!=SCHEMA or value['attempt']!=expected or
            value['outcome'] not in ('deferred','failed','target-healthy') or
            type(value['reopenRequested']) is not bool or
            value['error'] is not None and (not isinstance(value['error'],str) or len(value['error'])>2000) or
            value['releaseId'] is not None and (not isinstance(value['releaseId'],str) or len(value['releaseId'])>256)):
        raise ValueError('The independent update result is invalid. Preserve the attempt.')
    if value['transactionId'] is not None:attempt_id(value['transactionId'])
    if value['outcome']=='target-healthy' and (not value['releaseId'] or not value['transactionId']):
        raise ValueError('The successful result has no exact observed update identity.')
    if value['reopenRequested'] and value['outcome']!='target-healthy':
        raise ValueError('Failed/deferred updates cannot report normal app reopening.')
    return value


def write_result(directory, attempt, outcome, *, error=None, candidate=None, transaction=None, reopened=False):
    from platform_adapters.private_files import atomic_json,require_directory
    result={'schema':SCHEMA,'attempt':attempt_id(attempt),'outcome':outcome,
        'error':None if error is None else str(error)[:2000],
        'releaseId':None if candidate is None else release_id(candidate),
        'transactionId':transaction,'reopenRequested':reopened}
    validate_result(result,attempt)
    atomic_json(require_directory(Path(directory))/('attempt-'+attempt+'.json'),result)
    return result


def read_result(directory, attempt):
    from lifecycle.payload_integrity import _read,_json
    path=Path(directory)/('attempt-'+attempt_id(attempt)+'.json')
    try:raw=_read(path,65536)
    except FileNotFoundError:return None
    return validate_result(_json(raw,65536),attempt)
