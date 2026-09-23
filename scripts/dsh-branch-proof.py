#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise both DSH adapters against an isolated real DSH host and fixture model.

Requires an installed DSH CLI. DSH_TEST_MODULES names its profile node_modules;
only installed code is reused. No real profile settings or credentials are read.
"""
import http.server
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import yaml
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'apps/native'))
sys.path.insert(0,str(ROOT/'services'))
from augmentor_linux.adapters.dsh import DshAdapter
from dsh.branch import history


def until(check,seconds=35):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        try:
            value=check()
            if value:return value
        except (OSError,ValueError):pass
        time.sleep(.05)
    raise AssertionError('DSH acceptance condition timed out')


with tempfile.TemporaryDirectory(prefix='augmentor-dsh-branch-') as temporary:
    root=Path(temporary);home=root/'home';profile=home/'profiles/web';profile.mkdir(parents=True)
    modules=Path(os.environ['DSH_TEST_MODULES']).resolve();assert modules.is_dir()
    (profile/'node_modules').symlink_to(modules,target_is_directory=True)
    (profile/'package.json').write_text(json.dumps({'name':'augmentor-dsh-acceptance','private':True,'type':'module',
        'dsh':{'profile':{'bundles':['@deepseek-ai/dsh-base','@deepseek-ai/dsh-web-app']}}}))
    (profile/'cordis.yml').write_text('[]\n')
    # Disable title generation so every observed model call belongs to a prompt.
    (profile/'cordis.patch.yml').write_text('- id: session-title-llm\n  disabled: true\n')
    for preset in ('augmentor-linux','augmentor'):
        path=home/'.agent-presets'/preset;path.mkdir(parents=True)
        (path/'preset.yml').write_text('name: Augmentor branch fixture\n')
        (path/'agent.cordis.yml').write_text("- id: persona\n  name: '@deepseek-ai/dsh-persona'\n  config:\n    text: You are the Augmentor deterministic branch acceptance fixture.\n    complete: true\n    includeRuntimeContext: false\n")
    requests=[]
    class Model(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));requests.append(body)
            self.send_response(200);self.send_header('content-type','text/event-stream');self.end_headers()
            frame={'id':'fixture','object':'chat.completion.chunk','model':'fixture','choices':[{'index':0,'delta':{'role':'assistant','content':'Fixture response π'},'finish_reason':'stop'}]}
            self.wfile.write(('data: '+json.dumps(frame)+'\n\ndata: [DONE]\n\n').encode())
    model=http.server.ThreadingHTTPServer(('127.0.0.1',0),Model)
    threading.Thread(target=model.serve_forever,daemon=True).start()
    (home/'settings.yaml').write_text(yaml.safe_dump({'llm-pi-ai':{'providers':{'fixture':{'api':'openai-completions',
        'baseURL':f'http://127.0.0.1:{model.server_port}/v1','apiKeyEnv':'AUGMENTOR_FIXTURE_KEY','models':[{'id':'fixture','name':'Fixture','contextWindow':32000,'maxTokens':1024,'reasoning':False,'input':['text']}]}}},
        'agent-default-model':{'provider':'fixture','model':'fixture'}}))
    with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    env={**os.environ,'DSH_HOME':str(home),'DSH_TELEMETRY_MODE':'DISABLED','AUGMENTOR_FIXTURE_KEY':'fixture-not-a-secret',
         'DSH_AUGMENTOR_URL':f'http://127.0.0.1:{port}','AUGMENTOR_SHARED_STATE':str(root/'state')}
    log=(root/'host.log').open('wb')
    process=subprocess.Popen(['dsh','web','--no-open','--host','127.0.0.1','--port',str(port)],env=env,stdout=log,stderr=log,start_new_session=True)
    client=DshAdapter(base=env['DSH_AUGMENTOR_URL'],home=home)
    os.environ['AUGMENTOR_SHARED_STATE']=env['AUGMENTOR_SHARED_STATE']
    try:
        until(lambda:client.call('host.describe'))
        def prompt(sid,text):
            before=len(requests)
            client.call('session.prompt',{'sessionId':sid,'mode':'queue','content':[{'type':'text','text':text}]})
            until(lambda:len(requests)>before and not next(r for r in client.call('session.list')['items'] if r['sessionId']==sid).get('running'))
            until(lambda:any(e['type']=='turn/end' for e in history(client.call,sid)))
        def branch_browser(params):
            command="import {dshBranch} from './apps/browser/shared/branch.mjs';let s='';for await(const c of process.stdin)s+=c;console.log(JSON.stringify(await dshBranch(JSON.parse(s))));"
            result=subprocess.run([shutil.which('node'),'--input-type=module','-e',command],input=json.dumps(params),env=env,cwd=ROOT,text=True,capture_output=True,timeout=30)
            assert result.returncode==0,result.stderr
            return json.loads(result.stdout)
        for surface,preset in [('linux','augmentor-linux'),('browser','augmentor')]:
            sid='fixture-'+surface;cwd=root/surface;cwd.mkdir()
            client.call('session.create',{'sessionId':sid,'cwd':str(cwd),'agentPreset':preset})
            client.call('session.selectModel',{'sessionId':sid,'provider':'fixture','model':'fixture'})
            prompt(sid,'FIRST_CONTEXT_'+surface);prompt(sid,'LATER_CONTEXT_'+surface)
            original=history(client.call,sid);before=len(requests)
            replies=[e for e in original if e['type']=='assistant/message'];users=[e for e in original if e['type']=='user/message']
            call=lambda p:client.call('session.branch',p) if surface=='linux' else branch_browser(p)
            params={'sessionId':sid,'newSessionId':'branch-'+surface,'messageSeq':replies[0]['seq'],'mode':'reply'}
            child=call(params);assert len(requests)==before;assert call(params)==child
            assert history(client.call,sid)==original
            prompt(child['sessionId'],'FOLLOW_BRANCH_'+surface)
            content=json.dumps(requests[-1]['messages']);assert 'FIRST_CONTEXT_'+surface in content and 'LATER_CONTEXT_'+surface not in content
            edited=call({**params,'newSessionId':'edit-'+surface,'messageSeq':users[-1]['seq'],'mode':'edit'})
            prompt(edited['sessionId'],'REVISED_CONTEXT_'+surface)
            content=json.dumps(requests[-1]['messages']);assert 'FIRST_CONTEXT_'+surface in content and 'REVISED_CONTEXT_'+surface in content and 'LATER_CONTEXT_'+surface not in content
            assert history(client.call,sid)==original
            print(json.dumps({'surface':surface,'realDshApi':True,'actualModelContextVerified':True,'sourceUnchanged':True,'branchNeverReplayedPrompt':True}),flush=True)
        # The real Qt renderer/controller must expose working DSH actions too.
        os.environ.update(QT_QPA_PLATFORM=os.environ.get('QT_QPA_PLATFORM','offscreen'),XDG_CONFIG_HOME=str(root/'xdg-config'),XDG_STATE_HOME=str(root/'xdg-state'))
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QTextCursor
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from augmentor_linux.window import Window
        from augmentor_linux.controller import Controller
        app=QApplication.instance() or QApplication([]);app.setQuitOnLastWindowClosed(False)
        window=Window(preview=True);window.controller=Controller(window,client=client,harness='dsh');errors=[]
        window.controller.problem.connect(errors.append);window.bind_controller();window.show()
        def ui_until(check):
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                app.processEvents();QTest.qWait(20)
                assert not errors,errors
                if check():return
            raise AssertionError('Qt DSH action timed out: '+window.status.text())
        def click_icon(action,index):
            document=window.transcript.document();block=document.begin()
            while block.isValid():
                iterator=block.begin()
                while not iterator.atEnd():
                    fragment=iterator.fragment();format=fragment.charFormat()
                    if format.isImageFormat() and format.anchorHref()==f'augmentor-{action}:{index}':
                        cursor=QTextCursor(document);cursor.setPosition(fragment.position());window.transcript.setTextCursor(cursor);window.transcript.ensureCursorVisible();app.processEvents()
                        point=window.transcript.cursorRect(cursor).center();point.setX(point.x()+int(format.toImageFormat().width()/2))
                        QTest.mouseClick(window.transcript.viewport(),Qt.MouseButton.LeftButton,pos=point);return
                    iterator+=1
                block=block.next()
            raise AssertionError('Missing rendered DSH action '+action)
        try:
            ui_until(lambda:window.controller.online)
            source=next(r for r in client.call('session.list')['items'] if r['sessionId']=='fixture-linux')
            original=history(client.call,source['sessionId'])
            window.controller.open_session(source);ui_until(lambda:len(window.messages)==4 and not window.controller.navigating)
            click_icon('branch',1);ui_until(lambda:window.controller.session!='fixture-linux' and not window.controller.navigating)
            assert history(client.call,'fixture-linux')==original
            window.controller.open_session(source);ui_until(lambda:len(window.messages)==4 and not window.controller.navigating)
            click_icon('edit',2);assert window.composer.toPlainText()=='LATER_CONTEXT_linux'
            window.composer.setPlainText('NATIVE_UI_EDIT_CONTEXT');QTest.mouseClick(window.send_button,Qt.MouseButton.LeftButton)
            ui_until(lambda:window.controller.session!='fixture-linux' and not window.controller.running and any('Fixture response' in t for role,t in window.messages if role=='Augmentor'))
            content=json.dumps(requests[-1]['messages']);assert 'FIRST_CONTEXT_linux' in content and 'NATIVE_UI_EDIT_CONTEXT' in content and 'LATER_CONTEXT_linux' not in content
            assert history(client.call,'fixture-linux')==original
            print(json.dumps({'nativeQtPointerBranchAndEdit':True,'resubmittedModelContextVerified':True}),flush=True)
        finally:window.close();app.processEvents()
        result={'dsh':client.call('host.describe').get('version'),'surfaces':['linux','browser'],'model':'deterministic HTTP fixture','modelRequests':len(requests),'passed':True}
        (ROOT/'outputs/dsh-branch-proof.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)
    except Exception:
        print((root/'host.log').read_text()[-8000:],file=sys.stderr);raise
    finally:
        import signal
        os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        model.shutdown();model.server_close();log.close()
