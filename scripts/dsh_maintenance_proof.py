# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Admission/shutdown proof for an explicitly supplied disposable DSH host."""
import hashlib
import json
import secrets
import time
import urllib.error


def connection(base, home):
    from dsh.setup import http, product_token
    secret = product_token(home/'augmentor-product-token')
    description = http(base, '/api/augmentor-product')
    assert description.get('maintenanceAdmission') == 1
    assert description['homeId'] == hashlib.sha256(secret.encode()).hexdigest()
    token = secrets.token_hex(24)

    def control(action):
        return http(base, '/api/augmentor-product', {'action': 'maintenance',
            'method': 'host.maintenance.'+action, 'params': {} if action == 'status' else {'token': token}},
            {'x-augmentor-product-token': secret})
    return control


def refuse_busy(base, home):
    control = connection(base, home)
    try:
        control('prepare')
    except urllib.error.HTTPError as error:
        assert error.code == 409
        error.close()
        assert control('status')['phase'] == 'ready'
        return
    raise AssertionError('DSH accepted maintenance during an active model turn.')


def prove(adapter, base, home, session, wait_exit, exit_marker, *, control=None, busy_errors=(urllib.error.HTTPError,)):
    control = control or connection(base, home)

    def prepare():
        deadline = time.monotonic()+10
        while True:
            try:
                result = control('prepare')
                assert result['phase'] == 'prepared' and result['active'] == 0, result
                return
            except busy_errors as error:
                if error.code != 409 or time.monotonic() >= deadline: raise
                if hasattr(error,'close'):error.close()
                time.sleep(.1)

    before = adapter.call('session.history', {'sessionId': session})
    prepare()
    try:
        rejected = False
        try:
            adapter.call('session.prompt', {'sessionId': session, 'mode': 'queue',
                'content': [{'type': 'text', 'text': 'THIS_MAINTENANCE_REQUEST_MUST_NOT_START'}]})
        except (OSError, ValueError, RuntimeError): rejected = True
        assert rejected, 'The real gateway accepted input during maintenance.'
    finally:
        assert control('cancel')['phase'] == 'ready'
    assert adapter.call('session.history', {'sessionId': session}) == before
    prepare()
    assert control('commit')['phase'] == 'closing'
    assert wait_exit() == 0, 'DSH did not exit normally through its application lifecycle.'
    marker = json.loads(exit_marker.read_text(encoding='utf-8'))
    assert marker['exitCode'] == 0 and marker['pid'] > 0, 'Natural Node shutdown was not observed.'
    return {'preparedInputRefused': True, 'cancelPreservedHistory': True,
            'normalExitCode': 0, 'beforeExitObserved': True,
            'scope': 'Actual disposable DSH HTTP gateway and natural CLI shutdown; no live provider.'}
