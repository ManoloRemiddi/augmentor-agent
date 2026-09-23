#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Run inside a disposable Fedora container, never on the user's host."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

if 'Fedora' not in Path('/etc/os-release').read_text() or not Path('/run/.containerenv').exists():
    raise SystemExit('This proof requires a disposable Fedora container')
rpm=Path(sys.argv[1]).resolve()
def run(args,**kw):return subprocess.run(args,check=True,text=True,**kw)
run(['dnf','-y','install',str(rpm)])
run(['rpm','-V','augmentor-agent'])
app=Path('/usr/lib/augmentor')
sys.path.insert(0,str(app/'services/lifecycle'))
from lease import hold
# No dpkg is available: real startup must pass through the RPM-aware lease.
run(['runuser','-u','nobody','--','/usr/bin/python3',str(app/'scripts/run-component.py'),'runtime',str(app/'node/bin/node'),'--version'])
Path('/tmp/augmentor-fedora-user').mkdir(mode=0o777,exist_ok=True)
os.chmod('/tmp/augmentor-fedora-user',0o777)
run(['runuser','-u','nobody','--','env','HOME=/tmp/augmentor-fedora-user','QT_QPA_PLATFORM=offscreen','augmentor-agent','--preview','--screenshot','/tmp/augmentor-fedora-user/window.png'])
image=Path('/tmp/augmentor-fedora-user/window.png');assert image.stat().st_size>1000
for pattern in ('test_window.py','test_markdown.py'):
    run(['python3','-m','unittest','discover','-s','/tests','-p',pattern],env={**os.environ,'QT_QPA_PLATFORM':'offscreen','PYTHONPATH':str(app/'apps/native'),'HOME':'/tmp/augmentor-fedora-user'})
# An active runtime lease must prevent payload replacement.
holder=subprocess.Popen(['/usr/bin/python3',str(app/'scripts/run-component.py'),'runtime','/usr/bin/python3','-u','-c','import time; print("ready",flush=True); time.sleep(90)'],stdout=subprocess.PIPE,text=True)
try:
    assert holder.stdout.readline().strip()=='ready'
    blocked=subprocess.run(['dnf','-y','reinstall',str(rpm)],capture_output=True,text=True)
    assert 'Augmentor is still open' in blocked.stdout+blocked.stderr,blocked.stdout+blocked.stderr
    run(['rpm','-V','augmentor-agent'])
    removal=subprocess.run(['dnf','-y','remove','augmentor-agent','--setopt=clean_requirements_on_remove=False'],capture_output=True,text=True)
    assert 'Augmentor is still open' in removal.stdout+removal.stderr
    run(['rpm','-q','augmentor-agent'])
finally:
    holder.terminate();holder.wait(timeout=10)
run(['dnf','-y','reinstall',str(rpm)])
assert not list(Path('/run/augmentor').glob('*.pending'))
run(['rpm','-V','augmentor-agent'])
sentinel=Path('/tmp/augmentor-fedora-user/keep-my-data');sentinel.write_text('preserved')
versions=subprocess.check_output(['rpm','-q','python3','python3-pyside6','python3-numpy','qt6-qtbase'],text=True).splitlines()
run(['dnf','-y','remove','augmentor-agent','--setopt=clean_requirements_on_remove=False'])
assert sentinel.read_text()=='preserved'
assert not (app/'release.json').exists()
run(['dnf','-y','install',str(rpm)])
run(['rpm','-V','augmentor-agent'])
report={'target':'Fedora 44 x86_64 container','rpm':rpm.name,'sha256':hashlib.file_digest(rpm.open('rb'),'sha256').hexdigest(),'versions':versions,'dnfInstall':True,'nonRootRuntimeLease':True,'nonRootQtRender':True,'nativeWindowAndMarkdownTests':True,'activeRemovalBlocked':True,'activeReinstallBlocked':True,'idleReinstall':True,'removePreservesUserFiles':True,'reinstallAfterRemove':True,'realDesktopSessionTested':False,'dshModelTurnTested':False}
Path('/tmp/fedora-proof.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
