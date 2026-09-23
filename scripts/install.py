#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Install or update the Pi app in a separate user-owned directory."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--prefix',type=Path,default=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'augmentor-pi/app')
parser.add_argument('--no-desktop',action='store_true')
parser.add_argument('--shortcut',default=None)
args=parser.parse_args();source=Path(__file__).resolve().parents[1];target=args.prefix.resolve()
if target==source or source.is_relative_to(target):parser.error('Installation directory must be separate from the source checkout.')
node=shutil.which('node');npm=shutil.which('npm')
if not node or not npm:parser.error('Install Node >=22.19 and npm first.')
import importlib.util
if not all(importlib.util.find_spec(name) for name in ['PySide6','gi']):parser.error('Install Python PySide6 and GI/AT-SPI desktop dependencies first.')
if not (source/'dist/runtime/src/main.js').exists():parser.error('Build the source first with npm ci --ignore-scripts and npm run build.')
version=subprocess.check_output([node,'--version'],text=True).strip().lstrip('v').split('.')
if tuple(map(int,version[:2]))<(22,19):parser.error('Node >=22.19 is required.')
# Refuse to replace executable files while a Pi task is active.
sys.path.insert(0,str(source/'apps/native'))
from augmentor_linux.pi_client import PiClient
os.environ['AUGMENTOR_PI_NO_AUTOSTART']='1'
client=PiClient();running=False
try:status=client.call('host.describe');running=True
except Exception:status=None
if status and status.get('activeTurns'):parser.error('Stop active Pi tasks before updating the application.')
staging=target.with_name(target.name+'.staging-'+uuid.uuid4().hex[:8]);staging.mkdir(parents=True,mode=0o700)
try:
    for name in ['apps','dist','scripts','config','docs','services','adapters','licenses']:
        shutil.copytree(source/name,staging/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc','node_modules','.git'))
    for name in ['package.json','package-lock.json','LICENSE','README.md']:
        shutil.copy2(source/name,staging/name)
    # Reuse the exact tested dependency tree when installing from a built checkout.
    if (source/'node_modules').exists():subprocess.run(['cp','-a','--reflink=auto',str(source/'node_modules'),str(staging/'node_modules')],check=True)
    else:subprocess.run([npm,'ci','--ignore-scripts','--omit=dev'],cwd=staging,check=True)
    if running:client.call('host.shutdown')
    # One previous release is retained for rollback; application state is elsewhere.
    backup=target.with_name(target.name+'.previous')
    if backup.exists():shutil.rmtree(backup)
    if target.exists():target.rename(backup)
    staging.rename(target)
except Exception:
    if staging.exists():shutil.rmtree(staging)
    raise
# Pin the resolved Node path for launchers started with a minimal desktop PATH.
launch=target/'scripts/augmentor-linux'
text=launch.read_text();text=text.replace('set -euo pipefail','set -euo pipefail\nexport AUGMENTOR_PI_NODE='+__import__('shlex').quote(node),1);launch.write_text(text);launch.chmod(0o755)
if not args.no_desktop:
    command=[sys.executable,str(target/'scripts/install-desktop.py')]
    if args.shortcut:command+=['--shortcut',args.shortcut]
    subprocess.run(command,check=True)
(target/'installation.json').write_text(json.dumps({'desktop':not args.no_desktop,'version':json.loads((source/'package.json').read_text())['version']}))
print('Installed:',target)
print('Launch:',target/'scripts/augmentor-linux')
