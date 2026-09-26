#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Opt-in live-provider proof through the packaged macOS Qt composer and Send UI.

Run with the app's bundled Python. Uses a named test window and the user's saved
DSH connection; sends one real model request. Does not control another process's
window or certify microphone/browser permissions. No fixtures or API-only send.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-root',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--instance',required=True)
    parser.add_argument('--marker',required=True)
    parser.add_argument('--previous-marker',help='Require this earlier reply after reopening the window')
    parser.add_argument('--submit',choices=('button','enter'),default='button')
    parser.add_argument('--live',action='store_true',help='Authorize one real provider request')
    args=parser.parse_args()
    if not args.live:parser.error('This proof sends a real model request; use --live explicitly.')
    if sys.platform!='darwin':parser.error('Use the graphical macOS login session.')
    if not args.marker.isascii() or not args.marker or len(args.marker)>80:
        parser.error('Use a short ASCII response marker.')
    root=args.app_root.resolve()
    spec=importlib.util.spec_from_file_location('bundle_launcher',root/'scripts/launch-component.py')
    launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher);launcher.configure()
    sys.path.insert(0,str(root/'apps/native'))
    from augmentor_linux.instances import configure
    configure(args.instance)
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication,QDialog
    from augmentor_linux.window import Window
    args.out.mkdir(parents=True,exist_ok=False)
    app=QApplication([])
    window=Window(preview=False,harness='dsh')
    window.show();window.raise_();window.activateWindow()
    errors=[];window.controller.problem.connect(errors.append)
    report={'appRoot':str(root),'instance':args.instance,'submit':args.submit,'passed':False,
            'scope':'Packaged real Qt window, live DSH/provider, widget input and rendered transcript; separate driver process.'}
    def until(check,seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            app.processEvents()
            if errors:raise AssertionError(errors[-1])
            if check():return
            time.sleep(.02)
        raise AssertionError('UI proof timed out: '+window.status.text())
    try:
        until(lambda:window.controller.online and window.send_button.isEnabled(),30)
        assert not any(d.isVisible() for d in window.findChildren(QDialog)), 'A dialog blocks the composer'
        assert window.controller.client.product, 'Desktop retained its pre-setup DSH binding'
        assert window.controller.preset=='augmentor-linux-product'
        report['selection']=window.model_picker.currentData()
        if args.previous_marker:
            until(lambda:args.previous_marker in window.transcript.toPlainText(),20)
        previous_session=window.controller.session
        window.grab().save(str(args.out/'before.png'))
        prompt='Reply with exactly: '+args.marker+'. Do not use any tools.'
        QTest.mouseClick(window.composer.viewport(),Qt.MouseButton.LeftButton)
        QTest.keyClicks(window.composer,prompt)
        assert window.composer.toPlainText()==prompt
        if args.submit=='button':QTest.mouseClick(window.send_button,Qt.MouseButton.LeftButton)
        else:QTest.keyClick(window.composer,Qt.Key.Key_Return)
        until(lambda:bool(window.controller.session) and not window.controller.running
              and args.marker in window.transcript.toPlainText().split('Augmentor',1)[-1]
              and window.transcript.toPlainText().count(args.marker)>=2,120)
        assert not window.composer.toPlainText(), 'Submitted text remained in composer'
        assert window.transcript.toPlainText().count(prompt)==1, 'Duplicate or missing user message'
        if args.previous_marker:assert window.controller.session==previous_session, 'Reopen lost the conversation'
        window.grab().save(str(args.out/'after.png'))
        report.update(passed=True,session=window.controller.session,transcript=window.transcript.toPlainText(),
                      online=window.controller.online,modelReady=bool(window.model_picker.currentData()))
        print(json.dumps({k:v for k,v in report.items() if k!='transcript'}),flush=True)
    finally:
        report['errors']=errors
        (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        # Only this named proof window owns this session. Never cancel another window.
        if window.controller.running:window.controller.stop()
        window.controller.close();window.hide()
    return 0


if __name__=='__main__':raise SystemExit(main())
