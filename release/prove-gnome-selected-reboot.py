#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One reboot of an idle, explicitly selected artifact in an owned GNOME VM.

Read-only reconnect polling never repeats the reboot. This does not prove
password authentication, a connected harness, or agent desktop input.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {'ubuntu24': ('augmentor-gnome-ubuntu24-mesa2', 22491),
            'fedora44': ('augmentor-gnome-fedora44', 22489)}


def verify_host(vm, identity, target):
    if target not in PROFILES or os.geteuid() == 0:
        raise ValueError('Use an ordinary host account and explicit owned target.')
    vm, identity = vm.resolve(), identity.resolve()
    if not vm.is_relative_to(ROOT/'outputs') or not identity.is_relative_to(ROOT/'outputs'):
        raise ValueError('The VM and private key must belong to the ignored qualification outputs.')
    info = identity.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077 or not stat.S_ISREG(info.st_mode):
        raise ValueError('The owned SSH key is not private.')
    pid = int((vm/'qemu.pid').read_text())
    arguments = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
    name, port = PROFILES[target]
    if (Path(f'/proc/{pid}').stat().st_uid != os.getuid() or
        name.encode() not in arguments or
        f'user,id=net0,hostfwd=tcp:127.0.0.1:{port}-:22'.encode() not in arguments or
        any(fragment in arg for arg in arguments for fragment in
            (b'vfio', b'virtfs', b'virtiofs', b'fsdev', b'usb-host', b'/dev/', b'host_device')) or
        vm/'guest.qcow2' not in {p.resolve() for p in Path(f'/proc/{pid}/fd').iterdir()}):
        raise ValueError('The running QEMU identity, private forwarding or disk differs.')
    return ['ssh', '-i', str(identity), '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
            '-o', 'ConnectTimeout=5', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile='+shlex.quote(str(vm/'known_hosts')),
            '-p', str(port), 'augmentor-proof@127.0.0.1']


def begin_receipt(path, receipt):
    # Existing or interrupted evidence refuses a new mutation, even at the same
    # artifact. The host receipt is deliberately retained after every outcome.
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'w') as stream:
        json.dump(receipt, stream, indent=2); stream.write('\n')
        stream.flush(); os.fsync(stream.fileno())


def request_once(ssh, code, receipt):
    receipt['singleRebootRequestAttempted'] = True
    # Never retry this dispatch after timeout or a lost connection. A new boot
    # identity, not SSH's exit status, is the later outcome evidence.
    try:
        result = subprocess.run(ssh+['/usr/bin/python3 -I -B -'], input=code,
                                text=True, capture_output=True, timeout=30)
        receipt['requestExitCode'] = result.returncode
        receipt['requestStdout'] = result.stdout
        receipt['requestStderr'] = result.stderr
    except subprocess.TimeoutExpired:
        receipt['requestTransportTimeout'] = True


GUEST = '''import importlib.util,json,os,socket,subprocess,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('reboot_qualification',Path.home()/'gnome-vm-qualification.py')
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
contract=q.verified_profile(target,source)
assert contract['selection']['artifactSha256']==artifact
assert not os.path.lexists(Path.home()/'noble-shortcut-proof-state.json')
assert not (Path.home()/'.config/systemd/user/augmentor-desktop.service.d/90-owned-settings-proof.conf').exists()
env=dict(row.split('=',1) for row in subprocess.check_output(['systemctl','--user','show-environment'],text=True,timeout=20).splitlines() if '=' in row)
assert env['XDG_SESSION_TYPE']=='wayland' and env['XDG_CURRENT_DESKTOP']==q.PROFILES[target]['desktop']
for key in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','XDG_CURRENT_DESKTOP','XDG_SESSION_TYPE','DBUS_SESSION_BUS_ADDRESS'):
 if key in env:os.environ[key]=env[key]
def exchange(suffix=''):
 with socket.socket(socket.AF_UNIX) as client:
  client.settimeout(10)
  try:client.connect('/run/user/1000/augmentor-linux-pi'+suffix+'.sock')
  except (FileNotFoundError,ConnectionRefusedError):return None
  client.sendall(b'maintenance.status');return json.loads(client.makefile('rb').readline(16384))
status=exchange();assert status and status['buildRoot']==contract['root']
assert not any(status[k] for k in ('running','draftPresent','online','repairing')) and exchange('-secondary') is None
assert int(subprocess.check_output(['systemctl','--user','show','augmentor-desktop.service','--value','-p','MainPID'],text=True,timeout=20))==status['pid']
if action=='reboot':
 assert status['accepted'] and not status['busy']
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot
 print('One owned guest reboot requested.',flush=True)
 subprocess.run(['sudo','-n','systemctl','reboot'],check=True,timeout=15)
else:
 if action=='before':assert status['accepted'] and not status['busy']
 sys.path.insert(0,str(Path(contract['root'])/'services/desktop'))
 from gnome import GnomeObserver
 from gi.repository import Gio
 scene=GnomeObserver(Gio.bus_get_sync(Gio.BusType.SESSION,None)).read()
 assert scene['guards']['screenShieldAvailable'] and not scene['guards']['locked']
 sessions=[]
 for row in subprocess.check_output(['loginctl','list-sessions','--no-legend'],text=True,timeout=20).splitlines():
  fields=row.split()
  if len(fields)>3 and fields[2:4]==['augmentor-proof','seat0']:
   properties=dict(line.split('=',1) for line in subprocess.check_output(['loginctl','show-session',fields[0],'-p','Type','-p','Class','-p','State','-p','Active','-p','Seat'],text=True,timeout=20).splitlines())
   sessions.append(properties)
 assert sessions==[{'Seat':'seat0','Type':'wayland','Class':'user','Active':'yes','State':'active'}]
 print(json.dumps({'bootId':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'contract':contract,'status':status,'scene':scene,'graphicalSessions':sessions,'packageAndSecurityVerified':True}))
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory', type=Path, required=True)
    p.add_argument('--identity', type=Path, required=True)
    p.add_argument('--target', choices=PROFILES, required=True)
    p.add_argument('--source', required=True)
    p.add_argument('--artifact', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if not re.fullmatch('[a-f0-9]{40}', a.source) or not re.fullmatch('[a-f0-9]{64}', a.artifact):
        p.error('Exact source and selected artifact digests are required.')
    out = a.output.resolve()
    if not out.is_relative_to(ROOT/'outputs') or out.exists():
        p.error('Use a fresh private output path.')
    out.parent.mkdir(parents=True, exist_ok=True)
    receipt_path = Path(str(out)+'.run.json')
    receipt = {'format': 'augmentor-owned-selected-reboot-run/1', 'target': a.target,
               'source': a.source, 'artifactSha256': a.artifact,
               'proofSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'phase': 'preflight', 'singleRebootRequestAttempted': False}
    begin_receipt(receipt_path, receipt)
    ssh = verify_host(a.directory, a.identity, a.target)
    helper = ROOT/'release/gnome-vm-qualification.py'
    subprocess.run(ssh+['test ! -e ~/noble-shortcut-proof-state.json && test ! -L ~/noble-shortcut-proof-state.json'],
                   check=True, capture_output=True, timeout=20)
    subprocess.run(ssh+['umask 077; cat > ~/gnome-vm-qualification.py'],
                   input=helper.read_bytes(), check=True, capture_output=True, timeout=20)
    digest = subprocess.check_output(ssh+['sha256sum ~/gnome-vm-qualification.py'], text=True, timeout=20).split()[0]
    assert digest == hashlib.sha256(helper.read_bytes()).hexdigest()
    receipt['qualificationHelperSha256'] = digest
    def code(action, boot=None):
        return 'target='+repr(a.target)+'\nsource='+repr(a.source)+'\nartifact='+repr(a.artifact)+'\naction='+repr(action)+'\nboot='+repr(boot)+'\n'+GUEST
    def inspect(action):
        result = subprocess.run(ssh+['/usr/bin/python3 -I -B -'], input=code(action),
                                text=True, capture_output=True, timeout=160)
        if result.returncode:raise RuntimeError('Read-only '+action+' refused: '+result.stderr)
        return json.loads(result.stdout)
    try:
        before = inspect('before'); receipt['before'] = before; receipt['phase'] = 'request-pending'
        receipt_path.write_text(json.dumps(receipt, indent=2)+'\n')
        request_once(ssh, code('reboot', before['bootId']), receipt)
        receipt['phase'] = 'observe-new-boot'; receipt_path.write_text(json.dumps(receipt, indent=2)+'\n')
        deadline = time.monotonic()+300; after = None; last_error = ''
        while time.monotonic() < deadline:
            try:
                candidate = inspect('after')
                if candidate['bootId'] != before['bootId']:
                    if candidate['contract'] != before['contract']:
                        raise ValueError('Selected artifact changed across reboot.')
                    if candidate['status']['pid'] == before['status']['pid'] and candidate['scene']['epoch'] == before['scene']['epoch']:
                        raise ValueError('No new graphical application/observer generation.')
                    after = candidate; break
            except (RuntimeError, subprocess.TimeoutExpired) as error:last_error = str(error)
            time.sleep(2)
        if after is None:raise RuntimeError('No verified graphical recovery after one request: '+last_error)
        report = {'format':'augmentor-owned-selected-reboot-proof/1','passed':True,
                  'target':a.target,'source':a.source,'artifactSha256':a.artifact,
                  'proofSha256':receipt['proofSha256'],'qualificationHelperSha256':digest,
                  'singleRebootRequest':True,'kernelBootIdentityChanged':True,
                  'sameSelectedArtifactAfterReboot':True,'serviceOwnsActualAppAfterReboot':True,
                  'realWaylandLoginAfterReboot':True,'before':before,'after':after,
                  'loginAuthenticationTested':False,'shortcutDeliveryTested':False,
                  'connectedHarnessTested':False,'gnomeInputToolsEnabled':False}
        receipt['phase'] = 'complete'
        begin_receipt(out, report)
        print(json.dumps({k:v for k,v in report.items() if k not in ('before','after')}))
    except BaseException as error:
        receipt['phase'] = 'failed'; receipt['failure'] = str(error); raise
    finally:receipt_path.write_text(json.dumps(receipt, indent=2)+'\n')


if __name__ == '__main__':main()
