# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Settings reads must preserve the explicit system-dictation off switch."""
from . import dictation


def snapshot(method, params=None):
    status = dictation.request(method, params, timeout=75)
    if method != 'status':
        status = dictation.request('status')
    models = dictation.request('models', timeout=75) if status.get('enabled') and status.get('installed', True) else []
    if models:
        status = dictation.request('status')
    devices = dictation.request('devices', timeout=75) if models else []
    return {'status': status, 'models': models, 'devices': devices}
