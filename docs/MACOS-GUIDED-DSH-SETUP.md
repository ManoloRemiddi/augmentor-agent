<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Guided DSH installation on Mac

The 32 GB Mac had the public 0.2.12 preview from `ea128d6`, including DSH,
Node and Python, but no saved DSH connection. The running desktop was offline
with “Use Connect DSH to save the matching local connection before automatic
startup.” No DSH managed profile existed. This was a first-run UX failure, not
an absent runtime binary. The older form said Connect and did not explain DSH
installation. Dismissing it left the ordinary recovery loop reporting an error.

## Behavior

For a Mac without a saved connection or conversation, the native window now
opens **Install DSH** before starting connection monitoring. The same action
remains in Settings if the user chooses Later. The form explains that the
runtime is included and installed automatically, with no Terminal or separate
download. The only required input is the user's model connection; DSH does not
include model weights or a provider account. Context size is an advanced field.

The existing managed installer remains the only installation engine. Its fixed
phase IDs stream through private subprocess stdout to the UI: check model,
prepare runtime, add Augmentor capabilities, start login service, verify ready.
Credentials remain on stdin and in private configuration, never process arguments
or progress text. Duplicate submissions and dismissal during provisioning are
blocked. Failure keeps entered settings and offers Retry setup. An incomplete
acknowledgment does not claim success or automatically replay installation.
The existing ownership journal checks or finishes the same installation on retry.

A saved external or managed connection retains normal recovery and configuration.
An incomplete app copy receives a specific diagnosis and download action rather
than an external DSH form. The install helper also refuses incomplete candidate
payloads before replacement, while permitting an old incomplete destination to
be replaced. Its manifest includes the CLI link used by provisioning.

## Verification and deployment

The 32 GB Apple-silicon Mac (macOS 26.6.2) passed all 109 Mac tests and 27 native
window tests. The installation form was rendered and visually inspected using
the bundled Qt runtime. These tests exercise the actual Qt widgets, missing payloads, preserved external
connections, progress, failure/retry, private credentials and managed-service
ownership. A deterministic model fixture is not live provider evidence.

A separate candidate was staged from the sealed `ea128d6` public preview with
only the ten implementation/document files recorded in its `release.json`
changed. Its application inventory was regenerated and the candidate resealed
with an ad-hoc integrity signature. Application code is from `2fb9a5b`; later
commit `3e88750` changes test cleanup only. This is a scoped candidate based on
the published binary, not a claim of a new clean-build public release.

On that candidate, the real managed-service proof passed in 11.879 seconds,
including all three required plugins, a completed chat, repeated setup without
another installation, service restart and restored conversation. Its temporary
LaunchAgent and prompt/memory services were removed. The real native Window
in an isolated Qt profile opened Install DSH automatically, did not start
recovery, and allowed Later followed by reopening setup. These checks did not
use the owner's credentials, conversation or model service.

The first Mac CI attempt passed its assertions but crashed during interpreter
shutdown with retained test widgets. The test-only follow-up explicitly drains
deferred Qt destruction and uses the canonical module import. This follows
[Qt's event-loop lifetime contract](https://doc.qt.io/qt-6.8/qobject.html#deleteLater).
The [macOS 14/26 workflow at `3e88750`](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36247499831)
then passed completely, including clean packaging, bundled DSH/Qt contracts,
managed chat/restart/history and post-use signature checks. Run bundled Python
diagnostics with `-B` and `PYTHONDONTWRITEBYTECODE=1` (including subprocesses) so
test imports cannot add bytecode caches to sealed apps.
The original app's integrity was restored and checked after archiving such
test-generated caches; no source file or user data was removed.

The broader Linux workflow initially stopped in an unchanged Chromium fixture:
its temporary profile cleanup raised `ENOTEMPTY`. The Mac workflow is independent
and passed. The Linux workflow was retried; that intermittent browser cleanup
failure is not claimed fixed by the Mac setup changes.

Installation is staged pending the owner closing the desktop. The earlier
desktop does not include unsent text in its maintenance status and does not
persist that draft when closed, so its idle flag alone is not sufficient to
approve an automated close. The public `v0.2.12-macos-preview.1` DMG is unchanged.
