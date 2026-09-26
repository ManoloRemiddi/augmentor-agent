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

## Qualified candidate and activation boundary

Application source `252215b` is published on PR #13. A separate ad-hoc-sealed
candidate applies nine application/document files over the installed runtime-first
candidate from `60413de`, retaining the public `ea128d6` binary and dependencies.
Its exact application-inventory SHA-256 is
`957fba0a08a82a063c3957c3057bbf34b5924ff664a9bf7f522b8415fc04d0f1`.
The sealed candidate passed the complete Cocoa resize/menu proof and strict
signature verification after use. Synthetic window/menu screenshots were visually
inspected. No owner model request, conversation, database or configuration change
was part of qualification.

The [Mac 14/26 workflow at `252215b`](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36259216754)
passed. The [full validation run](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36259216763)
also passed its Debian, Home and Browser jobs at the recorded checkpoint; installed
package lifecycle qualification was still running. Do not report that whole run
as successful from those individual jobs. The preceding documentation-only
`f0bc3c8` run had a Chromium fixture cleanup `ENOTEMPTY` failure; it is not a passing
full-suite checkpoint.

Activation is pending the owner closing the 32 GB Mac's desktop. The current
normal app does not expose unsent draft state, so an idle status is insufficient
permission to discard input. The owner was asked to finish any draft and quit.
The existing installer refuses live component leases; no forced closure or
in-place patch was attempted. At this checkpoint the installed desktop remains
`60413de`, online with one configured provider and one session. Only the staged
candidate has the menu/resize fix. A private activation helper is prepared to
verify an idle DSH, preserve its saved profile/session metadata, drain only its
verified owned runtime/helpers, atomically install with a retained backup, and
resume the same service. Recheck current state before using it.

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
