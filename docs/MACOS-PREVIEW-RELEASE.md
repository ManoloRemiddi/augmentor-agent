<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# macOS 0.2.12 preview release

The owner explicitly approved direct distribution without Apple Developer ID or
notarization after Apple enrollment failed. This supersedes the Apple prerequisite
for **this preview only** in the older release audit. Apple signing remains the
intended stable distribution path. Never disable Gatekeeper globally, remove
quarantine as an installation instruction, or label an ad-hoc build notarized.

Target: Apple silicon, macOS 14+. Release tag: `v0.2.12-macos-preview.1`.
Publication is pending final artifact checks. See the bundled
[customer guide](MACOS-PREVIEW.html); the deployed website has a separate Mac guide.
The existing Debian release is unchanged.

## Included and deliberately limited

The app bundles Python, Node, locked DSH, Model Picker 1.1.2, Adaptive Reasoning
0.2.3 and Resonant Voice 0.1.16. Exact public plugin archives are retained in
`release/dsh/plugins`; all dependencies are prepared before distribution. The
same package lock and staging inputs serve Linux and Mac. No private profile,
provider key, transcript, model weights or speech model is a release input.

Fresh Mac setup accepts a user-provided OpenAI-compatible chat endpoint and model.
It starts a private managed DSH login job. Existing DSH remains an explicit option.
Credentials are in owner-only local files, not Keychain. The browser setup menu
prepares a content-addressed extension outside the sealed app and registers the
matching native host. Users approve Load unpacked in Chrome/Chromium. The prepared
folder is immutable to repeat setup; an edited folder is preserved and rejected.

Automatic updates, OAuth onboarding, Intel Macs, complete desktop-control consent,
physical microphone/speech-engine qualification and local memory installation are
outside this preview's qualified scope. Do not advertise these as completed.
A future update must drain the managed DSH job and shared leases before replacing
the app; the earlier installer only pauses the shortcut and is not a public update
flow for this new managed runtime. Preserve data and do not overwrite a busy app.

## Third-party distribution material

`release/macos-sources.json` pins original archive URLs, versions and SHA-256s.
`prepare-macos-sources.py` verifies every input before creating source assets and
collecting notices. Publish the Qt and PySide source archives and the native
source archive alongside the DMG, with final checksums. The native archive includes
sharp-libvips 1.3.3's build recipe, each native dependency, the exact applied
patches, glib's gvdb subproject, and all 350 registry crates in librsvg's lock,
including unused build/test dependencies. It does not execute any upstream recipe.
Cargo archives are checked against the upstream lock checksums.

The macOS Widgets payload retains QtCore, QtGui, QtWidgets, QtNetwork, QtDBus,
QtSvg and QtTest only. It removes unused QML/Quick, Designer and other frameworks,
including GPL-only optional modules. Every retained Mach-O reference is checked
for missing Qt frameworks. The existing Qt base/SVG/image-format and PySide
attribution collections accompany the bundle, as do Python/Node/npm notices.
The complete Python build's dependency notices are collected separately from its
trimmed interpreter archive. npm text collection is distinct from native source
and embedded dependency review; inventory flags alone are not legal conclusions.

Qt, PySide, Shiboken and libvips are dynamically loaded. Their applicable LGPL
terms, including modification and debugging rights, take precedence over the
Augmentor resale restriction for those libraries. No additional library hash
check or Apple library-validation restriction prevents replacement in this
ad-hoc preview. See [library replacement](MACOS-LIBRARY-REPLACEMENT.md).

## Candidate workflow

Use a fresh build environment with `release/macos-requirements.txt`. Prepare the
sources outside the checkout, then build on ARM64 macOS from the exact source
commit using `package-macos.py --preview --source-commit COMMIT --source-notices
NOTICES --dmg --out NEW_DIRECTORY`. The source-notice manifest must match every
copied file. All generated apps stay under a private `.noindex` cache until an
explicit installation. The app includes a readable Start here guide on its DMG.

Run managed setup, actual Qt composer, browser native-host and post-use signature
checks on the candidate. Keep deterministic model and live provider evidence
separate. Record a failed Gatekeeper assessment as expected for an unnotarized
build; it is not evidence of a successful user Open Anyway interaction. The
builder deliberately leaves `publicReleaseReady: false`; the operator's release
record must state the tests and preview limitations before publication.
