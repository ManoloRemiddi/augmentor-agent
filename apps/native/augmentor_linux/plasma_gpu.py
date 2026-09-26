# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Native-resolution plasma through Qt's shared Metal/OpenGL rendering backend.

The chat UI remains QWidget based. Only its existing input-transparent exterior
canvas embeds a Quick surface. Missing graphics support retains the CPU renderer.
"""
import math
import os
from pathlib import Path

import numpy as np
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QSurfaceFormat, QVector2D, QVector4D


def create(canvas):
    if os.environ.get('AUGMENTOR_PLASMA_RENDERER') == 'cpu':
        return None
    if QGuiApplication.platformName() in ('offscreen', 'minimal'):
        return None
    if os.environ.get('QT_QUICK_BACKEND') == 'software':
        return None
    try:
        from PySide6.QtQuick import QQuickImageProvider
        from PySide6.QtQuickWidgets import QQuickWidget
    except ImportError:
        return None

    class Textures(QQuickImageProvider):
        def __init__(self, noise):
            super().__init__(QQuickImageProvider.ImageType.Image)
            self.set_noise(noise)
            self.flow = QImage(1, 1, QImage.Format.Format_RGBA8888_Premultiplied)
            self.flow.fill(Qt.GlobalColor.transparent)
            self.base = self.flow

        def set_noise(self, noise):
            self.noise_identity = noise
            encoded = np.rint(np.asarray(noise.values).reshape(128, 128)*65535).astype(np.uint16)
            rgba = np.zeros((128, 128, 4), np.uint8)
            rgba[..., 0] = encoded >> 8
            rgba[..., 1] = encoded & 255
            rgba[..., 3] = 255
            self.noise = QImage(rgba.data, 128, 128, 512, QImage.Format.Format_RGBA8888).copy()

        def requestImage(self, name, size, requested):
            result = getattr(self, name.split('/')[0], self.flow)
            size.setWidth(result.width()); size.setHeight(result.height())
            return result

    class PlasmaSurface(QQuickWidget):
        def __init__(self):
            super().__init__(canvas)
            self.available = True
            self.serial = 0
            self.last_frame = None
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.setClearColor(Qt.GlobalColor.transparent)
            fmt = QSurfaceFormat()
            fmt.setAlphaBufferSize(8)
            self.setFormat(fmt)
            self.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
            self.textures = Textures(canvas.activity.noise)
            self.engine().addImageProvider('plasma', self.textures)
            self.statusChanged.connect(self.check_status)
            self.sceneGraphError.connect(lambda *_: self.disable())
            self.setSource(QUrl.fromLocalFile(str(Path(__file__).with_name('effects')/'plasma.qml')))
            self.setGeometry(canvas.rect())

        def check_status(self, status):
            if status == QQuickWidget.Status.Error:
                self.disable()

        def disable(self):
            self.available = False
            self.hide()
            canvas.activity.geometry_key = None
            canvas.activity.frame_key = None
            canvas.activity.timer.setInterval(40)

        def refresh(self, rect, accent):
            if self.quickWindow().rendererInterface().graphicsApi().name == 'Software':
                self.disable(); return
            root = self.rootObject()
            if root is None or root.property('failed'):
                self.disable(); return
            self.setGeometry(canvas.rect())
            activity = canvas.activity
            if self.last_frame == activity.frame_key:
                return
            self.last_frame = activity.frame_key
            self.serial += 1
            if self.textures.noise_identity is not activity.noise:
                self.textures.set_noise(activity.noise)
                root.setProperty('noiseSource', 'image://plasma/noise/'+str(self.serial))
            self.textures.flow = activity.frame
            self.textures.base = activity.coarse_source.convertToFormat(QImage.Format.Format_RGBA8888_Premultiplied)
            breath = .5-.5*math.cos(activity.breath_phase) if activity.animated else .5
            hue, saturation, value, _ = accent.getHsvF()
            tint = QColor.fromHsvF(max(0., hue), min(1., saturation*(.8+.7*breath)), min(1., value*(.86+.14*breath)))
            root.setProperty('logicalSize', QVector2D(canvas.width(), canvas.height()))
            root.setProperty('surface', QVector4D(*rect.getRect()))
            root.setProperty('tint', QVector4D(*tint.getRgbF()))
            radius = min(rect.width(), rect.height())/2 if activity.window.compact else 20.
            t = activity.phase if activity.animated else 0.
            root.setProperty('frameState', QVector4D(t, breath, activity.strength, radius))
            intensity = 0.
            if activity.animated and activity.flare:
                flare = activity.flare
                progress = (t-flare['start'])/flare['duration']
                if 0 <= progress < 1:
                    side = flare['side']
                    along = (rect.left()+rect.width()*flare['position'] if side in (0, 2) else rect.top()+rect.height()*flare['position'])
                    height = 2+flare.get('travel', 43)*math.sin(progress*math.pi)**.8
                    intensity = math.sin(progress*math.pi)**1.3
                    root.setProperty('eruption', QVector4D(side, along, flare['width'], height))
            root.setProperty('eruptionState', QVector2D(intensity, float(intensity > 0)))
            root.setProperty('flowSource', 'image://plasma/flow/'+str(self.serial))
            root.setProperty('baseSource', 'image://plasma/base/'+str(self.serial))
            self.show()

    return PlasmaSurface()
