# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real mouse-event contracts for platforms without system resize support."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QEvent, QCoreApplication
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QWidget
from augmentor_linux.resize import ResizeBorders


class Surface(QWidget):
    compact = False
    def surface_rect(self): return self.rect()
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'borders'): self.borders.update()


class ResizeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = Surface(); self.window.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.window.setMinimumSize(364, 364); self.window.setMaximumSize(620, 680)
        self.window.setGeometry(150, 180, 424, 484)
        self.window.borders = ResizeBorders(self.window); self.window.show(); self.app.processEvents()
        self.native = Mock(return_value=False)
        self.patcher = patch.object(self.window, 'windowHandle', return_value=SimpleNamespace(startSystemResize=self.native))
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop(); self.window.close(); self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def event(self, handle, kind, global_position, button, buttons):
        local = handle.mapFromGlobal(global_position)
        event = QMouseEvent(kind, QPointF(local), QPointF(global_position), button, buttons, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(handle, event); self.app.processEvents()

    def begin(self, handle, button=Qt.MouseButton.LeftButton):
        origin = handle.mapToGlobal(handle.rect().center())
        self.event(handle, QEvent.Type.MouseButtonPress, origin, button, button)
        return origin

    def move(self, handle, point):
        self.event(handle, QEvent.Type.MouseMove, point, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)

    def end(self, handle, point):
        self.event(handle, QEvent.Type.MouseButtonRelease, point, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)

    def test_every_edge_and_corner_resizes_when_native_operation_is_unsupported(self):
        initial = QRect(self.window.geometry())
        expected = [(0,40,0,-40),(0,0,0,40),(60,0,-60,0),(0,0,60,0),
                    (60,40,-60,-40),(0,40,60,-40),(60,0,-60,40),(0,0,60,40)]
        for handle, (dx,dy,dw,dh) in zip(self.window.borders.handles, expected):
            with self.subTest(edges=handle.edges):
                self.window.setGeometry(initial); self.app.processEvents()
                origin = self.begin(handle); target = origin+QPoint(60,40)
                self.move(handle, target); self.end(handle, target)
                self.assertEqual(self.window.geometry(), QRect(initial.x()+dx,initial.y()+dy,initial.width()+dw,initial.height()+dh))

    def test_clamped_top_left_drag_keeps_opposite_corner_and_original_pointer_anchor(self):
        initial = QRect(self.window.geometry()); handle = self.window.borders.handles[4]
        origin = self.begin(handle)
        self.move(handle,origin+QPoint(2000,2000))
        self.assertEqual(self.window.size(),self.window.minimumSize())
        self.assertEqual(self.window.geometry().bottomRight(),initial.bottomRight())
        self.move(handle,origin-QPoint(2000,2000))
        self.assertEqual(self.window.size(),self.window.maximumSize())
        self.assertEqual(self.window.geometry().bottomRight(),initial.bottomRight())
        self.move(handle,origin+QPoint(20,10))
        self.assertEqual(self.window.geometry(),QRect(initial.x()+20,initial.y()+10,initial.width()-20,initial.height()-10))
        self.end(handle,origin+QPoint(20,10))

    def test_release_or_lost_capture_ends_manual_resize(self):
        for finish in ('release','ungrab','hide'):
            with self.subTest(finish=finish):
                handle = self.window.borders.handles[7]; origin = self.begin(handle)
                self.move(handle,origin+QPoint(15,20)); before = QRect(self.window.geometry())
                if finish=='release': self.end(handle,origin+QPoint(15,20))
                elif finish=='ungrab': QApplication.sendEvent(handle,QEvent(QEvent.Type.UngrabMouse))
                else: handle.hide(); self.app.processEvents()
                self.move(handle,origin+QPoint(100,100))
                self.assertEqual(self.window.geometry(),before)
                self.assertIsNone(handle.drag_origin); handle.show()

    def test_linux_native_resize_path_does_not_apply_a_second_geometry_change(self):
        self.native.return_value=True;handle=self.window.borders.handles[7]
        before=QRect(self.window.geometry());origin=self.begin(handle)
        self.move(handle,origin+QPoint(60,40));self.end(handle,origin+QPoint(60,40))
        self.native.assert_called_once_with(handle.edges)
        self.assertEqual(self.window.geometry(),before);self.assertIsNone(handle.drag_origin)

    def test_secondary_click_and_compact_orb_do_not_resize(self):
        handle=self.window.borders.handles[7];self.begin(handle,Qt.MouseButton.RightButton)
        self.native.assert_not_called();self.assertIsNone(handle.drag_origin)
        self.window.compact=True;self.window.borders.update()
        self.assertTrue(all(not h.isVisible() for h in self.window.borders.handles))
