#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Live KDE/AT-SPI and visible-browser dispatch checks with the Pi UI."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tempfile
import shutil
import atexit
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'apps/native'))
os.environ['QT_QPA_PLATFORM']='xcb'
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from augmentor_linux.window import Window
from augmentor_linux.workspaces import pin_kwin,release_kwin
from augmentor_linux.browser import refresh_accessibility_bus
refresh_accessibility_bus()
app=QApplication([]);window=Window(preview=True);window.show()
QTest.qWait(500)
wid=str(int(window.winId()))
def prop(name):return subprocess.check_output(['xprop','-id',wid,name],text=True).strip()
assert pin_kwin(True);QTest.qWait(300)
pinned=prop('_NET_WM_DESKTOP');assert '4294967295' in pinned,pinned
above=prop('_NET_WM_STATE');assert '_NET_WM_STATE_ABOVE' in above,above
assert pin_kwin(False);QTest.qWait(300)
unpinned=prop('_NET_WM_DESKTOP');assert '4294967295' not in unpinned,unpinned
helper=root/'apps/native/augmentor_linux/desktop.py'
work=Path(tempfile.mkdtemp(prefix='augmentor-pi-desktop-'))
(work/'config/agent').mkdir(parents=True)
shutil.copy2(root/'config/models.local.example.json',work/'config/agent/models.json')
native=subprocess.Popen([str(root/'scripts/augmentor-linux')],env={**os.environ,'AUGMENTOR_PI_CONFIG':str(work/'config'),'AUGMENTOR_PI_STATE':str(work/'state')},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
atexit.register(lambda:native.terminate() if native.poll() is None else None)
lock=Path(os.environ['XDG_RUNTIME_DIR'])/'augmentor-linux-pi.lock'
end=time.monotonic()+15
while not lock.exists() and time.monotonic()<end:app.processEvents();QTest.qWait(30)
assert lock.exists(), 'Native app did not create its desktop connection'
assert native.poll() is None, 'Native launcher failed'
def desktop(value):
    child=subprocess.Popen(['/usr/bin/python3',str(helper)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    child.stdin.write(json.dumps(value));child.stdin.close()
    deadline=time.monotonic()+15
    while child.poll() is None and time.monotonic()<deadline:app.processEvents();QTest.qWait(20)
    if child.poll() is None:child.kill();raise AssertionError('Desktop helper timed out')
    return json.loads(child.stdout.read())
observed=desktop({'action':'observe','appPid':os.getpid()});assert observed['ok'] and observed.get('nodes'),observed
assert not desktop({'action':'browser_open','url':'file:///tmp/no'})['ok']
# Opening one harmless URL proves dispatch in the real Chromium profile.
# Browser automation and verification of page loading belong to the later extension.
opened=desktop({'action':'browser_open','url':'https://example.com/'});assert opened.get('ok') and opened.get('dispatched') and opened.get('verified') is False,opened
result={'pinned':pinned,'unpinned':unpinned,'above':above,'atspiNodes':len(observed['nodes']),'browser':opened}
(root/'outputs/desktop-acceptance.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
release_kwin();window.close();app.processEvents();native.terminate();native.wait(timeout=5)
os.environ['AUGMENTOR_PI_STATE']=str(work/'state')
from augmentor_linux.pi_client import PiClient
PiClient().call('host.shutdown')
