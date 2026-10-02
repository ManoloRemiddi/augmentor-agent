#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Provision graphical login only in the owned full Fedora GNOME test guest.

Run as its dedicated SSH user after installing GNOME and a verified package.
Uses the package's real per-user startup installer and a private observer copy.
Starts GDM with fixture autologin. Performs no model, microphone or input action.
This does not establish successful login or application startup.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

MARKER='Isolated Augmentor Fedora GNOME qualification VM\n'
if (not Path('/etc/augmentor-test-vm').is_file()
        or Path('/etc/augmentor-test-vm').read_text()!=MARKER
        or os.geteuid()==0 or os.environ.get('USER')!='augmentor-proof'
        or 'VERSION_ID=44' not in Path('/etc/os-release').read_text()
        or subprocess.check_output(['systemd-detect-virt'],text=True).strip()!='qemu'):
    raise SystemExit('Only the dedicated ordinary user in the owned Fedora 44 QEMU guest may run this.')
ROOT=Path('/usr/lib/augmentor')
release=json.loads((ROOT/'release.json').read_text())
if release.get('version')!='0.2.13' or release.get('source',{}).get('dirty') is not False:
    raise SystemExit('Install a verified clean 0.2.13 package before provisioning this fixture.')
subprocess.run(['rpm','-V','augmentor-agent'],check=True,timeout=30)
if subprocess.check_output(['getenforce'],text=True).strip()!='Enforcing':
    raise SystemExit('Keep SELinux enforcing in this full-session fixture.')
uuid='observer@augmentoragent.com'
source=ROOT/'services/desktop/gnome-extension'/uuid
destination=Path.home()/'.local/share/gnome-shell/extensions'/uuid
if destination.exists():
    for name in ('extension.js','metadata.json'):
        if (destination/name).read_bytes()!=(source/name).read_bytes():
            raise SystemExit('Existing private observer differs; do not overwrite it silently.')
else:shutil.copytree(source,destination)
import gi
from gi.repository import Gio
settings=Gio.Settings.new('org.gnome.shell')
enabled=settings.get_strv('enabled-extensions')
if uuid not in enabled:
    if not settings.set_strv('enabled-extensions',enabled+[uuid]):raise RuntimeError('Private observer registration refused.')
Gio.Settings.sync()
subprocess.run(['python3',str(ROOT/'scripts/install-desktop-startup.py'),
    '--root',str(ROOT),'--python','/usr/bin/python3','--node',str(ROOT/'node/bin/node')],check=True,timeout=30)
configuration='[daemon]\nAutomaticLoginEnable=True\nAutomaticLogin=augmentor-proof\n'
# The marker is checked again inside the privileged guest operation. No host
# configuration or owner desktop is reachable through this helper.
configure_code='''from pathlib import Path
import os,shutil,tempfile
assert Path('/etc/augmentor-test-vm').read_text()=="Isolated Augmentor Fedora GNOME qualification VM\\n"
p=Path('/etc/gdm/custom.conf');backup=p.with_name('custom.conf.augmentor-fixture-original')
if p.exists() and not backup.exists():shutil.copy2(p,backup)
descriptor,name=tempfile.mkstemp(prefix='augmentor-fixture-',dir=p.parent)
try:
    with os.fdopen(descriptor,'w') as stream:stream.write("[daemon]\\nAutomaticLoginEnable=True\\nAutomaticLogin=augmentor-proof\\n")
    os.chmod(name,0o644);os.replace(name,p)
finally:
    if os.path.exists(name):os.unlink(name)
'''
subprocess.run(['sudo','python3','-c',configure_code],check=True,timeout=10)
subprocess.run(['sudo','restorecon','/etc/gdm/custom.conf'],check=True,timeout=10)
subprocess.run(['sudo','systemctl','enable','gdm'],check=True,timeout=20)
subprocess.run(['sudo','systemctl','set-default','graphical.target'],check=True,timeout=20)
subprocess.run(['sudo','systemctl','start','gdm'],check=True,timeout=45)
report={'format':'augmentor-gnome-full-vm-provisioning/1','source':release['source'],
    'version':release['version'],'rpmVerifiedBeforeStartup':True,'selinuxEnforcingBeforeStartup':True,
    'observerSourceSha256':{name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in ('extension.js','metadata.json')},
    'provisioningSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'startupInstallerSha256':hashlib.sha256((ROOT/'scripts/install-desktop-startup.py').read_bytes()).hexdigest(),
    'desktopLauncherSha256':hashlib.sha256((ROOT/'scripts/desktop-launch.py').read_bytes()).hexdigest(),
    'gdmAutologinRequested':True,'actualLoginTested':False,'applicationStartupTested':False,
    'modelRequestsTested':False,'gnomeInputToolsEnabled':False}
out=Path.home()/'gnome-provisioning.json';out.write_text(json.dumps(report,indent=2)+'\n');out.chmod(0o600)
print(json.dumps(report))
