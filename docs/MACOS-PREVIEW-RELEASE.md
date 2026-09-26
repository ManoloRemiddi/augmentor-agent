<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# macOS 0.2.12 preview release

The owner explicitly approved direct distribution without Apple Developer ID or
notarization after Apple enrollment failed. This supersedes the Apple prerequisite
for **this preview only** in the older release audit. Apple signing remains the
intended stable distribution path. Never disable Gatekeeper globally, remove
quarantine as an installation instruction, or label an ad-hoc build notarized.

Target: Apple silicon, macOS 14+. Release tag: `v0.2.12-macos-preview.1`.
The [versioned release](https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.12-macos-preview.1)
was published on September 26, 2026. See the bundled [customer guide](MACOS-PREVIEW.html)
and [website installation guide](https://augmentoragent.com/macos.html).
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

## Final artifact qualification

The final binary source is `ea128d6f75bca49aae6cc80bf11251a1218fbf02`, merged
through [PR #10](https://github.com/ManoloRemiddi/augmentor-agent/pull/10).
The DMG is `augmentor-desktop-0.2.12-macos-arm64-preview.dmg`, 508,240,784 bytes,
SHA-256 `058a0920e4da753593372a7d499d980b7672590e8499cf929371460b459db8e4`.
The application inventory SHA-256 is
`360bec0babc8fe6b18ec29fb8e51874407ccd6aa6252b8b80397e6a3d1a4377b`.

Both final-source workflows passed: [macOS 14/26 build and managed setup](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36244110988)
and [Linux, Home, Browser and installed-package lifecycle](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36244111028).
On the 16 GB ARM64 Mac Mini running macOS 26.5.1, the final bundle also passed
fresh managed setup, all three extra plugins active, actual native Send/Enter
submissions across reopening, conversation restoration and Chrome 153 chat through
the compiled native host. These checks used a deterministic local provider and
an isolated private profile. Native sharp/libvips PNG creation/readback passed.

The final DMG passed mount/copy into a Unicode path, actual LaunchServices launch,
Qt/DSH approval allow/reject/cancel, question and conversation checks, and an
intact app signature after use. The Qt library-replacement proof below used the
preceding candidate with identical Qt inputs and staging policy. Published
`BUILD-AND-TESTS.json` preserves that distinction. Open Anyway consent, manual
browser folder selection, physical speech and complete privacy-permission flows
are not claimed as tested.

Temporary test applications, their application registrations and completed
fixture login jobs were removed after verifying their processes had stopped.
The owner's one installed application remained unchanged and online/model-ready;
its private model profile is not part of the release.

## Publication verification

The release was published at 13:24 UTC on September 26, 2026 as a prerelease,
without replacing the existing Linux release. All eight release asset names,
sizes and server-side SHA-256 digests matched the prepared publication files.
An anonymous download of the complete 508,240,784-byte DMG and `SHA256SUMS`
finished at 13:28 UTC; the downloaded DMG matched the final checksum above.
Public Mac and Linux download destinations returned HTTP 200.

Website commit `bd205bb` deployed successfully through
[GitHub Pages](https://github.com/ManoloRemiddi/augmentoragent.com/actions/runs/36245144362);
its [website checks](https://github.com/ManoloRemiddi/augmentoragent.com/actions/runs/36245144697)
also passed. The live homepage and Mac guide showed the correct versioned DMG,
Apple-silicon/macOS requirements, Open Anyway instructions and preview limits.
Guide navigation and its rendered layout were checked in the browser. The existing
Linux prompt retained its matching URLs; its live copy button reported success.
Clipboard-content readback is not claimed for this verification.
Subsequent documentation-only commits record this outcome; they do not change
the published binary or the tested website interface.

## Earlier candidate evidence

The `6c7735e` candidate passed macOS 14 and 26 CI build/managed setup matrices
([run 36243551473](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36243551473)).
On the 16 GB ARM64 Mac, 89 Mac unit cases passed. Real native processes completed
Send-button and Enter requests across a reopen, retaining the same conversation;
a fresh Chrome 153 profile loaded the exact extension ID
`dgfpmlnbofacjafljfohgmfacobgfjbh` and completed managed DSH chat. All used an isolated
deterministic model, not private owner configuration. The first combined fixture
incorrectly reused the identical prompt while asserting it appeared once; unique
reopen markers corrected the test without changing product chat behavior.

Its DMG passed mount/copy/relocation, actual LaunchServices launch, Qt/DSH approval
and conversation tests, plus intact signatures after use. Native sharp/libvips
completed PNG creation/readback. Replacing QtCore from its original wheel, modifying
framework metadata, renewing an ad-hoc signature and launching Qt Widgets also
passed in a disposable copy. The release adds ripgrep 15.0.0 / PCRE2 10.45 and
locked Rust notices, plus accurate Mac update-panel text, before final packaging.

Gatekeeper correctly rejects this ad-hoc build by default. A user must approve
Open Anyway; the actual consent dialog and browser folder chooser are not claimed
as automated acceptance. Full production permission and updater gates remain.
The earlier shared Home CI had a timing-sensitive 100 ms deadline fixture fail before
its expected device dispatch; this is separate from the successful Mac and
Browser checks. The final-source full workflow passed as recorded above; no Home
code was changed and the earlier timing sensitivity is not claimed resolved.
