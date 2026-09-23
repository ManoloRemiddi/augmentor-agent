#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Uninstall a disposable signed copy with a real login service and owned hosts."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
TOOLS=Path(os.environ.get('AUGMENTOR_PROOF_TOOLS_ROOT',ROOT))
if sys.platform!='darwin':raise SystemExit('Run on macOS.')
spec=importlib.util.spec_from_file_location('uninstaller',TOOLS/'scripts/uninstall-macos.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
login=Path.home()/'Library/LaunchAgents'/f'{module.shortcut.LABEL}.plist'
if login.exists() or login.is_symlink():raise SystemExit('The proof will not replace a login registration.')
original=Path(sys.argv[1]).resolve()
fixture=Path(tempfile.mkdtemp(prefix='augmentor-uninstall-',dir='/tmp'))
app=fixture/'Disposable Desktop.app'
subprocess.run(['ditto',str(original),str(app)],check=True)
os.environ['XDG_CONFIG_HOME']=str(fixture/'config')
sentinel=fixture/'config/augmentor/conversations-retained.json'
sentinel.parent.mkdir(parents=True);sentinel.write_text('fixture user data')
support=fixture/'support'
value=module.browser.manifest(app)
host=support/'Chromium/NativeMessagingHosts'
module.browser.register(value,host)
module.shortcut.validate(app)
module.shortcut.manage(app,'install')
sys.path.insert(0,str(app/'Contents/Resources/app/apps/native'))
from augmentor_linux.macos_shortcut_service import request
deadline=time.monotonic()+20
while True:
    try:request({'operation':'status'});break
    except OSError:
        if time.monotonic()>deadline:raise
        time.sleep(0.1)
request({'operation':'save','sequence':'Ctrl+Meta+Alt+Shift+F19'})
result=module.uninstall(app,support=support)
assert not app.exists() and original.exists()
assert not login.exists()
assert not module.shortcut.manage(app,'status')['loaded']
assert not (host/'com.augmentor.agent.json').exists()
assert sentinel.read_text()=='fixture user data'
assert (fixture/'config/augmentor/shortcut.json').exists()
receipt=json.loads(Path(result['receipt']).read_text())
retained=Path(receipt['moves'][-1]['retained'])
subprocess.run(['codesign','--verify','--deep','--strict',str(retained)],check=True)
evidence={'signedDisposableAppRemoved':True,'previewPreserved':str(original),
          'uninstallerFile':str(module.__file__),
          'realLoginServiceStopped':True,'ownedBrowserHostRemoved':True,
          'userSettingsPreserved':True,'retainedSignatureVerified':True,
          'trashReceipt':result['receipt'],'fixture':str(fixture),'interruptedUninstallTested':False}
output=ROOT/'outputs/cross-platform/mac-uninstall-proof.json'
output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(evidence,indent=2)+'\n')
print(json.dumps(evidence))
