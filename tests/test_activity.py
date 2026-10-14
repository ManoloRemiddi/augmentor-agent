# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Shared plasma fidelity checks; no platform-specific renderer or live agent."""
import unittest
from unittest.mock import patch
import numpy as np
from PySide6.QtCore import Qt, QPointF, QPoint, QRect, QCoreApplication
from PySide6.QtGui import QImage, QMoveEvent
from PySide6.QtWidgets import QApplication
from augmentor_linux.activity import FlowNoise, image_array, restore_emission_detail
from augmentor_linux.window import Window


def image(data):
    h, w = data.shape[:2]
    return QImage(data.data, w, h, w*4, QImage.Format.Format_RGBA8888).copy()


class ActivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_vector_noise_preserves_field_at_negative_and_wrapped_coordinates(self):
        noise = FlowNoise()
        x = np.array([-256.3, -128., -.8, 0., 1.4, 127.75, 999.2], np.float32)
        y = np.array([37.2, -19., 1.7, 127.9, -85., 1000., -300.8], np.float32)
        expected = [noise.sample(float(a), float(b)) for a, b in zip(x, y)]
        np.testing.assert_allclose(noise.sample_array(x, y), expected, atol=2e-7)

    def test_exterior_effect_never_requests_a_native_shadow(self):
        window=Window(preview=True)
        try:
            self.assertTrue(window.activity.canvas.windowFlags() & Qt.WindowType.NoDropShadowWindowHint)
        finally:
            window.close()

    def test_nonanimated_canvas_displacement_recovers_without_moving_owner_or_starting_animation(self):
        window=Window(preview=True)
        try:
            window.setGeometry(300,300,424,484);window.show()
            activity=window.activity;activity.configure(animated=False,busy=True)
            QCoreApplication.processEvents()
            owner=QRect(window.geometry());extra=activity.extent-activity.margin
            expected=QRect(window.mapToGlobal(QPoint()),window.size()).adjusted(-extra,-extra,extra,extra)
            self.assertFalse(activity.timer.isActive())
            # A platform/transient notification can move only the canvas after
            # the owner's own Move has finished. No user input or model work.
            activity.canvas.move(expected.topLeft()+QPoint(0,80))
            QCoreApplication.processEvents();QCoreApplication.processEvents()
            self.assertEqual(activity.canvas.geometry(),expected)
            self.assertEqual(window.geometry(),owner)
            self.assertFalse(activity.timer.isActive())
        finally:
            window.close()

    def test_refused_canvas_placement_is_bounded_and_an_owner_move_renews_it(self):
        window=Window(preview=True)
        try:
            window.setGeometry(300,300,424,484);window.show()
            activity=window.activity;activity.configure(animated=False,busy=True)
            QCoreApplication.processEvents();canvas=activity.canvas
            canvas.move(canvas.pos()+QPoint(0,80))
            with patch.object(canvas,'setGeometry') as refused:
                for _ in range(12):
                    QCoreApplication.sendEvent(canvas,QMoveEvent(canvas.pos(),canvas.pos()))
                    QCoreApplication.processEvents()
                self.assertGreater(refused.call_count,0)
                self.assertLessEqual(refused.call_count,2)
                previous=refused.call_count
                window.move(window.pos()+QPoint(10,10))
                QCoreApplication.processEvents()
                self.assertGreater(refused.call_count,previous)
            self.assertFalse(activity.timer.isActive())
        finally:
            window.close()

    def test_queued_canvas_correction_cannot_reshow_a_hidden_owner(self):
        window=Window(preview=True)
        try:
            window.show();activity=window.activity;activity.configure(animated=False,busy=True)
            QCoreApplication.processEvents()
            activity.canvas.move(activity.canvas.pos()+QPoint(0,80));window.hide()
            QCoreApplication.processEvents();QCoreApplication.processEvents()
            self.assertFalse(activity.canvas.isVisible())
            self.assertFalse(activity.timer.isActive())
        finally:
            window.close()

    def test_detail_restores_thin_emission_instead_of_stretching_a_coarse_cell(self):
        data = np.zeros((80, 80, 4), np.uint8)
        data[10:70, 39:41] = (60, 180, 140, 160)
        source = image(data)
        coarse = source.scaled(20, 20, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        stationary = coarse.convertToFormat(QImage.Format.Format_RGBA8888_Premultiplied)
        result_image = restore_emission_detail(source, coarse, stationary)
        result = image_array(result_image)
        expected_image = source.convertToFormat(QImage.Format.Format_RGBA8888_Premultiplied)
        np.testing.assert_array_equal(result, image_array(expected_image))
        self.assertEqual(np.count_nonzero(result[40, :, 3]), 2)

    def test_detached_transported_smoke_survives_without_an_emission_source(self):
        source = image(np.zeros((80, 80, 4), np.uint8))
        coarse = source.scaled(20, 20)
        smoke = np.zeros((20, 20, 4), np.uint8)
        smoke[8:12, 8:12] = (50, 100, 90, 80)
        transported = image(smoke).convertToFormat(QImage.Format.Format_RGBA8888_Premultiplied)
        result_image = restore_emission_detail(source, coarse, transported)
        result = image_array(result_image)
        expected_image = transported.scaled(80, 80, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        expected = image_array(expected_image)
        np.testing.assert_array_equal(result, expected)
        self.assertGreater(result[40, 40, 3], 0)

    def test_screen_density_changes_detail_cache_without_expanding_fluid_work(self):
        window = Window(preview=True)
        try:
            window.resize(424, 484)
            a = window.activity; a.position_canvas(); rect = a.canvas_surface_rect()
            with patch.object(a.canvas, 'devicePixelRatioF', return_value=1.):
                a.prepare_geometry(rect)
                self.assertEqual((a.image_width, a.image_height), (744, 804))
                key = a.geometry_key; coarse = (a.flow_width, a.flow_height)
            with patch.object(a.canvas, 'devicePixelRatioF', return_value=2.):
                a.prepare_geometry(rect)
                self.assertNotEqual(a.geometry_key, key)
                self.assertGreater(a.image_width, 744)
                self.assertLessEqual(a.image_width*a.image_height, 1_005_000)
                self.assertEqual((a.flow_width, a.flow_height), coarse)
        finally:
            window.close()

    def test_large_windows_have_bounded_detail_and_rebuild_after_resize(self):
        window = Window(preview=True)
        try:
            a = window.activity
            for width, height in ((1600, 1200), (424, 484)):
                window.resize(width, height); a.position_canvas()
                a.prepare_geometry(a.canvas_surface_rect())
                self.assertLess(a.image_width*a.image_height, 1_005_000)
                self.assertEqual(a.distance_grid.shape, (a.flow_height, a.flow_width))
            self.assertEqual((a.image_width, a.image_height), (744, 804))
        finally:
            window.close()

    def test_animated_flare_and_pointer_motion_keep_valid_premultiplied_edges(self):
        window = Window(preview=True)
        try:
            window.resize(424, 484); a = window.activity; a.position_canvas()
            rect = a.canvas_surface_rect(); a.breath_phase = 2.
            a.flare = dict(start=0., duration=3., side=0, position=.5, width=55., travel=150.)
            for i in range(8):
                a.phase = .6+i*.04
                a.pointer = QPointF(rect.center().x()-20+i*6, rect.top()-30)
                a.render_field(rect, window.accent)
                pixels = image_array(a.frame)
                self.assertTrue(np.all(pixels[..., :3] <= pixels[..., 3, None]))
                self.assertFalse(np.any(pixels[[0, -1], :, 3]))
                self.assertFalse(np.any(pixels[:, [0, -1], 3]))
            self.assertGreater(np.max(np.abs(a.fluid.velocity)), 0)
            self.assertGreater(pixels[..., 3].max(), 40)
        finally:
            window.close()
