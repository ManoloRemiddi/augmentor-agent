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

The owner subsequently confirmed the flare is working well. Preserve this renderer
and the disabled native effect-window shadow.

## Size preference — historical startup-only implementation

Superseded by [live zoom](MACOS-LIVE-ZOOM-2026-09-27.md) after the owner reported that
moving the slider did not visibly change the running window.

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

The clean preview built from **`7ff67122d77f5d7007741694e4e5b9d1639a1062`** is
installed at `/Applications/Augmentor Agent Desktop.app` on the 32 GB M4 Mac.
It replaces `c3a7fab`; no source overlay was applied to an installed bundle.

- ZIP: `augmentor-desktop-0.2.12-macos-arm64-preview.zip`, 339,759,999 bytes.
- ZIP SHA-256: `7b38a698254a87037f83867f7419781622a10316162dbe4af9a06deb0a407aa7`.
- Application inventory: 589 entries, SHA-256 `e4b3c8fe3b464bf901e8a1b78b2aa9aaa94e2ec63c63d8f4847d7508d90cb995`.
- Running primary read-back: **110%**, **1.1 DPR**, online, model-ready, and the
  canonical installed build root. Full inventory and strict ad-hoc signature pass.
- Packaged Metal transparency, Appearance keyboard/persistence/draft checks and
  all eight Cocoa resize handles passed at 110%. The native effect shadow is false;
  all four outer eight-pixel strips are transparent, including the actual flare.
- The installed native app restored its dedicated qualification conversation and
  received a real provider reply via the composer/Send button. It closed idle;
  the owner's primary window remains open with test control disabled.
- Saved DSH settings, connection and all four conversation metadata records matched
  before/after replacement. The only intended primary appearance change was 110%.
- The owned shortcut service reports protocol 2, **Fn+Space active**, no error.
  Physical keypress and whole-display compositor capture remain unqualified.
- The temporary candidate, rollback bundle and source staging were removed after
  retaining the verified rollback ZIP in a non-indexed cache. The build Mac's own
  temporary bundle/source were also removed. Finder/Spotlight returns one app,
  LaunchServices has one application registration, and the Dock has one tile.

At the binary source revision, both [Mac 14/26 jobs](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36308457163),
Debian validation, Browser and Home passed. The installed Linux package job caught
a pre-existing maintenance race: the desktop exited after `identity()` but before
the second `/proc/PID/stat` read. The Linux maintenance helper now treats only
that missing-file race as successful exit, preserving permission errors.
Its six lifecycle tests pass, including two new regressions. That Linux-only
correction is later than the Mac artifact above and is not an installed Mac patch.
At `fa77135`, the [complete validation workflow](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36309091775) passed, including Debian, Browser, Home and installed-package installation/upgrade/interruption/rollback/removal. The [Mac 14/26 workflow](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36309091817) also passed at that revision. Later documentation records do not change the installed Mac bytes.

Linux selection, the other Mac's working app and the public website download
remain unchanged. This is an installed private preview update, not a new public
release, Apple signing, or automatic-update qualification.
