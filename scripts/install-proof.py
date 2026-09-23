#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Verify release extraction, fresh install, upgrade, runtime boot and removal."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
root=Path(__file__).resolve().parents[1]
work=Path(tempfile.mkdtemp(prefix='augmentor-pi-install-'))
env={**os.environ,'XDG_DATA_HOME':str(work/'data'),'AUGMENTOR_PI_CONFIG':str(work/'config'),'AUGMENTOR_PI_STATE':str(work/'state'),'QT_QPA_PLATFORM':'offscreen'}
version=json.loads((root/'package.json').read_text())['version']
archive=root/'outputs'/f'augmentor-linux-pi-{version}.tar.gz'
with tarfile.open(archive) as source:source.extractall(work,filter='data')
extracted=work/f'augmentor-linux-pi-{version}';installed=work/'data/augmentor-pi/app'
def run(command):subprocess.run(command,env=env,cwd=extracted,check=True)
run([sys.executable,str(extracted/'scripts/install.py'),'--no-desktop'])
run([sys.executable,str(installed/'scripts/setup-local.py')])
run([sys.executable,str(installed/'scripts/ensure-runtime.py')])
run([str(installed/'scripts/augmentor-linux'),'--preview','--screenshot',str(work/'installed.png')])
assert (work/'installed.png').exists()
# The installed release supplies its own dependency tree; no source checkout imports.
run([sys.executable,str(installed/'scripts/doctor.py')])
marker=work/'state/preserved.txt';marker.write_text('keep user state')
# Update from the installed release's exact dependency tree to exercise replacement.
run([sys.executable,str(installed/'scripts/install.py'),'--prefix',str(work/'data/augmentor-pi/update-source'),'--no-desktop'])
update=work/'data/augmentor-pi/update-source'
run([sys.executable,str(update/'scripts/install.py'),'--no-desktop'])
assert marker.read_text()=='keep user state'
run([sys.executable,str(installed/'scripts/ensure-runtime.py')])
run([sys.executable,str(installed/'scripts/uninstall.py')])
assert not installed.exists();assert marker.exists();assert (work/'config/agent/models.json').exists()
result={'work':str(work),'freshInstall':True,'runtimeBoot':True,'installedQtPreview':True,'upgrade':True,'uninstall':True,'statePreserved':True}
(root/'outputs/install-proof.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
