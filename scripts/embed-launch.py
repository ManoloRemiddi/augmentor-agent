#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Launch the Browser embedding service from the selected immutable product."""
import json
import importlib.util
import os
import sys
from pathlib import Path
selected=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'augmentor/desktop.json'
config=json.loads(selected.read_text())
entry=Path(config['root'])/'apps/browser/embed/server.mjs'
if not entry.is_file(): raise SystemExit('Selected Augmentor release does not support embedding. Install a compatible release.')
env={**os.environ,'AUGMENTOR_PYTHON':config['python']}
root=Path(config['root'])
if (sys.platform == 'linux' and (root/'scripts/linux-python-runtime.py').is_file()) or (root/'linux-python-runtime.json').exists() or (root/'linux-python-runtime.json').is_symlink():
 spec=importlib.util.spec_from_file_location('embed_linux_runtime',root/'scripts/linux-python-runtime.py')
 runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
 _,env=runtime.launch(root,config['python'],env)
os.execve(config['node'],[config['node'],str(entry)],env)
