#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Check installed UI, QEMU hardware-key shortcut, reboot persistence and cleanup."""
import argparse
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--vm-dir',type=Path,default=ROOT/'outputs/desktop-vm')
parser.add_argument('--port',type=int,default=22487)
args=parser.parse_args();vm=args.vm_dir.resolve()
hosts_option='UserKnownHostsFile="'+str(vm/'known_hosts')+'"'
ssh=['ssh','-i',str(vm/'id_ed25519'),'-p',str(args.port),'-o','BatchMode=yes','-o','ConnectTimeout=5','-o',hosts_option,'beta@127.0.0.1']


def remote(*command):
    result=subprocess.run([*ssh,shlex.join(command)],text=True,capture_output=True,timeout=90)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    return result.stdout


def guest(action,*rest):return json.loads(remote('python3','vm-session.py',action,*rest))
def until(check,timeout=45):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        try:
            value=check()
            if value:return value
        except (RuntimeError,subprocess.TimeoutExpired):pass
        time.sleep(.3)
    raise AssertionError('VM acceptance condition timed out')


def qmp(command,arguments=None):
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(10);connection.connect(os.path.relpath(vm/'qmp.sock'))
        with connection.makefile('rwb',buffering=0) as stream:
            assert 'QMP' in json.loads(stream.readline())
            def call(name,params):
                stream.write((json.dumps({'execute':name,'arguments':params,'id':name})+'\n').encode())
                while True:
                    response=json.loads(stream.readline())
                    if response.get('id')==name:
                        assert 'error' not in response,response
                        return response['return']
            call('qmp_capabilities',{})
            return call(command,arguments or {})


def key():
    qmp('send-key',{'keys':[{'type':'qcode','data':name} for name in ('ctrl','alt','j')],'hold-time':100})


assert remote('cat','/etc/augmentor-test-vm').startswith('Isolated Augmentor')
scp=['scp','-i',str(vm/'id_ed25519'),'-P',str(args.port),'-o','BatchMode=yes','-o',hosts_option]
subprocess.run([*scp,str(ROOT/'release/vm-session.py'),str(ROOT/'scripts/copy-scroll-proof.py'),'beta@127.0.0.1:'],check=True)
versions=guest('versions');assert versions['session']=='wayland',versions
print(json.dumps({'stage':'installed-session','environment':versions}),flush=True)
print(remote('python3','vm-session.py','first-run'),flush=True)
print(remote('python3','vm-session.py','copy'),flush=True)
assert not guest('windows')
assert guest('shortcut')['saved']
print('Checking hardware shortcut launch/hide/show',flush=True)
key();original=until(lambda:guest('windows'))
assert len(original)==1
qmp('screendump',{'filename':str(vm/'first-launch.ppm')})
key();until(lambda:not guest('windows'))
key();until(lambda:guest('windows')==original)
remote('python3','vm-session.py','close-dialog')
guest('prepare')
assert not guest('windows')
boot=remote('cat','/proc/sys/kernel/random/boot_id').strip()
print('Rebooting the desktop VM',flush=True)
remote('sudo','systemctl','reboot')
until(lambda:remote('cat','/proc/sys/kernel/random/boot_id').strip()!=boot,timeout=120)
until(lambda:guest('versions').get('session')=='wayland',timeout=90)
until(lambda:guest('ready'),timeout=90)
print('Desktop is ready; checking shortcut without registration',flush=True)
# No registration after reboot. QEMU injects hardware keyboard events into the
# Wayland compositor; xdotool is only the window-state observer here.
key();until(lambda:guest('windows'))
remote('python3','vm-session.py','close-dialog')
removed=guest('prepare','--remove')
assert len(removed['removedIntegrations'])==2,removed
key();time.sleep(1)
assert not guest('windows')
result={'environment':versions,'realPlasmaWaylandSession':True,'installedFirstRunAndFileTask':True,
        'sixExternalClipboardCases':True,'hardwareKeyLaunchHideShow':True,'shortcutSurvivedReboot':True,
        'releaseLeasesRecreatedAfterReboot':True,'ownedShortcutRemoved':True,'model':'deterministic local fixture'}
(vm/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
