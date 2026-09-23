#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise retained image codecs in the installed macOS Qt distribution."""
import json
import sys
from pathlib import Path
from PySide6.QtCore import QByteArray,QBuffer,QIODevice
from PySide6.QtGui import QImage,QImageReader,QColor
from PySide6.QtWidgets import QApplication,QWidget
import PySide6

if sys.platform!='darwin':raise SystemExit('Run with the installed macOS Python')
app=QApplication([]);window=QWidget();window.show();app.processEvents()
formats={bytes(value).decode() for value in QImageReader.supportedImageFormats()}
verified=[]
try:
    for name in ('png','jpeg','webp'):
        original=QImage(32,24,QImage.Format.Format_RGB32);original.fill(QColor('#36aabb'))
        data=QByteArray();buffer=QBuffer(data);assert buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        assert original.save(buffer,name.upper()),name;buffer.close()
        decoded=QImage.fromData(data,name.upper())
        assert not decoded.isNull() and decoded.width()==32 and decoded.height()==24,name
        verified.append(name)
    svg=QByteArray(b'<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10"><rect width="20" height="10" fill="red"/></svg>')
    decoded=QImage.fromData(svg,'SVG')
    assert not decoded.isNull() and decoded.width()==20 and decoded.height()==10
    verified.append('svg')
    print(json.dumps({'python':sys.executable,'pyside':PySide6.__file__,'platform':app.platformName(),
        'supportedFormats':sorted(formats),'verifiedRoundTrips':verified,'nativeWindow':window.isVisible()}))
finally:window.close()
