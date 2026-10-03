#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bounded shortcut proofs in the owned Noble or Fedora GNOME VM.

Noble requires its separately authenticated Mesa comparison fixture. Actual
Settings and QMP delivery are separate phases; this is test instrumentation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import socket
import stat
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--directory',type=Path,required=True)
parser.add_argument('--identity',type=Path,required=True)
parser.add_argument('--source',required=True)
parser.add_argument('--target',choices=('ubuntu24','fedora44'),default='ubuntu24')
parser.add_argument('--output',type=Path,required=True,help='New private report; existing evidence is never overwritten.')
parser.add_argument('--app-settings-only',action='store_true',help='Both existing real windows must explicitly opt into UI test control; no launch or native key delivery in this phase.')
args=parser.parse_args()
assert os.geteuid()!=0 and re.fullmatch('[a-f0-9]{40}',args.source)
vm=args.directory.resolve();identity=args.identity.resolve()
assert vm.is_relative_to(ROOT/'outputs') and identity.is_relative_to(ROOT/'outputs')
assert identity.stat().st_uid==os.getuid() and identity.stat().st_mode&0o077==0
pid=int((vm/'qemu.pid').read_text())
argv=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
name,port=(('augmentor-gnome-ubuntu24-mesa2',22491) if args.target=='ubuntu24' else ('augmentor-gnome-fedora44',22489))
assert name.encode() in argv
assert f'user,id=net0,hostfwd=tcp:127.0.0.1:{port}-:22'.encode() in argv
assert Path(f'/proc/{pid}').stat().st_uid==os.getuid()
assert not any(fragment in argument for argument in argv for fragment in
               (b'vfio',b'virtfs',b'virtiofs',b'fsdev',b'usb-host',b'/dev/',b'host_device'))
assert stat.S_ISSOCK((vm/'qmp.sock').stat().st_mode) and (vm/'qmp.sock').stat().st_uid==os.getuid()
assert vm/'guest.qcow2' in {p.resolve() for p in Path(f'/proc/{pid}/fd').iterdir()}
report_path=args.output.resolve()
assert report_path.is_relative_to(ROOT/'outputs') and not report_path.exists()
report_path.parent.mkdir(parents=True,exist_ok=True)
ssh=['ssh','-i',str(identity),'-o','IdentitiesOnly=yes','-o','BatchMode=yes',
     '-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=10',
     '-o','UserKnownHostsFile="'+str(vm/'known_hosts')+'"','-p',str(port),'augmentor-proof@127.0.0.1']
guest=ROOT/'release/noble-gnome-shortcut-session.py'
helper=ROOT/'release/gnome-vm-qualification.py'
# Preserve the original staged recovery scripts as well as a pending journal.
# The guest repeats this check after runtime verification and uses exclusive
# journal creation, so a racing run cannot adopt this run's ownership.
subprocess.run(ssh+['test ! -e /home/augmentor-proof/noble-shortcut-proof-state.json && test ! -L /home/augmentor-proof/noble-shortcut-proof-state.json'],
               check=True,capture_output=True,timeout=30)
for path in (guest,helper):
    uploaded=subprocess.run(ssh+['umask 077; cat > '+shlex.quote('/home/augmentor-proof/'+path.name)],
                            input=path.read_bytes(),capture_output=True,timeout=30)
    assert uploaded.returncode==0,uploaded.stderr
    assert subprocess.check_output(ssh+['sha256sum '+shlex.quote('/home/augmentor-proof/'+path.name)],text=True,timeout=30).split()[0]==hashlib.sha256(path.read_bytes()).hexdigest()
guest_hash=hashlib.sha256(guest.read_bytes()).hexdigest()
discovery="import importlib.util,json;from pathlib import Path;s=importlib.util.spec_from_file_location('owned_qualification',Path.home()/'gnome-vm-qualification.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);print(json.dumps(m.verified_profile("+repr(args.target)+","+repr(args.source)+")))"
contract=json.loads(subprocess.check_output(ssh+[shlex.join(['/usr/bin/python3','-I','-B','-c',discovery])],text=True,timeout=180))
python=contract['python']
proof_token=secrets.token_hex(32)
receipt_path=Path(str(report_path)+'.run.json')
receipt={'format':'augmentor-gnome-shortcut-run/1','source':args.source,'target':args.target,
         'proofToken':proof_token,'guestProofSha256':guest_hash,
         'qualificationHelperSha256':hashlib.sha256(helper.read_bytes()).hexdigest(),
         'selectedRoot':contract['root'],'python':python}
with os.fdopen(os.open(receipt_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as stream:
    json.dump(receipt,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())


def run(action,name='main'):
    command=shlex.join([python,'-B','/home/augmentor-proof/noble-gnome-shortcut-session.py',
                       action,'--instance',name,'--target',args.target,'--source',args.source,'--proof-token',proof_token])
    result=subprocess.run(ssh+[command],text=True,capture_output=True,timeout=220)
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
    assert run('journal-check')['journalAbsent'] is True
    run('dismiss')
    initial=run('snapshot')
    assert initial['states']['main']['accepted']
    if args.app_settings_only:assert initial['states']['secondary'] and initial['states']['secondary']['accepted']
    else:assert initial['states']['secondary'] is None
    assert len(initial['visible']['main'])==1 and initial['servicePid']==initial['states']['main']['pid']
    prepared=True
    saved=run('prepare-app-settings' if args.app_settings_only else 'prepare')
    events.append({'event':'actual-two-app-settings-save-and-conflicts' if args.app_settings_only else 'standalone-qt-save-and-conflicts','result':saved})
    if not args.app_settings_only:
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
            if state['states']['secondary'] and not args.app_settings_only:
                run('dismiss','secondary');cleanup.append(run('close','secondary'))
        except Exception as error:
            cleanup.append({'error':str(error)})
            if failure is None:failure='Cleanup failed: '+str(error)
        try:cleanup.append(run('restore'))
        except Exception as error:
            cleanup.append({'settingsRestoreError':str(error)})
            if failure is None:failure='Settings restore failed: '+str(error)
report={'format':'augmentor-gnome-real-shortcut-proof/2','target':args.target,'source':{'commit':args.source,'dirty':False},
        'proofToken':proof_token,'runReceipt':str(receipt_path),
        'proofSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'guestProofSha256':guest_hash,
        'qualificationHelperSha256':hashlib.sha256(helper.read_bytes()).hexdigest(),'verifiedSelectedContract':contract,
        'inputTransport':'app-local Qt test events only' if args.app_settings_only else 'owned QEMU QMP send-key; auto-release after 50ms',
        'actualApplicationSettingsTested':args.app_settings_only,'nativeShortcutDeliveryTested':not args.app_settings_only and failure is None,
        'events':events,'cleanup':cleanup,
        'passed':failure is None,'failure':failure,'gnomeInputToolsEnabled':False,'connectedHarnessTested':False,
        'loginAuthenticationTested':False,'shortcutLockFencingTested':False}
with report_path.open('x') as stream:stream.write(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('events','cleanup')}))
if failure:raise SystemExit(1)
