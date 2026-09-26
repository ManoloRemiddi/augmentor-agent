<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Desktop window resizing

The expanded frameless window has invisible resize handles on all four edges
and corners. The corresponding pointer appears on hover. Linux delegates the
drag to the desktop compositor when Qt accepts it. On macOS, where the installed
Cocoa backend returns false from `startSystemResize`, the same handles apply the
pointer delta to the window geometry. This restores the existing interaction
without adding a control or changing the approved appearance.

The fallback uses global logical coordinates, anchors the opposite edge, and
respects the current minimum (364 × 364) and maximum dimensions. Releasing the
pointer, losing its grab, or hiding the handle ends the drag. The circular view
remains fixed at 104 × 104 and restores the expanded size. Conversation content
and the unsent composer remain untouched. The native compositor path is retained
on platforms that support it; see [Qt's resize contract](https://doc.qt.io/qt-6/qwindow.html#startSystemResize)
and [Qt's platform guidance](https://www.qt.io/blog/custom-window-decorations).

## September 26 macOS correction

The owner requested restoring resize parity and moving the recently added DSH
setup/browser controls into the existing three-dot menu. The main setup row has
been removed; **Agent setup** and **Open DSH in browser** remain in that menu.
First-run setup and authenticated browser opening are retained. Other visible
changes need the owner's permission.

Before the fix, the 32 GB Mac's actual Cocoa window returned false from native
resize and stayed at 424 × 484 after a corner drag. The corrected source passed
all eight drags in `scripts/macos-resize-proof.py`, using synthetic Qt pointer
events on a real Cocoa window. The proof also checks menu placement, preserved
draft/answer, hide/show, and circular-view restoration, and captures the window
and menu for visual inspection. It uses a temporary profile, no model calls and
no owner data. This is not a physical mouse or Retina-display acceptance claim.

Five regression tests cover all handles, min/max clamps, the anchored opposite
edge, release/capture loss, compact mode, and native-path delegation. They passed
on Linux and macOS; the Mac's full 117 Mac tests and 27 native-window tests also
passed. Linux's locally installed Qt lacks QtTest, so its full window suite could
not complete locally; the focused resize tests require no QtTest. The actual
Cocoa proof and screenshots passed on the 32 GB Mac. Artifact qualification and
installed scope are recorded below after activation; source checks alone do not
establish an installed update.

## Earlier Linux 0.2.5 evidence — historical

The original implementation replaced the tiny footer corner grip with invisible
border handles and retained the compositor's drag behavior. Its then-current
minimum was 300 × 300. The following evidence belongs to that historical build.

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
