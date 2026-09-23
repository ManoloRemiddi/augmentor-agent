#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real native shortcut ownership and persisted-settings proof in isolated state."""
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
APP=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT
if sys.platform!='darwin':raise SystemExit('Run on the Mac with the compiled hotkey helper.')
sys.path.insert(0,str(APP/'apps/native'))
os.environ['AUGMENTOR_MACOS_HOTKEY']=str(APP/'native/augmentor-hotkey' if APP!=ROOT else ROOT/'outputs/native/augmentor-hotkey')
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QKeySequence
from augmentor_linux.macos_shortcuts import ShortcutManager,current_keys,configuration

app=QApplication([])
with tempfile.TemporaryDirectory() as directory:
    os.environ['XDG_CONFIG_HOME']=directory
    first=ShortcutManager();other=ShortcutManager()
    before=QKeySequence('Ctrl+Meta+Alt+Shift+J');conflict=QKeySequence('Ctrl+Meta+Alt+Shift+K')
    try:
        first.save(before);assert current_keys()==[before[0].toCombined()]
        other.save(conflict,persist=False)
        try:first.save(conflict);raise AssertionError('Conflict accepted')
        except ValueError:pass
        assert first.key==before[0].toCombined() and first.process.poll() is None
        assert current_keys()==[before[0].toCombined()]
        assert configuration().stat().st_mode&0o777==0o600
        first.close();restored=ShortcutManager()
        try:
            restored.restore();assert restored.key==before[0].toCombined()
            function=QKeySequence('Ctrl+Meta+Alt+Shift+F19')
            restored.save(function)
            assert current_keys()==[function[0].toCombined()]
            assert restored.command(function)[1]=='80'
            assert restored.command(QKeySequence('Ctrl+Alt+Left'))[1]=='123'
        finally:restored.close()
        result={'appRoot':str(APP),'saved':True,'conflictPreservesPrior':True,'restored':True,'privateConfig':True,
                'functionKeyRegistration':True,'navigationKeyResolution':True,
                'actualKeyDeliveryTested':False,'launchWhenClosedTested':False}
        (ROOT/'outputs/cross-platform').mkdir(parents=True,exist_ok=True)
        (ROOT/'outputs/cross-platform/mac-shortcut-settings-proof.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
    finally:first.close();other.close()
