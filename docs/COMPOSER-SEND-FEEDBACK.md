<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Immediate composer feedback — September 25, 2026

Desktop and Browser move a submitted draft into a temporary “You · Sending…”
message and clear the composer before waiting for session preparation or prompt
acknowledgment. The durable user/command event replaces that preview once. A newer
draft is never erased by an older acknowledgment. Failure preserves the original
text without automatically resending an action of unknown outcome.

## Regression and correction

The installed shared-surface Desktop preview subscribes to DSH host status when
opening its event connection. Its initial idle baseline can arrive while a local
send is preparing. Previously that baseline released the controller's busy state;
the window treated any idle notification as a failed send, removed the immediate
preview and restored the submitted draft. An unrelated history error had the same
restoration effect. Consequently the message only appeared again when the durable
backend event arrived, while the restored composer text remained.

The controller keeps its local turn reservation during preparation. Draft recovery
now uses a submission-specific failure/cancellation signal; general idle/error
notifications do not own it. This also prevents a duplicate send during the idle
baseline race. The source controller now handles the host-status notifications
already present in the installed shared-surface preview.

Browser had a separate acknowledgment-dependent composer: it cleared only after
awaiting the prompt RPC and could erase a newer draft at that point. Its sender
now clears and previews first, guards repeated submissions during preparation,
and reconciles real user and command events. Edit-branch preparation follows the
same path. A durable event wins over a lost acknowledgment. Connection failures
preserve the draft and ask the user to check chat before retrying.

## Verification and deployment scope

Regression tests cover the native idle baseline, unrelated errors, explicit
rejection, cancellation before sending, and delayed durable delivery. The idle
restoration test fails against the old installed artifact. Browser tests exercise
immediate transfer, delayed/early acknowledgments, commands, repeated submission,
newer drafts, rejected/unknown submissions, and edit preparation.

Source and installed artifacts are distinct. The compatible installed candidate
starts from selected release `20260924-205229-78c3c113` (artifact SHA-256
`6466feffb8661e73e9b8dba84565c18a420365e62f9930f9d61159fdd2ac3090`) and changes
only the native send/status handlers. Existing Home, voice, shared appearance,
flare, and model settings are preserved. Browser changes are applied separately
to a copy of the installed 0.2.11 extension, retaining its surface and prompt
animation. Follow [desktop deployment](DESKTOP-DEPLOYMENTS.md) for selected versus
running identity; extension reload is a separate adoption step.

These are deterministic UI/controller/DOM checks, not model-speed measurements or
claims of microphone, physical-keyboard, or public release qualification.

Validation: full native suite **415 tests, one skipped**; all **30 Browser unit
tests** passed. The mixed installed candidate passed **68 focused native tests**
and its Browser files passed **19 sender/renderer tests**. Tests used Qt 6.8.2.1
in an isolated test environment; the installed Python interpreter is unchanged.
