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
    # Microsoft supplies different internal CRT sets for its browser CPUs.
    # Validate the native entry point and keep the entire hash-verified vendor
    # tree. Our inference CRT is independently checked from the pinned VC CAB.
    required = [vendor/'msedgewebview2.exe']
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
    signature_env={**os.environ, 'AUGMENTOR_VENDOR_FILE': str(required[0])}
    # A pwsh 7 CI parent exports its own module paths. Windows PowerShell 5 must
    # discover its matching inbox Security module instead of loading pwsh's.
    signature_env={name:value for name,value in signature_env.items() if name.casefold()!='psmodulepath'}
    signature = json.loads(subprocess.check_output(
        [str(powershell), '-NoProfile', '-NonInteractive', '-Command', script],
        env=signature_env, text=True, timeout=60))
    if signature['status'] != 'Valid' or not re.search(r'(?:^|,\s*)O=Microsoft Corporation(?:,|$)', signature['subject']):
        raise ValueError('Microsoft runtime publisher signature is not valid.')
    # Keep the complete vendor tree and notices. These DLLs also supply the
    # inference executable; put them next to it for the Windows DLL loader.
    notices = output/'notices/webview2'; notices.mkdir(parents=True)
    shutil.copy2(terms, notices/'LICENSE.txt')
    record = {'version': pins['version'], 'arch': arch, **item,
              'licenseUrl': pins['licenseUrl'], 'licenseSha256': pins['licenseSha256'],
              'publisherVerified': True}
    # ONNX Runtime imports this extra C++ standard-library DLL, which WebView2's
    # CAB does not contain. Read the pinned Microsoft redist as data only: never
    # execute its per-machine installer on a build host or customer computer.
    vc=json.loads((ROOT/'components/handy/visual-c-runtime.json').read_text(encoding='utf-8'))
    supplier=vc['targets'][arch]
    vc_terms=ROOT/'components/handy/licenses/Visual-C-runtime.txt'
    if digest(vc_terms)!=vc['licenseSha256']:raise ValueError('Visual C++ terms changed.')
    with tempfile.TemporaryDirectory(prefix='augmentor-vc-runtime-') as temporary:
        temporary=Path(temporary)
        with urlopen(supplier['url'],timeout=90) as response:data=response.read()
        if len(data)!=supplier['bytes'] or hashlib.sha256(data).hexdigest()!=supplier['sha256']:
            raise ValueError('Visual C++ supplier checksum differs.')
        offset=supplier['cabinetOffset'];size=supplier['cabinetBytes']
        if data[offset:offset+4]!=b'MSCF' or struct.unpack_from('<I',data,offset+8)[0]!=size or offset+size>len(data):
            raise ValueError('Reviewed Visual C++ cabinet layout changed.')
        cabinet=temporary/'payload.cab';cabinet.write_bytes(data[offset:offset+size])
        payloads=temporary/'payloads';payloads.mkdir()
        subprocess.run([str(expand),'-F:*',str(cabinet),str(payloads)],check=True,stdout=subprocess.DEVNULL,timeout=60)
        library=temporary/'library';library.mkdir()
        subprocess.run([str(expand),'-F:*',str(payloads/supplier['payloadCab']),str(library)],
                       check=True,stdout=subprocess.DEVNULL,timeout=60)
        for name,pin in supplier['libraries'].items():
            dll=library/pin['member']
            if digest(dll)!=pin['sha256'] or machine(dll) not in allowed:
                raise ValueError('Wrong Visual C++ library bytes or target: '+name)
            shutil.copy2(dll,output/'bin'/name)
    vc_notice=output/'notices/visual-c';vc_notice.mkdir()
    shutil.copy2(vc_terms,vc_notice/'LICENSE.txt')
    vc_record={'version':vc['version'],'arch':arch,**supplier,'licenseUrl':vc['licenseUrl'],'licenseSha256':vc['licenseSha256']}
    (vc_notice/'supplier.json').write_text(json.dumps(vc_record,indent=2)+'\n',encoding='utf-8')
    record['visualC']=vc_record
    (notices/'supplier.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    return record
