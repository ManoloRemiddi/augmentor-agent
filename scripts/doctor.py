#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'apps/native'))
from augmentor_linux.doctor import report
value=report();value['dependencies']={name:importlib.util.find_spec(name) is not None for name in ['PySide6','gi','yaml']}
value['node']=shutil.which('node');value['build']=(root/'dist/runtime/src/main.js').exists()
value['piInstalled']=(root/'node_modules/@earendil-works/pi-coding-agent/package.json').exists()
value['launch']=str(root/'scripts/augmentor-linux')
try:
    from augmentor_linux.pi_client import PiClient
    os.environ['AUGMENTOR_PI_NO_AUTOSTART']='1'
    value['runtime']=PiClient().call('host.describe')
except Exception as exc:value['runtime']={'available':False,'message':str(exc)}
print(json.dumps(value,indent=2))
sys.exit(0 if value['node'] and value['build'] and value['piInstalled'] and value['dependencies']['PySide6'] else 1)
