#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual native composer and fresh Chromium browser against the managed fixture.

Called while macos-managed-setup-proof.py owns its temporary DSH job. No personal
browser profile, model credential or installed application is changed.
"""
import base64
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request


def verify(root, work, out):
    app = root.parents[2]
    environment = {**os.environ, 'AUGMENTOR_PYTHON':str(root/'python/bin/python3'),
                   'AUGMENTOR_PI_NODE':str(root/'node/bin/node')}
    environment.pop('QT_QPA_PLATFORM',None)
    ipc = Path(environment['XDG_RUNTIME_DIR'])/'augmentor-linux-pi-release-proof.sock'
    launch = ['open','-n','-W','--stdout',str(out/'desktop.stdout'),'--stderr',str(out/'desktop.stderr')]
    for key,value in environment.items():
        if key.startswith(('AUGMENTOR_','XDG_')):launch += ['--env',key+'='+value]
    launch += [str(app),'--args','--instance','release-proof','--ui-test-control']
    def exchange(command):
        with socket.socket(socket.AF_UNIX) as peer:
            peer.settimeout(8);peer.connect(str(ipc));peer.sendall(command.encode())
            return json.loads(peer.makefile('rb').readline(2*1024*1024))
    def wait(check,seconds=45):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            try:
                value=check()
                if value:return value
            except (OSError,ValueError):pass
            time.sleep(.2)
        raise AssertionError('Preview UI check timed out')
    def close_native(process):
        status=exchange('maintenance.close');assert status['accepted'],status
        process.wait(timeout=20)
    def desktop_check(previous=False):
        process=subprocess.Popen(launch,env=environment)
        try:
            wait(lambda:ipc.exists())
            args=[str(root/'python/bin/python3'),'-I','-B',str(root/'scripts/macos-live-chat-proof.py'),
                '--app-root',str(root),'--out',str(out/('desktop-reopened' if previous else 'desktop-first')),
                '--instance','release-proof','--marker','Managed setup reopened' if previous else 'Managed setup verified','--submit','enter' if previous else 'button',
                '--native-socket',str(ipc),'--live']
            if previous:args += ['--previous-marker','Managed setup verified']
            subprocess.run(args,env=environment,check=True,timeout=180)
        finally:close_native(process)
    desktop_check();desktop_check(True)
    # The registrar and extension content are the ones shipped in the candidate.
    spec=importlib.util.spec_from_file_location('preview_registration',root/'scripts/register-macos-browser.py')
    registrar=importlib.util.module_from_spec(spec);spec.loader.exec_module(registrar)
    browser_app=Path(os.environ.get('AUGMENTOR_PROOF_BROWSER_APP','/Applications/Google Chrome.app'))
    browser=registrar.browser_application(browser_app)
    source_directory=registrar.browser_data_directory(browser_app,Path.home()/'Library/Application Support')
    # Comet uses its default native-host location independently of --user-data-dir.
    # Isolate both Cocoa's home lookup and HOME; never register test hosts in the
    # owner's real browser or let browser background tasks use their home.
    browser_home=work/'browser-home'
    support=browser_home/'Library/Application Support'
    profile=support/source_directory.relative_to(Path.home()/'Library/Application Support')
    profile.mkdir(parents=True);(profile/'Local State').write_text('{}')
    prepared=registrar.prepare_extension(app,browser_app,support)
    assert Path(prepared['manifest']).parent==profile/'NativeMessagingHosts'
    import websocket
    with (out/'chrome.log').open('w') as log:
        chrome=subprocess.Popen([browser['executable'],
            '--headless=new','--no-first-run','--remote-allow-origins=*','--remote-debugging-port=0',
            '--enable-unsafe-extension-debugging','--user-data-dir='+str(profile),'about:blank'],
            env={**environment,'HOME':str(browser_home),'CFFIXED_USER_HOME':str(browser_home)},stdout=log,stderr=log)
        ws=None
        try:
            portfile=profile/'DevToolsActivePort';port_lines=[]
            def port_ready():
                nonlocal port_lines
                try:port_lines=portfile.read_text().splitlines()
                except FileNotFoundError:port_lines=[]
                if chrome.poll() is not None:raise RuntimeError('Chrome exited before its debugging endpoint became ready.')
                return len(port_lines)>=2 and port_lines[0].isdigit() and port_lines[1].startswith('/devtools/browser/')
            wait(port_ready)
            port=port_lines[0]
            info=json.load(urllib.request.urlopen('http://127.0.0.1:'+port+'/json/version'))
            ws=websocket.create_connection(info['webSocketDebuggerUrl'],suppress_origin=True,timeout=30)
            sequence=0
            def cdp(method,params=None,session=None):
                nonlocal sequence
                sequence+=1;identity=sequence;request={'id':identity,'method':method,'params':params or {}}
                if session:request['sessionId']=session
                ws.send(json.dumps(request))
                while True:
                    reply=json.loads(ws.recv())
                    if reply.get('id')==identity:
                        assert 'error' not in reply,reply
                        return reply.get('result',{})
            loaded=cdp('Extensions.loadUnpacked',{'path':prepared['extensionDirectory']})
            assert loaded['id']==prepared['extensionId']
            target=cdp('Target.createTarget',{'url':'chrome-extension://'+loaded['id']+'/sidepanel.html'})['targetId']
            panel=cdp('Target.attachToTarget',{'targetId':target,'flatten':True})['sessionId']
            def evaluate(expression):
                result=cdp('Runtime.evaluate',{'expression':expression,'awaitPromise':True,'returnByValue':True},panel)
                assert 'exceptionDetails' not in result,result
                return result.get('result',{}).get('value')
            wait(lambda:evaluate('typeof chrome!=="undefined" && !!chrome.runtime'))
            assert evaluate('typeof chrome.sidePanel?.setPanelBehavior === "function"'), 'Browser does not support the extension side panel'
            def status():return evaluate('chrome.runtime.sendMessage({type:"log"})')
            wait(lambda:(value if (value:=status()) and value.get('harness')=='dsh' and value.get('phase')=='ready' else None),90)
            evaluate('document.querySelector("#input").focus()')
            cdp('Input.insertText',{'text':'Reply with exactly: Managed setup verified. Do not use tools.'},panel)
            rect=evaluate('(()=>{const r=document.querySelector("#send").getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()')
            cdp('Input.dispatchMouseEvent',{'type':'mousePressed','button':'left','clickCount':1,**rect},panel)
            cdp('Input.dispatchMouseEvent',{'type':'mouseReleased','button':'left','clickCount':1,**rect},panel)
            wait(lambda:evaluate('(document.querySelector("#log").textContent.match(/Managed setup verified/g)||[]).length>=2') and not status().get('running'),120)
            shot=cdp('Page.captureScreenshot',{},panel)['data'];(out/'browser.png').write_bytes(base64.b64decode(shot))
            return {'nativeComposerButton':True,'nativeComposerEnterAfterReopen':True,'nativeConversationRestored':True,
                    'freshChromiumNativeHost':True,'browserManagedDshChat':True,'browser':info['Browser'],
                    'browserApplication':browser['name'],'browserBundleId':browser['bundleId'],'sidePanelApi':True,
                    'extensionId':loaded['id'],'browserManualApprovalTested':False,'gatekeeperOpenAnywayTested':False}
        finally:
            if ws:
                try: cdp('Browser.close')
                except (OSError, websocket.WebSocketException): pass
                finally: ws.close()
            if chrome.poll() is None:
                chrome.terminate()
                try: chrome.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    # Only the Popen-owned disposable browser. Never mask the
                    # original proof result with a hung fixture shutdown.
                    chrome.kill(); chrome.wait(timeout=10)
