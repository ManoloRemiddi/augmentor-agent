#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Prepare a separate Qwen template candidate; never modify a running service.

The observed template emits the initial system text but rejects later system
messages. llama.cpp maps Codex developer messages to that role. Preserve those
messages as explicit system turns instead of dropping application instructions.
Live model/tool qualification is required before activating this candidate.
"""
import argparse
import hashlib
import json
from pathlib import Path

REJECT = '''    {%- if message.role == "system" %}
        {%- if not loop.first %}
            {{- raise_exception('System message must be at the beginning.') }}
        {%- endif %}
    {%- elif message.role == "user" %}'''
PRESERVE = '''    {%- if message.role == "system" %}
        {%- if not loop.first %}
            {{- '<|im_start|>system\\n' + render_content(message.content, false, true)|trim + '<|im_end|>\\n' }}
        {%- endif %}
    {%- elif message.role == "user" %}'''


def prepare(source: Path, output: Path):
    if source.resolve() == output.resolve():
        raise ValueError('Choose a separate output; preserve the original template.')
    original = source.read_bytes()
    if len(original) > 256 * 1024:
        raise ValueError('Template exceeds the candidate size limit.')
    text = original.decode('utf-8')
    if text.count(REJECT) != 1:
        raise ValueError('This template does not have the exact reviewed Qwen rejection block.')
    candidate = text.replace(REJECT, PRESERVE).encode('utf-8')
    # Exclusive creation protects existing candidates, backups and symlinks.
    with output.open('xb') as target:
        target.write(candidate)
    return {'sourceSha256': hashlib.sha256(original).hexdigest(),
            'candidateSha256': hashlib.sha256(candidate).hexdigest(),
            'changedBlocks': 1, 'activated': False, 'liveQualification': 'required'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.out)))
