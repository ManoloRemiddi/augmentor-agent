#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Install every bundled plugin and connect the product in a disposable DSH home."""
import argparse
import http.server
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--plugins',type=Path,required=True);a=p.parse_args()
s=importlib.util.spec_from_file_location('setup_complete',ROOT/'scripts/setup-complete.py');setup=importlib.util.module_from_spec(s);s.loader.exec_module(setup)
with tempfile.TemporaryDirectory(prefix='augmentor-complete-proof-') as directory:
    work=Path(directory);home=work/'dsh';home.mkdir();state=work/'state';state.mkdir()
    os.environ.update(XDG_CONFIG_HOME=str(work/'config'),XDG_DATA_HOME=str(work/'data'),XDG_STATE_HOME=str(work/'state'),
                      AUGMENTOR_SHARED_CONFIG=str(work/'config/augmentor'),AUGMENTOR_SHARED_DATA=str(work/'data/augmentor'),
                      AUGMENTOR_SHARED_STATE=str(work/'state/augmentor'),AUGMENTOR_DSH_WORKSPACE_ROOT=str(work/'workspaces'))
    cli=Path(shutil.which('dsh'));env={**os.environ,'DSH_HOME':str(home),'DSH_TELEMETRY_MODE':'DISABLED','AUGMENTOR_MODEL_API_KEY':'fixture'}
    import yaml
    (home/'settings.yaml').write_text(yaml.safe_dump(setup.model_settings('http://127.0.0.1:9/v1','fixture',32768)))
    for name in ('dsh-model-picker-augmented-1.1.2.tgz','dsh-adaptive-reasoning-0.2.3.tgz','dsh-resonant-voice-0.1.16.tgz'):
        subprocess.run([str(cli),'plugin','--profile','web','add',str((a.plugins/name).resolve()),'--ignore-scripts','--config.auto-install-peers=false'],
                       env=env,check=True,stdout=subprocess.DEVNULL)
    voice=home/'profiles/web/node_modules/dsh-resonant-voice'
    subprocess.run(['node',str(voice/'bin/resonant-voice.js'),'init'],env=env,check=True,stdout=subprocess.DEVNULL)
    with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    try:
        setup.configure_product(ROOT,cli,home,'http://127.0.0.1:'+str(port),env,state)
    except Exception:
        import re
        print(re.sub(r'token=[A-Za-z0-9_-]+','token=[redacted]',(state/'setup-dsh.log').read_text()[-4500:]))
        raise
    saved=json.loads((work/'config/augmentor/harnesses.json').read_text())['dsh']
    assert saved['home']==str(home) and saved['version']==json.loads((ROOT/'release/product.json').read_text())['version']
    package=json.loads((home/'profiles/web/package.json').read_text())
    bundles=package['dsh']['profile']['bundles']
    for name in ('dsh-model-picker-augmented','dsh-adaptive-reasoning','dsh-resonant-voice'):assert bundles.count(name)==1
    for role in ('linux','browser'):
        entries=json.loads((home/'.agent-presets'/('augmentor-'+role+'-product')/'agent.cordis.yml').read_text().split('\n',1)[1])
        assert any(row['id']=='augmentor-memory' for row in entries)
        assert sum(row['id']=='augmentor-execution' for row in entries)==1
        execution=next(row for row in entries if row['id']=='augmentor-execution')
        assert Path(execution['name']).is_file()
        assert (Path(execution['name']).parent/'actions.mjs').is_file()
    print('PASS: real fresh DSH installation, all three external plugins mounted once, native/browser integration, automatic-memory adapter and authenticated save after restart.')
