<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Linux window resizing

The expanded, frameless Linux window has mouse resize handles on all four edges
and corners. Hovering changes the pointer to the corresponding resize cursor;
pressing and dragging delegates resizing to the desktop compositor. This handles
screen scaling, pointer capture and the existing 300 × 300 minimum size. The
footer's tiny, single-corner grip is replaced by the window borders. Content
margins keep the border handles away from the chat controls.

The circular view remains fixed in size. Returning to the conversation restores
its expanded dimensions; existing placement persistence preserves the selected
size when the window is hidden and reopened. Both harnesses share this UI.

Verification: all 91 native tests passed. `scripts/proof-window-resize.py` uses
real UInput mouse events and KWin observations against an isolated Qt preview,
without model calls or user state changes. All eight edges/corners resized the
expected dimensions, retained the answer and composer draft, and preserved size
through hide/show and circular-view toggling. Evidence is in
`outputs/resize-desktop-proof/proof.json` and `resized.png`.

The Debian artifact is recorded in `outputs/debian-resize-0.2.5/artifacts.json`.

Installed successfully through the Debian package installer. The installed native
files match the tested source. A further real mouse test enlarged and shrank the
user's running Augmentor window, with the saved answer still visible. Its
original dimensions were restored afterward. Evidence:
`outputs/resize-installed-proof.json` and `resize-installed-expanded.png`.
Both the Linux app and browser companion were reconnected after installation.
