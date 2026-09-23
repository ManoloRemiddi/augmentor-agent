# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Mouse resize borders for the frameless conversation window."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


class ResizeHandle(QWidget):
    def __init__(self, window, edges, cursor):
        super().__init__(window)
        self.edges = edges
        self.setCursor(cursor)
        self.setAccessibleName('Resize window')
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle:
                # Let the compositor handle scaling, limits and pointer capture.
                handle.startSystemResize(self.edges)
            event.accept()
        else:
            super().mousePressEvent(event)


class ResizeBorders:
    def __init__(self, window):
        self.window = window
        edge = Qt.Edge
        cursor = Qt.CursorShape
        self.handles = [
            ResizeHandle(window, edge.TopEdge, cursor.SizeVerCursor),
            ResizeHandle(window, edge.BottomEdge, cursor.SizeVerCursor),
            ResizeHandle(window, edge.LeftEdge, cursor.SizeHorCursor),
            ResizeHandle(window, edge.RightEdge, cursor.SizeHorCursor),
            ResizeHandle(window, edge.TopEdge | edge.LeftEdge, cursor.SizeFDiagCursor),
            ResizeHandle(window, edge.TopEdge | edge.RightEdge, cursor.SizeBDiagCursor),
            ResizeHandle(window, edge.BottomEdge | edge.LeftEdge, cursor.SizeBDiagCursor),
            ResizeHandle(window, edge.BottomEdge | edge.RightEdge, cursor.SizeFDiagCursor),
        ]
        self.update()

    def update(self):
        surface = self.window.surface_rect()
        width, height = surface.width(), surface.height()
        corner, border = 12, 6
        rectangles = [
            (corner, 0, width - 2 * corner, border),
            (corner, height - border, width - 2 * corner, border),
            (0, corner, border, height - 2 * corner),
            (width - border, corner, border, height - 2 * corner),
            (0, 0, corner, corner),
            (width - corner, 0, corner, corner),
            (0, height - corner, corner, corner),
            (width - corner, height - corner, corner, corner),
        ]
        for handle, rectangle in zip(self.handles, rectangles):
            x, y, w, h = rectangle
            handle.setGeometry(surface.x() + x, surface.y() + y, w, h)
            handle.setVisible(not self.window.compact)
            handle.raise_()
