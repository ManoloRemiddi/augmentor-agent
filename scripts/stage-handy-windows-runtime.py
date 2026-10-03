#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bundle the pinned Microsoft browser and CRT; never run a global installer."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
CRT = ('concrt140.dll', 'msvcp140.dll', 'msvcp140_codecvt_ids.dll',
       'vcruntime140.dll', 'vcruntime140_1.dll')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def machine(path):
    with path.open('rb') as stream:
        header = stream.read(64)
        if len(header) != 64 or header[:2] != b'MZ':
            raise ValueError('Expected a native Microsoft executable: '+str(path))
        stream.seek(struct.unpack_from('<I', header, 60)[0])
        pe = stream.read(6)
        if pe[:4] != b'PE\0\0': raise ValueError('Invalid PE executable.')
        return struct.unpack_from('<H', pe, 4)[0]


def stage(output):
    if sys.platform != 'win32': raise ValueError('Stage this supplier on native Windows.')
    arch = {'AMD64': 'x64', 'ARM64': 'arm64'}.get(platform.machine())
    if arch is None: raise ValueError('Unsupported Windows architecture.')
    pins = json.loads((ROOT/'components/handy/webview2.json').read_text(encoding='utf-8'))
    item = pins['targets'][arch]
    terms = ROOT/'components/handy/licenses/WebView2-fixed.txt'
    if digest(terms) != pins['licenseSha256']: raise ValueError('Microsoft terms changed.')
    destination = output/'webview2'
    if destination.exists(): raise ValueError('Choose an unstaged WebView2 destination.')
    destination.mkdir()
    with tempfile.TemporaryDirectory(prefix='augmentor-webview2-') as temporary:
        cabinet = Path(temporary)/'runtime.cab'
        with urlopen(item['url'], timeout=120) as response, cabinet.open('wb') as target:
            shutil.copyfileobj(response, target)
        if cabinet.stat().st_size != item['size'] or digest(cabinet) != item['sha256']:
            raise ValueError('Microsoft fixed runtime differs from the reviewed supplier.')
        expand = Path(os.environ['SystemRoot'])/'System32/expand.exe'
        subprocess.run([str(expand), '-F:*', str(cabinet), str(destination)],
                       check=True, stdout=subprocess.DEVNULL, timeout=180)
    vendor = destination/item['folder']
    required = [vendor/'msedgewebview2.exe', *(vendor/name for name in CRT)]
    allowed = {0x8664} if arch == 'x64' else {0xaa64, 0xa641, 0xa64e}
    for file in required:
        if not file.is_file() or machine(file) not in allowed:
            raise ValueError('Missing or wrong-architecture Microsoft runtime: '+str(file))
    # The pinned CAB supplies all files. Verify the native publisher signature as
    # an additional native intake check, using data passed through an environment
    # variable rather than interpreting supplier paths as PowerShell source.
    script = '$s=Get-AuthenticodeSignature -LiteralPath $env:AUGMENTOR_VENDOR_FILE; '
    script += '@{status=[string]$s.Status;subject=[string]$s.SignerCertificate.Subject}|ConvertTo-Json -Compress'
    powershell = Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
    signature = json.loads(subprocess.check_output(
        [str(powershell), '-NoProfile', '-NonInteractive', '-Command', script],
        env={**os.environ, 'AUGMENTOR_VENDOR_FILE': str(required[0])}, text=True, timeout=60))
    if signature['status'] != 'Valid' or not re.search(r'(?:^|,\s*)O=Microsoft Corporation(?:,|$)', signature['subject']):
        raise ValueError('Microsoft runtime publisher signature is not valid.')
    # Keep the complete vendor tree and notices. These DLLs also supply the
    # inference executable; put them next to it for the Windows DLL loader.
    for name in CRT: shutil.copy2(vendor/name, output/'bin'/name)
    notices = output/'notices/webview2'; notices.mkdir(parents=True)
    shutil.copy2(terms, notices/'LICENSE.txt')
    record = {'version': pins['version'], 'arch': arch, **item,
              'licenseUrl': pins['licenseUrl'], 'licenseSha256': pins['licenseSha256'],
              'publisherVerified': True}
    (notices/'supplier.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    return record
