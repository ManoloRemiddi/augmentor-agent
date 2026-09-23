#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Install the user launcher and an available KDE shortcut; never replace another binding."""
import os
import argparse
import shutil
import sys
from pathlib import Path
import subprocess

from PySide6.QtGui import QKeySequence

project = Path(__file__).resolve().parent.parent
name = 'com.augmentor.LinuxPi.desktop'
sys.path.insert(0,str(project/'apps/native'))
from augmentor_linux.shortcuts import current_keys,SHORTCUT_FLAGS
parser=argparse.ArgumentParser()
parser.add_argument('--shortcut',default=None,help='Qt key name emitted by the keyboard')
args=parser.parse_args()
try:existing=current_keys()
except RuntimeError:existing=[]
shortcut = args.shortcut or (QKeySequence(existing[0]).toString() if existing else 'Meta+Alt+Space')
key = QKeySequence(shortcut)[0].toCombined()
dbus = ['gdbus', 'call', '--session', '--dest', 'org.kde.kglobalaccel', '--object-path', '/kglobalaccel', '--method']
available = subprocess.run(dbus + ['org.kde.KGlobalAccel.isGlobalShortcutAvailable', str(key), name], capture_output=True, text=True, timeout=5)
bind = key in existing or (available.returncode == 0 and 'true' in available.stdout)
exec_path = str(project / 'scripts/augmentor-linux').replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')
desktop = '# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0\n[Desktop Entry]\nType=Application\nName=Augmentor Agent\nComment=Native Linux assistant with Pi and DSH\nExec="' + exec_path + '"\nIcon=com.augmentor.LinuxPi\nTerminal=false\nCategories=Utility;\nStartupWMClass=Augmentor Agent\n'
if bind or existing:
    desktop += 'X-KDE-Shortcuts=' + (shortcut if bind else QKeySequence(existing[0]).toString()) + '\n'
data = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share'))
icon_path=data/'icons/hicolor/scalable/apps/com.augmentor.LinuxPi.svg'
icon_path.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(project/'apps/native/augmentor_linux/assets/augmentor.svg',icon_path)
paths = [project / 'outputs' / name, data / 'applications' / name, data / 'kglobalaccel' / name]
for path in paths:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(desktop)
subprocess.run(['desktop-file-validate', str(paths[0])], check=True)
subprocess.run(['kbuildsycoca6', '--noincremental'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
if bind:
    action = "['com.augmentor.LinuxPi.desktop','_launch','Augmentor Agent','Show or hide Augmentor Agent']"
    subprocess.run(dbus + ['org.kde.KGlobalAccel.doRegister', action], check=True, capture_output=True, timeout=5)
    result = subprocess.run(dbus + ['org.kde.KGlobalAccel.setShortcut', action, '[' + str(key) + ']', SHORTCUT_FLAGS], check=True, capture_output=True, text=True, timeout=5)
    print('Shortcut registration:', result.stdout.strip())
    print('Show / hide:', shortcut)
else:
    print('Launcher installed. Shortcut not assigned: KDE unavailable or requested combination is already in use.')
print('Application menu entry:', paths[1])
