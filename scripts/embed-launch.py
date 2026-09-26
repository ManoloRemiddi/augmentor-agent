#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Launch the Browser embedding service from the selected immutable product."""
import json
import os
from pathlib import Path
selected=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'augmentor/desktop.json'
config=json.loads(selected.read_text())
entry=Path(config['root'])/'apps/browser/embed/server.mjs'
if not entry.is_file(): raise SystemExit('Selected Augmentor release does not support embedding. Install a compatible release.')
os.environ['AUGMENTOR_PYTHON']=config['python']
os.execv(config['node'],[config['node'],str(entry)])
