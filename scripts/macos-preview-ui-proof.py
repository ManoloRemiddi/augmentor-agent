#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual native composer and fresh Chrome profile against the managed fixture.

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
    prepared=registrar.prepare_extension(app,'chrome',work/'support')
    profile=work/'chrome-profile';hosts=profile/'NativeMessagingHosts';hosts.mkdir(parents=True)
    (hosts/'com.augmentor.agent.json').write_text(Path(prepared['manifest']).read_text())
    import websocket
    with (out/'chrome.log').open('w') as log:
        chrome=subprocess.Popen(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '--headless=new','--no-first-run','--remote-allow-origins=*','--remote-debugging-port=0',
            '--enable-unsafe-extension-debugging','--user-data-dir='+str(profile),'about:blank'],
            env=environment,stdout=log,stderr=log)
        ws=None
        try:
            portfile=profile/'DevToolsActivePort';wait(portfile.exists)
            port=portfile.read_text().splitlines()[0]
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
                    'freshChromeNativeHost':True,'browserManagedDshChat':True,'browser':info['Browser'],
                    'extensionId':loaded['id'],'browserManualApprovalTested':False,'gatekeeperOpenAnywayTested':False}
        finally:
            if ws:ws.close()
            chrome.terminate();chrome.wait(timeout=15)
