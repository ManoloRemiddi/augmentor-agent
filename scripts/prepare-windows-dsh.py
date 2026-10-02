#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Apply narrowly pinned Windows terminal lifecycle fixes before packaging.

The published node-pty inbox ConPTY path loses its HPCON on natural exit. Select
its bundled Microsoft ConPTY DLL, whose release protocol ends the console with
its clients, and close the JS input/worker resources when output finally closes.
No runtime mutation, native monkey-patch, forced-success exit or unref workaround.
Original MIT notices remain in the staged dependency tree and license inventory.
"""
import hashlib
from pathlib import Path
import sys

PATCHES = [
    {
        'path': 'node_modules/@deepseek-ai/dsh-subprocess-local/lib/index.js',
        'sha256': 'a3f85e92ce5eddc824348f83cf685d3e417a26c5f1ab602a81fe1bd13315fe2c',
        'old': '\t\t\tcwd: spec.cwd,\n\t\t\tenv\n\t\t};',
        'new': '\t\t\tcwd: spec.cwd,\n\t\t\t// Augmentor: bundled ConPTY releases its host on natural shell exit.\n\t\t\tuseConptyDll: true,\n\t\t\tenv\n\t\t};',
        'reason': 'Select bundled Microsoft ConPTY on Windows; node-pty issue 965.',
    },
    {
        'path': 'node_modules/node-pty/lib/windowsPtyAgent.js',
        'sha256': '4f503c377b11cbd113e1f32b3932fdc35e8132b0e647f4c6b70dc84224127c53',
        'old': "        this._outSocket.setEncoding('utf8');\n",
        'new': "        this._outSocket.setEncoding('utf8');\n"
               "        // Augmentor: output has drained; release the paired input and worker.\n"
               "        this._outSocket.once('close', function () {\n"
               "            _this._inSocket.destroy();\n"
               "            _this._conoutSocketWorker.dispose();\n"
               "        });\n",
        'reason': 'Release natural-exit pipe/worker resources; node-pty issues 887 and 947.',
    },
]


def prepare(target, *, platform=None):
    if (platform or sys.platform) != 'win32':
        return []
    pending = []
    for patch in PATCHES:
        path = Path(target)/patch['path']
        original = path.read_bytes()
        if hashlib.sha256(original).hexdigest() != patch['sha256']:
            raise ValueError('Review changed Windows terminal source before staging: '+patch['path'])
        before, after = patch['old'].encode(), patch['new'].encode()
        if original.count(before) != 1:
            raise ValueError('The reviewed Windows terminal patch does not match exactly once.')
        pending.append((patch, path, original.replace(before, after)))
    result = []
    for patch, path, content in pending:
        path.write_bytes(content)
        result.append({'path': patch['path'], 'originalSha256': patch['sha256'],
                       'preparedSha256': hashlib.sha256(content).hexdigest(), 'reason': patch['reason']})
    return result
