# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Small theme-coloured SVG icons for settings navigation."""
from pathlib import Path
from PySide6.QtCore import QSize,QBuffer,QByteArray,QIODevice
from PySide6.QtGui import QIcon,QPixmap,QImageReader
from PySide6.QtWidgets import QWidget,QHBoxLayout,QLabel


def settings_icon(name,colour):
    path=Path(__file__).parent/'assets/settings'/f'{name}.svg'
    data=QByteArray(path.read_text().replace('currentColor',colour.name()).encode())
    buffer=QBuffer(data);buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    reader=QImageReader(buffer,b'svg');reader.setScaledSize(QSize(48,48))
    return QIcon(QPixmap.fromImage(reader.read()))


def settings_label(text,name,colour):
    row=QWidget();layout=QHBoxLayout(row);layout.setContentsMargins(0,0,0,0)
    icon=QLabel();icon.setPixmap(settings_icon(name,colour).pixmap(QSize(18,18)))
    layout.addWidget(icon);layout.addWidget(QLabel(text),1)
    return row
