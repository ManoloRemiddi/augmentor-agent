<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor 0.2.12 desktop flare correction

## Current source: late canvas placement — October 15

The original managed transient can receive a native Move after its owner's own
geometry notification. Activity previously observed only owner events and the
animation tick. A static effect therefore remained offset after a late external
canvas move. The common Qt test and real isolated X11/KWin external-move proof
both fail against the preceding code and pass with the correction. The native
proof confirms an actual spontaneous canvas notification, fixed owner geometry
and an inactive animation timer; it does not rely on an ignored move command.

Activity now observes its canvas too and coalesces reconciliation through an
owned zero-delay timer. The owner's existing target rectangle, exterior extent,
window flags, appearance, input transparency, workspace/stacking and renderer
are preserved. A correction changes only the canvas; it starts no animation.
At most two corrections are attempted for an unresolved owner target, so a
platform that refuses placement cannot drive an unbounded correction loop.
Owner movement/normal synchronization renews the opportunity. Hidden, minimized,
morphing or disabled effects are not revealed by queued work. Qt's
[geometry/event contract](https://doc.qt.io/qt-6/qwidget.html#geometry-prop)
and [move recursion warning](https://doc.qt.io/qt-6/qwidget.html#pos-prop)
support deferred correction rather than recursive movement in the canvas event.

At application **2458816ed4dc43a2e0d442d0e1ee8ce4e437d520**, ten common Activity cases pass. The
strengthened ten-phase two-process X11/KWin proof passes on source and fresh
ordinary trees, on CPU and Qt Quick/OpenGL via forced Mesa llvmpipe. The latter
is software-backed shader-path evidence; physical RTX/Metal acceptance remains
open. Existing Linux/macOS recipes cover Activity; Windows Desktop now includes
it. No model or real speech service is used by these proofs.

The unchanged Harness cohort passes **272/272 on source and ordinary trees**,
64 files including all 44 Harness Chromium files and 15 shared prompt DOM cases,
two workers, unchanged deadlines and no skips/cancellations. All 921 compiled
files retain the preceding qualified bytes; 2,048 executable source/test/fixture
files match after the explicitly tracked test-only follow-up. Production
20,847 dependency entries/155 npm instances/Node 24.19.0 and 1,932 Browser test
dependency entries remain unchanged. Version, type and private-source-boundary
checks pass. [The portable record](../release/harness-canvas-reconciliation.json)
separates exact refs, fixtures, genuine native proofs and pending acceptance.

Full Python/Qt passes **878 with 45 identified skips / 923 cases** on source at
the application ref and on ordinary at fixture-only **7dfcb1bd83218927d5faac3edcb94f90091ba744**.
The initial source run's one dictation failure came from a fake executable
shebang splitting the interpreter path at spaces. Quoting the same interpreter
through a shell wrapper passes all 22 focused dictation cases, preserving the
existing child-recovery and saved-preference assertions. Five ordinary packaging
errors came from using deliberately excluded optional QuickJS extensions as
fixture inputs. A separate test-only upstream selector verifies every original
WASM/extension hash before constructing the same synthetic packages; all eight
focused source packaging cases and the full ordinary suite pass. Runtime
extensions, source/notices gates and distribution approval stay unchanged.
Failed staging and missing native-import-path invocations are retained as driver
errors. No test, assertion or deadline is dropped or relaxed.

An initial blocking-sync/edge-placement external-move probe was invalid and is
retained; the valid positive-coordinate proof observes the actual native event.
The animated baseline/diagnostic trace pass locally, with late canvas moves
repaired by the old animation tick. **2929c60 / Validate 38646604138** retains its
original animated post-move rectangle mismatch. Static drift establishes a
related missed-notification gap, not that failure's exact timing or sole cause.
At preceding **797f60a**, [Validate 38650213221](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/38650213221)
passes main Node 1,202/34 identified skips/zero failures, Browser 121/121,
Python/Qt 875/45 identified skips and both original X11 proofs, then refuses the
retained Office exact-source/rebuild packaging gate.
[SDK 38650213155](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/38650213155)
passes all three platforms and
[Windows Desktop 38650213045](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/38650213045)
passes. Separate Windows command-job settlement failures and Windows/macOS
missing reviewed Koffi platform license text remain open; this change qualifies
neither issue. New-head hosted, physical/installed and wider migration acceptance
remain pending. Current/prior review inventories and all four processes,
selection/drafts, 38 canonical changes and Qwen/speech/GPU settings are preserved.
This source qualification does not relabel or deploy published 0.2.12 below.

The exterior plasma/flare canvas now follows its owning Desktop window’s
workspace and stacking order. Previously it bypassed the window manager and
requested a global keep-above layer, so it could remain on another workspace
or cover a second agent raised over its owner. The managed transient canvas
keeps its exterior reach and input transparency. Butterfly effects share it.

This matched Debian 13 amd64 preview retains the 0.2.11 WebSocket security fix
and existing DSH, Model Picker 1.1.2, Adaptive Reasoning 0.2.3 and Resonant Voice
0.1.16 dependencies. Home/shared-surface feature previews are not included.

## Qualification and distribution

The isolated X11/KWin proof uses two native processes and checks workspace
switching, pin/unpin, effect reappearance, stacking in both directions, desktop
edges, minimize/restore, hide/show and compact transitions. It makes no model
calls and does not touch the user’s desktop. CI runs it alongside existing checks.
This does not qualify native Wayland or macOS window-manager behavior.

Published [0.2.12 complete preview](https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.12-complete-preview.1),
artifact source [`e027310`](https://github.com/ManoloRemiddi/augmentor-agent/commit/e02731023153e3b2e1440e50b8c14b64ad0a82e5),
merged through [PR #8](https://github.com/ManoloRemiddi/augmentor-agent/pull/8).
All three [release CI jobs](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/35997094189)
passed: source/native/artifact checks, installed-package lifecycle, and packaged Browser.
The first CI attempt identified a missing `wmctrl` test dependency; the final run includes it.

Additional qualification:

- Local native regression: 403 tests, one skipped; built shared prompt service included.
- Original canvas flags fail the managed-window regression; corrected source and
  packaged native code pass the two-process X11/KWin proof.
- The exact final complete archive installed as a fresh ordinary Debian user:
  real DSH/plugins, private settings, native Qt render, second-window/login entries,
  Browser registration and repeated-install preservation. The model endpoint was
  a fixture; optional speech and memory engines were deferred.
- Artifact review verified source/version identities, inventories, notices and
  absence of private state. All internal bundle checksums matched.
- Anonymous download of the public archive matched `SHA256SUMS`:
  `2ce620233e9312db86a0dccac9d07257bd9f700a0d19326b96460463379d1fa4`.
- Attached npm tarball installed and passed real plugin/WebSocket round trips
  with fixture DSH services/browser. Registry publication required interactive
  authentication, so npm `latest` remains 0.2.11; plugin implementation is unchanged.
  The Desktop fix is delivered by the complete bundle and native packages.

The website’s visible versions, download links and copied installation prompts
were updated together in website commit `fc427ce`. Pages deployment and all 15
website tests passed. Live browser verification confirmed the 0.2.12 archive URL
and installation prompt; clicking Copy succeeded and clipboard contents matched
the full visible prompt exactly.
Existing installations follow [matched upgrade guidance](RELEASE-0.2.11.md#existing-installations)
with version 0.2.12. Source publication does not reload open windows. Preserve
active tasks and unsent drafts; managed local previews must retain their extra
features when applying this scoped native correction.


## Installed local preview

The user’s Home/shared-surface preview remains product 0.2.11 for compatibility
with its running DSH integration. The original native activity module was
byte-compared against public main; only the flare correction was applied to a
separate copy of selected artifact `615b8837791ac5cbea85cfb9eb89b5c982e9b0ddc03a71f60cd9d2c9a932133c`.
That candidate passed the two-process workspace/stacking proof.

`augmentor-update` staged and activated `20260924-140435-fa4c42f4`, artifact
`3e204236d3ecb223e53dfbaff2421fb782a3892c090c7863d077096dcfe6c15f`.
Import, inventory and authenticated compatibility checks passed. Main/mobile
still run `20260924-125423-63307454`; secondary still runs
`20260924-125950-12694ac7`. All were online with voice available and
`updatePending: true`. No windows or backend services were restarted; preserve
active work and unsent drafts. Reopen through managed launchers to adopt the fix.
Selection rollback remains available. This local mixed preview is distinct from
the public 0.2.12 complete bundle.
