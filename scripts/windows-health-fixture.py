#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Synthetic health response for the exact Inno-template admission proof only.

The real native launcher/private Python runs under the installer observer. This
script checks kernel admission but does not render Qt or qualify application UI.
It replaces the health script only inside the disposable small template payload.
"""
import ctypes
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import subprocess
import sys

if len(sys.argv)!=4 or sys.argv[1]!='--qualification-root' or sys.argv[3]!='--local-health':
    raise SystemExit('Use the isolated native template health fixture.')
base=Path(sys.argv[2]); pending=base/'updates/active.json'
record=pending.read_bytes()
with (base/'updates/writer.lock').open('r+b') as writer:
    try:msvcrt.locking(writer.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:pass
    else:
        msvcrt.locking(writer.fileno(),msvcrt.LK_UNLCK,1)
        raise AssertionError('The independent observer released its writer lock.')
try:stream=pending.open('r+b')
except OSError:pass
else:
    stream.close();raise AssertionError('The independent observer released its active-record pin.')

kernel=ctypes.WinDLL('kernel32',use_last_error=True)
module_name=kernel.GetModuleFileNameW
module_name.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint32]
module_name.restype=ctypes.c_uint32
name=ctypes.create_unicode_buffer(32768)
assert 0<module_name(None,name,len(name))<len(name)
ordinary=subprocess.run([name.value,'--qualification-root',str(base)],
    stdin=subprocess.DEVNULL,capture_output=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
assert ordinary.returncode==74, 'An unresolved journal admitted ordinary native startup.'

create=kernel.CreateFileW
create.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,
                 ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p]
create.restype=ctypes.c_void_p
close=kernel.CloseHandle;close.argtypes=[ctypes.c_void_p];close.restype=ctypes.c_int
handle=create(str(base/'run/installation.lock'),0xC0000000,0,None,3,0x00200000,None)
if handle!=ctypes.c_void_p(-1).value:
    close(handle);raise AssertionError('The independent observer released installation admission.')
assert ctypes.get_last_error()==32, 'Unexpected installation sharing error.'
assert pending.read_bytes()==record
with (base/'health-admission.json').open('x',encoding='utf-8') as stream:
    json.dump({'writerHeld':True,'recordPinned':True,'installationHeld':True,
               'ordinaryStartupRefused':True,'scope':'Synthetic health; no GUI qualification'},stream)
if (base/'health-fixture-refuse').exists():
    raise SystemExit(79)  # Explicit disposable failure after proving admission.

raw=(Path(__file__).resolve().parents[1]/'release.json').read_bytes();release=json.loads(raw)
report={'schema':'augmentor-local-health/1','releaseSHA256':hashlib.sha256(raw).hexdigest(),
        **{key:release[key] for key in ('version','sourceCommit','target')},
        'qtPlatform':'windows','rendered':True,'width':424,'height':484,'fontCoverage':True}
os.write(1,(json.dumps(report)+'\n').encode())
