#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Provision first graphical login in the marked private Noble QEMU guest only.

Install a clean Noble candidate and prepare its offline Python runtime first.
This configures fixture autologin/startup, not successful desktop acceptance.
Never run against a host or an already logged-in graphical fixture user.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

MARKER='Isolated Augmentor Ubuntu 24.04 GNOME qualification VM\n'
ROOT=Path('/usr/lib/augmentor')


def validate_guest(info,marker,uid,user,virtualization):
    if (marker!=MARKER or uid==0 or user!='augmentor-proof' or virtualization!='qemu' or
            info.get('ID')!='ubuntu' or info.get('VERSION_ID')!='24.04'):
        raise ValueError('Only the dedicated ordinary user in the marked Ubuntu 24.04 QEMU guest may run this.')


def run(arguments,timeout=30):
    return subprocess.check_output(arguments,text=True,timeout=timeout).strip()


def main():
    info={key:value.strip('"') for key,value in (line.split('=',1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)}
    marker=Path('/etc/augmentor-test-vm')
    validate_guest(info,marker.read_text() if marker.is_file() else '',os.geteuid(),os.environ.get('USER'),run(['systemd-detect-virt']))
    # Refuse repeated provisioning that could interrupt a real guest session.
    for line in run(['loginctl','list-sessions','--no-legend']).splitlines():
        fields=line.split()
        if len(fields)>3 and fields[1]==str(os.getuid()) and 'seat0' in fields:
            raise ValueError('The fixture user already has a graphical session; inspect it without reprovisioning.')
    release=json.loads((ROOT/'release.json').read_text())
    if (release.get('version')!='0.2.13' or release.get('source',{}).get('dirty') is not False or
            release.get('target')!='ubuntu24.04-amd64' or not release.get('pythonRuntime')):
        raise ValueError('Install a verified clean Noble 0.2.13 candidate first.')
    if run(['dpkg','--verify','augmentor-runtime','augmentor-desktop']):
        raise ValueError('Installed package files differ; do not provision a patched payload.')
    if Path('/sys/module/apparmor/parameters/enabled').read_text().strip()!='Y':
        raise ValueError('Keep Ubuntu AppArmor enabled in this fixture.')
    selected_python=run(['/usr/bin/python3',str(ROOT/'scripts/linux-python-runtime.py'),'resolve','--app-root',str(ROOT)],timeout=180)
    uuid='observer@augmentoragent.com'
    source=ROOT/'services/desktop/gnome-extension'/uuid
    metadata=json.loads((source/'metadata.json').read_text())
    if '46' not in metadata.get('shell-version',[]) or metadata.get('session-modes')!=['user']:
        raise ValueError('The installed candidate lacks the user-only GNOME 46 observer profile.')
    session=Path('/usr/share/wayland-sessions/ubuntu.desktop')
    if not session.is_file() or 'GNOME_SHELL_SESSION_MODE=ubuntu' not in session.read_text():
        raise ValueError('Install the actual Ubuntu Wayland session before provisioning.')
    destination=Path.home()/'.local/share/gnome-shell/extensions'/uuid
    if destination.exists():
        for name in ('extension.js','metadata.json'):
            if (destination/name).read_bytes()!=(source/name).read_bytes():
                raise ValueError('Existing observer differs; do not overwrite it silently.')
    else:shutil.copytree(source,destination)
    import gi
    from gi.repository import Gio
    settings=Gio.Settings.new('org.gnome.shell');enabled=settings.get_strv('enabled-extensions')
    if uuid not in enabled and not settings.set_strv('enabled-extensions',enabled+[uuid]):
        raise RuntimeError('Private observer registration refused.')
    Gio.Settings.sync()
    subprocess.run(['/usr/bin/python3',str(ROOT/'scripts/install-desktop-startup.py'),'--root',str(ROOT),
                    '--python',selected_python,'--node',str(ROOT/'node/bin/node')],check=True,timeout=180)
    # GDM 46 reads AccountsService Session and SessionType. Use its public
    # setters to request Ubuntu Wayland; actual login must be checked later.
    account='/org/freedesktop/Accounts/User'+str(os.getuid())
    for method,value in (('SetSession','ubuntu'),('SetSessionType','wayland')):
        run(['sudo','gdbus','call','--system','--dest','org.freedesktop.Accounts','--object-path',account,
             '--method','org.freedesktop.Accounts.User.'+method,value])
    configure='''from pathlib import Path
import os,shutil,tempfile
assert Path('/etc/augmentor-test-vm').read_text()=="Isolated Augmentor Ubuntu 24.04 GNOME qualification VM\\n"
p=Path('/etc/gdm3/custom.conf');backup=p.with_name('custom.conf.augmentor-fixture-original')
if p.exists() and not backup.exists():shutil.copy2(p,backup)
descriptor,name=tempfile.mkstemp(prefix='augmentor-fixture-',dir=p.parent)
try:
    with os.fdopen(descriptor,'w') as stream:stream.write("[daemon]\\nAutomaticLoginEnable=True\\nAutomaticLogin=augmentor-proof\\n")
    os.chmod(name,0o644);os.replace(name,p)
finally:
    if os.path.exists(name):os.unlink(name)
'''
    run(['sudo','python3','-c',configure])
    run(['sudo','systemctl','set-default','graphical.target'])
    run(['sudo','systemctl','restart','gdm3'],timeout=60)
    report={'format':'augmentor-gnome-full-vm-provisioning/1','target':release['target'],
        'source':release['source'],'version':release['version'],'dpkgVerifiedBeforeStartup':True,
        'apparmorEnabledBeforeStartup':True,'python':selected_python,
        'observerSourceSha256':{name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in ('extension.js','metadata.json')},
        'provisioningSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'startupInstallerSha256':hashlib.sha256((ROOT/'scripts/install-desktop-startup.py').read_bytes()).hexdigest(),
        'requestedSession':'ubuntu','requestedSessionType':'wayland','defaultUbuntuExtensionsDisabled':False,
        'gdmAutologinRequested':True,'actualLoginTested':False,'applicationStartupTested':False,
        'modelRequestsTested':False,'gnomeInputToolsEnabled':False}
    out=Path.home()/'gnome-provisioning.json';out.write_text(json.dumps(report,indent=2)+'\n');out.chmod(0o600)
    print(json.dumps(report))


if __name__=='__main__':main()
