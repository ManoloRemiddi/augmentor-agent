#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual Chromium extension + native bridge + real Pi SDK, deterministic model."""
import base64
import http.server
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import websocket
root=Path(__file__).resolve().parents[1]
# macOS's default per-user temporary path leaves too little room for Unix
# sockets. Match the short runtime location used by the packaged launcher.
temp=Path(tempfile.mkdtemp(prefix='augmentor-browser-proof-',dir='/tmp' if sys.platform=='darwin' else None)).resolve()
app_root=Path(os.environ.get('AUGMENTOR_PROOF_APP_ROOT',str(root)))
extension=Path(os.environ.get('AUGMENTOR_PROOF_EXTENSION',str(root/'apps/browser/extension')))
harness=os.environ.get('AUGMENTOR_PROOF_HARNESS','pi')
assert harness == 'pi'
requests=[];setup_requests=[]
class Model(http.server.BaseHTTPRequestHandler):
    def log_message(self,*_):pass
    def do_GET(self):
        page=b'<html><title>Augmentor fixture</title><input id="entry"><button id="apply" onclick="document.querySelector(\'#result\').textContent=document.querySelector(\'#entry\').value">Apply</button><p id="result">Waiting</p></html>'
        self.send_response(200);self.send_header('content-type','text/html');self.end_headers();self.wfile.write(page)
    def do_POST(self):
        data=json.loads(self.rfile.read(int(self.headers['content-length'])))
        (requests if data.get('tools') else setup_requests).append(data)
        done=sum(m['role']=='tool' for m in data['messages'])
        actions=[('browser_navigate',{'url':f'http://127.0.0.1:{server.server_port}/fixture'}),('browser_snapshot',{}),('browser_type',{'selector':'#entry','text':'VERIFIED BROWSER'}),('browser_click',{'selector':'#apply'}),('browser_snapshot',{})]
        if os.environ.get('AUGMENTOR_PROOF_ONBOARDING') and any('Set up shared Hindsight' in str(m.get('content','')) for m in data['messages']):
            if done==0:
                code="import sys,json;sys.path.insert(0,"+repr(str(root/'apps/native'))+");from augmentor_linux.prompt_client import PromptClient;print(json.dumps(PromptClient().call('memory.describe')))"
                delta={'role':'assistant','tool_calls':[{'index':0,'id':'setup-inspect','type':'function','function':{'name':'bash','arguments':json.dumps({'command':'python3 -c '+shlex.quote(code)})}}]};reason='tool_calls'
            else:delta={'role':'assistant','content':'I checked your shared memory configuration. Hindsight is not connected. Would you like me to install it locally or connect an existing service?'};reason='stop'
        elif not data.get('tools'):delta={'role':'assistant','content':'READY'};reason='stop'
        elif done<len(actions):
            name,args=actions[done];delta={'role':'assistant','tool_calls':[{'index':0,'id':'call-'+str(done),'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]};reason='tool_calls'
        else:delta={'role':'assistant','content':'VERIFIED BROWSER'};reason='stop'
        self.send_response(200);self.send_header('content-type','text/event-stream');self.end_headers()
        for value,finish in [(delta,None),({},reason)]:
            self.wfile.write(('data: '+json.dumps({'id':'proof','object':'chat.completion.chunk','created':1,'model':'test','choices':[{'index':0,'delta':value,'finish_reason':finish}]})+'\n\n').encode())
        self.wfile.write(b'data: [DONE]\n\n')
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Model);threading.Thread(target=server.serve_forever,daemon=True).start()
env={**os.environ,'XDG_CONFIG_HOME':str(temp/'xdg'),'AUGMENTOR_PI_CONFIG':str(temp/'pi-config'),'AUGMENTOR_PI_STATE':str(temp/'pi-state'),'AUGMENTOR_SHARED_DATA':str(temp/'shared-data'),'AUGMENTOR_SHARED_STATE':str(temp/'shared-state')}
if os.environ.get('AUGMENTOR_PROOF_ONBOARDING'):
    (temp/'runtime').mkdir(mode=0o700);env.update(XDG_RUNTIME_DIR=str(temp/'runtime'),QT_QPA_PLATFORM='offscreen',AUGMENTOR_PYTHON=str(root/'.venv/bin/python'))
(temp/'runtime').mkdir(mode=0o700,exist_ok=True)
env.update(XDG_RUNTIME_DIR=str(temp/'runtime'),AUGMENTOR_PI_SOCKET=str(temp/'pi.sock'),PYTHONDONTWRITEBYTECODE='1')
config=temp/'pi-config';(config/'agent').mkdir(parents=True)
if not os.environ.get('AUGMENTOR_PROOF_FRESH'):(config/'agent/models.json').write_text(json.dumps({'providers':{'test':{'baseUrl':f'http://127.0.0.1:{server.server_port}/v1','api':'openai-completions','apiKey':'test','models':[{'id':'test','name':'Test','reasoning':False,'input':['text'],'contextWindow':32000,'maxTokens':2048}]}}}))
if not os.environ.get('AUGMENTOR_PROOF_FRESH'):(config/'settings.json').write_text(json.dumps({'revision':0,'defaultPreset':'danger-full-access','pinned':[],'hidden':[],'defaultModel':{'provider':'test','model':'test'}}))
launcher=temp/'native-host';launcher.write_text('#!/bin/sh\nexec '+shlex.quote(str(app_root/'node/bin/node') if (app_root/'node/bin/node').exists() else subprocess.check_output(['which','node'],text=True).strip())+' '+shlex.quote(str(app_root/'apps/browser/native-host.mjs'))+' "$@"\n');launcher.chmod(0o700)
if os.environ.get('AUGMENTOR_PROOF_NATIVE_HOST'):launcher=Path(os.environ['AUGMENTOR_PROOF_NATIVE_HOST'])
manifest=temp/'profile/NativeMessagingHosts/com.augmentor.agent.json';manifest.parent.mkdir(parents=True)
# Public manifest key gives a stable extension ID in all test profiles.
key=json.loads((extension/'manifest.json').read_text())['key']
import hashlib
ext_id=''.join(chr(ord('a')+int(n,16)) for n in hashlib.sha256(base64.b64decode(key)).hexdigest()[:32])
manifest.write_text(json.dumps({'name':'com.augmentor.agent','description':'Augmentor proof','path':str(launcher),'type':'stdio','allowed_origins':['chrome-extension://'+ext_id+'/']}))
log=(temp/'chrome.log').open('w');chrome=subprocess.Popen([os.environ.get('AUGMENTOR_PROOF_BROWSER_BINARY','chromium'),*([] if os.environ.get('AUGMENTOR_PROOF_HEADED') else ['--headless=new']),*(['--no-sandbox','--disable-gpu','--ozone-platform=x11'] if sys.platform=='linux' else []),'--no-first-run','--remote-allow-origins=*','--remote-debugging-port=0','--enable-unsafe-extension-debugging','--user-data-dir='+str(temp/'profile'),'about:blank'],env=env,stdout=log,stderr=log)
ws=None;seq=0
try:
    portfile=temp/'profile/DevToolsActivePort'
    for _ in range(100):
        if portfile.exists():break
        time.sleep(.05)
    port=portfile.read_text().splitlines()[0]
    info=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/version'));ws=websocket.create_connection(info['webSocketDebuggerUrl'],suppress_origin=True,timeout=20)
    def cdp(method,params={},session=None):
        global seq
        seq+=1;identity=seq;msg={'id':identity,'method':method,'params':params}
        if session:msg['sessionId']=session
        ws.send(json.dumps(msg))
        while True:
            reply=json.loads(ws.recv())
            if reply.get('method')=='Page.javascriptDialogOpening' and os.environ.get('AUGMENTOR_PROOF_MEMORY'):
                assert reply['params']['message']=='Delete this source document and its associated memories from Hindsight?',reply
                seq+=1;ws.send(json.dumps({'id':seq,'method':'Page.handleJavaScriptDialog','params':{'accept':True},'sessionId':reply['sessionId']}))
            if reply.get('id')==identity:
                if 'error' in reply:raise AssertionError(reply['error'])
                return reply.get('result',{})
    result=cdp('Extensions.loadUnpacked',{'path':str(extension)});assert result['id']==ext_id
    def worker():
        for _ in range(100):
            targets=cdp('Target.getTargets')['targetInfos']
            target=next((t for t in targets if t['type']=='service_worker' and ext_id in t['url']),None)
            if target:return cdp('Target.attachToTarget',{'targetId':target['targetId'],'flatten':True})['sessionId']
            time.sleep(.05)
        raise AssertionError('Extension worker did not start')
    def evaluate(expression,session):
        r=cdp('Runtime.evaluate',{'expression':expression,'awaitPromise':True,'returnByValue':True},session)
        if 'exceptionDetails' in r:raise AssertionError(r['exceptionDetails'])
        return r.get('result',{}).get('value')
    target=cdp('Target.createTarget',{'url':f'chrome-extension://{ext_id}/sidepanel.html'})['targetId']
    panel=cdp('Target.attachToTarget',{'targetId':target,'flatten':True})['sessionId']
    cdp('Page.enable',{},panel)
    for _ in range(100):
        if evaluate("typeof chrome !== 'undefined' && !!chrome.runtime",panel):break
        time.sleep(.05)
    assert evaluate("typeof chrome !== 'undefined' && !!chrome.runtime",panel),evaluate("({url:location.href,title:document.title,text:document.body?.innerText})",panel)
    def send(kind,payload={}):return evaluate('chrome.runtime.sendMessage('+json.dumps({'type':kind,**payload})+')',panel)
    # Fresh profiles now default to the shared DSH agent. This fixture explicitly
    # qualifies Pi before its later DSH setup/switch assertions.
    assert send('harness/select',{'harness':harness})['ok']
    end=time.monotonic()+60
    while time.monotonic()<end:
        status=send('log')
        if status and status.get('harness')==harness and status.get('phase') in ('ready','needs-setup'):break
        time.sleep(.15)
    assert status.get('phase') in ('ready','needs-setup'),status
    assert status.get('harness')==harness,status
    def click(selector,scroll=True):
        rect=evaluate("(()=>{const e=document.querySelector("+json.dumps(selector)+");if(!e)throw Error('Missing '+"+json.dumps(selector)+");"+("e.scrollIntoView({block:'center'});" if scroll else "")+"const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()",panel)
        cdp('Input.dispatchMouseEvent',{'type':'mousePressed','button':'left','clickCount':1,**rect},panel)
        cdp('Input.dispatchMouseEvent',{'type':'mouseReleased','button':'left','clickCount':1,**rect},panel)
    def fill(selector,text):
        evaluate("(()=>{const e=document.querySelector("+json.dumps(selector)+");e.focus();e.select()})()",panel)
        cdp('Input.insertText',{'text':text},panel)
    def until(fn,seconds=12):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            value=fn()
            if value:return value
            time.sleep(.1)
        raise AssertionError('Timed out waiting for browser condition: '+str(evaluate('document.body.innerText.slice(-1600)',panel)))
    def button(label):
        evaluate('Array.from(document.querySelectorAll("section:not([hidden]) dialog button")).find(b=>b.textContent==='+json.dumps(label)+').id="proof-action"',panel);click('#proof-action');evaluate('document.querySelector("#proof-action")?.removeAttribute("id")',panel)
    chat_panel=panel
    settings_target=None
    def open_settings(section):
        global panel,settings_target
        panel=chat_panel
        click('#settings')
        def find_settings():
            return next((t for t in cdp('Target.getTargets')['targetInfos'] if '/settings.html' in t['url']),None)
        settings_target=until(find_settings)['targetId']
        panel=cdp('Target.attachToTarget',{'targetId':settings_target,'flatten':True})['sessionId']
        cdp('Page.enable',{},panel)
        until(lambda:evaluate('!!document.querySelector("#nav-'+section+'")',panel))
        click('#nav-'+section)
        if section not in ('appearance','memory'):
            until(lambda:evaluate('!!document.querySelector("#section-'+section+' dialog[open]")',panel))
            if section in ('models','harnesses'):
                if not evaluate('document.querySelector("#section-'+section+' .advanced").open',panel):click('#section-'+section+' .advanced > summary')
        return panel
    def back_to_chat():
        global panel
        panel=chat_panel;cdp('Target.activateTarget',{'targetId':target})
    if os.environ.get('AUGMENTOR_PROOF_SETTINGS'):
        from proof_browser_settings import prove
        evidence=prove(root,temp,cdp,evaluate,click,fill,until,send,open_settings,back_to_chat,chat_panel)
        (root/'outputs/browser-settings-proof.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence),flush=True)
        raise SystemExit(0)
    if os.environ.get('AUGMENTOR_PROOF_DSH_SETUP_ONLY'):
        from proof_browser_dsh_setup import prove
        evidence=prove(root,temp,panel,cdp,evaluate,click,fill,button,until,send,server.server_port,open_settings,back_to_chat)
        (root/'outputs/browser-dsh-setup-proof.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence),flush=True)
        raise SystemExit(0)
    if os.environ.get('AUGMENTOR_PROOF_FRESH'):
        open_settings('models')
        until(lambda:evaluate('!!document.querySelector(".model-setup[open]")',panel))
        click('.model-setup details summary')
        fill('input[aria-label="Connection name"]','Fixture')
        fill('input[aria-label="Endpoint URL"]',f'http://127.0.0.1:{server.server_port}/v1')
        fill('input[aria-label="API key"]','literal-!$-fixture-key')
        fill('input[aria-label="Model ID"]','test')
        button('Check connection')
        until(lambda:evaluate('Array.from(document.querySelectorAll("section:not([hidden]) dialog button")).some(b=>b.textContent==="Save and use model"&&!b.disabled)',panel))
        assert len(setup_requests)==1 and not requests
        assert not (config/'agent/models.json').exists()
        fill('input[aria-label="Model ID"]','test-again')
        assert evaluate('Array.from(document.querySelectorAll("section:not([hidden]) dialog button")).find(b=>b.textContent==="Save and use model").disabled',panel)
        fill('input[aria-label="Model ID"]','test');button('Check connection')
        until(lambda:evaluate('Array.from(document.querySelectorAll("section:not([hidden]) dialog button")).some(b=>b.textContent==="Save and use model"&&!b.disabled)',panel))
        evaluate('(()=>{const e=document.querySelector('+json.dumps('select[aria-label="Approval mode"]')+');e.value="danger-full-access";e.dispatchEvent(new Event("change"))})()',panel)
        button('Save and use model');until(lambda:send('log').get('phase')=='ready',30)
        assert (config/'agent/models.json').stat().st_mode&0o777==0o600
        assert len(setup_requests)==2 and not requests
        back_to_chat()
    fill('#input','Test the browser fixture.');click('#send')
    end=time.monotonic()+35
    while time.monotonic()<end:
        status=send('log')
        if not status.get('running') and any('VERIFIED BROWSER' in json.dumps(row) for row in status['log'] if row.get('kind')=='event'):break
        time.sleep(.1)
    targets=cdp('Target.getTargets')['targetInfos'];page=next(t for t in targets if t['url'].endswith('/fixture'))
    page_session=cdp('Target.attachToTarget',{'targetId':page['targetId'],'flatten':True})['sessionId']
    assert evaluate("document.querySelector('#result').textContent",page_session)=='VERIFIED BROWSER'
    assert len(requests)==6,len(requests)
    assert not evaluate("!!document.querySelector('#harness-picker')",panel)
    cdp('Target.activateTarget',{'targetId':target})
    # Real mouse actions, real OS clipboard in a separate X session.
    until(lambda:evaluate("document.querySelectorAll('.msg-branch').length > 0 && document.querySelectorAll('.msg-edit').length === 1",panel))
    for selector,expected in [(".user .msgaction",'Test the browser fixture.'),(".assistant .msgaction",'VERIFIED BROWSER')]:
        # Renderer's message blocks use role classes; do not invoke handlers.
        if not evaluate('!!document.querySelector('+json.dumps(selector)+')',panel):
            selector='.msgaction' if expected.startswith('Test') else '.msgactions:last-child button[aria-label="Copy"]'
        evaluate('document.querySelector('+json.dumps(selector)+').scrollIntoView({block:"center"})',panel)
        before=evaluate('document.querySelector("#log").scrollTop',panel)
        click(selector,False)
        until(lambda:evaluate('!!document.querySelector("button.copied")',panel))
        if os.environ.get('AUGMENTOR_PROOF_HEADED'):
            actual=subprocess.check_output(['pbpaste'] if sys.platform=='darwin' else ['xclip','-selection','clipboard','-o'],text=True,timeout=5)
        else:actual=evaluate('navigator.clipboard.readText()',panel)
        assert actual==expected,(actual,expected)
        assert evaluate('document.querySelector("#log").scrollTop',panel)==before
        time.sleep(2.2)  # Include the two-second idle poll as well as tick expiry.
        assert evaluate('document.querySelector("#log").scrollTop',panel)==before
        assert not evaluate('!!document.querySelector("button.copied")',panel)
    original=send('log')['sessionId']
    import sys
    sys.path.insert(0,str(app_root/'apps/native'));os.environ.update({k:v for k,v in env.items() if k.startswith('AUGMENTOR_')})
    from augmentor_linux.pi_client import PiClient
    from augmentor_linux.prompt_client import PromptClient
    runtime=PiClient();prompts=PromptClient()
    parent=runtime.call('session.history',{'sessionId':original,'maxMessages':100})
    click('.msg-branch');child=until(lambda:(v if (v:=send('log')['sessionId'])!=original else None))
    assert runtime.call('session.history',{'sessionId':original,'maxMessages':100})==parent
    fill('#input','Continue after the verified tools.');click('#send')
    until(lambda:len(requests)==7 and not send('log')['running'])
    assert sum(m['role']=='tool' for m in requests[-1]['messages'])==5
    until(lambda:evaluate('document.querySelectorAll(".msg-edit").length===1',panel))
    click('.msg-edit');assert evaluate('document.querySelector("#input").value',panel)=='Continue after the verified tools.'
    fill('#input','Revised continuation.');click('#send')
    until(lambda:len(requests)==8 and not send('log')['running'])
    edited=send('log')['sessionId'];assert edited not in (child,original)
    sent=[m['content'] if isinstance(m['content'],str) else ''.join(p.get('text','') for p in m['content']) for m in requests[-1]['messages'] if m['role']=='user']
    assert 'Revised continuation.' in sent and 'Continue after the verified tools.' not in sent,sent
    assert sum(m['role']=='tool' for m in requests[-1]['messages'])==5
    assert runtime.call('session.history',{'sessionId':original,'maxMessages':100})==parent
    until(lambda:evaluate('document.querySelectorAll(".msg.user").length===2',panel))
    previous_pid=runtime.call('host.describe')['pid'];runtime.call('host.shutdown')
    def previous_exited():
        if sys.platform=='darwin':
            result=subprocess.run(['ps','-p',str(previous_pid),'-o','stat='],capture_output=True,text=True,check=False)
            return result.returncode==1 or (result.returncode==0 and result.stdout.strip().startswith('Z'))
        try:return Path('/proc',str(previous_pid),'stat').read_text().rsplit(')',1)[1].split()[0]=='Z'
        except FileNotFoundError:return True
    # Minimal container PID 1 may not reap the detached runtime. A zombie has
    # exited and released its files/leases; it cannot replay an action.
    until(previous_exited,10)
    until(lambda:(v:=send('log')).get('phase')=='ready' and v.get('sessionId')==edited,30)
    assert runtime.call('host.describe')['pid']!=previous_pid
    assert len(requests)==8
    # Prompt editor writes literals; an independent Python client observes edits.
    open_settings('prompts')
    fill('section:not([hidden]) dialog input','proof');fill('section:not([hidden]) dialog textarea','Rewrite: ')
    evaluate('document.querySelector("section:not([hidden]) dialog textarea").setSelectionRange(9,9)',panel)
    def button(label):
        evaluate('Array.from(document.querySelectorAll("section:not([hidden]) dialog button")).find(b=>b.textContent==='+json.dumps(label)+').id="proof-action"',panel);click('#proof-action');evaluate('document.querySelector("#proof-action")?.removeAttribute("id")',panel)
    button('Insert clipboard');assert evaluate('document.querySelector("section:not([hidden]) dialog textarea").value',panel)=='Rewrite: [clipboard]'
    button('Save');until(lambda:len(prompts.call('prompts.list')['prompts'])==1)
    until(lambda:evaluate('document.querySelector("section:not([hidden]) dialog p").textContent==="Prompt saved." && !document.querySelector("section:not([hidden]) dialog input").disabled',panel))
    row=prompts.call('prompts.list')['prompts'][0];assert row['content']=='Rewrite: [clipboard]'
    evaluate('(()=>{const e=document.querySelector("section:not([hidden]) dialog select");e.value='+json.dumps(row['id'])+';e.dispatchEvent(new Event("change"))})()',panel)
    fill('section:not([hidden]) dialog textarea','My unsaved draft')
    prompts.call('prompts.save',{'id':row['id'],'name':'proof-renamed','content':'Rewrite: [clipboard]','expectedRevision':row['revision']})
    until(lambda:'proof-renamed' in evaluate('document.querySelector("section:not([hidden]) dialog select").textContent',panel))
    button('Save');until(lambda:'revision' in evaluate('document.querySelector("section:not([hidden]) dialog p").textContent',panel).lower() or 'changed' in evaluate('document.querySelector("section:not([hidden]) dialog p").textContent',panel).lower())
    assert evaluate('document.querySelector("section:not([hidden]) dialog textarea").value',panel)=='My unsaved draft'
    back_to_chat()
    copied='Literal [clipboard] inside clipboard'
    if os.environ.get('AUGMENTOR_PROOF_HEADED'):subprocess.run(['pbcopy'] if sys.platform=='darwin' else ['xclip','-selection','clipboard'],input=copied,text=True,check=True)
    else:evaluate('navigator.clipboard.writeText('+json.dumps(copied)+')',panel)
    evaluate('window.promptPointerEvents=[];for(const type of ["mousedown","mouseup","click","blur"]){document.addEventListener(type,event=>{const e=event.target;if(window.promptPointerEvents.length<30)window.promptPointerEvents.push({type,tag:e.tagName,id:e.id,classes:typeof e.className==="string"?e.className:"",x:event.clientX,y:event.clientY})},true)}',panel)
    fill('#input','/proof-renamed')
    # Hidden menus retain their buttons. Wait for an actual pointer target,
    # not merely a DOM node whose bounding rectangle can still be (0, 0).
    until(lambda:evaluate('(()=>{const m=document.querySelector("#prompt-completions"),b=m.querySelector("button");if(m.hidden||!b)return false;const r=b.getBoundingClientRect();return r.width>0&&r.height>0&&b.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))})()',panel))
    if os.environ.get('AUGMENTOR_PROOF_PROMPT_REFRESH'):
        rect=evaluate('(()=>{window.pressedCompletion=document.querySelector("#prompt-completions button");const r=window.pressedCompletion.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()',panel)
        evaluate('window.promptPressPoint='+json.dumps(rect)+';window.promptHitBefore=document.elementFromPoint(window.promptPressPoint.x,window.promptPressPoint.y)?.id',panel)
        cdp('Input.dispatchMouseEvent',{'type':'mousePressed','button':'left','clickCount':1,**rect},panel)
        evaluate('document.querySelector("#input").dispatchEvent(new Event("input",{bubbles:true}))',panel)
        assert evaluate('window.pressedCompletion.isConnected && window.pressedCompletion===document.querySelector("#prompt-completions button")',panel),'Refresh detached the pressed completion'
        cdp('Input.dispatchMouseEvent',{'type':'mouseReleased','button':'left','clickCount':1,**rect},panel)
    else:click('#prompt-completions button',False)
    try:
        until(lambda:evaluate('document.querySelector("#input").value',panel)=='Rewrite: '+copied)
    except AssertionError:
        # Keep clipboard contents private if another application changed them.
        diagnostic=evaluate('({focused:document.hasFocus(),activeElement:document.activeElement?.id,inputLength:document.querySelector("#input").value.length,inputStillTrigger:document.querySelector("#input").value==="/proof-renamed",completionCount:document.querySelectorAll("#prompt-completions button").length})',panel)
        if sys.platform=='darwin':diagnostic['clipboardStillFixture']=subprocess.check_output(['pbpaste'],text=True)==copied
        diagnostic['pointer']=evaluate('({events:window.promptPointerEvents,point:window.promptPressPoint,hitBefore:window.promptHitBefore,menuHidden:document.querySelector("#prompt-completions").hidden})',panel)
        print('Prompt expansion diagnostic: '+json.dumps(diagnostic),flush=True)
        raise
    assert len(requests)==8
    open_settings('support');until(lambda:evaluate('!!document.querySelector(".support-dialog textarea")?.value',panel))
    support=json.loads(evaluate('document.querySelector(".support-dialog textarea").value',panel))
    assert support['schema']=='augmentor-support/1' and support['release']['version']==json.loads((extension/'manifest.json').read_text())['version']
    for private in [copied,'My unsaved draft',str(temp),'VERIFIED BROWSER']:assert private not in json.dumps(support)
    downloads=temp/'downloads';downloads.mkdir(exist_ok=True);cdp('Browser.setDownloadBehavior',{'behavior':'allow','downloadPath':str(downloads)})
    button('Save report');until(lambda:(downloads/'augmentor-support.json').exists());assert json.loads((downloads/'augmentor-support.json').read_text())==support
    back_to_chat()
    memory_verified=None
    if os.environ.get('AUGMENTOR_PROOF_MEMORY'):
        from proof_browser_memory import prove
        memory_verified=prove(root,temp,panel,cdp,evaluate,click,fill,button,until,send,prompts,open_settings,back_to_chat)
    # A second engine uses the same rendered surface and native host.
    dsh_verified=False
    if os.environ.get('AUGMENTOR_PROOF_DSH'):
        assert send('harness/select',{'harness':'dsh'})['ok']
        until(lambda:(v:=send('log')).get('phase')=='ready' and v.get('harness')=='dsh',30)
        catalog=send('models');models=catalog.get('models',catalog.get('groups',[]))
        local=next(m for g in models for m in g['models'] if m['model']=='Qwen3.8-27B-UD-Q6_K_XL')
        changed=send('model',{'provider':local['provider'],'model':local['model']});assert changed.get('ok'),changed
        fill('#input',f'Use only your browser tools. Navigate to http://127.0.0.1:{server.server_port}/fixture . Type DSH VERIFIED BROWSER into the input with selector #entry, click #apply, inspect #result and report its exact contents. Do not use bash.')
        click('#send');until(lambda:send('log').get('running'),20)
        until(lambda:not send('log').get('running'),150)
        targets=cdp('Target.getTargets')['targetInfos'];dsh_page=next(t for t in targets if t['url'].endswith('/fixture'))
        ds=cdp('Target.attachToTarget',{'targetId':dsh_page['targetId'],'flatten':True})['sessionId']
        assert evaluate("document.querySelector('#result').textContent",ds)=='DSH VERIFIED BROWSER',send('log')
        assert send('log')['model']['model']==local['model']
        assert send('log')['capabilities']['branch'] is True
        until(lambda:evaluate('!!document.querySelector(".msg-edit") && !!document.querySelector(".msg-branch")',panel))
        from augmentor_linux.adapters.dsh import DshAdapter
        from sys import path as module_path
        module_path.insert(0,str(root/'services'))
        from dsh.branch import history as dsh_history
        dsh=DshAdapter();source=send('log')['sessionId'];source_history=dsh_history(dsh.call,source)
        evaluate('Array.from(document.querySelectorAll(".msg-branch")).at(-1).id="dsh-final-branch"',panel)
        click('#dsh-final-branch');branched=until(lambda:(v if (v:=send('log')['sessionId'])!=source else None))
        assert dsh_history(dsh.call,source)==source_history
        fill('#input','Reply exactly DSH BRANCH CONTINUED. Do not use tools.');click('#send')
        until(lambda:send('log')['running'],20);until(lambda:not send('log')['running'],90)
        until(lambda:evaluate('document.querySelectorAll(".msg-edit").length===1',panel))
        click('.msg-edit');assert evaluate('document.querySelector("#input").value',panel)=='Reply exactly DSH BRANCH CONTINUED. Do not use tools.'
        fill('#input','Reply exactly DSH EDIT VERIFIED. Do not use tools.');click('#send')
        until(lambda:send('log')['sessionId'] not in (source,branched),20)
        until(lambda:send('log')['running'],20);until(lambda:not send('log')['running'],90)
        edited_history=dsh_history(dsh.call,send('log')['sessionId'])
        texts=[json.dumps(e['data']) for e in edited_history if e['type']=='user/message']
        assert any('DSH EDIT VERIFIED' in t for t in texts) and not any('DSH BRANCH CONTINUED' in t for t in texts),texts
        assert dsh_history(dsh.call,source)==source_history
        assert any(e['type']=='tool/result' for e in edited_history),'Branch dropped browser tool context'
        assert evaluate('document.querySelector("#log").textContent.includes("DSH EDIT VERIFIED")',panel)
        assert prompts.call('prompts.list')['prompts'][0]['name']=='proof-renamed'
        dsh_verified=True
    shot=cdp('Page.captureScreenshot' ,{},panel)['data'];(root/'outputs').mkdir(exist_ok=True);(root/'outputs/browser-composable.png').write_bytes(base64.b64decode(shot))
    proof={'engine':'real Pi SDK','model':'deterministic local fixture','browser':info['Browser'],'navigateSnapshotTypeClick':True,'actualPageResultVerified':True,'dshRealLocalModelBrowser':dsh_verified,'copyClipboardAndScroll':True,'reconnectWithoutReplay':True,'branchToolContext':True,'editResubmitsOnce':True,'sharedPromptsConflictAndClipboard':True,'memory':memory_verified,'appRoot':str(app_root),'extensionRoot':str(extension),'supportReportDownloadedAndPrivate':True,'promptRefreshDuringClick':bool(os.environ.get('AUGMENTOR_PROOF_PROMPT_REFRESH')),'freshBrowserSetup':bool(os.environ.get('AUGMENTOR_PROOF_FRESH')),'setupRequests':len(setup_requests),'modelRequests':len(requests),'isolatedState':str(temp)}
    (root/'outputs/browser-composable-proof.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof),flush=True)
finally:
    if os.environ.get('AUGMENTOR_PROOF_ONBOARDING'):
        import socket
        try:
            with socket.socket(socket.AF_UNIX) as client:
                client.settimeout(3);client.connect(str(temp/'runtime/augmentor-linux-pi.sock'));client.sendall(b'maintenance.close');reply=json.loads(client.recv(4096))
                if not reply.get('accepted'):
                    import signal
                    os.kill(reply['pid'],signal.SIGTERM)
        except OSError:pass
    if ws:ws.close()
    chrome.terminate();chrome.wait(timeout=10);server.shutdown()
    # Stop only the isolated runtime, never the user's Pi host.
    import sys
    sys.path.insert(0,str(app_root/'apps/native'));os.environ.update({k:v for k,v in env.items() if k.startswith('AUGMENTOR_')})
    try:
        if os.environ.get('AUGMENTOR_PROOF_DSH_SETUP_ONLY'):raise RuntimeError('No Pi task started in this proof')
        from augmentor_linux.pi_client import PiClient
        c=PiClient();c.call('host.shutdown')
    except Exception:pass
    # Failed startup may leave a different isolated harness alive, and the
    # prompt daemon also owns a package lease. Never leave either test owner
    # holding installed-product files after the fixture browser closes.
    import signal
    # Reach only the private fixture socket; do not autostart a daemon during
    # cleanup. This also works on macOS, where /proc is unavailable.
    import socket
    try:
        with socket.socket(socket.AF_UNIX) as connection:
            connection.settimeout(3)
            connection.connect(str(temp/'shared-state/prompts.sock'))
            connection.sendall(b'{"protocol":"augmentor-prompts/1","id":"cleanup","method":"host.describe","params":{}}\n')
            with connection.makefile('rb') as reader:
                response=json.loads(reader.readline(65536))
            if response.get('id')=='cleanup' and response.get('result',{}).get('protocol')=='augmentor-prompts/1':
                os.kill(response['result']['pid'],signal.SIGTERM)
    except (OSError,ValueError,KeyError):pass
    for process in (Path('/proc').iterdir() if sys.platform=='linux' else []):
        if not process.name.isdigit() or int(process.name)==os.getpid():continue
        try:
            if process.stat().st_uid!=os.getuid():continue
            process_env=dict(item.split(b'=',1) for item in (process/'environ').read_bytes().split(b'\0') if b'=' in item)
            if process_env.get(b'AUGMENTOR_SHARED_STATE')!=str(temp/'shared-state').encode():continue
            arguments=(process/'cmdline').read_bytes().split(b'\0')
            owned=any(arg.endswith((b'/dist/runtime/src/main.js',b'/services/prompt-library/service.py')) for arg in arguments)
            if owned:os.kill(int(process.name),signal.SIGTERM)
        except (OSError,ValueError):pass
