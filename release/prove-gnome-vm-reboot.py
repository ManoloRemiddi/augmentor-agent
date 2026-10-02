#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Reboot only the owned GNOME guest after idle preflight, then inspect real login.

Run on the ordinary build host, with the preparation tool's ignored VM directory.
Reboot is requested exactly once; reconnect polling never replays that action.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--directory', type=Path, required=True)
p.add_argument('--managed-source')
a = p.parse_args()
if a.managed_source:assert re.fullmatch('[0-9a-f]{40}', a.managed_source)
vm = a.directory.resolve()
assert os.geteuid() != 0 and vm.is_relative_to(ROOT/'outputs')
pid = int((vm/'qemu.pid').read_text())
arguments = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
assert b'augmentor-gnome-fedora44' in arguments
assert b'file=guest.qcow2,format=qcow2,if=virtio' in arguments
# QEMU daemonization changes cwd to /. Verify its actually opened disk rather
# than assuming the launch directory remains its working directory.
assert vm/'guest.qcow2' in {entry.resolve() for entry in Path(f'/proc/{pid}/fd').iterdir()}
ssh = ['ssh', '-i', str(vm/'id_ed25519'), '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
       '-o', 'ConnectTimeout=5', '-o', 'StrictHostKeyChecking=yes',
       '-o', 'UserKnownHostsFile='+str(vm/'known_hosts'), '-p', '22489',
       'augmentor-proof@127.0.0.1']
preflight = '''from pathlib import Path
import json,subprocess,socket,os,importlib.util
assert os.geteuid()!=0 and os.environ.get('USER')=='augmentor-proof'
assert Path('/etc/augmentor-test-vm').read_text()=="Isolated Augmentor Fedora GNOME qualification VM\\n"
assert subprocess.check_output(['systemd-detect-virt'],text=True).strip()=='qemu'
assert subprocess.check_output(['getenforce'],text=True).strip()=='Enforcing'
subprocess.run(['rpm','-V','augmentor-agent'],check=True,timeout=30)
with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
 s.settimeout(3);s.connect('/run/user/'+str(os.getuid())+'/augmentor-linux-pi.sock');s.sendall(b'maintenance.status')
 with s.makefile('rb') as stream:status=json.loads(stream.readline(16384))
assert status['accepted'] and not status['busy'] and not status['running'] and not status['draftPresent'] and not status['online']
root=Path('/usr/lib/augmentor')
selection=json.loads((Path.home()/'.local/share/augmentor/desktop.json').read_text())
if expected_source:
 root=Path(selection['root']);data=Path.home()/'.local/share/augmentor'
 assert root.is_relative_to(data/'releases') and selection['sourceRef']==expected_source
 spec=importlib.util.spec_from_file_location('owned_reboot_deployment',data/'desktop-deployment.py')
 deployment=importlib.util.module_from_spec(spec);spec.loader.exec_module(deployment);deployment.verify(root)
 assert json.loads((root/'release.json').read_text())['source']=={'commit':expected_source,'dirty':False}
assert status['buildRoot']==str(root)
assert int(subprocess.check_output(['systemctl','--user','show','augmentor-desktop.service','--value','-p','MainPID'],text=True))==status['pid']
print(json.dumps({'bootId':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'status':status,'selection':selection,'release':json.loads((root/'release.json').read_text())}))
'''
r = subprocess.run(ssh+['python3 -'], input='expected_source='+repr(a.managed_source)+'\n'+preflight, text=True, capture_output=True, timeout=90)
assert r.returncode == 0, r.stderr
before = json.loads(r.stdout)
reboot = '''from pathlib import Path
import subprocess,sys
assert Path('/etc/augmentor-test-vm').read_text()=="Isolated Augmentor Fedora GNOME qualification VM\\n"
print('Requesting one owned-guest reboot.',flush=True)
subprocess.run(['sudo','systemctl','reboot'],check=True,timeout=15)
'''
requested = subprocess.run(ssh+['python3 -'], input=reboot, text=True, capture_output=True, timeout=25)
assert requested.returncode in (0, 255), requested.stderr
deadline = time.monotonic() + 240
after = None
last_error = ''
while time.monotonic() < deadline:
    r = subprocess.run(ssh+['cat /proc/sys/kernel/random/boot_id'], text=True,
                       capture_output=True, timeout=12)
    if r.returncode == 0 and r.stdout.strip() != before['bootId']:
        inspection = 'python3 ~/inspect-gnome-vm.py'+(' --managed-source '+a.managed_source if a.managed_source else '')
        result = subprocess.run(ssh+[inspection], text=True,
                                capture_output=True, timeout=90)
        if result.returncode == 0:
            after = json.loads(result.stdout)
            assert after['source'] == before['release']['source']
            assert after['version'] == before['release']['version']
            if a.managed_source:assert after['selection'] == before['selection'] and after['managedInventoryVerified']
            break
        last_error = result.stderr
    time.sleep(2)
assert after is not None, 'Guest did not restore its actual graphical app: '+last_error
assert hashlib.sha256((ROOT/'release/inspect-gnome-vm.py').read_bytes()).hexdigest() == after['inspectionSha256']
report = {'format': 'augmentor-gnome-full-vm-reboot/1',
    'source': after['source'], 'version': after['version'],
    'proofSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'singleRebootRequest': True, 'idleDraftFreeUnconnectedPreflight': True,
    'kernelBootIdentityChanged': True, 'sameInstalledSourceAfterReboot': True,
    'managedSource': a.managed_source, 'sameSelectedArtifactAfterReboot': bool(a.managed_source),
    'realGdmWaylandLoginAfterReboot': True, 'serviceOwnsActualAppAfterReboot': True,
    'selinuxEnforcingAfterReboot': after['selinuxEnforcing'],
    'packageVerifiedAfterReboot': after['packageVerified'], 'after': after,
    'harnessConnectionTested': False, 'modelTurnTested': False,
    'loginAuthenticationTested': False, 'standardWorkstationInstallerTested': False,
    'gnomeInputToolsEnabled': False}
(vm/('managed-reboot.json' if a.managed_source else 'reboot.json')).write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k != 'after'}))
