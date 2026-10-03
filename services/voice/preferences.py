# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Browser settings use the same primary voice profile and native preferences."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'apps/native'))
from augmentor_linux.voice_provider import provider_settings

def request(value):
    return provider_settings(value)

if __name__=='__main__':
    try:
        raw=sys.stdin.read(16385)
        if len(raw)>16384:raise ValueError('Voice settings request is too large')
        print(json.dumps(request(json.loads(raw))))
    except Exception as error:
        print(json.dumps({'error':str(error)}));sys.exit(1)
