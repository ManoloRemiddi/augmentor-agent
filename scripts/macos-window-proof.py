#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Read back AppKit pin behavior on a real Cocoa Qt window (no Spaces navigation)."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
APP=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT
if sys.platform!='darwin':raise SystemExit('Run on macOS in the GUI session.')
sys.path.insert(0,str(APP/'apps/native'))
from PySide6.QtWidgets import QApplication,QWidget
from augmentor_linux.macos_windows import collection_behavior,pin_spaces

app=QApplication([]);window=QWidget();window.show();app.processEvents()
try:
    original=collection_behavior(window)[1]
    for _ in range(2):
        pin_spaces(window,True)
        current=collection_behavior(window)[1]
        assert current&3==1 and current&~3==original&~3
    pin_spaces(window,False)
    assert collection_behavior(window)[1]==original
    result={'appRoot':str(APP),'nativeQtWindow':True,'pinBitVerified':True,'unpinRestoresBehavior':True,
            'spacesNavigationVerified':False,'originalBehavior':original}
    (ROOT/'outputs/cross-platform').mkdir(parents=True,exist_ok=True)
    (ROOT/'outputs/cross-platform/mac-window-proof.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
finally:window.close()
