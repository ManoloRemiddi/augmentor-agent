#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise installed Qt shortcut settings with the native Mac registration helper."""
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
APP=Path(sys.argv[1]).resolve()
if sys.platform!='darwin':raise SystemExit('Run on macOS.')
sys.path.insert(0,str(APP/'apps/native'))
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from augmentor_linux.window import Window
from augmentor_linux.panels import SettingsDialog
from augmentor_linux.controller import Controller
from augmentor_linux import macos_shortcuts
from augmentor_linux.macos_shortcut_service import request

registration=Path.home()/'Library/LaunchAgents/com.augmentor.Agent.shortcut.plist'
if registration.exists() or registration.is_symlink():raise SystemExit('The proof will not replace an existing login registration.')

app=QApplication([])
with tempfile.TemporaryDirectory(prefix='augmentor-shortcut-dialog-') as directory:
    os.environ['XDG_CONFIG_HOME']=directory
    os.environ['AUGMENTOR_PI_CONFIG']=str(Path(directory)/'pi')
    os.environ['AUGMENTOR_PI_STATE']=str(Path(directory)/'state')
    os.environ['AUGMENTOR_SHARED_STATE']=str(Path(directory)/'shared')
    window=Window(preview=True);window.show()
    # Settings uses the controller's worker dispatcher; no model connection is
    # needed for shortcut configuration, but preview mode omits the controller.
    window.controller=Controller(window)
    macos_shortcuts.initialize(window)
    dialog=SettingsDialog(window);dialog.show()
    def until(check):
        end=time.monotonic()+30
        while time.monotonic()<end:
            app.processEvents()
            if check():return
            QTest.qWait(20)
        raise AssertionError(dialog.note.text())
    try:
        until(lambda:dialog.current is not None)
        sequence=QKeySequence('Ctrl+Meta+Alt+Shift+F19')
        dialog.editor.setKeySequence(sequence)
        until(lambda:dialog.apply.isEnabled())
        QTest.mouseClick(dialog.apply,Qt.MouseButton.LeftButton)
        until(lambda:dialog.note.text()=='Shortcut saved.')
        assert macos_shortcuts.current_keys()==[sequence[0].toCombined()]
        assert isinstance(macos_shortcuts.manager,macos_shortcuts.ManagedShortcutManager)
        assert request({'operation':'status'})['active']
        macos_shortcuts.manager.close()
        assert request({'operation':'status'})['active'],'Closing the UI stopped the shortcut service'
        output=ROOT/'outputs/cross-platform';output.mkdir(parents=True,exist_ok=True)
        dialog.grab().save(str(output/'mac-shortcut-dialog.png'))
        result={'appRoot':str(APP),'qtSaveButton':True,'nativeRegistration':True,
                'persistedChoice':True,'loginRegistrationCreatedBySettings':registration.exists(),
                'serviceSurvivesClientClose':True,'actualShortcutPress':False}
        (output/'mac-shortcut-dialog-proof.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
    finally:
        macos_shortcuts.manager.close();dialog.close();window.close()
        subprocess.run([sys.executable,'-I','-B',str(APP/'scripts/register-macos-shortcut.py'),
                        str(APP.parents[2]),'remove'],check=True,capture_output=True)
