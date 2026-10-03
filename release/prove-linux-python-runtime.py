#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Verify a locked Linux overlay in a disposable ordinary-user, offline fixture.

Run under the prepared interpreter and a private Xvfb session. This is an
import/render/immutability proof, not installed product or GNOME qualification.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--policy', type=Path, default=ROOT/'release/ubuntu24.04-python.json')
    parser.add_argument('--wheelhouse', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    assert os.geteuid() != 0
    assert args.runtime.absolute().is_relative_to(Path.home())
    assert args.out.absolute().is_relative_to(Path.home())
    assert Path(sys.prefix) == args.runtime.absolute() and sys.prefix != sys.base_prefix
    tool = load('owned_linux_runtime', ROOT/'scripts/linux-python-runtime.py')
    policy_path=args.policy.resolve()
    assert policy_path.is_relative_to(ROOT/'release')
    value = tool.policy(policy_path)
    receipt = tool.verify(value, args.runtime)
    previous = (args.runtime/tool.RECEIPT).read_bytes()
    reused = tool.prepare(value, args.wheelhouse, args.runtime.parent)
    assert reused == receipt and (args.runtime/tool.RECEIPT).read_bytes() == previous
    # Deliberately corrupt only this disposable runtime's config. Both verify
    # and prepare must refuse it, preserving the previous files for diagnosis.
    config = args.runtime/'pyvenv.cfg'
    original = config.read_bytes()
    try:
        config.write_bytes(original+b'\n# synthetic corruption\n')
        for check in (lambda: tool.verify(value, args.runtime),
                      lambda: tool.prepare(value, args.wheelhouse, args.runtime.parent)):
            try:
                check()
            except ValueError as error:
                assert 'files changed' in str(error)
            else:
                raise AssertionError('Changed runtime was accepted.')
        assert config.read_bytes() == original+b'\n# synthetic corruption\n'
        assert (args.runtime/tool.RECEIPT).read_bytes() == previous
    finally:
        config.write_bytes(original)
    tool.verify(value, args.runtime)

    from PySide6.QtCore import QByteArray, QUrl, Qt
    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtWidgets import QApplication, QWidget
    from PySide6.QtQuickWidgets import QQuickWidget
    from PySide6.QtSvg import QSvgRenderer
    QApplication.setDesktopFileName('com.augmentor.Agent')
    app = QApplication([])
    assert app.platformName() == 'xcb'
    widget = QWidget()
    widget.resize(240, 120); widget.show()
    for _ in range(10):app.processEvents()
    assert widget.isVisible() and widget.grab().size().width() == 240
    svg = QSvgRenderer(QByteArray(b'<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="32" height="32" fill="#336699"/></svg>'))
    assert svg.isValid()
    image = QImage(32, 32, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image); svg.render(painter); painter.end()
    assert image.pixelColor(16, 16) == QColor('#336699')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    qml = args.out.parent/'synthetic-runtime.qml'
    qml.write_text('import QtQuick\nRectangle { width: 100; height: 60; color: "#336699" }\n')
    quick = QQuickWidget()
    quick.resize(100, 60)
    quick.setSource(QUrl.fromLocalFile(str(qml)))
    quick.show()
    for _ in range(20):app.processEvents()
    assert quick.status() == QQuickWidget.Status.Ready, [str(e) for e in quick.errors()]
    assert quick.grabFramebuffer().pixelColor(50, 30) == QColor('#336699')
    quick.close(); widget.close()
    inventory = load('owned_linux_qt_inventory', ROOT/'scripts/qt-library-inventory.py').inventory()
    inventory_path = args.out.parent/'qt-binaries.json'
    inventory_path.write_text(json.dumps(inventory, indent=2)+'\n')
    report = {'format': 'augmentor-linux-python-runtime-fixture/1', 'target': value['target'],
              'policySha256': tool.digest(policy_path),
              'proofSha256': tool.digest(Path(__file__)),
              'runtimeToolSha256': tool.digest(ROOT/'scripts/linux-python-runtime.py'),
              'qtInventoryToolSha256': tool.digest(ROOT/'scripts/qt-library-inventory.py'),
              'lockIdentity': receipt['lockIdentity'], 'runtimeArtifactSha256': receipt['artifactSha256'],
              'runtimeFileCount': len(receipt['files']), 'imports': receipt['imports'],
              'offlineLockedWheelPrepare':True, 'verifiedWheelCount':len(value['wheels']),
              'offlineFiveWheelPrepare':len(value['wheels'])==5, 'exactRuntimeReusedWithoutRewrite': True,
              'tamperedRuntimeRefusedWithoutRepair': True,
              'qtWidgetsXcbRendered': True, 'qtSvgRendered': True, 'qtQuickSoftwareRendered': True,
              'qtBinaryCount': len(inventory['binaries']), 'qtSymlinkCount': len(inventory['symlinks']),
              'qtInventorySha256': tool.digest(inventory_path),
              'installedProductTested': False, 'approvedUiTested': False,
              'gnomeLoginTested': False, 'secretServiceLifecycleTested': False,
              'physicalAudioTested': False, 'handsFreeTested': False,
              'licenseReviewComplete': False, 'embeddedSourceCoverageComplete': False}
    args.out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
