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
ownership. A deterministic model fixture is not live provider evidence. Candidate
and deployment evidence will follow qualification. The public
`v0.2.12-macos-preview.1` DMG is unchanged by this source correction.
