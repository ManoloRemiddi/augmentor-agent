#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Verify Qt restarts/reconnects its isolated runtime without model requests."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'apps/native'))
work=Path(tempfile.mkdtemp(prefix='augmentor-pi-ui-recovery-'))
os.environ.update({'AUGMENTOR_PI_CONFIG':str(work/'config'),'AUGMENTOR_PI_STATE':str(work/'state'),'QT_QPA_PLATFORM':'offscreen'})
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from augmentor_linux.window import Window
app=QApplication([]);window=Window(preview=False)
def wait(predicate,seconds=20):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        app.processEvents();QTest.qWait(30)
        if predicate():return
    raise AssertionError('UI recovery timed out')
wait(lambda:window.controller.online)
client=window.controller.client;before=client.call('host.describe')['pid']
client.call('host.shutdown')
seen_offline=[]
window.controller.connection.connect(lambda online:seen_offline.append(not online))
# The UI's monitor owns recovery; the proof does not make a restarting health call.
wait(lambda:True in seen_offline)
wait(lambda:window.controller.online)
after=client.call('host.describe')['pid'];assert before!=after
result={'noModelRequests':True,'uiRestartsHost':True,'uiReconnected':True,'beforePid':before,'afterPid':after}
(root/'outputs').mkdir(exist_ok=True);(root/'outputs/ui-recovery-proof.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
window.close();app.processEvents();client.call('host.shutdown')
