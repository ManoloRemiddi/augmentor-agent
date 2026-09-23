#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Remove this installed Pi application; preserve preferences and conversations."""
import os
import json
from pathlib import Path
import shutil
import subprocess
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'apps/native'))
from augmentor_linux.pi_client import PiClient
os.environ['AUGMENTOR_PI_NO_AUTOSTART']='1'
client=PiClient()
try:status=client.call('host.describe')
except Exception:status=None
if status:
    if status.get('activeTurns'):raise SystemExit('Stop active Pi tasks before uninstalling.')
    client.call('host.shutdown')
data=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))
if root!= (data/'augmentor-pi/app').resolve():raise SystemExit('Uninstall only runs from the installed user application. The source checkout is preserved.')
from augmentor_linux.shortcuts import call,ACTION
try:
    if json.loads((root/'installation.json').read_text()).get('desktop'):call('setShortcut',ACTION,'[]','4')
except RuntimeError:pass
for relative in ['applications/com.augmentor.LinuxPi.desktop','kglobalaccel/com.augmentor.LinuxPi.desktop','icons/hicolor/scalable/apps/com.augmentor.LinuxPi.svg']:(data/relative).unlink(missing_ok=True)
shutil.rmtree(root)
previous=root.with_name(root.name+'.previous')
if previous.exists():shutil.rmtree(previous)
subprocess.run(['kbuildsycoca6','--noincremental'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
print('Pi application removed. Preferences and conversations are preserved in the augmentor-pi config/state directories.')
