#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Native scaling and Appearance input, with an isolated unsent draft."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-root',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--percent',type=int,default=110)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(args.app_root.resolve()/'apps/native'))
    with tempfile.TemporaryDirectory(prefix='augmentor-size-') as directory:
        for name in ('AUGMENTOR_PI_CONFIG','AUGMENTOR_PI_STATE','AUGMENTOR_SHARED_STATE','AUGMENTOR_SHARED_DATA','XDG_RUNTIME_DIR'):
            path=Path(directory)/name;path.mkdir();os.environ[name]=str(path)
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        from PySide6.QtTest import QTest
        from augmentor_linux.preferences import Preferences
        from augmentor_linux.ui_scale import startup_scale
        from augmentor_linux.window import Window
        preferences=Preferences();preferences.values['ui_scale']=args.percent;preferences.save()
        with startup_scale(Preferences().values['ui_scale']):
            app=QApplication([])
        app.setProperty('augmentorUiScale',args.percent)
        window=Window(preview=True)
        window.preferences.persistent=True;window.preferences.values.update(Preferences().values)
        window.show();QTest.qWait(100)
        window.composer.setFocus();QTest.keyClicks(window.composer,'Unsent size verification draft')
        window.grab().save(str(args.out/'window.png'))
        dpr=window.devicePixelRatioF()
        report={'percent':args.percent,'dpr':dpr,'windowLogical':list(window.size().toTuple()),
                'windowPixels':list(window.grab().size().toTuple()),'fontLogicalPixels':window.brand.font().pixelSize(),
                'buttonLogical':list(window.send_button.size().toTuple()),'buttonPixels':list(window.send_button.grab().size().toTuple())}
        window.open_appearance();QTest.qWait(1000);dialog=window.appearance_dialog
        assert dialog.size_slider.value()==args.percent
        dialog.size_slider.setFocus();QTest.keyClick(dialog.size_slider,Qt.Key.Key_Left)
        QTest.qWait(250)
        assert Preferences().values['ui_scale']==max(75,args.percent-5), (dialog.size_slider.value(),window.preferences.values['ui_scale'],Preferences().values['ui_scale'])
        QTest.keyClick(dialog.size_slider,Qt.Key.Key_Right);QTest.qWait(250)
        assert Preferences().values['ui_scale']==args.percent
        assert window.composer.toPlainText()=='Unsent size verification draft'
        assert window.devicePixelRatioF()==dpr
        assert dialog.height()<=window.screen().availableGeometry().height()
        dialog.grab().save(str(args.out/'appearance.png'))
        dialog.accept();window.hide();window.show();QTest.qWait(100)
        assert window.composer.toPlainText()=='Unsent size verification draft'
        report.update(passed=True,keyboardSliderPersistence=True,draftPreserved=True,hideShowPreserved=True)
        (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
        window.close()


if __name__=='__main__':main()
