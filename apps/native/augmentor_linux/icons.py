# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Render the extension's SVG theme symbols in the current interface colours."""
from pathlib import Path
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPixmap


def theme_icon(mode,colour):
    source=(Path(__file__).parent/'assets'/f'{mode}.svg').read_text().replace('currentColor',colour)
    source=source.replace('width="12" height="12"','width="40" height="40"')
    pixmap=QPixmap()
    if not pixmap.loadFromData(QByteArray(source.encode()),'SVG'):raise RuntimeError('The Qt SVG image plugin is unavailable')
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)
