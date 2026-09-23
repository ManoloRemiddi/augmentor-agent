#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Live DSH + Qt completion proof, using a separate chat and a local model."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'apps/native'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from augmentor_linux.adapters.dsh import DshAdapter
from augmentor_linux.controller import Controller
from augmentor_linux.window import Window

app = QApplication([])
client = DshAdapter()
model = client.local_models()[0]
session = 'augmentor-reply-proof-' + uuid.uuid4().hex
results = []
with tempfile.TemporaryDirectory(prefix='augmentor-reply-proof-') as workspace:
    client.call('session.create', {'sessionId': session, 'cwd': workspace, 'agentPreset': client.preset})
    controller = Controller(client=client, harness='dsh'); controller.session = session; controller.online = True
    window = Window(); window.controller = controller; window.resize(440, 500)
    controller.event.connect(window.on_event); controller.busy.connect(window.set_busy)
    controller.recovered.connect(window.restore_recovery)
    recovered = []; errors = []; observed = []
    controller.recovered.connect(lambda *args: recovered.append(True))
    controller.problem.connect(errors.append)
    real_frame = controller.frame
    fault = False
    def frame(value):
        event = value.get('payload', {}).get('event', {})
        observed.append(event)
        if fault and event.get('type') == 'assistant/message':
            value = json.loads(json.dumps(value))
            value['payload']['event']['data']['message']['content'] = []
        real_frame(value)
    controller.frame = frame
    window.set_models([model]); window.show(); app.processEvents()
    try:
        for fault in (False, True):
            count = len(recovered)
            controller.send('Display regression test: reply with exactly "The final answer stays visible." Do not use tools.', model)
            deadline = time.monotonic() + 90
            saw_stream = False
            while len(recovered) == count and not errors and time.monotonic() < deadline:
                app.processEvents(); saw_stream |= bool(window.partial); time.sleep(.01)
            assert not errors, errors
            assert len(recovered) > count, 'Completion was not reconciled'
            if os.environ.get('AUGMENTOR_PROOF_REQUIRE_STREAM'):
                assert saw_stream, 'The streaming fixture completed without visible incremental text'
            QTest.qWait(100)
            saved = client.call('session.history', {'sessionId': session, 'maxMessages':12})
            final = next(r['event'] for r in reversed(saved['events']) if r['event']['type']=='assistant/message')
            text = '\n'.join(p['text'] for p in final['data']['message']['content'] if p['type']=='text')
            assert text and window.messages[-1] == ('Augmentor', text)
            assert text in window.transcript.toPlainText() and not window.partial
            index = len(window.messages)-1; window.jump_latest(); app.processEvents()
            document = window.transcript.document(); block = document.begin(); point = None
            while block.isValid() and point is None:
                fragment = block.begin()
                while not fragment.atEnd():
                    part = fragment.fragment(); fmt = part.charFormat()
                    if fmt.isImageFormat() and fmt.anchorHref()==f'augmentor-copy:{index}':
                        cursor = QTextCursor(document); cursor.setPosition(part.position())
                        point = window.transcript.cursorRect(cursor).center(); point.setX(point.x()+int(fmt.toImageFormat().width()/2)); break
                    fragment += 1
                block = block.next()
            assert point is not None and window.transcript.viewport().rect().contains(point)
            bar = window.transcript.verticalScrollBar(); position = bar.value()
            QTest.mouseClick(window.transcript.viewport(), Qt.MouseButton.LeftButton, pos=point)
            assert app.clipboard().text() == text and bar.value() == position
            QTest.qWait(1700)
            assert text in window.transcript.toPlainText() and bar.value() == position
            assert len([e for e in observed if e.get('type')=='user/message' and e.get('data',{}).get('source',{}).get('kind')=='user']) == len(results)+1, 'Prompt was replayed'
            results.append({'emptyFinalInjected':fault, 'streamObserved':saw_stream, 'savedReplyVisible':True, 'copyByMouse':True, 'scrollPreserved':True, 'noPromptReplay':True})
        (ROOT/'outputs').mkdir(exist_ok=True)
        window.grab().save(str(ROOT/'outputs/dsh-reply-completion.png'))
        output = {'session':session, 'provider':model['provider'], 'model':model['model'], 'results':results}
        (ROOT/'outputs/dsh-reply-completion-proof.json').write_text(json.dumps(output, indent=2)+'\n')
        print(json.dumps(output))
    finally:
        controller.close(); window.close()
