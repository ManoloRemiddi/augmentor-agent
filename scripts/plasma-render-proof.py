#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Measure real Qt animation and capture its own windows, with isolated state."""
import argparse
import json
import math
import os
from pathlib import Path
import random
import statistics
import sys
import tempfile
import time
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=6)
    parser.add_argument('--cpu', action='store_true')
    args = parser.parse_args()
    if args.cpu: os.environ['AUGMENTOR_PLASMA_RENDERER'] = 'cpu'
    args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='aug-render-') as directory:
        for name in ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'XDG_RUNTIME_DIR',
                     'AUGMENTOR_PI_CONFIG', 'AUGMENTOR_PI_STATE', 'AUGMENTOR_SHARED_DATA', 'AUGMENTOR_SHARED_STATE'):
            path = Path(directory)/name; path.mkdir(); os.environ[name] = str(path)
        sys.path.insert(0, str(args.app_root.resolve()/'apps/native'))
        from PySide6.QtCore import Qt, QTimer, QPointF, QEventLoop
        from PySide6.QtGui import QImage, QPainter, QColor
        from PySide6.QtWidgets import QApplication
        from PySide6.QtTest import QTest
        from augmentor_linux.window import Window
        from augmentor_linux.activity import FlowNoise, image_array
        app = QApplication([])
        window = Window(preview=True)
        window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        window.resize(457, 578); window.move(300, 200); window.show(); app.processEvents()
        activity = window.activity
        with patch('augmentor_linux.activity.random.Random', return_value=random.Random(714)):
            activity.noise = FlowNoise()
        activity.rng = random.Random(719)
        activity.breath_phase = 2.; activity.phase = 0.
        activity.strength = 1.
        activity.configure(busy=True, enabled=True, animated=True, effect='plasma')
        activity.flare = dict(start=0., duration=args.seconds+2, side=0, position=.5, width=55., travel=150.)
        gpu = activity.canvas.gpu
        if not args.cpu:
            assert gpu and gpu.available, 'GPU surface did not initialize'
        timings = []; heartbeat = []; frames = []
        original = activity.render_field
        start = time.monotonic()
        def render(*values):
            before = time.monotonic(); original(*values)
            if before-start > 1.: timings.append((time.monotonic()-before)*1000)
        activity.render_field = render
        def pointer(dt):
            rect = activity.canvas_surface_rect()
            activity.pointer = QPointF(rect.center().x()+60*math.sin(activity.phase*1.4), rect.top()-18)
        activity.update_interaction = pointer
        if gpu:
            gpu.quickWindow().afterRendering.connect(lambda: frames.append(time.monotonic()), Qt.ConnectionType.DirectConnection)
        pulse = QTimer(); pulse.setTimerType(Qt.TimerType.PreciseTimer); pulse.setInterval(25)
        pulse.timeout.connect(lambda: heartbeat.append(time.monotonic())); pulse.start()
        loop = QEventLoop()
        QTimer.singleShot(round(args.seconds*1000), loop.quit)
        loop.exec(); activity.timer.stop(); pulse.stop()
        elapsed = time.monotonic()-start
        intervals = [(b-a)*1000 for a,b in zip(heartbeat, heartbeat[1:]) if a-start > 1.]
        assert timings and intervals
        assert not gpu or not gpu.rootObject().property('failed'), 'Shader failed at runtime'
        if gpu:
            backend = gpu.quickWindow().rendererInterface().graphicsApi().name
            assert backend in ('Metal', 'OpenGL', 'Vulkan', 'Direct3D11', 'Direct3D12'), backend
            native = gpu.grabFramebuffer()
            assert not native.isNull()
            assert native.size().width() == round(activity.canvas.width()*activity.canvas.devicePixelRatioF())
            native.save(str(args.out/'native-plasma.png'))
            rgba = native.convertToFormat(QImage.Format.Format_RGBA8888)
            pixels = image_array(rgba)
            assert pixels[...,3].max() > 40
            assert not pixels[0,:,3].any() and not pixels[:,0,3].any()
        else: backend = 'CPU'
        assert abs(activity.fluid.velocity).max() > 0, 'Pointer transport was not exercised'
        # Input targets the fixture's composer, never the owner's window.
        window.composer.setFocus(); QTest.keyClicks(window.composer, 'Unsent rendering proof')
        assert window.composer.toPlainText() == 'Unsent rendering proof'
        window.resize(510, 610); QTest.qWait(100)
        assert not gpu or gpu.geometry() == activity.canvas.rect()
        canvas = activity.canvas.grab(); panel = window.grab()
        image = QImage(canvas.size(), QImage.Format.Format_RGB32)
        image.setDevicePixelRatio(canvas.devicePixelRatio()); image.fill(QColor('#23262b'))
        painter = QPainter(image); painter.drawPixmap(0, 0, canvas); painter.drawPixmap(160, 160, panel); painter.end()
        image.save(str(args.out/'proof.png'))
        activity.configure(effect='butterflies'); app.processEvents()
        assert not gpu or not gpu.isVisible()
        activity.configure(effect='plasma'); app.processEvents()
        activity.configure(enabled=False); app.processEvents()
        assert not activity.canvas.isVisible() and not activity.timer.isActive()
        report = {'passed': True, 'backend': backend, 'seconds': elapsed,
                  'cpuFrameMedianMs': statistics.median(timings), 'cpuFrameP95Ms': sorted(timings)[int(len(timings)*.95)],
                  'heartbeatMaxGapMs': max(intervals), 'renderedFrames': len(frames),
                  'renderedFramesPerSecond': len(frames)/elapsed if gpu else None,
                  'dpr': window.devicePixelRatioF(), 'nativePixelBuffer': bool(gpu),
                  'pointerTransport': True, 'resize': True, 'composerInput': True,
                  'effectSwitchAndIdleShutdown': True,
                  'wholeDesktopCapture': False, 'syntheticPointer': True}
        (args.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report), flush=True)
        window.close()


if __name__ == '__main__': main()
