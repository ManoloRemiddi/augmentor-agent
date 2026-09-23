#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Build a Fedora x86_64 preview RPM from the checksum-verified Linux bundle.

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

def guard(version):
    source=(ROOT/'release/debian-maintainer.py').read_text()
    source=source.replace('@HOOK@','rpm-pre').replace('@VERSION@',version)
    source=source.replace('Run dpkg --configure -a after an interrupted upgrade.','Complete or retry the interrupted DNF transaction before starting Augmentor.')
    parts=[]
    for component in ('runtime','desktop'):
        parts.append("/usr/bin/python3 -I <<'AUGMENTOR_HOOK'\n"+source.replace('@COMPONENT@',component)+"\naction='upgrade'\nbegin()\nAUGMENTOR_HOOK\n")
    return 'set -e\n'+''.join(parts)

def build(bundle,out):
    verification=json.loads((bundle/'VERIFICATION.json').read_text())
    version=verification['version']
    if not all(c.isdigit() or c=='.' for c in version): raise ValueError('Invalid version')
    sums={line.split()[1].lstrip('*'):line.split()[0] for line in (bundle/'SHA256SUMS').read_text().splitlines() if line.strip()}
    inputs=[bundle/f'augmentor-{kind}_{version}_amd64.deb' for kind in ('runtime','desktop')]
    for path in inputs:
        if sums.get(path.name)!=digest(path):raise ValueError('Payload checksum mismatch: '+path.name)
        if subprocess.check_output(['dpkg-deb','-f',str(path),'Architecture'],text=True).strip()!='amd64':raise ValueError('x86_64 payload required')
    out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='augmentor-fedora-') as temp:
        top=Path(temp);payload=top/'payload';payload.mkdir()
        for source in inputs:subprocess.run(['dpkg-deb','-x',str(source),str(payload)],check=True)
        # Preserve the reviewed payload except the recorded RPM lifecycle adapter.
        # Separate Fedora packaging provenance avoids rewriting release.json.
        shutil.copy2(ROOT/'services/lifecycle/lease.py',payload/'usr/lib/augmentor/services/lifecycle/lease.py')
        record={'overrides':{'services/lifecycle/lease.py':digest(ROOT/'services/lifecycle/lease.py')},'target':'fedora44-x86_64','version':version,'payloadSource':verification,'inputDebs':{p.name:digest(p) for p in inputs}}
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
Release: 1.fc44
Summary: Augmentor Agent Desktop and browser companion (Fedora preview)
License: LicenseRef-Augmentor-MIT-Resale-1.0 AND MIT AND BSD-3-Clause AND Apache-2.0
URL: https://github.com/ManoloRemiddi/augmentor-agent
BuildArch: x86_64
AutoReqProv: no
Requires: rpm
Requires: python3 >= 3.11
Requires: python3-pyside6 >= 6.8.2
Requires: python3-pyyaml, python3-websocket-client, python3-pygments >= 2.18, python3-numpy >= 1.24
Requires: python3-gobject, qt6-qtsvg, at-spi2-core, gstreamer1, pipewire-gstreamer, gstreamer1-plugins-base
Requires: dejavu-sans-fonts, glib2, glibc >= 2.36, libstdc++
Requires(pretrans): python3
Requires(preun): python3
Requires(postun): python3
Requires(posttrans): python3
Conflicts: augmentor-runtime, augmentor-desktop

%description
Native Augmentor Agent and Chromium companion with DSH integration.
Experimental Fedora 44 package using the verified 0.2.9 Linux payload.
Dependency notices are installed in /usr/lib/augmentor/licenses.
DSH, models and the unpacked Browser extension are installed separately.

%prep
%build
%install
mkdir -p %{{buildroot}}
cp -a {shlex.quote(str(payload))}/. %{{buildroot}}/

%pretrans
{guard(version)}
%posttrans
{clean}
%preun
if [ "$1" -eq 0 ]; then
{guard(version)}
fi

%postun
if [ "$1" -eq 0 ]; then
{clean}
fi

%files
/usr/lib/augmentor
/usr/lib/tmpfiles.d/augmentor.conf
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
        (out/'artifacts.json').write_text(json.dumps(record,indent=2)+'\n')
        (out/'SHA256SUMS').write_text(f'{digest(target)}  {target.name}\n')
        print(json.dumps(record['rpm']))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--out',type=Path,default=ROOT/'outputs/fedora-0.2.9')
    args=p.parse_args();build(args.bundle.resolve(),args.out.resolve())
