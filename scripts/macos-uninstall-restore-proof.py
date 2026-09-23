#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Restore the prior disposable uninstall fixture and verify real service recovery."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
TOOLS=Path(os.environ.get('AUGMENTOR_PROOF_TOOLS_ROOT',ROOT))
if sys.platform!='darwin':raise SystemExit('Run on macOS.')
spec=importlib.util.spec_from_file_location('uninstaller',TOOLS/'scripts/uninstall-macos.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
evidence=json.loads((ROOT/'outputs/cross-platform/mac-uninstall-proof.json').read_text())
receipt=Path(evidence['trashReceipt']);fixture=Path(evidence['fixture'])
login=Path.home()/'Library/LaunchAgents'/f'{module.shortcut.LABEL}.plist'
if login.exists() or login.is_symlink():raise SystemExit('An existing login registration will not be replaced.')
if not receipt.is_file() or not fixture.is_dir():raise SystemExit('The prior disposable proof state is missing.')
record=json.loads(receipt.read_text());app=Path(record['app'])
if app!=fixture/'Disposable Desktop.app':raise SystemExit('This receipt does not describe the disposable fixture.')
os.environ['XDG_CONFIG_HOME']=str(fixture/'config')
interrupted=os.environ.get('AUGMENTOR_PROOF_INTERRUPT_RESTORE')=='1'
if interrupted:
    # Terminate after the real app rename, before the remaining registrations
    # are restored. Signature validation and recovery use packaged code.
    code='''import importlib.util,os,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location("uninstaller",sys.argv[1])
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
app=Path(sys.argv[4]);rename=Path.rename
def interrupted(self,destination):
    result=rename(self,destination)
    if destination==app:os._exit(19)
    return result
Path.rename=interrupted
m.restore(Path(sys.argv[2]),support=Path(sys.argv[3]))
'''
    child=subprocess.run([sys.executable,'-I','-B','-c',code,str(module.__file__),str(receipt),str(fixture/'support'),str(app)])
    assert child.returncode==19,child.returncode
    assert app.exists() and not login.exists()
result=module.restore(receipt,support=fixture/'support')
sys.path.insert(0,str(app/'Contents/Resources/app/apps/native'))
from augmentor_linux.macos_shortcut_service import request
from augmentor_linux.macos_shortcuts import current_keys
deadline=time.monotonic()+20
while True:
    try:
        status=request({'operation':'status'})
        break
    except OSError:
        if time.monotonic()>deadline:raise
        time.sleep(0.1)
assert status['active'] and current_keys()==[status['key']],status
assert module.shortcut.manage(app,'status')['loaded']
assert (fixture/'support/Chromium/NativeMessagingHosts/com.augmentor.agent.json').exists()
assert (fixture/'config/augmentor/conversations-retained.json').read_text()=='fixture user data'
module.installer.validate(app,development=True)
# The real login service holds a shared installation lease. A completed
# recovery retry must validate the intact files without requiring their removal.
module.restore(receipt,support=fixture/'support')
after_retry=request({'operation':'status'})
assert after_retry['active'] and after_retry['pid']==status['pid'],after_retry
removed=module.uninstall(app,support=fixture/'support')
assert not app.exists() and not login.exists()
assert Path(evidence['previewPreserved']).exists()
output={'signedAppRestored':True,'realLaunchdRestarted':True,'nativeShortcutRestored':True,
        'restoreRetryWithRunningService':True,
        'browserRegistrationRestored':True,'userDataPreserved':True,
        'disposableAppUninstalledAgain':True,'newTrashReceipt':removed['receipt'],
        'uninstallerFile':str(module.__file__),'sourceUninstallerUsed':TOOLS==ROOT,'interruptedRestoreTested':interrupted}
(ROOT/'outputs/cross-platform/mac-uninstall-restore-proof.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(output))
