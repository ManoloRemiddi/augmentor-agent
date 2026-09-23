#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Boot the marked disposable VM with two virtual GPUs; prove sharing refusal."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',action='store_true')
p.add_argument('--vm-dir',type=Path,default=ROOT/'outputs/desktop-vm')
a=p.parse_args();vm=a.vm_dir.resolve()
root='/home/beta/augmentor-desktop-candidate' if a.source else '/usr/lib/augmentor'
ssh=['ssh','-i',str(vm/'id_ed25519'),'-p','22487','-o','BatchMode=yes','-o','ConnectTimeout=3','-o','UserKnownHostsFile="'+str(vm/'known_hosts')+'"','beta@127.0.0.1']
def remote(args,data=None,check=True):
    r=subprocess.run([*ssh,shlex.join(args)],input=data,text=True,capture_output=True,timeout=20)
    if check and r.returncode:raise RuntimeError(r.stderr[-1500:])
    return r
def until(check,seconds=240):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if value:=check():return value
        time.sleep(1)
    raise AssertionError('VM monitor proof timed out')
def rpc(method):return json.loads(remote(['python3','vm-desktop-session.py',root,'rpc'],json.dumps({'method':method,'owner':'pi:monitor-proof'})).stdout)
def boot(command):
    subprocess.run(command,cwd=ROOT,check=True)
    until(lambda:remote(['test','-f','/etc/augmentor-test-vm'],check=False).returncode==0)
    until(lambda:remote(['systemctl','--user','is-active','plasma-kwin_wayland.service'],check=False).returncode==0)
def poweroff():
    assert remote(['cat','/etc/augmentor-test-vm']).stdout.startswith('Isolated Augmentor')
    pid=int((vm/'qemu.pid').read_text());remote(['sudo','poweroff'],check=False)
    def exited():
        try:return Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[0]=='Z'
        except FileNotFoundError:return True
    until(exited,120)

original=json.loads((vm/'qemu-command.json').read_text())
assert original[0]=='qemu-system-x86_64' and 'augmentor-desktop-acceptance' in original
assert remote(['cat','/etc/augmentor-test-vm']).stdout.startswith('Isolated Augmentor')
state=rpc('status')
if state['ok']:
    assert not state['result']['active'] and not state['result']['busy'];assert rpc('shutdown')['ok'];time.sleep(1)
service=None;log=None;changed=False
try:
    poweroff();changed=True;boot([*original,'-device','virtio-gpu-pci'])
    def screens():
        r=remote(['python3','vm-desktop-session.py',root,'scene'],check=False)
        if r.returncode:return None
        value=json.loads(r.stdout)
        return value if len(value['screens'])==2 else None
    scene=until(screens,60);print(json.dumps({'twoActiveMonitors':scene['screens']}),flush=True)
    log=(vm/'multi-monitor-executor.log').open('w')
    service=subprocess.Popen([*ssh,shlex.join(['python3','vm-desktop-session.py',root,'serve'])],stdout=log,stderr=log)
    until(lambda:rpc('status')['ok'],20)
    result=rpc('connect');assert not result['ok'] and 'one connected monitor' in result['error'],result
    status=rpc('status')['result'];assert not status['active'] and not status['sharing']
    evidence={'candidateSource':a.source,'screens':scene['screens'],'refusedBeforeSharing':True,'result':result}
    (vm/'multi-monitor-proof.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence),flush=True)
finally:
    if service:
        try:rpc('stop');rpc('shutdown')
        finally:
            service.terminate();service.wait(timeout=10);log.close()
    if changed:
        poweroff();boot(original);print('Original one-GPU VM restored',flush=True)
