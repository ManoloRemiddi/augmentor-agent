#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Build a Fedora x86_64 preview RPM from a checksum-verified Linux payload.

Reuses the reviewed payload, not Debian dependency metadata or dpkg hooks.
Requires dpkg-deb and rpmbuild on the build machine; neither is needed to install.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    with path.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def guard(version,fedora='44',*,removal=False):
    if fedora not in ('43','44'):raise ValueError('Use an explicit Fedora 43 or 44 target.')
    source=(ROOT/'release/debian-maintainer.py').read_text()
    source=source.replace('@HOOK@','rpm-preun' if removal else 'rpm-pre').replace('@VERSION@',version).replace('@TARGET@',f'fedora{fedora}-x86_64')
    source=source.replace('Run dpkg --configure -a after an interrupted upgrade.','Complete or retry the interrupted DNF transaction before starting Augmentor.')
    parts=[]
    for component in ('runtime','desktop'):
        parts.append("/usr/bin/python3 -I <<'AUGMENTOR_HOOK'\n"+source.replace('@COMPONENT@',component)+"\naction="+repr('remove' if removal else 'upgrade')+"\nbegin()\nAUGMENTOR_HOOK\n")
    return 'set -e\n'+''.join(parts)


def post_transaction():
    # Match Debian's active-user uinput setup. Missing udev/kernel tools in a
    # container do not establish real input permission or a passing product.
    return """/usr/bin/python3 -I <<'AUGMENTOR_POST'
from pathlib import Path
import shutil
import subprocess
for c in ('runtime','desktop'):
    Path('/run/augmentor/augmentor-'+c+'.pending').unlink(missing_ok=True)
for arguments in (['modprobe','-q','uinput'],['udevadm','control','--reload-rules'],['udevadm','trigger','--subsystem-match=misc','--sysname-match=uinput']):
    if shutil.which(arguments[0]):
        subprocess.run(arguments,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10,check=False)
AUGMENTOR_POST
"""

def payload_manifest(bundle):
    if (bundle/'artifacts.json').exists():
        verification=json.loads((bundle/'artifacts.json').read_text())
        sums={item['file']:item['sha256'] for item in verification['artifacts']}
    else:
        name='bundle.json' if (bundle/'bundle.json').exists() else 'VERIFICATION.json'
        verification=json.loads((bundle/name).read_text())
        sums={line.split()[1].lstrip('*'):line.split()[0] for line in (bundle/'SHA256SUMS').read_text().splitlines() if line.strip()}
        if name=='bundle.json' and any(sums.get(key)!=value for key,value in verification['sha256'].items()):
            raise ValueError('Complete bundle checksum records differ.')
    return verification,sums


def build(bundle,out,fedora='44'):
    if fedora not in ('43','44'):raise ValueError('Use Fedora 43 or 44; other releases require qualification.')
    verification,sums=payload_manifest(bundle)
    if verification.get('pythonRuntime') is not None or verification.get('target')=='ubuntu24.04-amd64':
        raise ValueError('The Noble runtime payload cannot be repackaged for Fedora.')
    version=verification['version']
    if not all(c.isdigit() or c=='.' for c in version): raise ValueError('Invalid version')
    inputs=[bundle/f'augmentor-{kind}_{version}_amd64.deb' for kind in ('runtime','desktop')]
    for path in inputs:
        if sums.get(path.name)!=digest(path):raise ValueError('Payload checksum mismatch: '+path.name)
        if subprocess.check_output(['dpkg-deb','-f',str(path),'Architecture'],text=True).strip()!='amd64':raise ValueError('x86_64 payload required')
    out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='augmentor-fedora-') as temp:
        top=Path(temp);payload=top/'payload';payload.mkdir()
        for source in inputs:subprocess.run(['dpkg-deb','-x',str(source),str(payload)],check=True)
        app=payload/'usr/lib/augmentor'
        release=json.loads((app/'release.json').read_text())
        if (app/'linux-python-runtime.json').exists() or (app/'linux-python-runtime.json').is_symlink() or release.get('pythonRuntime') is not None:
            raise ValueError('A declared Noble runtime cannot be used by this Fedora artifact.')
        if release['version']!=version:raise ValueError('Runtime product version differs from the input manifest.')
        if 'source' in verification and verification['source']!=release['source']:
            raise ValueError('Runtime source differs from the input manifest.')
        release['target']=f'fedora{fedora}-x86_64'
        (app/'release.json').write_text(json.dumps(release,indent=2)+'\n')
        desktop=(payload/'usr/share/augmentor/desktop-version').read_text().strip()
        if desktop!=version:raise ValueError('Desktop and runtime package versions differ.')
        # Current source already contains RPM-aware leases. Never silently replace
        # a reviewed dependency with this checkout's different implementation.
        if 'fedora-package.json' not in (app/'services/lifecycle/lease.py').read_text():
            raise ValueError('The payload lacks RPM-aware lifecycle support; rebuild it from current source.')
        record={'overrides':{},'target':f'fedora{fedora}-x86_64','version':version,'source':release['source'],
                'maintainerSourceSha256':digest(ROOT/'release/debian-maintainer.py'),
                'packagingRecipeSha256':digest(ROOT/'scripts/package-fedora.py'),
                'payloadSource':verification,'inputDebs':{p.name:digest(p) for p in inputs}}
        (payload/'usr/lib/augmentor/fedora-package.json').write_text(json.dumps(record,indent=2)+'\n')
        # Fedora Chromium also accepts this distro-specific system host directory.
        dest=payload/'usr/lib64/chromium/native-messaging-hosts';dest.mkdir(parents=True)
        shutil.copy2(payload/'etc/chromium/native-messaging-hosts/com.augmentor.agent.json',dest)
        for d in ('SPECS','BUILD','BUILDROOT','RPMS','SOURCES','SRPMS'):(top/d).mkdir()
        clean="/usr/bin/python3 -I <<'AUGMENTOR_CLEAN'\nfrom pathlib import Path\nfor c in ('runtime','desktop'):\n    Path('/run/augmentor/augmentor-'+c+'.pending').unlink(missing_ok=True)\nAUGMENTOR_CLEAN\n"
        spec=f'''# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
%global debug_package %{{nil}}
%global __os_install_post %{{nil}}
%global _build_id_links none
Name: augmentor-agent
Version: {version}
Release: 1.fc{fedora}
Summary: Augmentor Agent Desktop and browser companion (Fedora preview)
License: LicenseRef-Augmentor-MIT-Resale-1.0 AND MIT AND BSD-3-Clause AND Apache-2.0
URL: https://github.com/ManoloRemiddi/augmentor-agent
BuildArch: x86_64
AutoReqProv: no
Requires: rpm
Requires: python3 >= 3.11
Requires: python3-keyring >= 25.6, python3-secretstorage, gnome-keyring
Requires: python3-pyside6 >= 6.8.2
Requires: python3-pyyaml, python3-websocket-client, python3-pygments >= 2.18, python3-numpy >= 1.24
Requires: python3-gobject, gtk4, qt6-qtsvg, at-spi2-core, gstreamer1, pipewire-gstreamer, gstreamer1-plugins-base
Requires: qt6-qtdeclarative
Requires: wmctrl
Requires: dejavu-sans-fonts, glib2, glibc >= 2.39, libstdc++
Requires: libstdc++.so.6(GLIBCXX_3.4.32)(64bit)
Requires: gtk3, webkit2gtk4.1, javascriptcoregtk4.1, gtk-layer-shell, libappindicator-gtk3
Requires: openblas-serial, vulkan-loader, alsa-lib, alsa-plugins-pulseaudio
Requires: which, xdotool, wl-clipboard, xorg-x11-server-Xwayland, systemd-udev, kmod
Requires(pre): python3
Requires(preun): python3
Requires(postun): python3
Requires(posttrans): python3
Conflicts: augmentor-runtime, augmentor-desktop

%description
Native Augmentor Agent and Chromium companion with DSH integration.
Experimental Fedora {fedora} package using the verified {version} Linux payload.
Dependency notices are installed in /usr/lib/augmentor/licenses.
DSH, models and the unpacked Browser extension are installed separately.

%prep
%build
%install
mkdir -p %{{buildroot}}
cp -a {shlex.quote(str(payload))}/. %{{buildroot}}/

%pre
{guard(version,fedora)}
%posttrans
{post_transaction()}
%preun
if [ "$1" -eq 0 ]; then
{guard(version,fedora,removal=True)}
fi

%postun
if [ "$1" -eq 0 ]; then
{clean}
fi

%files
/usr/lib/augmentor
/usr/lib/tmpfiles.d/augmentor.conf
/usr/lib/udev/rules.d/70-augmentor-dictation.rules
/usr/lib/modules-load.d/augmentor-dictation.conf
/usr/lib64/chromium/native-messaging-hosts/com.augmentor.agent.json
/usr/bin/augmentor-agent
/usr/bin/augmentor-runtime
/usr/bin/augmentor-browser-host
/usr/bin/augmentor-maintenance
/usr/share/augmentor
/usr/share/applications/com.augmentor.Agent.desktop
/usr/share/icons/hicolor/scalable/apps/com.augmentor.Agent.svg
/usr/share/doc/augmentor-runtime
/usr/share/doc/augmentor-desktop
/etc/chromium/native-messaging-hosts/com.augmentor.agent.json
/etc/opt/chrome/native-messaging-hosts/com.augmentor.agent.json
'''
        path=top/'SPECS/augmentor-agent.spec';path.write_text(spec)
        subprocess.run(['rpmbuild','-bb','--define',f'_topdir {top}',str(path)],check=True)
        rpm=next((top/'RPMS/x86_64').glob('*.rpm'));target=out/rpm.name;shutil.copy2(rpm,target)
        record['rpm']={'file':target.name,'sha256':digest(target),'bytes':target.stat().st_size}
        record['artifacts']=[record['rpm']]
        (out/'artifacts.json').write_text(json.dumps(record,indent=2)+'\n')
        (out/'SHA256SUMS').write_text(f'{digest(target)}  {target.name}\n')
        print(json.dumps(record['rpm']))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    inputs=p.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--bundle',type=Path,help='Verified legacy or complete Linux bundle.')
    inputs.add_argument('--debian',type=Path,help='Current Debian artifacts.json and matching packages.')
    p.add_argument('--fedora',choices=('43','44'),default='44')
    p.add_argument('--out',type=Path,default=ROOT/'outputs/fedora')
    args=p.parse_args();build((args.debian or args.bundle).resolve(),args.out.resolve(),args.fedora)
