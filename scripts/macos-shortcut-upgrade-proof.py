#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Upgrade a real installed development bundle while its shortcut service runs."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if sys.platform != 'darwin':raise SystemExit('Run on macOS.')
candidate, installed = (Path(value).resolve() for value in sys.argv[1:3])
interrupt_stop = '--interrupt-stop' in sys.argv[3:]
source_installer = '--source-installer' in sys.argv[3:]
app_root = installed/'Contents/Resources/app'
sys.path.insert(0, str(app_root/'apps/native'))
from augmentor_linux.macos_shortcut_service import request
spec = importlib.util.spec_from_file_location('registration', app_root/'scripts/register-macos-shortcut.py')
registration = importlib.util.module_from_spec(spec);spec.loader.exec_module(registration)
path = Path.home()/'Library/LaunchAgents'/(registration.LABEL+'.plist')
if path.exists() or path.is_symlink():raise SystemExit('An existing login registration will not be replaced by this proof.')


def ready():
    deadline = time.monotonic()+20
    while time.monotonic()<deadline:
        try:return request({'operation':'status'})
        except OSError:time.sleep(0.1)
    raise RuntimeError('The installed shortcut service did not become ready.')


directory = tempfile.mkdtemp(prefix='asu-', dir='/tmp')
success = False
try:
    # Keep the normal runtime so every existing installation lease still applies.
    os.environ['XDG_CONFIG_HOME'] = directory
    registration.validate(installed)
    try:
        registration.manage(installed,'install')
        before = ready()
        saved = request({'operation':'save','sequence':'Ctrl+Meta+Alt+Shift+F19'})
        assert request({'operation':'status'})['active']
        candidate_root = candidate/'Contents/Resources/app'
        installer_script = candidate_root/'scripts/install-macos.py'
        if source_installer:installer_script = ROOT/'scripts/install-macos.py'
        if interrupt_stop:
            code = '''import importlib.util,os,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location("installer",sys.argv[1])
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
registrar=installer.shortcut_registrar()
manage=registrar.manage
def interrupted(app,action):
    result=manage(app,action)
    if action=="stop":os._exit(9)
    return result
registrar.manage=interrupted
installer.shortcut_registrar=lambda:registrar
with installer.installation_transaction(Path(sys.argv[2]),Path(sys.argv[3])):
    raise AssertionError("Process should exit after real launchd shutdown")
'''
            crashed = subprocess.run([sys.executable,'-B','-c',code,str(installer_script),
                                      str(installed),str(candidate)],capture_output=True,text=True,timeout=90)
            assert crashed.returncode == 9, crashed.stdout+crashed.stderr
            pending = installed.with_name('.'+installed.name+'.shortcut-resume.json')
            assert pending.exists()
            assert not registration.manage(installed,'status')['loaded']
        result = subprocess.run([str(candidate_root/'python/bin/python3'),'-I','-B',
                                 str(installer_script),str(candidate),
                                 '--destination',str(installed),'--development'],
                                capture_output=True,text=True,timeout=180)
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
        installation = json.loads(result.stdout)
        after = ready()
        assert before['pid'] != after['pid'] and after['active'] and after['key']==saved['key'], after
        assert Path(installation['backup']).is_dir()
        registration.validate(installed)
        if interrupt_stop:assert not pending.exists()
        record = {'installedBundleUpgrade':True,'nativeShortcutRestored':True,
                  'servicePidChanged':True,'previousBundleRetained':installation['backup'],
                  'strictSignatureAfterUse':True,'developmentSignature':True,
                  'physicalKeyDeliveryTested':False,'powerLossRecoveryTested':False,
                  'realLaunchdInterruptedAfterStop':interrupt_stop,
                  'sourceInstallerUsed':source_installer}
        output = ROOT/'outputs/cross-platform'/('mac-shortcut-interruption-proof.json' if interrupt_stop else 'mac-shortcut-upgrade-proof.json')
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps(record))
        success = True
    finally:
        if success:registration.manage(installed,'remove')
finally:
    if success:shutil.rmtree(directory)
    else:print('Proof state retained for recovery: XDG_CONFIG_HOME='+directory,file=sys.stderr)
