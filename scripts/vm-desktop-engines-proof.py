#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real Pi/DSH SDK tools against an isolated VM via a forwarded private socket.

Only the disposable guest executes desktop input. Host desktop autostart is
explicitly disabled. The model is a deterministic fixture, not visual reasoning.
"""
import argparse
import base64
import http.server
import json
import os
from pathlib import Path
import re
import shlex
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import yaml
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed',action='store_true')
p.add_argument('--vm-dir',type=Path,default=ROOT/'outputs/desktop-vm')
p.add_argument('--harness',choices=('pi','dsh','both'),default='both')
p.add_argument('--case',choices=('task','stop','both'),default='both')
p.add_argument('--focus-debug',action='store_true')
p.add_argument('--guest-root',help='Explicit staged source root in the disposable VM; cannot be combined with --installed')
p.add_argument('--capture-debug',action='store_true',help='Enable PipeWire/GStreamer diagnostics in the isolated executor log');args=p.parse_args()
if args.installed and args.guest_root:p.error('--guest-root is for staged source, not installed artifacts')
vm=args.vm_dir.resolve();work=Path(tempfile.mkdtemp(prefix='augmentor-vm-sdk-'));guest_root=args.guest_root or ('/usr/lib/augmentor' if args.installed else '/home/beta/augmentor-desktop-candidate')
ssh=['ssh','-i',str(vm/'id_ed25519'),'-p','22487','-o','BatchMode=yes','-o','UserKnownHostsFile="'+str(vm/'known_hosts')+'"','beta@127.0.0.1']
def remote(args,data=None):
    p=subprocess.run([*ssh,shlex.join(args)],input=data,capture_output=True,text=True,timeout=30)
    if p.returncode:raise RuntimeError(p.stderr[-1500:])
    return p.stdout
def guest(action,*p):return json.loads(remote(['python3','vm-desktop-session.py',guest_root,action,*p]))
def guest_rpc(method,p=None,owner='pi:setup'):return json.loads(remote(['python3','vm-desktop-session.py',guest_root,'rpc'],json.dumps({'method':method,'owner':owner,'params':p or {}})))
def until(check,seconds=120):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        value=check()
        if value:return value
        time.sleep(.15)
    raise AssertionError('SDK desktop condition timed out')
def qmp(name,p):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(10);s.connect(os.path.relpath(vm/'qmp.sock'));f=s.makefile('rwb',buffering=0);f.readline()
        for method,args in [('qmp_capabilities',{}),(name,p)]:
            f.write((json.dumps({'execute':method,'arguments':args,'id':method})+'\n').encode())
            while True:
                v=json.loads(f.readline())
                if v.get('id')==method:assert 'error' not in v,v;break

def click(x,y):
    screen=guest('scene')['screens'][0]['geometry'];x=x*1280/screen['width'];y=y*800/screen['height']
    for px,py in [(x-2,y-2),(x,y)]:
        qmp('input-send-event',{'events':[{'type':'abs','data':{'axis':'x','value':round(px/1280*32767)}},{'type':'abs','data':{'axis':'y','value':round(py/800*32767)}}]});time.sleep(.25)
    for down in (True,False):qmp('input-send-event',{'events':[{'type':'btn','data':{'down':down,'button':'left'}}]});time.sleep(.25)

def consent():
    def window():
        scene=guest('windows')
        match=next((w for w in scene['windows'] if w['title']=='Remote control requested'),None)
        if not match:return None
        if scene['window']['id']!=match['id']:
            # The portal may open behind Kate on a repeat request. Simulate
            # the tester using Alt+Tab to select the OS consent window.
            qmp('send-key',{'keys':[{'type':'qcode','data':'alt'},{'type':'qcode','data':'tab'}],'hold-time':100});time.sleep(.5)
            return None
        return match
    until(window,35);time.sleep(1)
    # KWin can animate the dialog position when Alt+Tab raises it. Read the
    # final geometry after that transition before dispatching a human click.
    w=until(window,5);g=w['geometry']
    print(json.dumps({'consent':harness+'-'+mode,'geometry':g,'fixture':str(work)}),flush=True)
    qmp('screendump',{'filename':str(vm/('consent-'+harness+'-'+mode+'.png')),'format':'png'})
    click(g['x']+139,g['y']+184)
    qmp('screendump',{'filename':str(vm/('consent-after-'+harness+'-'+mode+'.png')),'format':'png'})
    until(lambda:guest_rpc('status').get('result',{}).get('sharing'),15)

def metadata(messages):
    for m in reversed(messages):
        if m['role']!='tool':continue
        text=m['content']
        if isinstance(text,list):text=''.join(p.get('text','') for p in text)
        try:value,_=json.JSONDecoder().raw_decode(text.lstrip())
        except (ValueError,TypeError):continue
        if isinstance(value,dict) and 'token' in value:return value
    raise AssertionError('Snapshot metadata missing from model context')
received=[];failures=[];mode='task';harness='pi'
class Model(http.server.BaseHTTPRequestHandler):
    def log_message(self,*_):pass
    def do_POST(self):
        try:
            body=json.loads(self.rfile.read(int(self.headers['content-length'])));received.append(body)
            for message in body['messages']:
                if message['role']!='tool':continue
                content=message['content']
                if isinstance(content,list):content='\n'.join(part.get('text','') for part in content)
                if content.lstrip().startswith('Error:'):
                    failures.append(harness+' '+mode+': '+content[:2000])
                    # End the deterministic model turn without issuing another
                    # action from an observation that may already be consumed.
                    self.send_response(200);self.send_header('content-type','text/event-stream');self.end_headers()
                    self.wfile.write(('data: '+json.dumps({'id':'fixture-error','object':'chat.completion.chunk','created':1,'model':'fixture','choices':[{'index':0,'delta':{'role':'assistant','content':'Desktop fixture stopped after tool failure.'},'finish_reason':'stop'}]})+'\n\ndata: [DONE]\n\n').encode())
                    return
            done=sum(m['role']=='tool' for m in body['messages']);s=None
            if done and done%2==0:s=metadata(body['messages'])
            if mode=='stop':plan=['connect','snapshot','click','snapshot','type']
            else:plan=['connect','snapshot','click','snapshot','select','snapshot','type','snapshot','save','snapshot','stop']
            if done>=len(plan):delta={'role':'assistant','content':'SDK desktop verified'};reason='stop'
            else:
                action=plan[done];args={};name='linux_desktop_'+({'snapshot':'snapshot','connect':'connect','stop':'stop'}.get(action,'action'))
                if action not in ('snapshot','connect','stop'):
                    args={'token':s['token'],'kind':{'click':'click','select':'key','type':'type','save':'key'}[action]}
                    if action=='click':
                        g=s['window']['geometry'];screen=s['screen']['geometry'];args.update(x=(g['x']+g['width']/2-screen['x'])*1280/screen['width'],y=(g['y']+g['height']/2-screen['y'])*800/screen['height'])
                    elif action=='select':args['keys']=['CTRL','A']
                    elif action=='save':args['keys']=['CTRL','S']
                    else:args['text']='S'*256 if mode=='stop' else harness.upper()+' SDK verified'
                delta={'role':'assistant','tool_calls':[{'index':0,'id':'desktop-'+str(done),'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]};reason='tool_calls'
            self.send_response(200);self.send_header('content-type','text/event-stream');self.end_headers()
            for d,r in [(delta,None),({},reason)]:self.wfile.write(('data: '+json.dumps({'id':'fixture','object':'chat.completion.chunk','created':1,'model':'fixture','choices':[{'index':0,'delta':d,'finish_reason':r}]})+'\n\n').encode())
            self.wfile.write(b'data: [DONE]\n\n')
        except Exception as e:failures.append(str(e));raise
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Model);threading.Thread(target=server.serve_forever,daemon=True).start()
os.environ.update(AUGMENTOR_PI_CONFIG=str(work/'pi-config'),AUGMENTOR_PI_STATE=str(work/'pi-state'),AUGMENTOR_SHARED_CONFIG=str(work/'shared-config'),AUGMENTOR_SHARED_STATE=str(work/'shared-state'),AUGMENTOR_SHARED_DATA=str(work/'shared-data'),XDG_RUNTIME_DIR=str(work),AUGMENTOR_DESKTOP_NO_AUTOSTART='1',PI_OFFLINE='1')
sys.path.insert(0,str(ROOT/'apps/native'))
from augmentor_linux.pi_client import PiClient
from augmentor_linux.adapters.dsh import DshAdapter
folder=work/'pi-config/agent';folder.mkdir(parents=True)
model={'id':'fixture','name':'Fixture','reasoning':False,'input':['text','image'],'contextWindow':64000,'maxTokens':4096}
(folder/'models.json').write_text(json.dumps({'providers':{'fixture':{'baseUrl':f'http://127.0.0.1:{server.server_port}/v1','api':'openai-completions','apiKey':'fixture','models':[model]}}}))
(work/'pi-config/settings.json').write_text(json.dumps({'revision':0,'defaultPreset':'danger-full-access'}))
service=None;forward=None;dsh_process=None;logs=[];pi=PiClient()
try:
    assert remote(['cat','/etc/augmentor-test-vm']).startswith('Isolated Augmentor')
    remote(['python3','-c','import sys;from pathlib import Path;Path("vm-desktop-session.py").write_text(sys.stdin.read())'],(ROOT/'release/vm-desktop-session.py').read_text())
    previous=guest_rpc('status')
    if previous['ok']:assert not previous['result']['active'];guest_rpc('shutdown');time.sleep(1)
    guest('scale','1.0')
    command=['python3','vm-desktop-session.py',guest_root,'serve']
    if args.focus_debug:command=['env','AUGMENTOR_VM_FOCUS_DEBUG=1',*command]
    if args.capture_debug:command=['env','GST_DEBUG=2,pipewiresrc:6,pipewirepool:6','GST_DEBUG_NO_COLOR=1',*command]
    log=(work/'executor.log').open('w');logs.append(log);service=subprocess.Popen([*ssh,shlex.join(command)],stdout=log,stderr=log)
    until(lambda:guest_rpc('status')['ok'],20)
    forward=subprocess.Popen([*ssh[:-1],'-N','-o','ExitOnForwardFailure=yes','-L',str(work/'augmentor-desktop.sock')+':/run/user/1000/augmentor-desktop.sock',ssh[-1]],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    until(lambda:(work/'augmentor-desktop.sock').exists(),10)
    pi.call('host.describe')
    modules=Path(os.environ['DSH_TEST_MODULES']);home=work/'dsh';profile=home/'profiles/web';profile.mkdir(parents=True);(profile/'node_modules').symlink_to(modules,target_is_directory=True)
    (profile/'package.json').write_text(json.dumps({'name':'augmentor-desktop-sdk-proof','private':True,'type':'module','dsh':{'profile':{'bundles':['@deepseek-ai/dsh-base','@deepseek-ai/dsh-web-app']}}}))
    (profile/'cordis.yml').write_text('[]\n');(profile/'cordis.patch.yml').write_text('- id: session-title-llm\n  disabled: true\n')
    preset=home/'.agent-presets/augmentor-linux';preset.mkdir(parents=True);(preset/'preset.yml').write_text('name: Desktop fixture\n');(preset/'agent.cordis.yml').write_text(yaml.safe_dump([{'id':'persona','name':'@deepseek-ai/dsh-persona','config':{'prefix':'Desktop tool fixture','complete':True,'includeRuntimeContext':False}},{'id':'desktop','name':str(ROOT/'adapters/dsh-desktop/index.mjs')}]))
    (home/'settings.yaml').write_text(yaml.safe_dump({'llm-pi-ai':{'providers':{'fixture':{'api':'openai-completions','baseURL':f'http://127.0.0.1:{server.server_port}/v1','apiKeyEnv':'AUGMENTOR_FIXTURE_KEY','models':[model]}}},'agent-default-model':{'provider':'fixture','model':'fixture'},'permission':{'defaultPreset':'danger-full-access'}}))
    with socket.socket() as p:p.bind(('127.0.0.1',0));port=p.getsockname()[1]
    log=(work/'dsh.log').open('w');logs.append(log);dsh_process=subprocess.Popen(['dsh','web','--no-open','--host','127.0.0.1','--port',str(port)],env={**os.environ,'DSH_HOME':str(home),'DSH_TELEMETRY_MODE':'DISABLED','AUGMENTOR_FIXTURE_KEY':'fixture'},stdout=log,stderr=log,start_new_session=True)
    dsh=DshAdapter(base=f'http://127.0.0.1:{port}',home=home)
    def up():
        try:
            hits=re.findall(r'token=([A-Za-z0-9_-]+)',(work/'dsh.log').read_text())
            if not hits:return False
            os.environ['AUGMENTOR_DSH_AUTH_TOKEN']=hits[-1]
            return dsh.call('host.describe')
        except Exception:return False
    until(up,30)
    evidence=[]
    for harness,engine in [('pi',pi),('dsh',dsh)]:
        if args.harness not in ('both',harness):continue
        for mode in (('task','stop') if args.case=='both' else (args.case,)):
            editor=guest('editor');until(lambda:(w:=guest('scene')['window'])['application']=='org.kde.kate' and w['pid'] not in editor['previousPids'] and 'Not Responding' not in w['title'])
            until(lambda:any('Fixture ready' in text for text in guest('editor-text')['texts']),30)
            print(json.dumps({'harness':harness,'case':mode,'accessibleEditorReady':True}),flush=True)
            sid=harness+'-'+mode;before=len(received)
            if harness=='pi':engine.call('session.create',{'sessionId':sid,'cwd':str(work),'selection':{'provider':'fixture','model':'fixture'}})
            else:
                engine.call('session.create',{'sessionId':sid,'cwd':str(work),'agentPreset':'augmentor-linux'});engine.call('session.selectModel',{'sessionId':sid,'provider':'fixture','model':'fixture'})
            engine.call('session.prompt',{'sessionId':sid,'mode':'queue','content':[{'type':'text','text':'Execute the desktop fixture.'}]});consent()
            if mode=='stop':
                until(lambda:len(received)>=before+3 and guest_rpc('status')['result']['busy'])
                def typing_started():
                    if failures:raise AssertionError('Desktop tool failed before Stop: '+str(failures))
                    return any(0<t.count('S')<256 for t in guest('editor-text')['texts'])
                until(typing_started,25)
                engine.call('session.cancel',{'sessionId':sid})
            until(lambda:not next(r for r in engine.call('session.list')['items'] if r['sessionId']==sid)['running'],150)
            assert not failures,failures
            assert not guest_rpc('status')['result']['sharing'],'Turn must release desktop control'
            images=[part['image_url']['url'] for b in received[before:] for m in b['messages'] for part in (m['content'] if isinstance(m['content'],list) else []) if part.get('type')=='image_url']
            assert images and any(base64.b64decode(i.split(',',1)[1]).startswith(b'\xff\xd8') for i in images),'Model did not receive the actual screenshot'
            if mode=='task':assert guest('file','augmentor-desktop-acceptance.txt')['text']==harness.upper()+' SDK verified\n'
            else:
                qmp('send-key',{'keys':[{'type':'qcode','data':'ctrl'},{'type':'qcode','data':'s'}],'hold-time':100});time.sleep(.5)
                value=guest('file','augmentor-desktop-acceptance.txt')['text'];assert 0<value.count('S')<256,value
                count=len(received);time.sleep(1);assert len(received)==count
            evidence.append({'harness':harness,'case':mode,'modelScreenshot':True,'externalFile':True,'sharingReleased':True});print(json.dumps(evidence[-1]),flush=True)
    (vm/'desktop-engines-proof.json').write_text(json.dumps({'fixture':str(work),'transport':'private socket forwarded to disposable VM; host autostart disabled','guestRoot':guest_root,'sdkRoot':str(ROOT),'results':evidence},indent=2)+'\n')
finally:
    # Fixture-only model requests help distinguish SDK rendering failures from
    # consent failures without preserving screenshot payloads in this log.
    (work/'model-requests.json').write_text(re.sub(r'data:image/[^\"]+', 'data:image/OMITTED',json.dumps(received,indent=2)))
    try:pi.call('host.shutdown')
    except Exception:pass
    if dsh_process:
        os.killpg(dsh_process.pid,signal.SIGTERM)
        try:dsh_process.wait(timeout=10)
        except subprocess.TimeoutExpired:os.killpg(dsh_process.pid,signal.SIGKILL);dsh_process.wait()
    try:
        active=guest_rpc('status').get('result',{}).get('owner')
        if active:guest_rpc('stop',owner=active)
        guest_rpc('shutdown')
    except Exception:pass
    if service:service.terminate();service.wait(timeout=10)
    if forward:forward.terminate();forward.wait(timeout=10)
    for log in logs:log.close()
    server.shutdown();server.server_close()
