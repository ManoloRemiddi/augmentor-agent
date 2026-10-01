#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Pinned Codex/native adapter controlling only a marked disposable Plasma VM.

Stages this checkout's desktop service separately. The local Responses provider
uses deterministic actions, not visual reasoning; actual screenshot bytes, OS
consent, saved-file contents and Stop are verified. Host desktop autostart is off.
"""
import argparse
import base64
import http.server
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import socket
import struct
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import zlib

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--vm-dir', type=Path, required=True)
p.add_argument('--port', type=int, default=22487)
a = p.parse_args(); vm = a.vm_dir.resolve(); work = Path(tempfile.mkdtemp(prefix='augmentor-codex-vm-proof-'))
guest_root = '/home/beta/augmentor-codex-candidate'
inputs = [*sorted((ROOT/'dist/codex-runtime/src').glob('*.js')), ROOT/'dist/desktop/src/index.js', *sorted((ROOT/'services/desktop').glob('*.py')), ROOT/'apps/native/augmentor_linux/adapters/codex.py', Path(__file__).resolve()]
identity = {'sourceRevision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(), 'codexVersion':json.loads((ROOT/'node_modules/@openai/codex/package.json').read_text())['version'], 'sha256':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}}
ssh = ['ssh', '-i', str(vm/'id_ed25519'), '-p', str(a.port), '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=3', '-o', 'UserKnownHostsFile='+str(vm/'known_hosts'), 'beta@127.0.0.1']
def remote(command, data=None):
    result = subprocess.run([*ssh, shlex.join(command)], input=data, capture_output=True, text=True, timeout=45)
    if result.returncode: raise RuntimeError(result.stderr[-2000:])
    return result.stdout

def guest(action, *args): return json.loads(remote(['python3', 'vm-desktop-session.py', guest_root, action, *args]))
def rpc(method, owner='codex:setup'): return json.loads(remote(['python3', 'vm-desktop-session.py', guest_root, 'rpc'], json.dumps({'method': method, 'owner': owner})))
def until(check, seconds=60):
    end = time.monotonic()+seconds
    while time.monotonic() < end:
        value = check()
        if value: return value
        time.sleep(.15)
    raise AssertionError('VM Codex proof timed out')
def qmp(method, args):
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(10); connection.connect(str(vm/'qmp.sock')); stream = connection.makefile('rwb', buffering=0); stream.readline()
        for name, parameters in [('qmp_capabilities', {}), (method, args)]:
            stream.write((json.dumps({'execute': name, 'arguments': parameters, 'id': name})+'\n').encode())
            while True:
                response = json.loads(stream.readline())
                if response.get('id') == name:
                    assert 'error' not in response, response
                    break

def key(*keys): qmp('send-key', {'keys': [{'type':'qcode','data':name} for name in keys], 'hold-time':100})
def click(x, y):
    screen = guest('scene')['screens'][0]['geometry']; x=x*1280/screen['width']; y=y*800/screen['height']
    for px,py in [(x-2,y-2),(x,y)]:
        qmp('input-send-event', {'events':[{'type':'abs','data':{'axis':'x','value':round(px/1280*32767)}},{'type':'abs','data':{'axis':'y','value':round(py/800*32767)}}]}); time.sleep(.25)
    for down in (True,False): qmp('input-send-event', {'events':[{'type':'btn','data':{'down':down,'button':'left'}}]}); time.sleep(.25)

def consent(accept):
    def dialog():
        scene=guest('windows'); window=next((w for w in scene['windows'] if w['title']=='Remote control requested'),None)
        if window and scene['window']['id']!=window['id']: key('alt','tab'); time.sleep(.5); return None
        return window
    until(dialog,40); time.sleep(1); geometry=until(dialog,5)['geometry']
    assert abs(geometry['width']-278)<2 and abs(geometry['height']-210)<2, geometry
    qmp('screendump', {'filename':str(vm/('codex-consent-'+mode+'.png')), 'format':'png'})
    click(geometry['x']+(139 if accept else 228),geometry['y']+184)

def image_answer(url):
    data=base64.b64decode(url.split(',',1)[1]); compressed=[]; offset=8; width=0
    while offset<len(data):
        size=struct.unpack('>I',data[offset:offset+4])[0]; kind=data[offset+4:offset+8]; chunk=data[offset+8:offset+8+size]
        if kind==b'IHDR': width=struct.unpack('>I',chunk[:4])[0]
        if kind==b'IDAT': compressed.append(chunk)
        offset+=size+12
    pixels=zlib.decompress(b''.join(compressed)); palette={(220,0,0):'red',(0,160,0):'green',(0,0,255):'blue',(255,220,0):'yellow',(0,0,0):'black',(255,255,255):'white'}
    return ','.join(palette[tuple(pixels[(18*(width*3+1)+1+(i*36+18)*3):(18*(width*3+1)+1+(i*36+18)*3+3)])] for i in range(4))

received=[]; failures=[]; mode='qualification'
class Model(http.server.BaseHTTPRequestHandler):
    def log_message(self,*_): pass
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['content-length']))); received.append(body)
        tools=[item for item in body['input'] if item.get('type')=='function_call_output']
        plan=['connect'] if mode=='deny' else ['connect','snapshot','click','snapshot','type'] if mode=='stop' else ['connect','snapshot','click','snapshot','select','snapshot','type','snapshot','save','snapshot']
        step=len(tools); item=None
        try:
            if mode=='qualification':
                content=body['input'][0]['content']; text=image_answer(next(part['image_url'] for part in content if part['type']=='input_image'))
            elif step>=len(plan): text='Codex desktop fixture finished.'
            else:
                action=plan[step]; args={}; name='linux_desktop_'+('action' if action in ('click','select','type','save') else action)
                if action in ('click','select','type','save'):
                    parts=tools[-1]['output']; assert isinstance(parts,list), parts
                    metadata=json.loads(next(part['text'] for part in parts if part['type']=='input_text'))
                    assert any(part['type']=='input_image' for part in parts), 'Actual screenshot missing'
                    args={'token':metadata['token'],'kind':'click' if action=='click' else 'type' if action=='type' else 'key'}
                    if action=='click':
                        geometry=metadata['window']['geometry']; screen=metadata['screen']['geometry']; size=metadata['imageSize']
                        args.update(x=(geometry['x']+geometry['width']/2-screen['x'])*size['width']/screen['width'], y=(geometry['y']+geometry['height']/2-screen['y'])*size['height']/screen['height'])
                    elif action=='select': args['keys']=['CTRL','A']
                    elif action=='save': args['keys']=['CTRL','S']
                    else: args['text']='S'*256 if mode=='stop' else 'CODEX desktop verified'
                elif step and action=='snapshot':
                    prior=tools[-1]['output']; assert isinstance(prior,str), prior
                    value=json.loads(prior); assert value.get('dispatched') or value.get('sharing'), value
                item={'id':f'{mode}-item-{step}','type':'function_call','call_id':f'{mode}-call-{step}','name':name,'arguments':json.dumps(args)}
        except Exception as error: failures.append(str(error)); text='Fixture stopped on tool failure.'
        if item is None: item={'id':mode+'-answer','type':'message','role':'assistant','status':'completed','content':[{'type':'output_text','text':text,'annotations':[]}]}
        self.send_response(200); self.send_header('content-type','text/event-stream'); self.end_headers()
        for frame in [{'type':'response.created','response':{'id':mode+str(step),'status':'in_progress','output':[]}}, {'type':'response.output_item.added','output_index':0,'item':item}, {'type':'response.output_item.done','output_index':0,'item':item}, {'type':'response.completed','response':{'id':mode+str(step),'status':'completed','output':[item]}}]:
            self.wfile.write(('data: '+json.dumps(frame)+'\n\n').encode())

assert remote(['cat','/etc/augmentor-test-vm']).startswith('Isolated Augmentor')
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Model); threading.Thread(target=server.serve_forever,daemon=True).start()
os.environ.update(XDG_RUNTIME_DIR=str(work),AUGMENTOR_DESKTOP_NO_AUTOSTART='1',AUGMENTOR_CODEX_STATE=str(work/'host'),AUGMENTOR_CODEX_SOCKET=str(work/'codex.sock'),AUGMENTOR_CODEX_NO_AUTOSTART='1')
sys.path.insert(0,str(ROOT/'apps/native'))
from augmentor_linux.adapters.codex import CodexAdapter
client=CodexAdapter(); children=[]; logs=[]; evidence=[]
try:
    remote(['python3','-c','import sys;from pathlib import Path;Path("vm-desktop-session.py").write_text(sys.stdin.read())'],(ROOT/'release/vm-desktop-session.py').read_text())
    remote(['mkdir','-p',guest_root]); archive=io.BytesIO()
    with tarfile.open(fileobj=archive,mode='w') as tar:
        for part in ('services/desktop','services/lifecycle','services/platform_support.py'): tar.add(ROOT/part,arcname=part,filter=lambda item:None if '__pycache__' in item.name else item)
    subprocess.run([*ssh,shlex.join(['tar','-xf','-','-C',guest_root])],input=archive.getvalue(),check=True)
    previous=rpc('status')
    if previous['ok'] and previous['result'].get('available',True):
        assert not previous['result']['active'] and not previous['result'].get('busy'); rpc('shutdown'); time.sleep(1)
    log=(work/'executor.log').open('w'); logs.append(log)
    service=subprocess.Popen([*ssh,shlex.join(['python3','vm-desktop-session.py',guest_root,'serve'])],stdout=log,stderr=log); children.append(service)
    until(lambda:rpc('status').get('result',{}).get('pid'),30)
    forward=subprocess.Popen([*ssh[:-1],'-N','-o','ExitOnForwardFailure=yes','-L',str(work/'augmentor-desktop.sock')+':/run/user/1000/augmentor-desktop.sock',ssh[-1]],stdout=subprocess.DEVNULL,stderr=log); children.append(forward)
    until(lambda:(work/'augmentor-desktop.sock').exists(),10)
    log=(work/'host.log').open('w'); logs.append(log)
    host=subprocess.Popen(['node',str(ROOT/'dist/codex-runtime/src/main.js')],stdout=log,stderr=log); children.append(host)
    until(lambda:(work/'codex.sock').exists(),15)
    client.configure_profile({'id':'fixture','name':'VM fixture','kind':'local','model':'fixture-model','endpoint':f'http://127.0.0.1:{server.server_port}/v1'})
    assert client.call('profiles.test',{'id':'fixture','capability':'image'})['validation']=='responses-image'
    guest('scale','1.0')
    for mode in ('deny','task','stop'):
        editor=guest('editor'); until(lambda:(window:=guest('scene')['window'])['application']=='org.kde.kate' and window['pid'] not in editor['previousPids'] and 'Not Responding' not in window['title'])
        until(lambda:any('Fixture ready' in text for text in guest('editor-text')['texts']))
        sid='codex-'+mode; before=len(received)
        client.call('session.create',{'sessionId':sid,'profileId':'fixture','cwd':str(work)})
        print(json.dumps({'case':mode,'stage':'requesting-consent','fixture':str(work)}),flush=True)
        client.call('session.prompt',{'sessionId':sid,'requestId':mode,'content':[{'type':'text','text':'Run the disposable desktop fixture.'}]}); consent(mode!='deny')
        if mode=='stop':
            def typed():
                if failures: raise AssertionError(failures)
                return any(0<text.count('S')<256 for text in guest('editor-text')['texts'])
            until(typed,40); client.call('session.cancel',{'sessionId':sid})
        until(lambda:not next(row for row in client.session_rows() if row['sessionId']==sid)['running'],150)
        until(lambda:not client.call('host.describe')['desktopActive'],20)
        assert not failures, failures
        assert not rpc('status')['result']['sharing']
        if mode=='deny': assert not any(item.get('name')=='linux_desktop_snapshot' for body in received[before:] for item in body['input'])
        else:
            images=[part['image_url'] for body in received[before:] for item in body['input'] if item.get('type')=='function_call_output' and isinstance(item.get('output'),list) for part in item['output'] if part.get('type')=='input_image']
            assert images and any(base64.b64decode(image.split(',',1)[1]).startswith(b'\xff\xd8') for image in images)
            if mode=='task': assert guest('file','augmentor-desktop-acceptance.txt')['text']=='CODEX desktop verified\n'
            else:
                key('ctrl','s'); time.sleep(.5); partial=guest('file','augmentor-desktop-acceptance.txt')['text']; assert 0<partial.count('S')<256,partial
                count=len(received); time.sleep(1); key('ctrl','s'); time.sleep(.3)
                assert guest('file','augmentor-desktop-acceptance.txt')['text']==partial and len(received)==count
        evidence.append({'case':mode,'passed':True,'sharingReleased':True,'realScreenshot':mode!='deny','externalFile':mode!='deny'}); print(json.dumps(evidence[-1]),flush=True)
    (vm/'codex-desktop-proof.json').write_text(json.dumps({'identity':identity,'fixture':str(work),'source':str(ROOT),'guestRoot':guest_root,'provider':'synthetic Responses','transport':'native adapter + pinned Codex + private forwarded desktop socket','results':evidence},indent=2)+'\n')
finally:
    (work/'model-summary.json').write_text(json.dumps({'requests':len(received),'failures':failures,'evidence':evidence},indent=2)+'\n')
    try: client.call('host.shutdown')
    except Exception: pass
    try:
        owner=rpc('status').get('result',{}).get('owner')
        if owner and owner.startswith('codex:codex-'): rpc('stop',owner)
        rpc('shutdown')
    except Exception: pass
    for child in reversed(children):
        if child.poll() is None:
            child.terminate()
            try: child.wait(timeout=10)
            except subprocess.TimeoutExpired: child.kill(); child.wait()
    for log in logs: log.close()
    server.shutdown(); server.server_close()
