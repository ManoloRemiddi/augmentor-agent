#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Report actual Qt fallback glyphs for the unchanged native surface design.

Run with the selected ordinary-user Python and QT_QPA_PLATFORM=offscreen.
Reads the design as literal data; no application, service or device is started.
Missing shaped glyphs fail the probe, even when font packages are registered.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--design', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if os.geteuid() == 0:
        raise ValueError('Run the font probe as an ordinary user.')
    content = args.design.read_bytes()
    assignments = [node for node in ast.parse(content).body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == 'SURFACE' for target in node.targets)]
    if len(assignments) != 1:
        raise ValueError('Expected one literal native SURFACE design.')
    surface = ast.literal_eval(assignments[0].value)
    from PySide6 import QtCore, QtGui, QtWidgets
    application = QtWidgets.QApplication([])
    font = QtGui.QFont(surface['fontFamily'])
    font.setPixelSize(surface['iconFontSize'])
    raw = QtGui.QRawFont.fromFont(font)
    rows = {}
    for name, glyph in surface['glyphs'].items():
        layout = QtGui.QTextLayout(glyph, font)
        layout.beginLayout()
        line = layout.createLine()
        line.setLineWidth(1000)
        layout.endLayout()
        runs = [{'family': run.rawFont().familyName(), 'style': run.rawFont().styleName(),
                 'indexes': list(run.glyphIndexes())} for run in layout.glyphRuns()]
        indexes = [index for run in runs for index in run['indexes']]
        rows[name] = {'text': glyph, 'codepoints': [f'U+{ord(char):04X}' for char in glyph],
                      'primaryIndexes': list(raw.glyphIndexesForString(glyph)),
                      'runs': runs, 'present': bool(indexes) and all(index != 0 for index in indexes),
                      'advance': line.naturalTextWidth(), 'iconWidth': surface['iconSize']}
    report = {'format': 'augmentor-linux-surface-font-proof/1', 'uid': os.getuid(),
              'qtVersion': QtCore.qVersion(), 'designSha256': hashlib.sha256(content).hexdigest(),
              'probeSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'primaryFamily': raw.familyName(), 'primaryStyle': raw.styleName(),
              'pixelSize': surface['iconFontSize'], 'glyphs': rows,
              'passed': all(row['present'] and row['advance'] <= row['iconWidth'] for row in rows.values()),
              'realDesktopTested': False, 'ownerStateChanged': False}
    args.out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
