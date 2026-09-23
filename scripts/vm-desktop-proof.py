#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Deterministic desktop control on a disposable full Plasma Wayland QEMU VM.

Default tests installed code. --source stages the candidate executor separately;
its evidence explicitly identifies that limit. No access to the user's desktop.
"""
import argparse
import base64
import io
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import tarfile
import time

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',action='store_true');p.add_argument('--port',type=int,default=22487);p.add_argument('--scale',type=float,choices=(1,1.25,1.5),default=1)
p.add_argument('--vm-dir',type=Path,default=ROOT/'outputs/desktop-vm')
p.add_argument('--guest-root',help='Explicit staged source root in the disposable VM')
p.add_argument('--capture-count',type=int,default=0,help='Additional consecutive captures for reliability diagnostics')
p.add_argument('--capture-debug',action='store_true',help='Record PipeWire/GStreamer diagnostics in the disposable VM executor log')
a=p.parse_args()
if not 0<=a.capture_count<=1000:p.error('--capture-count must be between 0 and 1000')
vm=a.vm_dir.resolve();ssh=['ssh','-i',str(vm/'id_ed25519'),'-p',str(a.port),'-o','BatchMode=yes','-o','UserKnownHostsFile="'+str(vm/'known_hosts')+'"','beta@127.0.0.1']
root=a.guest_root or ('/home/beta/augmentor-desktop-candidate' if a.source else '/usr/lib/augmentor')
def remote(command,data=None,timeout=120):
    r=subprocess.run([*ssh,shlex.join(command)],input=data,text=True,capture_output=True,timeout=timeout)
    if r.returncode:raise RuntimeError(r.stderr[-2000:])
    return r.stdout
def guest(action,*rest):return json.loads(remote(['python3','vm-desktop-session.py',root,action,*rest]))
def rpc(method,params=None,owner='pi:acceptance'):
    return json.loads(remote(['python3','vm-desktop-session.py',root,'rpc'],json.dumps({'method':method,'owner':owner,'params':params or {}})))
def okay(response):assert response['ok'],response;return response['result']
def until(check,seconds=30):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        value=check()
        if value:return value
        time.sleep(.2)
    raise AssertionError('Desktop acceptance condition timed out')
def qmp(name,args):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(10);s.connect(os.path.relpath(vm/'qmp.sock'))
        f=s.makefile('rwb',buffering=0);assert 'QMP' in json.loads(f.readline())
        for method,params in [('qmp_capabilities',{}),(name,args)]:
            f.write((json.dumps({'execute':method,'arguments':params,'id':method})+'\n').encode())
            while True:
                response=json.loads(f.readline())
                if response.get('id')==method:assert 'error' not in response,response;break
        return response['return']
def click(x,y):
    # QEMU deduplicates unchanged tablet values. KWin can reposition its cursor
    # between sessions, so force both axes to change before the observed point.
    for px,py in [(x-2,y-2),(x,y)]:
        qmp('input-send-event',{'events':[{'type':'abs','data':{'axis':'x','value':round(px/1280*32767)}},{'type':'abs','data':{'axis':'y','value':round(py/800*32767)}}]});time.sleep(.25)
    for down in (True,False):
        qmp('input-send-event',{'events':[{'type':'btn','data':{'down':down,'button':'left'}}]});time.sleep(.25)
def key(*keys):qmp('send-key',{'keys':[{'type':'qcode','data':k} for k in keys],'hold-time':100})
def logical_click(x,y):
    screen=guest('scene')['screens'][0]['geometry'];click(x*1280/screen['width'],y*800/screen['height'])
def stop_click():
    pid=okay(rpc('status'))['pid'];scene=guest('scene');banner=next(w for w in scene['above'] if w['pid']==pid)['geometry']
    logical_click(banner['x']+banner['width']-90,banner['y']+banner['height']/2)
def async_rpc(method,params=None):
    child=subprocess.Popen([*ssh,shlex.join(['python3','vm-desktop-session.py',root,'rpc'])],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    child.stdin.write(json.dumps({'method':method,'owner':'pi:acceptance','params':params or {}}));child.stdin.close();child.stdin=None;return child

def consent(accept=True,stop=False):
    child=async_rpc('connect')
    try:
        def dialog():
            s=guest('windows');w=next((w for w in s['windows'] if w['title']=='Remote control requested'),None)
            if w and s['window']['id']!=w['id']:key('alt','tab');time.sleep(.5);return None
            return w
        until(dialog);time.sleep(1);w=until(dialog);g=w['geometry'];assert abs(g['width']-278)<2 and abs(g['height']-210)<2,g
        if stop:stop_click()
        else:logical_click(g['x']+(139 if accept else 228),g['y']+184)
        result=json.loads(child.communicate(timeout=20)[0])
        if accept and not stop:okay(result)
        else:assert not result['ok'],result;assert not okay(rpc('status'))['active']
    finally:
        if child.poll() is None:rpc('stop');child.terminate();child.wait(timeout=5)

def observe(title=None):
    def snapshot():
        r=rpc('capture')
        if not r['ok'] and 'changed during capture' in r['error']:return None
        s=okay(r)
        return s if title is None or title in s['window']['title'] else None
    return until(snapshot,20)
def act(kind,**params):
    s=observe();okay(rpc('action',{'token':s['token'],'kind':kind,**params}));return s

assert remote(['cat','/etc/augmentor-test-vm']).startswith('Isolated Augmentor')
remote(['python3','-c','import sys;from pathlib import Path;Path("vm-desktop-session.py").write_text(sys.stdin.read())'],(ROOT/'release/vm-desktop-session.py').read_text())
service=None;log=None
try:
    state=rpc('status')
    if state['ok']:assert not state['result']['active'],'Stop previous fixture control first';okay(rpc('shutdown'));time.sleep(1)
    if a.source:
        archive=io.BytesIO()
        with tarfile.open(fileobj=archive,mode='w') as tar:
            for part in ('services/desktop','services/lifecycle'):tar.add(ROOT/part,arcname=part,filter=lambda x:None if '__pycache__' in x.name else x)
        remote(['mkdir','-p',root])
        subprocess.run([*ssh,shlex.join(['tar','-xf','-','-C',root])],input=archive.getvalue(),check=True)
    command=['python3','vm-desktop-session.py',root,'serve']
    if a.capture_debug:command=['env','GST_DEBUG=2,pipewiresrc:6,pipewirepool:6','GST_DEBUG_NO_COLOR=1',*command]
    log=(vm/'desktop-executor.log').open('w');service=subprocess.Popen([*ssh,shlex.join(command)],stdout=log,stderr=log)
    until(lambda:rpc('status')['ok'])
    environment=guest('versions');assert environment['session']=='wayland'
    guest('scale',str(a.scale));time.sleep(2)
    remote(['python3','vm-desktop-session.py',root,'remove-output'])
    editor=guest('editor');until(lambda:(w:=guest('scene')['window'])['application']=='org.kde.kate' and w['pid'] not in editor['previousPids'] and 'Not Responding' not in w['title'])
    consent(False);print('Declined consent: no active sharing',flush=True)
    consent(stop=True);until(lambda:guest('scene')['window']['title']!='Remote control requested');print('Stop closes pending OS consent',flush=True)
    consent();s=observe('augmentor-desktop-acceptance.txt')
    if a.capture_count:
        captures=[];tokens=set()
        for index in range(a.capture_count):
            started=time.monotonic();response=rpc('capture')
            row={'index':index+1,'seconds':round(time.monotonic()-started,3),'ok':response['ok']}
            if response['ok']:
                value=response['result'];row['imageSize']=value['imageSize']
                row['freshToken']=value['token'] not in tokens;tokens.add(value['token'])
            else:row['error']=response['error']
            captures.append(row)
            (vm/'capture-reliability.json').write_text(json.dumps({'candidateSource':bool(a.source or a.guest_root),'guestRoot':root,'requested':a.capture_count,'scale':a.scale,'captures':captures},indent=2)+'\n')
            print('Repeated capture: '+json.dumps(row),flush=True)
            assert row['ok'] and row['freshToken'],row
        s=observe('augmentor-desktop-acceptance.txt')
    assert s['image']['width']==1280 and s['image']['height']==800
    (vm/'desktop-observation.jpg').write_bytes(base64.b64decode(s['image']['data']))
    assert not rpc('capture',owner='dsh:foreign')['ok']
    assert not rpc('action',{'token':s['token'],'kind':'type','text':'Unicode π'})['ok']
    assert not rpc('action',{'token':s['token'],'kind':'type','text':'must not replay'})['ok']
    s=observe();g=s['window']['geometry']
    assert not rpc('action',{'token':s['token'],'kind':'click','x':1,'y':1})['ok']
    s=observe();key('ctrl','shift','s');until(lambda:'Save File' in guest('scene')['window']['title'])
    assert not rpc('action',{'token':s['token'],'kind':'type','text':'must not enter another window'})['ok']
    key('esc');until(lambda:'Save File' not in guest('scene')['window']['title'])
    print('Foreign owner, unsupported text, replay, outside point and changed window refused',flush=True)
    s=observe();g=s['window']['geometry'];screen=s['screen']['geometry']
    okay(rpc('action',{'token':s['token'],'kind':'click','x':(g['x']+g['width']/2-screen['x'])*s['image']['width']/screen['width'],'y':(g['y']+g['height']/2-screen['y'])*s['image']['height']/screen['height']}))
    act('key',keys=['CTRL','A']);act('type',text='Wayland ASCII verified');act('key',keys=['CTRL','SHIFT','S']);observe('Save File')
    act('key',keys=['CTRL','A']);act('type',text='/home/beta/augmentor-desktop-acceptance-saved.txt');act('key',keys=['ENTER'])
    until(lambda:guest('file','augmentor-desktop-acceptance-saved.txt')['exists'])
    assert guest('file','augmentor-desktop-acceptance-saved.txt')['text']=='Wayland ASCII verified\n'
    print('Native Wayland Kate Save As: exact file verified',flush=True)
    act('key',keys=['CTRL','A']);s=observe();typing=async_rpc('action',{'token':s['token'],'kind':'type','text':'S'*256})
    until(lambda:okay(rpc('status'))['busy'])
    until(lambda:any(0<t.count('S')<256 for t in guest('editor-text')['texts']),25);stop_click()
    result=json.loads(typing.communicate(timeout=20)[0]);assert not result['ok'] and 'stopped' in result['error'].lower(),result
    until(lambda:not okay(rpc('status'))['busy']);assert not okay(rpc('status'))['sharing']
    key('ctrl','s');time.sleep(.5);partial=guest('file','augmentor-desktop-acceptance-saved.txt')['text']
    assert 0<len(partial.rstrip('\n'))<256 and set(partial.rstrip('\n'))=={'S'},repr(partial)
    time.sleep(1);key('ctrl','s');time.sleep(.3);assert guest('file','augmentor-desktop-acceptance-saved.txt')['text']==partial
    assert not rpc('action',{'token':s['token'],'kind':'type','text':'must not restart'})['ok']
    print('Actual Stop click interrupted typing; saved partial content stayed unchanged',flush=True)
    result={'environment':environment,'scale':a.scale,'candidateSource':bool(a.source or a.guest_root),'consentDenied':True,'pendingConsentStopped':True,'guards':True,'savedFileExact':True,'stopInterruptedInput':True,'partialCharacters':len(partial.rstrip('\n')),'noReplayAfterStop':True}
    (vm/'desktop-control-acceptance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
finally:
    try:rpc('stop');rpc('shutdown')
    finally:
        if service:
            try:service.wait(timeout=10)
            except subprocess.TimeoutExpired:service.terminate();service.wait(timeout=5)
        if log:log.close()
