<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor 0.2.12 desktop flare correction

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
were updated together in website commit `fc427ce`.
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
