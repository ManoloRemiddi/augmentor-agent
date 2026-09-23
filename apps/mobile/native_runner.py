# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Run the user's actual Desktop build; apply the opt-in touch adapter in memory."""
import importlib.util
import math
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
source = Path(os.environ.get('AUGMENTOR_REMOTE_DESKTOP_ROOT', ROOT))
sys.path.insert(0, str(source/'apps/native'))
os.environ['AUGMENTOR_WINDOW_ID']='mobile'
# The installed Desktop may predate the touch hook. Keep its source untouched.
os.environ.pop('AUGMENTOR_TOUCH_MODE', None)
from augmentor_linux import window as desktop
from PySide6.QtGui import QImage,QPainter
from PySide6.QtCore import Qt
spec=importlib.util.spec_from_file_location('augmentor_touch_adapter',ROOT/'apps/native/augmentor_linux/touch.py')
touch=importlib.util.module_from_spec(spec);spec.loader.exec_module(touch)
OriginalWindow=desktop.Window
OriginalTranscript=desktop.Transcript
OriginalComposer=desktop.Composer

class TouchComposer(OriginalComposer):
    def fit(self,*args):
        if getattr(self,'fitting',False):return
        self.fitting=True
        try:
            line=self.fontMetrics().lineSpacing();margin=2*self.document().documentMargin()
            chrome=self.height()-self.viewport().height()
            content=max(line+margin,min(5*line+margin,self.document().size().height()))
            self.setFixedHeight(max(58,math.ceil(content+chrome)))
        finally:self.fitting=False

class TouchTranscript(OriginalTranscript):
    def action_link(self,action,index,color,icon=None):
        # The same SVG artwork with transparent finger-sized padding.
        return super().action_link(action,index,color,icon).replace('width="14" height="14"','width="44" height="44"')
    def loadResource(self,kind,url):
        image=super().loadResource(kind,url)
        if url.scheme()=='augmentor-icon' and isinstance(image,QImage) and not image.isNull() and image.width()/image.devicePixelRatio()<44:
            ratio=image.devicePixelRatio();target=QImage(round(44*ratio),round(44*ratio),QImage.Format.Format_ARGB32_Premultiplied);target.fill(Qt.GlobalColor.transparent)
            image.setDevicePixelRatio(1);p=QPainter(target);p.drawImage(round((target.width()-image.width())/2),round((target.height()-image.height())/2),image);p.end();target.setDevicePixelRatio(ratio);return target
        return image

class TouchWindow(OriginalWindow):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.touch_layout=touch.TouchLayout(self)
    def apply_appearance(self,values):
        super().apply_appearance(values)
        if source!=ROOT and getattr(self,'touch_layout',None):self.touch_layout.style()

desktop.Composer=TouchComposer
desktop.Transcript=TouchTranscript
desktop.Window=TouchWindow
if __name__=='__main__':sys.exit(desktop.main())
