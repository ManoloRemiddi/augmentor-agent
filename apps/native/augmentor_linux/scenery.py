# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Paint the supplied landscape without altering or stretching the source image."""
from functools import lru_cache
from pathlib import Path
from PySide6.QtCore import QRectF
from PySide6.QtGui import QPixmap, QPainterPath, QColor, QLinearGradient, QPainter


@lru_cache(maxsize=1)
def landscape():
    return QPixmap(str(Path(__file__).parent/'assets/blossom-lake.png'))


@lru_cache(maxsize=2)
def uploaded_pixmap(encoded):
    from .backgrounds import decode_background
    return QPixmap.fromImage(decode_background(encoded))


def paint_landscape(painter, rect, dark=True, opacity=1., radius=20, encoded="", tint=None):
    if encoded:
        image=uploaded_pixmap(encoded)
    else:image=landscape()
    if image.isNull():return
    rect=QRectF(rect)
    scale=max(rect.width()/image.width(),rect.height()/image.height())
    width,height=rect.width()/scale,rect.height()/scale
    source=QRectF((image.width()-width)*.42,(image.height()-height)*.5,width,height)
    painter.save()
    clip=QPainterPath();clip.addRoundedRect(rect,radius,radius);painter.setClipPath(clip)
    painter.setOpacity(opacity);painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.drawPixmap(rect,image,source)
    wash=QLinearGradient(rect.topLeft(),rect.bottomLeft())
    colour=QColor(tint) if tint is not None else QColor('#16282f' if dark else '#fff1df')
    for position,alpha in ((0,155),(.22,95),(.65,65),(1,140)):
        tint=QColor(colour);tint.setAlpha(alpha);wash.setColorAt(position,tint)
    painter.fillRect(rect,wash);painter.restore()


@lru_cache(maxsize=1)
def landscape_butterfly_colours():
    from .backgrounds import butterfly_colours
    return butterfly_colours(landscape().toImage())
