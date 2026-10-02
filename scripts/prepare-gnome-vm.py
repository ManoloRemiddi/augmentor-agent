#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Prepare a signed Fedora Cloud overlay and owned QEMU VM for GNOME acceptance.

Writes only an ignored outputs directory, with dedicated SSH credentials. Does
not install host packages, attach host filesystems/devices or provision GNOME.
The guest has outbound NAT for subsequent package provisioning; only its SSH
port is forwarded, on host loopback. This is infrastructure, not acceptance.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import uuid

ROOT=Path(__file__).resolve().parents[1]
USER='augmentor-proof'
NAME='augmentor-gnome-fedora44'

def run(arguments,**kwargs):
    return subprocess.run(arguments,check=True,capture_output=True,text=True,**kwargs).stdout.strip()

def exclusive(path,content,mode=0o600):
    with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,mode),'w') as stream:
        stream.write(content)

def prepare(vm,manifest,port,boot):
    if os.geteuid()==0:raise ValueError('Run as an ordinary user; this needs no host administrative privileges.')
    vm=vm.resolve();outputs=(ROOT/'outputs').resolve()
    if not vm.is_relative_to(outputs) or vm==outputs:
        raise ValueError('Use a dedicated ignored subdirectory beneath this worktree outputs/.')
    vm.mkdir(parents=True,exist_ok=True,mode=0o700);vm.chmod(0o700)
    with (vm/'fixture.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        pidfile=vm/'qemu.pid'
        if pidfile.exists():
            pid=int(pidfile.read_text())
            if Path(f'/proc/{pid}').exists():
                raise ValueError('A process still owns the recorded VM PID; inspect it before another boot.')
            pidfile.unlink()
        image=vm/manifest['image'].rsplit('/',1)[-1]
        checksum=vm/manifest['checksum'].rsplit('/',1)[-1]
        keyring=vm/'fedora.gpg'
        for path,url in ((checksum,manifest['checksum']),(keyring,manifest['keyring']),(image,manifest['image'])):
            if not path.exists():
                temporary=path.with_name(path.name+'.download')
                run(['curl','--fail','--location','--retry','2','--max-time','900','--output',str(temporary),url],timeout=930)
                temporary.replace(path)
            if path.is_symlink() or not path.is_file():raise ValueError('Fixture download must be a regular file.')
        status=run(['gpgv','--keyring',str(keyring),'--status-fd','1',str(checksum)],timeout=30)
        if not any(line.startswith('[GNUPG:] VALIDSIG '+manifest['signingFingerprint']+' ') for line in status.splitlines()):
            raise ValueError('Checksum signer differs from the pinned official Fedora 44 fingerprint.')
        signed_line='SHA256 ('+image.name+') = '+manifest['sha256']
        if signed_line not in checksum.read_text().splitlines():raise ValueError('Signed checksum differs from pinned image.')
        with image.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if digest!=manifest['sha256'] or image.stat().st_size!=manifest['imageBytes']:
            raise ValueError('Base image differs from signed pinned bytes; never boot an incomplete download.')
        image.chmod(0o444)
        overlay=vm/'guest.qcow2'
        if not overlay.exists():
            run(['qemu-img','create','-f','qcow2','-F','qcow2','-b',str(image),str(overlay)],timeout=30)
            run(['qemu-img','resize',str(overlay),str(manifest['diskGiB'])+'G'],timeout=30)
        if overlay.is_symlink():raise ValueError('Do not use a symlink for the disposable guest.')
        overlay.chmod(0o600)
        identity=vm/'id_ed25519'
        if not identity.exists():
            run(['ssh-keygen','-q','-t','ed25519','-N','','-C',NAME,'-f',str(identity)],timeout=15)
        if identity.is_symlink() or identity.stat().st_uid!=os.getuid():raise ValueError('Use this ordinary user’s dedicated fixture key.')
        identity.chmod(0o600)
        seed=vm/'seed.iso'
        if not seed.exists():
            # The discarded random password permits GDM account validation.
            # SSH password authentication stays disabled; no owner key is used.
            password_hash=run(['openssl','passwd','-6','-stdin'],input=secrets.token_urlsafe(32)+'\n',timeout=10)
            user_data={'disable_root':True,'ssh_pwauth':False,
                'users':[{'name':USER,'shell':'/bin/bash','groups':['wheel'],
                    'sudo':['ALL=(ALL) NOPASSWD:ALL'],'lock_passwd':False,
                    'hashed_passwd':password_hash,'ssh_authorized_keys':[(vm/'id_ed25519.pub').read_text().strip()]}],
                'write_files':[{'path':'/etc/augmentor-test-vm','permissions':'0644',
                    'content':'Isolated Augmentor Fedora GNOME qualification VM\n'}]}
            exclusive(vm/'user-data','#cloud-config\n'+json.dumps(user_data,indent=2)+'\n')
            exclusive(vm/'meta-data',json.dumps({'instance-id':NAME+'-'+str(uuid.uuid4()),'local-hostname':NAME})+'\n')
            run(['genisoimage','-output',str(seed),'-volid','CIDATA','-joliet','-rock','user-data','meta-data'],cwd=vm,timeout=30)
            seed.chmod(0o600)
        record={'format':'augmentor-gnome-vm-infrastructure/1','base':manifest,
            'signedChecksumVerified':True,'baseHashVerified':True,'hostUser':os.getuid(),
            'guestUser':USER,'sshPort':port,'hostMounts':False,'hostDevicesAttached':False,
            'outboundGuestNat':True,'gnomeProvisioningPerformedByThisTool':False,'desktopAcceptanceTested':False,
            'qemuVersion':run(['qemu-system-x86_64','--version'],timeout=10).splitlines()[0],
            'sourceSha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('scripts/prepare-gnome-vm.py','release/fedora-gnome-vm.json')}}
        (vm/'infrastructure.json').write_text(json.dumps(record,indent=2)+'\n')
        if boot:
            if not 1024<=port<=65535:raise ValueError('Use an unprivileged dedicated SSH forwarding port.')
            with socket.socket() as probe:probe.bind(('127.0.0.1',port))
            run(['qemu-system-x86_64','-name',NAME,'-machine','q35,accel='+manifest['acceleration'],
                '-cpu',manifest['cpuModel'],'-smp',str(manifest['cpus']),'-m',str(manifest['memoryMiB']),
                '-drive','file=guest.qcow2,format=qcow2,if=virtio','-drive','file=seed.iso,format=raw,media=cdrom,readonly=on',
                '-device','virtio-vga','-display','none','-usb','-device','usb-tablet',
                '-netdev','user,id=net0,hostfwd=tcp:127.0.0.1:'+str(port)+'-:22','-device','virtio-net-pci,netdev=net0',
                '-serial','file:serial.log','-monitor','none','-qmp','unix:qmp.sock,server=on,wait=off',
                '-daemonize','-pidfile','qemu.pid'],cwd=vm,timeout=20)
        return record

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--ssh-port',type=int,default=22489)
    p.add_argument('--boot',action='store_true')
    a=p.parse_args()
    result=prepare(a.directory,json.loads((ROOT/'release/fedora-gnome-vm.json').read_text()),a.ssh_port,a.boot)
    print(json.dumps({'prepared':True,'bootRequested':a.boot,'sshPort':result['sshPort'],'desktopAcceptanceTested':False}))
