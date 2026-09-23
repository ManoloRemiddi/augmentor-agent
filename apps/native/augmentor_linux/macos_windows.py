# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""AppKit behavior for our own Qt windows, accessed only on the GUI thread."""
import ctypes
import sys
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication


def native_window(widget):
    if sys.platform != 'darwin' or QApplication.platformName() != 'cocoa':
        raise RuntimeError('A native macOS window is required.')
    if QThread.currentThread() != QApplication.instance().thread():
        raise RuntimeError('AppKit window changes require the GUI thread.')
    objc = ctypes.CDLL('/usr/lib/libobjc.A.dylib')
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    address = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value
    get = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(address)
    # Qt's macOS WId is NSView*, whose window owns collectionBehavior.
    window = get(int(widget.winId()), objc.sel_registerName(b'window'))
    if not window:
        raise RuntimeError('The Qt view is not attached to a macOS window.')
    return objc, address, window


def collection_behavior(widget):
    objc, address, window = native_window(widget)
    get = ctypes.CFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p)(address)
    return window, get(window, objc.sel_registerName(b'collectionBehavior'))


def pin_spaces(widget, pinned):
    objc, address, window = native_window(widget)
    _, current = collection_behavior(widget)
    previous = getattr(widget, '_augmentor_mac_pin', None)
    if previous is None or previous[0] != window:
        previous = (window, current & 3)
        widget._augmentor_mac_pin = previous
    # canJoinAllSpaces (1) and moveToActiveSpace (2) are mutually exclusive.
    # Preserve all unrelated collection behavior, including fullscreen policy.
    target = (current & ~3) | (1 if pinned else previous[1])
    setter = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong)(address)
    setter(window, objc.sel_registerName(b'setCollectionBehavior:'), target)
    if collection_behavior(widget)[1] != target:
        raise RuntimeError('macOS did not apply the requested workspace behavior.')
    if not pinned:
        del widget._augmentor_mac_pin
