# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual Pi and DSH tool execution against the proof's shared Hindsight bank."""
import http.server
import json
import os
import re
from pathlib import Path
import signal
import socket
import subprocess
import threading
import time
import yaml


def prove(root,work,suffix):
    from augmentor_linux.pi_client import PiClient
    from augmentor_linux.adapters.dsh import DshAdapter
    received=[]
    class Model(http.server.BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['content-length'])));received.append(body)
            self.send_response(200);self.send_header('content-type','text/event-stream');self.end_headers()
            if body['messages'][-1]['role']=='tool':delta={'role':'assistant','content':'Memory received.'};reason='stop'
            else:
                delta={'role':'assistant','tool_calls':[{'index':0,'id':'memory-call','type':'function','function':{'name':'memory_recall','arguments':json.dumps({'query':'What is the acceptance user nickname?'})}}]};reason='tool_calls'
            for d,r in [(delta,None),({},reason)]:
                self.wfile.write(('data: '+json.dumps({'id':'proof','object':'chat.completion.chunk','created':1,'model':'fixture','choices':[{'index':0,'delta':d,'finish_reason':r}]})+'\n\n').encode())
            self.wfile.write(b'data: [DONE]\n\n')
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Model);threading.Thread(target=server.serve_forever,daemon=True).start()
    def until(check):
        end=time.monotonic()+45
        while time.monotonic()<end:
            try:
                if check():return
            except (OSError,RuntimeError):pass
            time.sleep(.05)
        raise AssertionError('Engine memory proof timed out')
    os.environ.update(AUGMENTOR_PI_CONFIG=str(work/'pi-config'),AUGMENTOR_PI_STATE=str(work/'pi-state'),PI_OFFLINE='1')
    folder=work/'pi-config/agent';folder.mkdir(parents=True)
    (folder/'models.json').write_text(json.dumps({'providers':{'fixture':{'baseUrl':f'http://127.0.0.1:{server.server_port}/v1','api':'openai-completions','apiKey':'fixture','models':[{'id':'fixture','name':'Fixture','reasoning':False,'input':['text'],'contextWindow':32000,'maxTokens':1024}]}}}))
    pi=PiClient();process=None;log=None
    try:
        pi.call('host.describe')
        for surface in ('linux','browser'):
            sid='memory-'+surface;before=len(received)
            pi.call('session.create',{'sessionId':sid,'surface':surface,'cwd':str(work),'selection':{'provider':'fixture','model':'fixture'}})
            pi.call('session.prompt',{'sessionId':sid,'content':[{'type':'text','text':'Recall the acceptance user nickname.'}]})
            until(lambda:len(received)>=before+2 and not next(r for r in pi.call('session.list')['items'] if r['sessionId']==sid)['running'])
            assert any(m['role']=='tool' and suffix in json.dumps(m) for m in received[-1]['messages']),received[-1]
            tools=[t['function']['name'] for t in received[-1]['tools']]
            assert 'memory_recall' in tools and not any(n in tools for n in ('memory_retain','memory_delete'))
            print(json.dumps({'harness':'pi','surface':surface,'actualRecalledModelContext':True}),flush=True)
        modules=Path(os.environ['DSH_TEST_MODULES']).resolve();assert modules.is_dir()
        home=work/'dsh';profile=home/'profiles/web';profile.mkdir(parents=True);(profile/'node_modules').symlink_to(modules,target_is_directory=True)
        (profile/'package.json').write_text(json.dumps({'name':'augmentor-memory-proof','private':True,'type':'module','dsh':{'profile':{'bundles':['@deepseek-ai/dsh-base','@deepseek-ai/dsh-web-app']}}}))
        (profile/'cordis.yml').write_text('[]\n');(profile/'cordis.patch.yml').write_text('- id: session-title-llm\n  disabled: true\n')
        for preset in ('augmentor-linux','augmentor'):
            path=home/'.agent-presets'/preset;path.mkdir(parents=True)
            (path/'preset.yml').write_text('name: Augmentor memory fixture\n')
            (path/'agent.cordis.yml').write_text(yaml.safe_dump([{'id':'persona','name':'@deepseek-ai/dsh-persona','config':{'prefix':'You are the memory acceptance fixture.','complete':True,'includeRuntimeContext':False}},
                {'id':'augmentor-memory','name':str(root/'adapters/dsh-memory/index.mjs') }]))
        (home/'settings.yaml').write_text(yaml.safe_dump({'llm-pi-ai':{'providers':{'fixture':{'api':'openai-completions','baseURL':f'http://127.0.0.1:{server.server_port}/v1','apiKeyEnv':'AUGMENTOR_FIXTURE_KEY','models':[{'id':'fixture','name':'Fixture','contextWindow':32000,'maxTokens':1024,'reasoning':False,'input':['text']}]}}},'agent-default-model':{'provider':'fixture','model':'fixture'}}))
        with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        env={**os.environ,'DSH_HOME':str(home),'DSH_TELEMETRY_MODE':'DISABLED','AUGMENTOR_FIXTURE_KEY':'fixture'}
        log=(work/'dsh-memory.log').open('w');process=subprocess.Popen(['dsh','web','--no-open','--host','127.0.0.1','--port',str(port)],env=env,stdout=log,stderr=log,start_new_session=True)
        dsh=DshAdapter(base=f'http://127.0.0.1:{port}',home=home)
        def authenticated():
            tokens=re.findall(r'token=([A-Za-z0-9_-]+)',(work/'dsh-memory.log').read_text())
            if not tokens:return False
            os.environ['AUGMENTOR_DSH_AUTH_TOKEN']=tokens[-1]
            return dsh.call('host.describe')
        until(authenticated)
        for surface,preset in [('linux','augmentor-linux'),('browser','augmentor')]:
            sid='memory-'+surface;before=len(received)
            dsh.call('session.create',{'sessionId':sid,'cwd':str(work),'agentPreset':preset});dsh.call('session.selectModel',{'sessionId':sid,'provider':'fixture','model':'fixture'})
            dsh.call('session.prompt',{'sessionId':sid,'mode':'queue','content':[{'type':'text','text':'Recall the acceptance user nickname.'}]})
            until(lambda:len(received)>=before+2 and not next(r for r in dsh.call('session.list')['items'] if r['sessionId']==sid).get('running'))
            assert any(m['role']=='tool' and suffix in json.dumps(m) for m in received[-1]['messages']),received[-1]
            print(json.dumps({'harness':'dsh','surface':surface,'actualRecalledModelContext':True}),flush=True)
        return {'piLinux':True,'piBrowser':True,'dshLinux':True,'dshBrowser':True,'modelRequests':len(received)}
    finally:
        try:pi.call('host.shutdown')
        except Exception:pass
        if process:
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        if log:log.close()
        server.shutdown();server.server_close()
