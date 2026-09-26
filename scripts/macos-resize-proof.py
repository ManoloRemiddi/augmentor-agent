#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Synthetic Qt pointer drags on a real Cocoa window, isolated from owner data."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'darwin': raise SystemExit('Run in a macOS GUI session.')
    root = args.app_root.resolve(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(root/'apps/native'), str(root/'services')]
    os.environ.pop('QT_QPA_PLATFORM', None)
    with tempfile.TemporaryDirectory(prefix='augmentor-resize-') as profile:
        for name in ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'XDG_RUNTIME_DIR'):
            os.environ[name] = str(Path(profile)/name); Path(os.environ[name]).mkdir()
        os.environ['AUGMENTOR_SHARED_STATE'] = str(Path(profile)/'shared')
        os.environ['AUGMENTOR_PI_CONFIG'] = str(Path(profile)/'appearance')
        from PySide6.QtCore import Qt, QPoint, QRect, QTimer
        from PySide6.QtWidgets import QApplication, QPushButton, QMenu
        from PySide6.QtTest import QTest
        from augmentor_linux.window import Window
        app = QApplication([])
        assert app.platformName() == 'cocoa'
        window = Window(preview=True)
        window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        window.preferences.values.update(pinned=False, animation=False)
        window.messages = [('You', 'Keep this conversation while resizing.'), ('Augmentor', 'The answer remains intact.')]
        window.render_messages(); draft = 'Unsent resize verification draft'
        window.composer.setPlainText(draft)
        window.show(); window.setGeometry(300, 200, 424, 484); QTest.qWait(250)
        native = window.windowHandle(); original_resize = native.startSystemResize; accepted = []
        def resize(edges):
            result = original_resize(edges); accepted.append(result); return result
        native.startSystemResize = resize
        records = []
        try:
            directions = [('top',0,-1), ('bottom',0,1), ('left',-1,0), ('right',1,0),
                          ('top-left',-1,-1), ('top-right',1,-1), ('bottom-left',-1,1), ('bottom-right',1,1)]
            for handle, (name, horizontal, vertical) in zip(window.resize_borders.handles, directions):
                window.setGeometry(300, 200, 424, 484); QTest.qWait(30)
                before = QRect(window.geometry()); origin = handle.mapToGlobal(handle.rect().center())
                QTest.mousePress(native, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, window.mapFromGlobal(origin))
                # Small steps exercise hit-testing and the implicit mouse grab
                # while keeping the synthetic pointer within the moving border.
                for step in range(1, 25):
                    target = origin + QPoint(horizontal*step*2, vertical*step*2)
                    QTest.mouseMove(native, window.mapFromGlobal(target)); app.processEvents()
                QTest.mouseRelease(native, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, window.mapFromGlobal(target))
                QTest.qWait(30)
                expected = QRect(before.x()-48 if horizontal<0 else before.x(),
                                 before.y()-48 if vertical<0 else before.y(),
                                 before.width()+48*bool(horizontal), before.height()+48*bool(vertical))
                assert window.geometry() == expected, (name, before, window.geometry(), expected)
                assert handle.drag_origin is None
                assert window.composer.toPlainText() == draft, (name, repr(window.composer.toPlainText()))
                assert 'The answer remains intact.' in window.transcript.toPlainText()
                records.append({'handle': name, 'before': list(before.getRect()), 'after': list(window.geometry().getRect())})
            assert accepted == [False]*8, accepted
            expanded = QRect(window.geometry())
            window.hide(); window.show(); QTest.qWait(150)
            assert window.geometry() == expanded
            window.toggle_compact(); QTest.qWait(100)
            assert window.size().width() == 104 and not any(h.isVisible() for h in window.resize_borders.handles)
            window.toggle_compact(); QTest.qWait(100)
            assert window.size() == expanded.size() and all(h.isVisible() for h in window.resize_borders.handles)
            assert window.composer.toPlainText() == draft
            assert not any('DSH' in b.text() or 'Agent setup' in b.text() for b in window.findChildren(QPushButton))
            assert window.grab().save(str(out/'window.png'))
            # A preview has no live controller; supply only its harness identity
            # to inspect the actual menu. Do not trigger setup or browser actions.
            window.controller = SimpleNamespace(harness='dsh')
            menu_actions = []
            def inspect_menu():
                menu = QApplication.activePopupWidget()
                if isinstance(menu, QMenu):
                    menu_actions.extend(a.text() for a in menu.actions())
                    menu.grab().save(str(out/'menu.png')); menu.close()
            QTimer.singleShot(100, inspect_menu)
            QTimer.singleShot(2000, lambda: QApplication.activePopupWidget().close() if QApplication.activePopupWidget() else None)
            QTest.mouseClick(window.more_button, Qt.MouseButton.LeftButton)
            window.controller = None
            assert 'Agent setup' in menu_actions and 'Open DSH in browser' in menu_actions, menu_actions
            report = {'passed': True, 'platform': 'cocoa', 'syntheticQtPointerDrags': records,
                      'physicalMouseTested': False, 'devicePixelRatio': window.devicePixelRatio(),
                      'systemResizeAccepted': accepted, 'hideShowPreservesGeometry': True,
                      'compactRestoresSize': True, 'draftAndAnswerPreserved': True,
                      'mainSetupRowAbsent': True, 'menuActions': menu_actions}
            (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
            print(json.dumps(report))
        finally:
            window.controller = None; window.close()


if __name__ == '__main__': main()
