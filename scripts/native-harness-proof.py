#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise the same Qt UI through Pi and DSH using the selected local model."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'apps/native'));os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from augmentor_linux.window import Window
from augmentor_linux.controller import Controller
from augmentor_linux.pi_client import PiClient
from augmentor_linux.adapters.dsh import DshAdapter
app=QApplication([]);app.setQuitOnLastWindowClosed(False);results=[]
for harness,client in [('pi',PiClient()),('dsh',DshAdapter())]:
    w=Window(preview=True);w.controller=Controller(w,client=client,harness=harness);w.bind_controller();w.show();errors=[];w.controller.problem.connect(errors.append)
    def wait(predicate,seconds=35):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            app.processEvents();QTest.qWait(25)
            if predicate():return
            if errors:raise AssertionError(errors)
        raise AssertionError('Timed out: '+w.status.text())
    try:
        wait(lambda:w.controller.online)
        models=client.model_catalog();model=next(m for g in models['groups'] for m in g['models'] if 'Qwen3.8-27B-UD-Q6_K_XL'==m['model'])
        w.set_selection(model);w.composer.setPlainText('Reply with exactly AUGMENTOR HARNESS VERIFIED. Do not use tools.');w.send()
        wait(lambda:not w.controller.running and any(role=='Augmentor' for role,text in w.messages),60)
        assert any('AUGMENTOR HARNESS VERIFIED' in text for role,text in w.messages if role=='Augmentor'),w.messages
        assert w.controller.selection['model']==model['model']
        results.append({'harness':harness,'session':w.controller.session,'selectedModel':model['model'],'actualReplyVerified':True,'capabilities':w.controller.capabilities})
    finally:w.close();app.processEvents()
(root/'outputs/native-harness-proof.json').write_text(json.dumps(results,indent=2));print(json.dumps(results))
