# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""The native host allowlist follows the shipped extension's stable public key."""
import base64
import hashlib
import json


def extension_origin(manifest_path):
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    digest = hashlib.sha256(base64.b64decode(manifest['key'], validate=True)).hexdigest()[:32]
    return 'chrome-extension://'+''.join(chr(ord('a')+int(value, 16)) for value in digest)+'/'
