#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Register the unified native host; retains the legacy host for rollback."""
import argparse,base64,hashlib,json,os,shlex,shutil,time,sys
from pathlib import Path
if sys.platform == 'darwin':
    raise SystemExit('On macOS run register-macos-browser.py with the installed .app path. The Linux source registrar must not modify a signed app bundle.')
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config-root',type=Path,default=Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config')));p.add_argument('--deploy-extension',type=Path,help='Update an existing unpacked extension directory, retaining a code backup.');args=p.parse_args()
root=Path(__file__).resolve().parents[1];node=shutil.which('node')
if not node:raise SystemExit('Node >=22.19 is required')
key=json.loads((root/'apps/browser/extension/manifest.json').read_text())['key'];identity=''.join(chr(ord('a')+int(n,16)) for n in hashlib.sha256(base64.b64decode(key)).hexdigest()[:32])
launcher=root/'scripts/augmentor-browser-host';launcher.write_text('#!/bin/sh\n# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0\nexec '+shlex.quote(node)+' '+shlex.quote(str(root/'apps/browser/native-host.mjs'))+' "$@"\n');launcher.chmod(0o700)
manifest={'name':'com.augmentor.agent','description':'Augmentor · Pi and DSH','path':str(launcher),'type':'stdio','allowed_origins':['chrome-extension://'+identity+'/']}
for browser in ('chromium','google-chrome','google-chrome-beta','BraveSoftware/Brave-Browser'):
    directory=args.config_root/browser/'NativeMessagingHosts';directory.mkdir(parents=True,exist_ok=True)
    path=directory/'com.augmentor.agent.json';path.write_text(json.dumps(manifest,indent=2)+'\n');path.chmod(0o600)
print('Native host registered. Load the unpacked extension from:',root/'apps/browser/extension')

if args.deploy_extension:
    target=args.deploy_extension.resolve();source=root/'apps/browser/extension'
    if target==source:raise SystemExit('The installed extension already uses this directory.')
    existing=json.loads((target/'manifest.json').read_text())
    if existing.get('key')!=key:raise SystemExit('Refusing to replace a different extension.')
    stage=target.with_name(target.name+'.staging');backup=target.with_name(target.name+'.before-augmentor-'+time.strftime('%Y%m%d-%H%M%S'))
    if stage.exists():raise SystemExit('A deployment staging directory already exists.')
    shutil.copytree(source,stage)
    target.rename(backup)
    try:stage.rename(target)
    except Exception:backup.rename(target);raise
    print('Unpacked extension updated:',target)
    print('Previous extension code:',backup)
    print('Reload Augmentor in chrome://extensions to activate it; its ID and stored chats are preserved.')
