#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Record entry through the real lease-holding launcher, then exit normally.

Installed only in the inert Inno-script fixture. No GUI, DSH or customer runtime
behavior is claimed; a marker proves the native startup gate admitted this launch.
"""
import ctypes
import json
import os
from pathlib import Path
import sys
import sysconfig

if len(sys.argv) != 3 or sys.argv[1] != '--qualification-root':
    raise SystemExit('This fixture requires its explicit disposable data root.')
root = Path(sys.argv[2])
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
module_name = kernel.GetModuleFileNameW
module_name.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32]
module_name.restype = ctypes.c_uint32
name = ctypes.create_unicode_buffer(32768)
length = module_name(None, name, len(name))
if not 0 < length < len(name): raise ctypes.WinError(ctypes.get_last_error())
pending = root/'finish-launched.pending'
with pending.open('x', encoding='utf-8') as stream:
    json.dump({'pid':os.getpid(), 'executable':name.value, 'platform':sysconfig.get_platform()}, stream)
    stream.flush(); os.fsync(stream.fileno())
os.replace(pending, root/'finish-launched.json')
