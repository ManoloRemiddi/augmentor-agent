#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Inspect our own effect pixels and native shadow, without screen recording."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import random
import sys
import tempfile
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--baseline', action='store_true')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='augmentor-alpha-') as directory:
        for key in ('AUGMENTOR_PI_CONFIG', 'AUGMENTOR_PI_STATE', 'AUGMENTOR_SHARED_DATA', 'AUGMENTOR_SHARED_STATE', 'XDG_RUNTIME_DIR'):
            path = Path(directory)/key; path.mkdir(); os.environ[key] = str(path)
        sys.path.insert(0, str(args.app_root.resolve()/'apps/native'))
        import numpy as np
        from PySide6.QtCore import Qt, QPointF
        from PySide6.QtGui import QImage, QPainter, QColor
        from PySide6.QtWidgets import QApplication
        from PySide6.QtTest import QTest
        from augmentor_linux.window import Window
        from augmentor_linux.activity import FlowNoise, image_array
        app = QApplication([])
        window = Window(preview=True)
        window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        window.resize(457, 578); window.move(300, 240); window.show()
        a = window.activity
        with patch('augmentor_linux.activity.random.Random', return_value=random.Random(714)):
            a.noise = FlowNoise()
        a.configure(busy=True, enabled=True, animated=True, effect='plasma')
        a.timer.stop(); a.strength = 1.; a.breath_phase = 2.
        QTest.qWait(100)
        gpu = a.canvas.gpu
        assert gpu and gpu.available
        shadow = None
        if sys.platform == 'darwin':
            from augmentor_linux.macos_windows import native_window
            objc, address, native = native_window(a.canvas)
            get = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(address)
            shadow = get(native, objc.sel_registerName(b'hasShadow'))
        report = {'nativeShadow': shadow, 'dpr': a.canvas.devicePixelRatioF(),
                  'backend': gpu.quickWindow().rendererInterface().graphicsApi().name, 'frames': {}}
        for stage in ('no-flare', 'flare', 'decayed'):
            a.flare = dict(start=0., duration=3., side=0, position=.5, width=55., travel=150.) if stage == 'flare' else None
            for i in range(50):
                a.phase = (1.0 if stage == 'flare' else 3.)+i*.01
                rect = a.canvas_surface_rect()
                a.pointer = QPointF(rect.center().x()-50+i*2, rect.top()-30)
                a.canvas.update(); QTest.qWait(18)
            native = gpu.grabFramebuffer().convertToFormat(QImage.Format.Format_RGBA8888_Premultiplied)
            native.save(str(args.out/(stage+'-alpha.png')))
            pixels = image_array(native); alpha = pixels[..., 3]
            edge = max(int(alpha[:8].max()), int(alpha[-8:].max()), int(alpha[:, :8].max()), int(alpha[:, -8:].max()))
            top = round((rect.top()-70)*a.canvas.devicePixelRatioF())
            far = int(alpha[:top].max())
            report['frames'][stage] = {'outerEightPixelsAlpha': edge, 'farFlareAlpha': far}
            for name, colour in [('light', '#f5f5f5'), ('dark', '#23262b')]:
                composite = QImage(native.size(), QImage.Format.Format_RGB32)
                composite.fill(QColor(colour)); painter = QPainter(composite)
                painter.drawImage(0, 0, native); painter.end()
                composite.save(str(args.out/(stage+'-'+name+'.png')))
            assert edge == 0, (stage, edge)
            assert np.all(pixels[..., :3] <= alpha[..., None])
        assert report['frames']['flare']['farFlareAlpha'] > 10, 'An actual distant flare was not rendered'
        if not args.baseline:
            assert shadow is not True, 'Transparent exterior window must not cast a rectangular shadow'
        report['passed'] = True
        (args.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report), flush=True)
        window.close()


if __name__ == '__main__': main()
