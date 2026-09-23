# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real event-loop proof for the installed-build touch adapter; no agent or user state writes."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

with tempfile.TemporaryDirectory() as directory:
    viewport=Path(directory)/'viewport.json';viewport.write_text(json.dumps({'width':360,'height':760,'show':'proof'}))
    os.environ['AUGMENTOR_TOUCH_VIEWPORT']=str(viewport)
    installed=Path.home()/'.local/share/resonant-voice/augmentor-preview'
    if installed.exists():os.environ['AUGMENTOR_REMOTE_DESKTOP_ROOT']=str(installed)
    spec=importlib.util.spec_from_file_location('native_runner',Path(__file__).with_name('native_runner.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    app=QApplication([]);w=module.TouchWindow(preview=True);w.show()
    def first():
        w.composer.setPlainText('Touch keyboard: café');viewport.write_text(json.dumps({'width':412,'height':840,'show':'proof'}))
    def finish():
        try:
            assert w.size().toTuple()==(412,840),w.size().toTuple()
            assert w.composer.height()>=58,w.composer.height()
            assert w.composer.toPlainText()=='Touch keyboard: café'
            assert all(b.width()>=44 and b.height()>=44 for b in w.touch_layout.buttons)
            print(json.dumps({'passed':True,'window':w.size().toTuple(),'composerHeight':w.composer.height(),'timerAndResize':True}))
            app.exit(0)
        except Exception as error:
            print(repr(error));app.exit(1)
    QTimer.singleShot(150,first);QTimer.singleShot(800,finish)
    raise SystemExit(app.exec())
