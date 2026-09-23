#!/bin/bash
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends ca-certificates npm python3-venv libportaudio2 /bundle/augmentor-runtime_*_amd64.deb /bundle/augmentor-desktop_*_amd64.deb
useradd -m -s /bin/bash reviewer
install -d -m 700 -o reviewer -g reviewer /tmp/augmentor-reviewer-runtime
runuser -u reviewer -- env XDG_RUNTIME_DIR=/tmp/augmentor-reviewer-runtime QT_QPA_PLATFORM=offscreen AUGMENTOR_FIXTURE_KEY=fixture \
  /usr/bin/python3 /bundle/setup.py --bundle /bundle --skip-packages --no-services --non-interactive \
  --model-url http://127.0.0.1:9/v1 --model fixture --api-key-env AUGMENTOR_FIXTURE_KEY
runuser -u reviewer -- env XDG_RUNTIME_DIR=/tmp/augmentor-reviewer-runtime QT_QPA_PLATFORM=offscreen \
  /home/reviewer/.local/share/augmentor/python/bin/python - <<'PY'
import json,os,subprocess
from pathlib import Path
version=json.loads(Path('/bundle/bundle.json').read_text())['version']
home=Path.home();data=home/'.local/share/augmentor';config=home/'.config';state=home/'.local/state/augmentor-install'
assert json.loads((state/'installation.json').read_text())['status']=='installed'
assert (state/'model.env').stat().st_mode & 0o077==0
assert json.loads((config/'augmentor/harnesses.json').read_text())['dsh']['version']==version
manifest=json.loads((data/'desktop.json').read_text());assert manifest['dshService']=='augmentor-dsh.service'
assert (config/'autostart/com.augmentor.Agent.desktop').is_file()
assert (data.parent/'applications/com.augmentor.Agent.secondary.desktop').is_file()
assert (data/'browser'/version/'voice.mjs').is_file()
assert (config/'chromium/NativeMessagingHosts/com.augmentor.agent.json').is_file()
assert (data/'dsh-home/profiles/web/node_modules/dsh-resonant-voice/package.json').is_file()
for role in ('linux','browser'):
    preset=data/'dsh-home/.agent-presets'/('augmentor-'+role+'-product')/'agent.cordis.yml'
    entries=json.loads(preset.read_text().split('\n',1)[1])
    adapter=[e for e in entries if e['id']=='augmentor-execution'];assert len(adapter)==1
    assert Path(adapter[0]['name']).is_file()
    assert (Path(adapter[0]['name']).parent/'actions.mjs').is_file()
env={**os.environ,'PYTHONPATH':'/usr/lib/augmentor/apps/native'}
subprocess.run([manifest['python'],'-m','augmentor_linux','--preview','--screenshot',str(home/'desktop.png')],env=env,check=True)
assert (home/'desktop.png').stat().st_size>10000
# A repeated successful install reports the receipt without replacing files.
first=(config/'augmentor/harnesses.json').read_bytes()
subprocess.run(['/usr/bin/python3','/bundle/setup.py','--bundle','/bundle','--skip-packages','--no-services','--non-interactive'],env=env,check=True)
assert (config/'augmentor/harnesses.json').read_bytes()==first
print('PASS: complete bundle installed as a fresh ordinary Debian user; real DSH/plugins/product integration, private settings, native Qt rendering, second window, login/recovery entries, matching browser registration and repeat-run preservation.')
PY
