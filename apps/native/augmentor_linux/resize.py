# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Mouse resize borders for the frameless conversation window."""
from PySide6.QtCore import Qt, QRect, QEvent
from PySide6.QtWidgets import QWidget


class ResizeHandle(QWidget):
    def __init__(self, window, edges, cursor):
        super().__init__(window)
        self.edges = edges
        self.drag_origin = None
        self.drag_geometry = None
        self.setCursor(cursor)
        self.setAccessibleName('Resize window')
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            self.drag_origin = self.drag_geometry = None
            # Cocoa does not implement startSystemResize. Keep the native path
            # on Linux/other supported platforms, and honor its return value.
            if not handle or not handle.startSystemResize(self.edges):
                self.drag_origin = event.globalPosition().toPoint()
                self.drag_geometry = QRect(self.window().geometry())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_origin is None:
            super().mouseMoveEvent(event); return
        if not event.buttons() & Qt.MouseButton.LeftButton:
            self.drag_origin = self.drag_geometry = None
            return
        delta = event.globalPosition().toPoint() - self.drag_origin
        window = self.window()
        x, y, width, height = self.drag_geometry.getRect()
        # Global Qt coordinates are logical pixels, including on Retina. Anchor
        # to the original rectangle so limits never move the opposite edge.
        if self.edges & Qt.Edge.LeftEdge:
            new_width = max(window.minimumWidth(), min(window.maximumWidth(), width - delta.x()))
            x += width - new_width; width = new_width
        elif self.edges & Qt.Edge.RightEdge:
            width = max(window.minimumWidth(), min(window.maximumWidth(), width + delta.x()))
        if self.edges & Qt.Edge.TopEdge:
            new_height = max(window.minimumHeight(), min(window.maximumHeight(), height - delta.y()))
            y += height - new_height; height = new_height
        elif self.edges & Qt.Edge.BottomEdge:
            height = max(window.minimumHeight(), min(window.maximumHeight(), height + delta.y()))
        window.setGeometry(x, y, width, height)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.drag_origin is not None:
            self.drag_origin = self.drag_geometry = None
            event.accept(); return
        super().mouseReleaseEvent(event)

    def event(self, event):
        if event.type() in (QEvent.Type.UngrabMouse, QEvent.Type.Hide):
            self.drag_origin = self.drag_geometry = None
        return super().event(event)


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
