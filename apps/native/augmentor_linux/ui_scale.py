# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Native startup DPI plus live, per-window design metrics (never bitmap zoom)."""
from contextlib import contextmanager
import math
import os
import re
import weakref

MINIMUM = 75
MAXIMUM = 150
STEP = 5


def normalize(value):
    if type(value) is not int:
        return 100
    return round(max(MINIMUM, min(MAXIMUM, value)) / STEP) * STEP


@contextmanager
def startup_scale(percent):
    """Multiply the caller's Qt scale; restore its environment for child apps."""
    previous = os.environ.get('QT_SCALE_FACTOR')
    try:
        factor = float(previous or '1')
        if not math.isfinite(factor) or factor <= 0:
            factor = 1.
    except ValueError:
        factor = 1.
    os.environ['QT_SCALE_FACTOR'] = str(factor * normalize(percent) / 100)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop('QT_SCALE_FACTOR', None)
        else:
            os.environ['QT_SCALE_FACTOR'] = previous


# Import Qt lazily: startup_scale must also work before QApplication creation.
_bindings = weakref.WeakKeyDictionary()
_parent_filter = None


def context(obj):
    while obj is not None:
        result = getattr(obj, '_ui_scale', None)
        if result is not None:
            return result
        obj = obj.parent()
    return None


def factor(obj):
    owner = context(obj)
    return owner.factor if owner else 1.


def px(obj, value):
    return round(value * factor(obj))


def _value(value, ratio):
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QFont
    if isinstance(value, str):
        return re.sub(r'(-?\d+(?:\.\d+)?)px\b', lambda m: f'{round(float(m[1])*ratio)}px', value)
    if isinstance(value, QSize):
        return QSize(_value(value.width(), ratio), _value(value.height(), ratio))
    if isinstance(value, QFont):
        font = QFont(value)
        if font.pixelSize() > 0:font.setPixelSize(max(1, round(font.pixelSize()*ratio)))
        elif font.pointSizeF() > 0:font.setPointSizeF(font.pointSizeF()*ratio)
        return font
    # Qt's unconstrained maximum and automatic spacing are not design lengths.
    if value < 0 or value == 16777215:return value
    return round(value * ratio)


def _apply(obj):
    from shiboken6 import isValid
    if not isValid(obj):return
    from PySide6.QtWidgets import QLayout
    if isinstance(obj, QLayout) and context(obj):
        bindings=_bindings.setdefault(obj,{})
        margins=obj.contentsMargins()
        bindings.setdefault('setContentsMargins',(margins.left(),margins.top(),margins.right(),margins.bottom()))
        bindings.setdefault('setSpacing',(obj.spacing(),))
    ratio = factor(obj)
    for method, values in tuple(_bindings.get(obj, {}).items()):
        getattr(obj, method)(*(_value(value, ratio) for value in values))


class scaled:
    """Register original design units and apply the current owning window scale.

    Use for explicit sizes, spacing, fonts and styles; never for dimensions
    measured from a viewport, document, screen or another already-scaled widget.
    """
    def __init__(self, obj):self.obj = obj

    def __getattr__(self, method):
        def set_metric(*values):
            _bindings.setdefault(self.obj, {})[method] = values
            getattr(self.obj, method)(*(_value(value, factor(self.obj)) for value in values))
        return set_metric


class LiveScale:
    def __init__(self, window, base):
        self.base = normalize(base)
        self.percent = self.base
        self.factor = 1.
        self.window = weakref.ref(window)
        window._ui_scale = self
        _install_parent_filter()

    def set_percent(self, percent):
        from PySide6.QtCore import QObject
        self.percent = normalize(percent)
        self.factor = self.percent / self.base
        window = self.window()
        for obj in [window, *window.findChildren(QObject)]:
            _apply(obj)


def _install_parent_filter():
    global _parent_filter
    if _parent_filter is not None:return
    from PySide6.QtCore import QObject, QEvent
    from PySide6.QtWidgets import QApplication
    # One application filter, not one per window: settings dialogs and preview
    # windows must not add permanent work to every Qt event.
    class ParentFilter(QObject):
        def eventFilter(self, obj, event):
            if event.type() in (QEvent.Type.ParentChange, QEvent.Type.Polish) and context(obj):
                _apply(obj)
                for child in obj.findChildren(QObject):_apply(child)
            return False
    _parent_filter=ParentFilter(QApplication.instance())
    QApplication.instance().installEventFilter(_parent_filter)
