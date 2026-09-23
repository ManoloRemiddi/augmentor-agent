#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise real launchd with source code in a disposable bundle-shaped fixture."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if sys.platform != 'darwin':raise SystemExit('Run on macOS.')
helper = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location('registration', ROOT/'scripts/register-macos-shortcut.py')
registration = importlib.util.module_from_spec(spec);spec.loader.exec_module(registration)
sys.path.insert(0, str(ROOT/'apps/native'))
from augmentor_linux.macos_shortcut_service import request


def ready():
    deadline = time.monotonic()+20
    while time.monotonic()<deadline:
        try:return request({'operation':'status'})
        except OSError:time.sleep(0.1)
    state=registration.control('print',f'gui/{os.getuid()}/{registration.LABEL}')
    raise RuntimeError('The launchd service did not become ready.\n'+state.stdout+state.stderr)


path = Path.home()/'Library/LaunchAgents'/(registration.LABEL+'.plist')
if path.exists() or path.is_symlink():raise SystemExit('A registration already exists; the proof will not replace it.')
with tempfile.TemporaryDirectory(prefix='asl-',dir='/tmp') as temporary:
    directory = Path(temporary)
    app = directory/'Desktop Fixture.app'
    root = app/'Contents/Resources/app'
    root.mkdir(parents=True)
    (root/'python').symlink_to(Path(sys.prefix),target_is_directory=True)
    for relative in ('apps/native','services/lifecycle'):
        shutil.copytree(ROOT/relative,root/relative,ignore=shutil.ignore_patterns('__pycache__'))
    (root/'scripts').mkdir()
    shutil.copy2(ROOT/'scripts/launch-component.py',root/'scripts/launch-component.py')
    (root/'native').mkdir();(root/'native/augmentor-hotkey').symlink_to(helper)
    os.environ.update(XDG_RUNTIME_DIR=str(directory/'run'),XDG_CONFIG_HOME=str(directory/'config'),
                      XDG_DATA_HOME=str(directory/'data'),XDG_STATE_HOME=str(directory/'state'))
    try:
        registration.manage(app,'install')
        first = ready()
        saved = request({'operation':'save','sequence':'Ctrl+Meta+Alt+Shift+F19'})
        assert request({'operation':'status'})['active']
        registration.manage(app,'stop')
        # bootout can return before process teardown completes.
        deadline = time.monotonic()+20
        while (directory/'run/shortcut-control.sock').exists() and time.monotonic()<deadline:time.sleep(0.1)
        assert not (directory/'run/shortcut-control.sock').exists()
        registration.manage(app,'start')
        second = ready()
        assert second['pid'] != first['pid'] and second['active'] and second['key']==saved['key'],second
        registration.manage(app,'remove')
        assert not path.exists()
        assert (directory/'config/augmentor/shortcut.json').exists()
        result = {'launchdBootstrap':True,'nativeShortcutSaved':True,'bootout':True,
                  'restartRestoresKey':True,'removalPreservesSettings':True,
                  'signedInstalledBundleTested':False,'actualLogoutLoginTested':False}
        output = ROOT/'outputs/cross-platform/mac-shortcut-login-proof.json'
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
    finally:
        registration.manage(app,'remove')
