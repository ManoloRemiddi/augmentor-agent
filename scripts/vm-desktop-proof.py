#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Deterministic desktop control on a disposable full Plasma Wayland QEMU VM.

Default tests installed code. --source stages the candidate executor separately;
its evidence explicitly identifies that limit. No access to the user's desktop.
"""
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import tarfile
import time

ROOT=Path(__file__).resolve().parents[1]


def consent_point(record,window,*,allow,source,target,portal_package):
    """Use an explicitly observed native dialog, never guessed button geometry."""
    if (record.get('format')!='augmentor-kde-consent-observation/1' or record.get('source')!=source or
            record.get('target')!=target or record.get('portalPackage')!=portal_package):
        raise ValueError('Consent observation source/target/native portal differs.')
    dialog=record.get('dialog',{})
    if (not dialog.get('title') or not dialog.get('application') or window.get('title')!=dialog['title'] or
            window.get('application')!=dialog['application']):
        raise ValueError('The observed native consent window differs.')
    geometry=window['geometry']
    if any(geometry.get(key)!=dialog.get(key) for key in ('width','height')):
        raise ValueError('Native consent geometry changed; observe it again.')
    button=record.get('buttons',{}).get('allow' if allow else 'deny',{})
    if not isinstance(button.get('label'),str) or not button['label'].strip():
        raise ValueError('Record the actually observed native button label.')
    x=button.get('x');y=button.get('y')
    if (isinstance(x,bool) or isinstance(y,bool) or not isinstance(x,(float,int)) or not isinstance(y,(float,int)) or
            not 0<x<geometry['width'] or not 0<y<geometry['height']):
        raise ValueError('The observed consent point is outside its current dialog.')
    return geometry['x']+x,geometry['y']+y


def load_consent_observation(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise ValueError('Consent observation must be an ordinary file.')
    record=json.loads(path.read_text())
    screenshot=Path(record.get('screenshot',{}).get('file',''))
    if not screenshot.is_absolute() or screenshot.is_symlink() or not screenshot.is_file():
        raise ValueError('Consent evidence requires an ordinary absolute screenshot.')
    if not 0<screenshot.stat().st_size<=10*1024**2:
        raise ValueError('Consent screenshot exceeds its bound.')
    if hashlib.sha256(screenshot.read_bytes()).hexdigest()!=record['screenshot'].get('sha256'):
        raise ValueError('The observed consent screenshot hash differs.')
    return record


def portal_dialog(scene,pid,dialog=None):
    """Admit only the sole, focused window owned by the live native portal."""
    windows=[window for window in scene.get('windows',[]) if window.get('pid')==pid]
    if len(windows)!=1:return None
    window=windows[0]
    if not scene.get('window') or scene['window'].get('id')!=window.get('id'):return None
    if dialog and any(window.get(key)!=dialog.get(key) for key in ('title','application')):return None
    return window


def editor_fixture_name(editor,home):
    """Keep every save/readback on the editor's already owned fixture."""
    path=Path(editor['path']);home=Path(home)
    if not home.is_absolute() or path!=home/'augmentor-desktop-acceptance.txt':
        raise ValueError('Save requires the existing owned editor fixture.')
    return path.name


def save_owned_editor(editor,home,text):
    name=editor_fixture_name(editor,home)
    # Save As completion can add a covering popup during pathname typing. Keep
    # that scene-change refusal intact and qualify ordinary existing-file Save.
    act('key',keys=['CTRL','S'])
    until(lambda:guest('file',name).get('text')==text)
    assert guest('file',name)['text']==text
    return name


p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',action='store_true');p.add_argument('--port',type=int,default=22487);p.add_argument('--scale',type=float,choices=(1,1.25,1.5),default=1)
p.add_argument('--vm-dir',type=Path,default=ROOT/'outputs/desktop-vm')
p.add_argument('--guest-root',help='Explicit staged source root in the disposable VM')
p.add_argument('--capture-count',type=int,default=0,help='Additional consecutive captures for reliability diagnostics')
p.add_argument('--capture-debug',action='store_true',help='Record PipeWire/GStreamer diagnostics in the disposable VM executor log')
p.add_argument('--expected-source',required=True,help='Exact clean installed source commit; candidate runs remain separately labelled.')
p.add_argument('--expected-target',required=True)
p.add_argument('--expected-marker',required=True,help='Exact owned guest marker text, excluding its final newline.')
p.add_argument('--expected-vm-name',required=True,help='Exact QMP guest identity before any virtual input.')
p.add_argument('--guest-user',choices=('beta','augmentor-complete-proof'),default='beta')
p.add_argument('--guest-uid',type=int,choices=(1000,1001),default=1000)
p.add_argument('--consent-observation',type=Path,help='Current screenshot-bound native allow/deny button observation.')
p.add_argument('--observe-consent',action='store_true',help='Capture a fresh native pending-consent dialog then Stop; never grant.')
a=p.parse_args()
if not 0<=a.capture_count<=1000:p.error('--capture-count must be between 0 and 1000')
if len(a.expected_source)!=40 or any(c not in '0123456789abcdef' for c in a.expected_source):p.error('--expected-source must be an exact clean commit')
if bool(a.consent_observation)==bool(a.observe_consent):p.error('Select a screenshot-bound consent observation or explicit observe-only mode')
if (a.guest_user,a.guest_uid) not in (('beta',1000),('augmentor-complete-proof',1001)):p.error('Use the exact dedicated synthetic account/UID pair')
consent_observation=load_consent_observation(a.consent_observation) if a.consent_observation else None
vm=a.vm_dir.resolve();ssh=['ssh','-i',str(vm/'id_ed25519'),'-p',str(a.port),'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile="'+str(vm/'known_hosts')+'"',a.guest_user+'@127.0.0.1']
root=a.guest_root or ('/home/'+a.guest_user+'/augmentor-desktop-candidate' if a.source else '/usr/lib/augmentor')
guest_python='python3'
def remote(command,data=None,timeout=120):
    r=subprocess.run([*ssh,shlex.join(command)],input=data,text=True,capture_output=True,timeout=timeout)
    if r.returncode:raise RuntimeError(r.stderr[-2000:])
    return r.stdout
def helper_command(action,*rest):
    command=[guest_python,'-B','vm-desktop-session.py',root,action,*rest]
    if not (a.source or a.guest_root):
        # Verify metadata/inventories before executing the selected runner. Its
        # normal lease/runtime selector then supplies the loader environment.
        if action!='versions':
            command=['python3','-B',str(Path(root)/'scripts/run-component.py'),'desktop',*command]
        command=['env','AUGMENTOR_PYTHON='+guest_python,*command]
        command=['env','AUGMENTOR_PROOF_SOURCE='+a.expected_source,'AUGMENTOR_PROOF_TARGET='+a.expected_target,*command]
    command=['env','AUGMENTOR_PROOF_UID='+str(a.guest_uid),'AUGMENTOR_PROOF_USER='+a.guest_user,'AUGMENTOR_PROOF_PACKAGE_TARGET='+a.expected_target,*command]
    return command
def guest(action,*rest):return json.loads(remote(helper_command(action,*rest)))
def rpc(method,params=None,owner='pi:acceptance'):
    return json.loads(remote(helper_command('rpc'),json.dumps({'method':method,'owner':owner,'params':params or {}})))
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
        for method,params in [('qmp_capabilities',{}),('query-name',{}),(name,args)]:
            f.write((json.dumps({'execute':method,'arguments':params,'id':method})+'\n').encode())
            while True:
                response=json.loads(f.readline())
                if response.get('id')==method:
                    assert 'error' not in response,response
                    if method=='query-name':assert response['return']['name']==a.expected_vm_name,'QMP guest identity differs'
                    break
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
    child=subprocess.Popen([*ssh,shlex.join(helper_command('rpc'))],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    child.stdin.write(json.dumps({'method':method,'owner':'pi:acceptance','params':params or {}}));child.stdin.close();child.stdin=None;return child

def consent(accept=True,stop=False):
    child=async_rpc('connect')
    try:
        owner=guest('portal-owner')
        def dialog():
            scene=guest('windows');window=portal_dialog(scene,owner['pid'],consent_observation['dialog'])
            if window:return window
            if any(w.get('pid')==owner['pid'] for w in scene.get('windows',[])):key('alt','tab');time.sleep(.5)
            return None
        until(dialog);time.sleep(1);w=until(dialog)
        if stop:stop_click()
        else:
            x,y=consent_point(consent_observation,w,allow=accept,source=a.expected_source,target=a.expected_target,portal_package=environment['portalPackage'])
            logical_click(x,y)
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

assert remote(['cat','/etc/augmentor-test-vm'])==a.expected_marker.rstrip('\n')+'\n'
if not (a.source or a.guest_root):
    selection=json.loads(remote(['python3','-B','-c','import json;from pathlib import Path;v=json.loads((Path.home()/".local/share/augmentor/desktop.json").read_text());print(json.dumps({k:v[k] for k in ("root","python")}))']))
    root=selection['root'];guest_python=selection['python']
remote(['python3','-c','import sys;from pathlib import Path;Path("vm-desktop-session.py").write_text(sys.stdin.read())'],(ROOT/'release/vm-desktop-session.py').read_text())
service=None;log=None
try:
    if a.source:
        archive=io.BytesIO()
        with tarfile.open(fileobj=archive,mode='w') as tar:
            for part in ('services/desktop','services/lifecycle'):tar.add(ROOT/part,arcname=part,filter=lambda x:None if '__pycache__' in x.name else x)
        remote(['mkdir','-p',root])
        subprocess.run([*ssh,shlex.join(['tar','-xf','-','-C',root])],input=archive.getvalue(),check=True)
    environment=guest('versions');assert environment['session']=='wayland'
    if not (a.source or a.guest_root):assert environment['selectedIdentity']['source']==a.expected_source and environment['selectedIdentity']['target']==a.expected_target
    state=rpc('status')
    if state['ok']:assert not state['result']['active'],'Stop previous fixture control first';okay(rpc('shutdown'));time.sleep(1)
    command=helper_command('serve')
    if a.capture_debug:command=['env','GST_DEBUG=2,pipewiresrc:6,pipewirepool:6','GST_DEBUG_NO_COLOR=1',*command]
    log=(vm/'desktop-executor.log').open('w');service=subprocess.Popen([*ssh,shlex.join(command)],stdout=log,stderr=log)
    until(lambda:rpc('status')['ok'])
    guest('scale',str(a.scale));time.sleep(2)
    remote(helper_command('remove-output'))
    editor=guest('editor');until(lambda:(w:=guest('scene')['window'])['application']=='org.kde.kate' and w['pid'] not in editor['previousPids'] and 'Not Responding' not in w['title'])
    if a.observe_consent:
        child=async_rpc('connect')
        try:
            owner=guest('portal-owner')
            def pending_dialog():
                scene=guest('windows');window=portal_dialog(scene,owner['pid'])
                if window:return window
                if any(w.get('pid')==owner['pid'] for w in scene.get('windows',[])):key('alt','tab');time.sleep(.5)
                return None
            window=until(pending_dialog)
            screenshot=vm/'native-consent-observed.ppm'
            qmp('screendump',{'filename':str(screenshot)})
            record={'format':'augmentor-kde-consent-observation/1','source':a.expected_source,'target':a.expected_target,
                    'portalPackage':environment['portalPackage'],'portalOwner':owner,'selectedIdentity':environment['selectedIdentity'],
                    'dialog':{k:window[k] for k in ('title','application')},
                    'screenshot':{'file':str(screenshot),'sha256':hashlib.sha256(screenshot.read_bytes()).hexdigest()},
                    'buttons':{'allow':{'label':None,'x':None,'y':None},'deny':{'label':None,'x':None,'y':None}},
                    'scope':'Observed pending OS consent only; no grant or inferred button geometry.'}
            record['dialog'].update({k:window['geometry'][k] for k in ('width','height')})
            (vm/'consent-observation-pending.json').write_text(json.dumps(record,indent=2)+'\n')
            okay(rpc('stop'));result=json.loads(child.communicate(timeout=20)[0]);assert not result['ok'],result
            assert not okay(rpc('status'))['active']
            print(json.dumps(record),flush=True)
            raise SystemExit(0)
        finally:
            if child.poll() is None:rpc('stop');child.terminate();child.wait(timeout=5)
    consent(False);print('Declined consent: no active sharing',flush=True)
    consent(stop=True);until(lambda:guest('scene')['window'] is None or guest('scene')['window']['title']!=consent_observation['dialog']['title']);print('Stop closes pending OS consent',flush=True)
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
    act('key',keys=['CTRL','A']);act('type',text='Wayland ASCII verified')
    fixture_name=save_owned_editor(editor,'/home/'+a.guest_user,'Wayland ASCII verified\n')
    print('Native Wayland Kate existing-file Save: exact file verified',flush=True)
    act('key',keys=['CTRL','A']);s=observe();typing=async_rpc('action',{'token':s['token'],'kind':'type','text':'S'*256})
    until(lambda:okay(rpc('status'))['busy'])
    until(lambda:any(0<t.count('S')<256 for t in guest('editor-text')['texts']),25);stop_click()
    result=json.loads(typing.communicate(timeout=20)[0]);assert not result['ok'] and 'stopped' in result['error'].lower(),result
    until(lambda:not okay(rpc('status'))['busy']);assert not okay(rpc('status'))['sharing']
    key('ctrl','s');time.sleep(.5);partial=guest('file',fixture_name)['text']
    assert 0<len(partial.rstrip('\n'))<256 and set(partial.rstrip('\n'))=={'S'},repr(partial)
    time.sleep(1);key('ctrl','s');time.sleep(.3);assert guest('file',fixture_name)['text']==partial
    assert not rpc('action',{'token':s['token'],'kind':'type','text':'must not restart'})['ok']
    print('Actual Stop click interrupted typing; saved partial content stayed unchanged',flush=True)
    result={'environment':environment,'scale':a.scale,'candidateSource':bool(a.source or a.guest_root),'consentObservationSha256':hashlib.sha256(a.consent_observation.read_bytes()).hexdigest(),'proofScriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'guestHelperSha256':hashlib.sha256((ROOT/'release/vm-desktop-session.py').read_bytes()).hexdigest(),'consentDenied':True,'pendingConsentStopped':True,'guards':True,'savedFileExact':True,'saveScope':'existing-owned-editor-file','savedFile':fixture_name,'stopInterruptedInput':True,'partialCharacters':len(partial.rstrip('\n')),'noReplayAfterStop':True}
    (vm/'desktop-control-acceptance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
finally:
    failed=sys.exc_info()[0] is not None
    try:
        if service:rpc('stop');rpc('shutdown')
    except Exception as error:
        if not failed:raise
        print('Fixture cleanup also failed: '+str(error),file=sys.stderr)
    finally:
        if service:
            try:service.wait(timeout=10)
            except subprocess.TimeoutExpired:service.terminate();service.wait(timeout=5)
        if log:log.close()
