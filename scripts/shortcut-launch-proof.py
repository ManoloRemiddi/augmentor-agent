#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real KDE shortcut activation of the installed desktop, inside isolated X11/DBus.

Requires scripts/native-x11-proof.sh's isolated session. Never targets the user's
normal desktop. Tests actual key events, launcher activation and window mapping.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

APP=Path(__file__).resolve().parents[1]
assert (APP/'release.json').is_file(),'Run from the installed Debian app'
assert 'augmentor-x11-proof-' in os.environ.get('XDG_RUNTIME_DIR',''),'An isolated test desktop is required'
assert os.getuid()!=0,'Run as an ordinary user'
sys.path.insert(0,str(APP/'apps/native'))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from augmentor_linux.shortcuts import COMPONENT,ACTION,call,save_shortcut
from augmentor_linux.pi_client import socket_path
sys.path.insert(0,str(APP/'scripts'))
from maintenance import ui_call

app=QApplication([]);pid=None;daemon=None
assert COMPONENT=='com.augmentor.Agent.desktop'
def windows(pattern='^Augmentor Agent$'):
    result=subprocess.run(['xdotool','search','--onlyvisible','--name',pattern],capture_output=True,text=True)
    if result.returncode not in (0,1):raise AssertionError(result.stderr)
    return result.stdout.split()
def until(check):
    end=time.monotonic()+20
    while time.monotonic()<end:
        app.processEvents()
        if check():return
        QTest.qWait(30)
    raise AssertionError('Installed shortcut did not change the expected window state')
def press():
    subprocess.run(['xdotool','key','--clearmodifiers','ctrl+alt+j'],check=True)
def ready():
    try:
        status=ui_call('maintenance.status')
        return bool(status and status.get('pid')==pid and status.get('onboardingProtocol')==1)
    except (OSError,RuntimeError):return False
def shortcuts_ready():
    try:call('shortcut',ACTION);return True
    except RuntimeError:return False
try:
    # Debian starts this through Plasma's session, which the isolated Xvfb test
    # does not run. Start the real packaged daemon, not a replacement service.
    daemon=subprocess.Popen(['/usr/lib/x86_64-linux-gnu/libexec/kglobalacceld'],stdin=subprocess.DEVNULL)
    until(shortcuts_ready)
    assert not windows()
    save_shortcut(QKeySequence('Ctrl+Alt+J'))
    press();until(lambda:len(windows())==1)
    wid=windows()[0];pid=int(subprocess.check_output(['xdotool','getwindowpid',wid],text=True))
    assert pid!=os.getpid()
    until(ready)
    assert not Path(socket_path()).exists(),'DSH first launch unexpectedly started Pi'
    # Allow the first-run dialog to appear; both parent and dialog must hide.
    until(lambda:len(windows('^Connect DSH'))==1)
    press();until(lambda:not windows() and not windows('^Connect DSH'))
    press();until(lambda:windows()==[wid] and len(windows('^Connect DSH'))==1)
    daemon.terminate();daemon.wait(timeout=5)
    daemon=subprocess.Popen(['/usr/lib/x86_64-linux-gnu/libexec/kglobalacceld'],stdin=subprocess.DEVNULL)
    until(shortcuts_ready)
    # Do not re-register: the desktop files and KDE settings must restore it.
    press();until(lambda:not windows())
    press();until(lambda:windows()==[wid])
    # Close the first-run dialog using real input, then exercise the shipped
    # maintenance command. It must remove both live and persisted shortcuts.
    setup=windows('^Connect DSH')[0]
    subprocess.run(['xdotool','windowactivate','--sync',setup,'key','Escape'],check=True)
    until(lambda:not windows('^Connect DSH'))
    prepared=json.loads(subprocess.check_output(['augmentor-maintenance','prepare','--remove'],text=True))
    until(lambda:not windows())
    data=Path(os.environ['XDG_DATA_HOME'])
    assert not (data/'applications'/COMPONENT).exists()
    assert not (data/'kglobalaccel'/COMPONENT).exists()
    daemon.terminate();daemon.wait(timeout=5)
    daemon=subprocess.Popen(['/usr/lib/x86_64-linux-gnu/libexec/kglobalacceld'],stdin=subprocess.DEVNULL)
    until(shortcuts_ready)
    press();QTest.qWait(700)
    assert not windows(),'Removed shortcut launched Augmentor after the service restarted'
    assert prepared['dataPreserved']
    result={'desktopId':COMPONENT,'input':'xdotool Ctrl+Alt+J','launched':True,'hidden':True,'restoredSameWindow':True,'survivedShortcutServiceRestart':True,'firstRunHarness':'dsh','piWorkerNotStarted':True}
    result['maintenanceRemovedShortcutAfterRestart']=True
    (Path(os.environ['AUGMENTOR_PROOF_OUTPUT'])/'shortcut-launch-proof.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
finally:
    try:
        if shortcuts_ready():call('setShortcut',ACTION,'[]','4')
    finally:
        if pid:
            try:os.kill(pid,signal.SIGTERM)
            except ProcessLookupError:pass
        if daemon:
            daemon.terminate()
            try:daemon.wait(timeout=5)
            except subprocess.TimeoutExpired:daemon.kill();daemon.wait()
