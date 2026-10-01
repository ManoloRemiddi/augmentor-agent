#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Install the selected-product Browser service; no competing agent or model."""
import json
import os
from pathlib import Path
import shutil
import subprocess
root=Path(__file__).resolve().parents[1]
data=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'augmentor'
selected=json.loads((data/'desktop.json').read_text())
if Path(selected['root']).resolve()!=root:raise SystemExit('Run this installer from the selected managed release.')
launcher=data/'embed-launch.py';shutil.copy2(root/'scripts/embed-launch.py',launcher)
unit=Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'systemd/user/augmentor-embed.service'
unit.parent.mkdir(parents=True,exist_ok=True)
unit.write_text('# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0\n[Unit]\nDescription=Augmentor Browser embedding service\nAfter=network.target '+(selected.get('dshService') or '')+'\nWants='+(selected.get('dshService') or '')+'\nStartLimitIntervalSec=0\n\n[Service]\nType=simple\nExecStart=/usr/bin/python3 "'+str(launcher)+'"\nRestart=always\nRestartSec=3\nTimeoutStopSec=10\nUMask=0077\nNoNewPrivileges=true\n\n[Install]\nWantedBy=default.target\n')
subprocess.run(['systemctl','--user','daemon-reload'],check=True)
subprocess.run(['systemctl','--user','enable','--now','augmentor-embed.service'],check=True)
