#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real QMP key delivery to two pristine installed windows in the owned Noble VM.

Requires the separately authenticated Mesa comparison fixture. This is test
instrumentation, not a production input adapter or approval bypass.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import socket
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--directory',type=Path,required=True)
parser.add_argument('--identity',type=Path,required=True)
parser.add_argument('--source',required=True)
args=parser.parse_args()
assert os.geteuid()!=0 and re.fullmatch('[a-f0-9]{40}',args.source)
vm=args.directory.resolve();identity=args.identity.resolve()
assert vm.is_relative_to(ROOT/'outputs') and identity.is_relative_to(ROOT/'outputs')
assert identity.stat().st_uid==os.getuid() and identity.stat().st_mode&0o077==0
pid=int((vm/'qemu.pid').read_text())
argv=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
assert b'augmentor-gnome-ubuntu24-mesa2' in argv
assert b'user,id=net0,hostfwd=tcp:127.0.0.1:22491-:22' in argv
assert vm/'guest.qcow2' in {p.resolve() for p in Path(f'/proc/{pid}/fd').iterdir()}
ssh=['ssh','-i',str(identity),'-o','IdentitiesOnly=yes','-o','BatchMode=yes',
     '-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=10',
     '-o','UserKnownHostsFile="'+str(vm/'known_hosts')+'"','-p','22491','augmentor-proof@127.0.0.1']
guest=ROOT/'release/noble-gnome-shortcut-session.py'
uploaded=subprocess.run(ssh+['umask 077; cat > ~/noble-gnome-shortcut-session.py'],
                        input=guest.read_bytes(),capture_output=True,timeout=30)
assert uploaded.returncode==0,uploaded.stderr
guest_hash=hashlib.sha256(guest.read_bytes()).hexdigest()
assert subprocess.check_output(ssh+['sha256sum ~/noble-gnome-shortcut-session.py'],text=True,timeout=30).split()[0]==guest_hash
python=subprocess.check_output(ssh+['cat ~/selected-python.txt'],text=True,timeout=30).strip()
assert python.startswith('/home/augmentor-proof/.local/share/augmentor/python-runtimes/') and python.endswith('/bin/python3')


def run(action,name='main'):
    command=shlex.join([python,'-B','/home/augmentor-proof/noble-gnome-shortcut-session.py',
                       action,'--instance',name,'--source',args.source])
    result=subprocess.run(ssh+[command],text=True,capture_output=True,timeout=100)
    if result.returncode:raise RuntimeError(action+' failed: '+result.stderr)
    return json.loads(result.stdout)


def wait(predicate,label,seconds=100):
    deadline=time.monotonic()+seconds;last=''
    while time.monotonic()<deadline:
        try:
            state=run('snapshot')
            if predicate(state):return state
        except RuntimeError as error:last=str(error)
        time.sleep(.3)
    raise RuntimeError('Timed out waiting for '+label+': '+last)


def send_key(function):
    # AF_UNIX has a short path limit. Only connect after verifying QEMU's
    # actual open disk; daemonization makes its own cwd unsuitable as a guard.
    previous=Path.cwd()
    try:
        os.chdir(vm)
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as control:
            control.settimeout(10);control.connect('qmp.sock')
            with control.makefile('rwb',buffering=0) as stream:
                assert 'QMP' in json.loads(stream.readline())
                def execute(name,parameters=None):
                    request={'execute':name}
                    if parameters is not None:request['arguments']=parameters
                    stream.write(json.dumps(request).encode()+b'\n')
                    while True:
                        reply=json.loads(stream.readline())
                        if 'error' in reply:raise RuntimeError(str(reply['error']))
                        if 'return' in reply:return reply['return']
                execute('qmp_capabilities')
                execute('send-key',{'keys':[{'type':'qcode','data':key} for key in ('ctrl','alt','shift',function)],'hold-time':50})
    finally:os.chdir(previous)


events=[];prepared=False;failure=None;cleanup=[]
try:
    run('dismiss')
    initial=run('snapshot')
    assert initial['states']['main']['accepted'] and initial['states']['secondary'] is None
    assert len(initial['visible']['main'])==1 and initial['servicePid']==initial['states']['main']['pid']
    prepared=True
    saved=run('prepare');events.append({'event':'qt-save-and-conflicts','result':saved})
    main_pid=initial['states']['main']['pid']
    send_key('f9')
    hidden=wait(lambda s:not s['visible']['main'] and s['states']['main'] and s['states']['main']['pid']==main_pid,'main hiding')
    events.append({'event':'main-hide','result':hidden})
    send_key('f9')
    shown=wait(lambda s:len(s['visible']['main'])==1 and s['states']['main']['pid']==main_pid,'same main showing')
    events.append({'event':'main-show','result':shown})
    send_key('f10')
    secondary=wait(lambda s:s['states']['secondary'] and s['states']['secondary']['busy'] and s['visible']['secondary'],'secondary cold launch and setup dialog')
    secondary_pid=secondary['states']['secondary']['pid'];assert secondary_pid!=main_pid
    run('dismiss','secondary')
    stable=run('snapshot');assert stable['states']['main']['pid']==main_pid and len(stable['visible']['main'])==1
    send_key('f10')
    secondary_hidden=wait(lambda s:not s['visible']['secondary'] and s['states']['secondary']['pid']==secondary_pid,'secondary hiding')
    assert len(secondary_hidden['visible']['main'])==1 and secondary_hidden['states']['main']['pid']==main_pid
    events.append({'event':'independent-secondary-hide','result':secondary_hidden})
    send_key('f10')
    secondary_shown=wait(lambda s:len(s['visible']['secondary'])==1 and s['states']['secondary']['pid']==secondary_pid,'same secondary showing')
    events.append({'event':'independent-secondary-show','result':secondary_shown})
    send_key('f9')
    main_hidden=wait(lambda s:not s['visible']['main'],'main hiding with secondary present')
    assert main_hidden['states']['main']['pid']==main_pid and main_hidden['states']['secondary']['pid']==secondary_pid and len(main_hidden['visible']['secondary'])==1
    events.append({'event':'independent-main-hide','result':main_hidden})
    send_key('f9');wait(lambda s:len(s['visible']['main'])==1,'main showing before idle close')
    closed=run('close');events.append({'event':'accepted-idle-main-close','result':closed})
    wait(lambda s:s['states']['main'] is None and s['servicePid']==0,'main clean service exit')
    send_key('f9')
    reopened=wait(lambda s:s['states']['main'] and s['states']['main']['busy'] and s['visible']['main'],'shortcut cold main launch')
    assert reopened['states']['main']['pid']!=main_pid and reopened['servicePid']==reopened['states']['main']['pid']
    assert reopened['states']['secondary']['pid']==secondary_pid and len(reopened['visible']['secondary'])==1
    run('dismiss');events.append({'event':'shortcut-canonical-main-cold-launch','result':reopened})
except Exception as error:
    failure=str(error)
finally:
    if prepared:
        try:
            # Cleanup uses application status independently of the observer:
            # an invalid compositor scene must not strand our owned bindings.
            state=run('states')
            if state['states']['secondary']:
                run('dismiss','secondary');cleanup.append(run('close','secondary'))
            cleanup.append(run('restore'))
        except Exception as error:
            cleanup.append({'error':str(error)})
            if failure is None:failure='Cleanup failed: '+str(error)
report={'format':'augmentor-noble-gnome-real-shortcut-proof/1','source':{'commit':args.source,'dirty':False},
        'proofSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'guestProofSha256':guest_hash,
        'inputTransport':'owned QEMU QMP send-key; auto-release after 50ms','events':events,'cleanup':cleanup,
        'passed':failure is None,'failure':failure,'gnomeInputToolsEnabled':False,'connectedHarnessTested':False,
        'loginAuthenticationTested':False,'shortcutLockFencingTested':False}
(vm/'noble-shortcuts.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('events','cleanup')}))
if failure:raise SystemExit(1)
