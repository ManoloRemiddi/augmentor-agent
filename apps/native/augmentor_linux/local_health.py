# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bounded shared UI health without services, network or persistent preferences.

The platform caller must configure a disposable profile before importing the UI.
This checks local renderability only; artifact trust, complete file integrity,
data compatibility and transaction completion remain the caller's responsibility.
"""


def render_preview(*, platform):
    from PySide6.QtGui import QFontDatabase, QFontMetrics
    from PySide6.QtWidgets import QApplication
    from .window import Window

    app = QApplication.instance() or QApplication(['augmentor-local-health'])
    if app.platformName() != platform:
        raise RuntimeError('The expected native Qt platform did not load.')
    window = Window(preview=True)
    try:
        if window.controller is not None or window.preferences.persistent:
            raise RuntimeError('Local health must not open a persistent conversation.')
        window.ensurePolished()
        window.composer.setPlainText('Augmentor local health · café 012')
        app.processEvents()
        metrics = QFontMetrics(window.composer.font())
        if not QFontDatabase.families() or not all(metrics.inFontUcs4(ord(c)) for c in 'Augmentor 012 café'):
            raise RuntimeError('Native text rendering is unavailable.')
        rendered = window.grab()
        if rendered.isNull() or rendered.width() < 1 or rendered.height() < 1:
            raise RuntimeError('The shared interface could not render.')
        return {'qtPlatform': app.platformName(), 'rendered': True,
                'width': rendered.width(), 'height': rendered.height(), 'fontCoverage': True}
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()
