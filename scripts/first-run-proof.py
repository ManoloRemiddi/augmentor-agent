#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise the actual first-run form, SDK model check and file task in isolated state.

Pass an installed application root to verify packaged code. Requires Qt/X11 and
Node, supplied by the package or the test environment; no developer model/key.
"""
import http.server
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
APP=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT
sys.path.insert(0,str(APP/'apps/native'))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from augmentor_linux.window import Window

with tempfile.TemporaryDirectory(prefix='augmentor-first-run-') as directory:
    work=Path(directory);target=work/'completed.txt';requests=[]
    os.environ.update(AUGMENTOR_PI_CONFIG=str(work/'config'),AUGMENTOR_PI_STATE=str(work/'state'),
        AUGMENTOR_SHARED_DATA=str(work/'prompts'),AUGMENTOR_SHARED_STATE=str(work/'shared-state'),
        AUGMENTOR_PI_SOCKET=str(work/'runtime.sock'),AUGMENTOR_PI_NO_AUTOSTART='1',PI_OFFLINE='1')
    class Model(http.server.BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));requests.append(body)
            messages=body['messages'];check='verify this connection' in json.dumps(messages)
            if check:delta={'role':'assistant','content':'READY'};finish='stop'
            elif messages[-1]['role']=='tool':delta={'role':'assistant','content':'Created the fixture file.'};finish='stop'
            else:
                delta={'role':'assistant','tool_calls':[{'index':0,'id':'first-task','type':'function','function':{
                    'name':'write','arguments':json.dumps({'path':str(target),'content':'First-run task: Café π\n'})}}]};finish='tool_calls'
            self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
            self.wfile.write(('data: '+json.dumps({'id':'first-run','object':'chat.completion.chunk','model':'fixture',
                'choices':[{'index':0,'delta':delta,'finish_reason':finish}]})+'\n\ndata: [DONE]\n\n').encode())
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Model)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    bundled=APP/'node/bin/node';node=str(bundled) if bundled.exists() else shutil.which('node')
    log=(work/'runtime.log').open('wb')
    process=subprocess.Popen([node,str(APP/'dist/runtime/src/main.js')],stdout=log,stderr=log)
    app=QApplication.instance() or QApplication([]);window=None
    def until(check,timeout=20):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            assert process.poll() is None,(work/'runtime.log').read_text()
            app.processEvents()
            if check():return
            QTest.qWait(20)
        raise AssertionError('First-run proof timed out: '+(window.status.text() if window else 'starting'))
    try:
        until(lambda:(work/'runtime.sock').exists())
        window=Window(preview=False,harness='pi');window.show()
        until(lambda:window.setup_dialog and window.setup_dialog.isVisible())
        dialog=window.setup_dialog
        assert not dialog.save.isEnabled()
        dialog.endpoint.setText(f'http://127.0.0.1:{server.server_port}/v1');dialog.model.setText('fixture')
        dialog.name.setText('First-run fixture');dialog.key.setText('fixture-not-a-secret')
        dialog.mode.setCurrentIndex(dialog.mode.findData('danger-full-access'))
        output=Path(os.environ.get('AUGMENTOR_PROOF_OUTPUT',str(ROOT/'outputs')));output.mkdir(exist_ok=True)
        app.processEvents();dialog.grab().save(str(output/'first-run-setup.png'))
        QTest.mouseClick(dialog.check,Qt.MouseButton.LeftButton)
        until(lambda:dialog.save.isEnabled())
        assert not (work/'config/agent/models.json').exists(),'Check persisted configuration'
        assert len(requests)==1 and not requests[0].get('tools')
        dialog.model.setText('fixture-edited');assert not dialog.save.isEnabled()
        dialog.model.setText('fixture');QTest.mouseClick(dialog.check,Qt.MouseButton.LeftButton)
        until(lambda:dialog.save.isEnabled())
        QTest.mouseClick(dialog.save,Qt.MouseButton.LeftButton)
        until(lambda:dialog.finished_setup and not dialog.isVisible())
        assert not dialog.key.text()
        configured=json.loads((work/'config/agent/models.json').read_text())
        assert configured['providers']['augmentor-first-run-fixture']['models'][0]['id']=='fixture'
        assert (work/'config/agent/models.json').stat().st_mode&0o777==0o600
        assert window.model_picker.currentData()['model']=='fixture'
        window.composer.setPlainText('Create the first-run fixture file.')
        QTest.mouseClick(window.send_button,Qt.MouseButton.LeftButton)
        until(lambda:target.exists() and not window.controller.running and bool(window.messages))
        assert target.read_text()=='First-run task: Café π\n'
        until(lambda:any(role=='Augmentor' for role,_ in window.messages))
        window.close();window=None
        before=len(requests)
        window=Window(preview=False,harness='pi');window.show()
        until(lambda:window.controller.online)
        QTest.qWait(300)
        assert window.setup_dialog is None,'Setup reopened over an existing model'
        assert window.model_picker.currentData()['model']=='fixture';assert len(requests)==before,'Restart replayed a request'
        result={'appRoot':str(APP),'automaticFirstRun':True,'toolFreeCheck':True,'editRequiresRecheck':True,
                'privateConfiguration':True,'modelSelected':True,'fileTaskVerified':True,'reopenWithoutReplay':True}
        (output/'first-run-proof.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    finally:
        if window:window.close()
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        # Both shared companions deliberately survive a chat/runtime restart.
        # Close this fixture's services before deleting their private state.
        sys.path.insert(0,str(APP/'scripts'))
        from maintenance import stop_companions
        stop_companions()
        server.shutdown();server.server_close();log.close()
