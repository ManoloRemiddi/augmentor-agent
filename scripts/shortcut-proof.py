#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Live KDE/Wayland regression: inject Ctrl+Hangul and observe Pi hide/show.

Requires the installed Pi app running, its Ctrl+Hangul shortcut, XWayland,
xdotool, xwininfo and a configured ydotool daemon. Does not capture keyboard
input or change bindings. This tests synthetic key events, not keyboard firmware.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from PySide6.QtGui import QKeySequence

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'apps/native'))
from augmentor_linux.shortcuts import current_keys

def component_call(component,method):
    return subprocess.check_output(['gdbus','call','--session','--dest','org.kde.kglobalaccel',
        '--object-path','/component/'+component,'--method','org.kde.kglobalaccel.Component.'+method],text=True).strip()

component='com_augmentor_LinuxPi_desktop'
assert current_keys()==[QKeySequence('Ctrl+Hangul')[0].toCombined()],'This proof requires Ctrl+Hangul'
assert component_call(component,'isActive')=='(true,)','KDE saved the binding but left it inactive'
legacy=component_call('com_augmentor_Linux_desktop','allShortcutInfos')
runtime=Path(os.environ.get('XDG_RUNTIME_DIR','/run/user/'+str(os.getuid())))
pid=(runtime/'augmentor-linux-pi.lock').read_text().splitlines()[0]
windows=subprocess.check_output(['xdotool','search','--pid',pid],text=True).split()

def visible():
    return any('Map State: IsViewable' in subprocess.check_output(['xwininfo','-id',wid],text=True) for wid in windows)

def press():
    # Linux KEY_LEFTCTRL=29, KEY_HANGEUL=122. Release both in the same command.
    subprocess.run(['ydotool','key','29:1','122:1','122:0','29:0'],check=True)

initial=visible()
states=[initial]
try:
    for expected in [not initial,initial]:
        press()
        end=time.monotonic()+5
        while visible()!=expected and time.monotonic()<end:time.sleep(.1)
        states.append(visible())
        assert states[-1]==expected,states
    assert component_call('com_augmentor_Linux_desktop','allShortcutInfos')==legacy
    result={'date':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'shortcut':'Ctrl+Hangul',
        'input':'ydotool Linux key events','kdeActive':True,'piVisible':states,'legacyBindingUnchanged':True}
    (root/'outputs').mkdir(exist_ok=True)
    (root/'outputs/shortcut-proof.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
finally:
    if visible()!=initial:press()
