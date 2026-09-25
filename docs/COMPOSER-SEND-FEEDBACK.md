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

## Installed acceptance

Implementation `ba2fecf` is selected in managed release
`20260925-095859-da27e123`, artifact SHA-256
`638709fa8653d5a32dbda61009c4f4da0d6e9f2d87c6f7e6ea00affe4849dc1a`.
Stage/import/inventory and authenticated product-compatibility activation passed.
The secondary instance was idle, then closed through its guarded maintenance
endpoint and reopened with the canonical launcher. It reports the new root,
online and voice available, with `updatePending:false`. Its existing nonempty
draft was backed up privately and restored through accessibility; exact text and
saved conversation/model metadata were verified unchanged. No model prompt was
submitted to the user's conversation during this check.

The owner's Fn + Option + Space shortcut targets this secondary instance. Its
previous `20260924-125950-12694ac7` build includes the initial host-status baseline
and the controller handler that triggered draft restoration. Main and mobile
still run `20260924-125423-63307454`, which lacks that handler/initial baseline.
Two normal-send/one-bubble checks pass against the primary's actual artifact.
Those processes were left running; they adopt the selected correction on their
next normal restart. The secondary is the only conversation window restarted.

The three tested Browser UI files were installed into the existing compatible
0.2.11 extension, with prior files backed up privately. No service-worker or
backend restart was required. An already open sidebar retains its old modules;
close/reopen the sidebar (or reload the extension) to adopt the fix. The connected
browser tool only exposed Codex's in-app browser, so live adoption in the user's
Chromium profile was not verified. Source and installed-copy DOM tests passed.
This is a local update, not a new public binary release.
