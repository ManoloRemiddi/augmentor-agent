#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Render the shared preview using Windows QPA and assert real font coverage."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'apps/native'))
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontDatabase, QFontInfo, QFontMetrics
from PySide6.QtWidgets import QApplication
from augmentor_linux.window import Window


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('This proof requires the Windows Qt platform plugin.')
    app = QApplication([])
    assert app.platformName() == 'windows', 'Offscreen rendering cannot establish Windows font/shell behavior'
    window = Window(preview=True)
    window.bring_forward()

    def capture():
        try:
            assert QFontDatabase.families(), 'The platform supplied no usable fonts'
            metrics = QFontMetrics(window.composer.font())
            assert all(metrics.inFontUcs4(ord(c)) for c in 'Augmentor 012 café'), 'Desktop text rendered as missing glyphs'
            args.out.mkdir(parents=True, exist_ok=True)
            assert window.grab().save(str(args.out/'desktop-windows.png'))
            (args.out/'desktop-windows.json').write_text(json.dumps({
                'platformPlugin': app.platformName(), 'font': QFontInfo(window.composer.font()).family(),
                'fontCoverage': True, 'rendered': True,
                'scope': 'Shared source preview in hosted Windows session; not installed app or physical graphics acceptance.'
            }, indent=2)+'\n', encoding='utf-8')
        except Exception as error:
            print(str(error), file=sys.stderr)
            app.exit(1)
        else:
            app.exit(0)
    QTimer.singleShot(700, capture)
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
