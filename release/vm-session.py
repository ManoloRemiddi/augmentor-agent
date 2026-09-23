#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Run installed UI checks in the real, expendable Plasma Wayland login."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

assert Path('/etc/augmentor-test-vm').is_file() and os.getuid()!=0
APP=Path('/usr/lib/augmentor')
allowed={'DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','XDG_SESSION_TYPE','XDG_CURRENT_DESKTOP','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS'}
for line in subprocess.check_output(['systemctl','--user','show-environment'],text=True).splitlines():
    key,_,value=line.partition('=')
    if key in allowed:os.environ[key]=value
os.environ.update(QT_QPA_PLATFORM='xcb',AUGMENTOR_PROOF_OUTPUT=str(Path.home()/'desktop-evidence'))
Path(os.environ['AUGMENTOR_PROOF_OUTPUT']).mkdir(exist_ok=True)
assert os.environ.get('WAYLAND_DISPLAY'),'No real Wayland session was found'

action=sys.argv[1]
if action in ('first-run','copy'):
    script=APP/'scripts/first-run-proof.py' if action=='first-run' else Path.home()/'copy-scroll-proof.py'
    subprocess.run(['python3',str(script),str(APP)],check=True)
elif action=='shortcut':
    sys.path.insert(0,str(APP/'apps/native'))
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QKeySequence
    from augmentor_linux.shortcuts import save_shortcut
    app=QApplication([])
    save_shortcut(QKeySequence('Ctrl+Alt+J'))
    print(json.dumps({'saved':True}))
elif action=='ready':
    # Environment variables are exported before Plasma finishes starting.
    # Readiness must not register or look up Augmentor's shortcut itself.
    active=subprocess.run(['systemctl','--user','is-active','--quiet','graphical-session.target']).returncode==0
    shell=subprocess.run(['gdbus','call','--session','--dest','org.freedesktop.DBus','--object-path','/org/freedesktop/DBus','--method','org.freedesktop.DBus.NameHasOwner','org.kde.plasmashell'],capture_output=True,text=True)
    compositor=subprocess.run(['gdbus','call','--session','--dest','org.kde.KWin','--object-path','/KWin','--method','org.kde.KWin.supportInformation'],capture_output=True,text=True)
    print(json.dumps(active and 'true' in shell.stdout and compositor.returncode==0))
elif action=='windows':
    result=subprocess.run(['xdotool','search','--onlyvisible','--name','^Augmentor Agent$'],capture_output=True,text=True)
    assert result.returncode in (0,1),result.stderr
    print(json.dumps(result.stdout.split()))
elif action=='close-dialog':
    # The installed application is deliberately unconfigured in this fixture.
    # Its first-run dialog arrives asynchronously after cold Pi startup.
    deadline=time.monotonic()+70
    while time.monotonic()<deadline:
        probe=subprocess.run(['xdotool','search','--onlyvisible','--name','^Connect a model'],capture_output=True,text=True)
        if probe.stdout.strip():break
        time.sleep(.2)
    else:raise AssertionError('The installed first-run dialog did not arrive')
    result=subprocess.run(['xdotool','search','--onlyvisible','--name','^Connect a model'],capture_output=True,text=True)
    for window in result.stdout.split():
        subprocess.run(['xdotool','windowactivate','--sync',window,'key','Escape'],check=True)
elif action=='prepare':
    subprocess.run(['augmentor-maintenance','prepare',*sys.argv[2:]],check=True)
elif action=='versions':
    version=subprocess.check_output(['dpkg-query','-W','-f=${Package} ${Version}\n','augmentor-runtime','augmentor-desktop','plasma-workspace','kwin-wayland','xdg-desktop-portal-kde','chromium'],text=True)
    print(json.dumps({'packages':version.splitlines(),'session':os.environ.get('XDG_SESSION_TYPE'),'display':os.environ['WAYLAND_DISPLAY'],'release':json.loads((APP/'release.json').read_text())}))
else:raise SystemExit('Unknown VM test action')
