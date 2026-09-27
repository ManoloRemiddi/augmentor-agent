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

Implementation is under qualification on `fix/macos-recovery-parity`, PR #16.
Source tests and the installed artifact are separate: the 32 GB Mac still runs
`7ff6712` until a clean candidate passes native proofs and safe activation.
The public website download and selected Linux installation are unchanged.

The new proof exercises actual pointer drags through 150%, 75%, 130% and back to
110%, asserting visible window, font and button dimensions, saved settings and an
unsent draft. Tests cover repeated round trips, rich text, undo, selected input,
newly opened controls, skins, restart normalization and non-default startup DPI.
The opt-in native UI test interface can operate App size during a real model reply;
normal app launches do not expose that test control.
