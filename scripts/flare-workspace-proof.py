#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise halo ownership in isolated X11/KWin, using two real native processes.

Run via AUGMENTOR_UI_PROOF=scripts/flare-workspace-proof.py bash scripts/native-x11-proof.sh.
No model or user session is accessed. Optional AUGMENTOR_NATIVE_ROOT tests an artifact.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(os.environ.get('AUGMENTOR_NATIVE_ROOT', ROOT)) / 'apps/native'))
from PySide6.QtCore import QPoint, QRect
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from augmentor_linux.window import Window
from augmentor_linux.workspaces import release_kwin

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
window = Window(preview=True)
window.preferences.values['pinned'] = False
window.setGeometry(320, 250, 424, 484)
window.show()
window.set_busy(True)
canvas = window.activity.canvas

def settle():
    QTest.qWait(350)

def command(*args):
    result = subprocess.check_output(args, text=True, timeout=10)
    settle()
    return result

def prop(widget, name):
    return command('xprop', '-id', str(int(widget.winId())), name)

def desktop(widget):
    value = prop(widget, '_NET_WM_DESKTOP')
    return int(value.split('=')[1].strip()) if '=' in value else None

def stack():
    return [int(value, 16) for value in re.findall(r'0x[0-9a-f]+', command('xprop', '-root', '_NET_CLIENT_LIST_STACKING'))]

def geometry():
    extra = window.activity.extent - window.activity.margin
    assert canvas.geometry() == QRect(window.mapToGlobal(QPoint()), window.size()).adjusted(-extra, -extra, extra, extra), (canvas.geometry(), window.geometry())

if '--peer' in sys.argv:
    settle()
    Path(sys.argv[-1]).write_text(json.dumps({'window': int(window.winId()), 'halo': int(canvas.winId())}))
    sys.exit(app.exec())

peer = None
try:
    command('wmctrl', '-n', '2')
    command('wmctrl', '-s', '0')
    window.apply_pin(); settle()
    ids = [int(window.winId()), int(canvas.winId())]
    assert ids[1] in stack(), 'Halo bypasses window management'
    assert hex(ids[0]) in prop(canvas, 'WM_TRANSIENT_FOR'), 'Halo has no native owner'
    assert desktop(window) == desktop(canvas) == 0
    command('wmctrl', '-s', '1')
    assert desktop(window) == 0
    assert not canvas.isVisible() or desktop(canvas) == 0, 'Unlocked halo follows other desktops'
    command('wmctrl', '-s', '0')
    window.preferences.values['pinned'] = True; window.apply_pin(); settle()
    assert desktop(window) == desktop(canvas) == 0xffffffff, 'Pin does not include halo'
    command('wmctrl', '-s', '1')
    window.preferences.values['pinned'] = False; window.apply_pin(); settle()
    assert desktop(window) == desktop(canvas) == 1, 'Unpin does not release halo'
    # A newly shown busy effect must inherit the unlocked owner workspace.
    window.set_busy(False); QTest.qWait(1000); window.set_busy(True); settle()
    assert desktop(window) == desktop(canvas) == 1
    with tempfile.TemporaryDirectory() as temporary:
        ready = Path(temporary) / 'peer.json'
        peer = subprocess.Popen([sys.executable, __file__, '--peer', str(ready)])
        for _ in range(100):
            QTest.qWait(100)
            if ready.exists(): break
        other = json.loads(ready.read_text())
        for top, below in ((other['window'], ids[1]), (ids[0], other['halo']), (other['window'], ids[1])):
            command('xdotool', 'windowactivate', '--sync', str(top))
            order = stack()
            assert order.index(below) < order.index(top), ('Halo escapes owner stacking', order, top, below)
        peer.terminate(); peer.wait(timeout=5); peer = None
    for point in (QPoint(0, 0), QPoint(500, 400), QPoint(-100, -80)):
        window.move(point); settle(); geometry()
    window.showMinimized(); settle()
    assert not canvas.isVisible(), 'Minimized owner leaves halo visible'
    window.showNormal(); settle(); assert canvas.isVisible(); geometry()
    window.hide(); settle(); assert not canvas.isVisible()
    window.show(); settle(); assert canvas.isVisible(); geometry()
    window.toggle_compact(); QTest.qWait(700); geometry()
    window.toggle_compact(); QTest.qWait(700); geometry()
    print(json.dumps({'passed': ['managed transient', 'workspace switch', 'pin/unpin', 'effect reappearance', 'two-process stacking both directions', 'desktop edges', 'minimize/restore', 'hide/show', 'compact/expanded'], 'platform': app.platformName()}))
finally:
    if peer is not None: peer.terminate(); peer.wait(timeout=5)
    window.close(); release_kwin()
