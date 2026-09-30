#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Private stdin/stdout credential bridge; only OS-backed stores are permitted."""
import json
import re
import sys

SERVICE = 'Augmentor Agent Codex'


def backend():
    # Choose the native implementation directly; never load a configured plaintext
    # keyring, an environment plugin, or keyring's fallback/chainer backend.
    if sys.platform == 'darwin':
        from keyring.backends.macOS import Keyring
    elif sys.platform == 'linux':
        from keyring.backends.SecretService import Keyring
    else:
        raise RuntimeError('Unsupported credential platform')
    return Keyring()


def handle(request, store):
    if not isinstance(request, dict) or request.get('operation') not in ('get', 'put', 'delete'):
        raise ValueError('Invalid operation')
    reference = request.get('reference')
    if not isinstance(reference, str) or not re.fullmatch(r'codex-[a-zA-Z0-9_-]{1,100}', reference):
        raise ValueError('Invalid credential reference')
    if request['operation'] == 'get':
        return {'value': store.get_password(SERVICE, reference)}
    if request['operation'] == 'put':
        value = request.get('value')
        if not isinstance(value, str) or not value or len(value) > 65536 or '\0' in value:
            raise ValueError('Invalid credential')
        store.set_password(SERVICE, reference, value)
        return {'saved': True}
    if store.get_password(SERVICE, reference) is not None:
        store.delete_password(SERVICE, reference)
    return {'deleted': True}


def main():
    try:
        raw = sys.stdin.buffer.read(262145)
        if len(raw) > 262144:
            raise ValueError('Oversized request')
        result = handle(json.loads(raw), backend())
        sys.stdout.write(json.dumps({'result': result}) + '\n')
    except Exception:
        # Backend exceptions can include secret material or private keychain paths.
        sys.stdout.write(json.dumps({'error': 'OS credential storage is unavailable or locked. Unlock it and retry; no plaintext fallback was used.'}) + '\n')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
