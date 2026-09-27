<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Live app zoom — September 27, 2026

The owner accepts the flare correction but reports that moving App size changes
nothing visually. The previous implementation saved startup DPI only. This change
makes the same shared 75–150% control update the current window immediately.

Qt widgets, original layout/style metrics and custom paint geometry resize at
native resolution. The process, harness controller and conversation stay alive.
Transcript HTML reflows with its selection and reading anchor retained; drafts and
undo remain intact. Existing startup DPI remains the baseline, and saved dimensions
are normalized to prevent doubled enlargement after a restart. The Appearance
window remains anchored during a drag, with scrollable controls. Skins do not own
this personal preference. Linux and macOS share the implementation.

The registry uses public Qt APIs and weak object references. One application event
filter handles controls parented after construction; dialogs opened after zoom
inherit the owning window's metrics. Explicit design sizes use `scaled`, measured
viewport geometry does not. Editable document margins are deliberately not changed:
Qt records those as undo operations, which would disrupt the user's next Undo.
The accepted flare renderer and native shadow correction are unchanged.

## Qualification and deployment

The clean artifact from **`b8dac9d36ab3e2d91c2d532e05638e89fa7910e5`** is installed
at `/Applications/Augmentor Agent Desktop.app` on the 32 GB Mac, replacing `7ff6712`.
The user's saved **120%** was preserved; the primary process reports 1.2 DPR and
metric factor 1, online and model-ready with no connection/restoration error.
The branch is `fix/macos-recovery-parity`, [PR #16](https://github.com/ManoloRemiddi/augmentor-agent/pull/16).
The public website download and selected Linux installation are unchanged.

- ZIP SHA-256: `9445e86466fe917abde886ac829ba5199cd58fa385ef23fd0debf5a61d16b02e`,
  339,767,464 bytes, `augmentor-desktop-0.2.12-macos-arm64-preview.zip`.
- Application inventory: 590 entries, SHA-256
  `f125ef11e11da5a579dd60cce8495ee91c50d98f538f234e4db55f03d8c8461f`.
- Source: 528 native tests passed (three environment skips), 182 Node tests,
  TypeScript check/build. Linux X11 and packaged Cocoa pointer-drag proofs pass.
- At startup 110%, the same Cocoa process changes logical width/font/button from
  424/13/24 to 578/18/33 at 150%, then 289/9/16 at 75%, 501/15/28 at 130%, and back
  to 424/13/24 at 110%. Percentage persistence, draft and hide/show checks pass.
- Packaged Cocoa: all eight resize handles and compact/expanded restoration pass.
  Metal transparency still has no native shadow and zero alpha in all four outer
  eight-pixel strips, with an actual distant flare reaching alpha 52.
- Installed native live test restored the dedicated qualification conversation,
  submitted through its actual Send button, and changed size four times while
  the real provider reply was running. The same PID/session completed the reply.
  A separate unsent draft survived three further changes. The test window closed
  idle; normal primary launches keep UI test control disabled.
- Safe activation retained DSH settings, saved connection and all five session
  metadata records. Both owned services resumed. Fn+Space reports protocol 2,
  active, no error. Physical keypress testing is not claimed.
- Strict signature and application inventory checks pass. Temporary build,
  candidate and backup bundles are removed after retaining a rollback ZIP in a
  non-indexed cache. The missing installer staging registration is explicitly
  unregistered. Final read-back finds exactly one Spotlight app, one LaunchServices
  application registration and one Dock tile.

Mac 14/26 and full repository CI were dispatched for the exact source revision;
the final workflow results are recorded below when available.

The new proof exercises actual pointer drags through 150%, 75%, 130% and back to
110%, asserting visible window, font and button dimensions, saved settings and an
unsent draft. Tests cover repeated round trips, rich text, undo, selected input,
newly opened controls, skins, restart normalization and non-default startup DPI.
The opt-in native UI test interface can operate App size during a real model reply;
normal app launches do not expose that test control.
