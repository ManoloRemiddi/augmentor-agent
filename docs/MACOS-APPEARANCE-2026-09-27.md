<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# September 27 transparency and app size

The owner reported a remaining flare outline on the installed `c3a7fab` build.
That report supersedes any implication that the previous GPU performance proof
established visual acceptance. Read-back confirmed that the latest private build
was running; this was not an obsolete application selected by Finder.

## Transparent effect window

The isolated Cocoa fixture using the installed modules reported **NSWindow.hasShadow
= true** for the exterior effect window. AppKit's separate shadow can retain a
coarse silhouette as transparent animated content changes. Apple documents
[explicit shadow invalidation](https://developer.apple.com/documentation/appkit/nswindow/invalidateshadow()).
The effect surface now requests Qt's **NoDropShadowWindowHint** on both platforms.
The native Mac read-back becomes **false**. The main panel keeps its existing
window behavior. The effect is light and should not cast an additional shadow.

The older performance proof assigned its test flare before `configure(busy=True)`,
which clears an existing flare on the transition to busy. It now assigns it
after that transition. The new `plasma-transparency-proof.py` verifies actual
distant flare pixels, no-flare and decaying states, all four outer borders,
premultiplied color validity, and native shadow state. It saves light/dark
composites of the native Metal framebuffer. At 100% and 110% on the 32 GB Mac,
all outer eight-pixel strips had alpha zero; a flare reached alpha 51–52 beyond
70 logical pixels from the panel. At 110%, the native shadow was false and the
decaying distant smoke reached alpha 1 after the scripted decay interval.

These are own-window fixtures and native property read-backs, not a capture of
the complete desktop compositor or a claim of subjective owner acceptance.
Screen Recording and Accessibility permissions remain unchanged.

## Size preference

The owner requested a uniform 10% enlargement and an Appearance slider. The
shared [App size control](SKINS.md#app-size) supports 75–150%, with 100% reset,
per-window persistence, skin independence and native-resolution rendering.
It takes effect on the next process start. This avoids restarting active work
or depending on Qt's private runtime scaling interfaces. The Appearance dialog
is constrained to available screen height and retains its scrolling content.

Unit checks cover saved input bounds, external scale multiplication without
subprocess leakage, actual raster dimensions in new Qt processes, slider
persistence and draft preservation. `ui-scale-proof.py` exercises keyboard
slider input and captures a real Cocoa window and its Appearance dialog.

Source checks passed: 524 native tests (three environment skips), 182 Node tests,
TypeScript checking and build. Actual Mac 110% raster size was 466 × 532 for a
424 × 484 logical window, with a 26 × 26 pixel rendering of the 24 × 24 logical
button. Keyboard slider persistence, drafts, hide/show, all eight resize handles
and compact/expanded transitions passed on Cocoa at 1.1 DPR. Linux OpenGL passed
the same transparency proof; a native X11 150% fixture passed input, persistence,
draft preservation and a scrollable Appearance dialog constrained to its display.
The first size fixture incorrectly replaced the Preferences object after the
save timer had bound the original object. It was corrected to retain the object;
the actual slider changed correctly throughout. No product persistence defect
was inferred from that fixture mistake.

## Deployment state

Source qualification is in progress. This document does not yet certify a new
installed artifact. The 32 GB Mac still runs `c3a7fab` until the sealed candidate
passes checks and is activated. Linux selection, the other Mac's working app,
and the public website download are unchanged.
