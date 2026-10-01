<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor 0.2.13: general browser reliability

This matched Desktop/Browser preview preserves fresh page observations before
first model use, exposes bounded continuation for long pages, and lets the agent
recover omitted evidence from its own saved tool results. Explicit reads of other
tabs no longer redirect subsequent actions. These changes apply across websites;
there is no shopping-specific agent, Amazon rule or product-comparison workflow.
The release includes the context/evidence and general execution-recovery adapters
on which the browser repair depends, together with existing main-branch features.

See [browser observation repair](BROWSER-OBSERVATION-REPAIR.md) for implementation,
admission bounds, binary protection, isolated browser tests and real local-model
qualification using historical page evidence. See [task reliability](TASK-RELIABILITY.md)
for recovery semantics and limits. Complete merged-source checks pass:
TypeScript check/build, 207 Node tests and 44 Browser tests. Final package and
Linux/macOS qualification are recorded below.
The Mac packager preserves the complete verified source-notice inventory, including
upstream test-directory README notices excluded by its application source copier.

## Distribution

Linux delivery is a Debian 13 amd64 complete preview, containing matching Desktop,
Browser, DSH and required plugin artifacts. Mac delivery is an Apple-silicon macOS
14+ preview with bundled runtime and matching Browser; it retains the previously
owner-approved ad-hoc signature and explicit Open Anyway first-launch process.
Neither model credentials nor model weights nor private conversations are included.
Speech, memory and desktop permissions retain their documented setup requirements.
This repair does not certify every model or website, and fixture acceptance is not
a claim of physical microphone, permission-dialog or live Amazon acceptance.

## Existing installations

Finish work and preserve drafts before replacing components. Follow the matched
Linux [upgrade guidance](RELEASE-0.2.11.md#existing-installations), selecting 0.2.13
artifacts throughout. For Mac use the [preview guide](https://augmentoragent.com/macos.html)
and its update limitations; do not drag a new application over a working runtime.
Reload the installed matching Chromium extension after updating its files.
Saved conversations and configured models do not need a new shopping-specific chat.
Managed local mixed previews must preserve their compatible SDK/runtime composition;
public release packaging is separate from the owner's installed 0.2.11 selection.

## Qualified package source

Both matched candidates use clean source
`0eb2ec112afa52b886b63606f80967198a7feb0c`, merged into canonical `main` through
[PR #26](https://github.com/ManoloRemiddi/augmentor-agent/pull/26), including the
[PR #21](https://github.com/ManoloRemiddi/augmentor-agent/pull/21) reliability dependency.
Release tags retain this exact binary source; later documentation commits do not
change the packaged source or the versioned downloads.

[Linux/Home/Browser CI](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36884501804)
passes runtime, Debian packaging, installed lifecycle and Chromium checks.
[Mac CI](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36884501664)
passes on macOS 14 and 26. The final complete Debian archive also passes a fresh
ordinary-user installation in an isolated pinned Debian 13 container, including
runtime/plugins, private configuration, Qt rendering, second window, login,
browser registration and repeated-install protection.

On the physical Apple-silicon Mac, the exact final application passes native
Send and Enter after reopening, conversation restoration, managed DSH restart,
required plugins and fresh Comet native-host chat. The final DMG passes mount,
copy, LaunchServices launch from a Unicode path, native runtime/DSH integration
and strict signature verification after use. Model responses in these interface
checks use deterministic fixtures. All 1,568 source-notice entries are verified.
The existing personal Mac application was not replaced. Physical Open Anyway,
manual extension approval, microphone and privacy-consent dialogs remain outside
this qualification; the package retains the existing ad-hoc preview limits.

## Publication evidence

Both preview releases are public and retain the qualified source ref above:

- [Debian 13 amd64 complete preview](https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.13-complete-preview.1):
  `augmentor-0.2.13-complete-preview.1.tar.gz`, 72,665,721 bytes, SHA-256
  `6c327d99b04796f2901850364670aa61015b17f739582c64126421858b56b65d`.
- [Apple-silicon Mac preview](https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.13-macos-preview.1):
  `augmentor-desktop-0.2.13-macos-arm64-preview.dmg`, 522,788,721 bytes, SHA-256
  `ad7545be4759281ebffc40c27dd109fc691f64dd924e2a799e911e7fd598aac4`.

Every uploaded asset matches its local size and SHA-256. Full anonymous Linux
and Mac downloads independently match both the published SHA256SUMS and the tested
local candidates. Linux carries matching component archives, complete bundle
metadata and build/review evidence. Mac carries the exact Augmentor source archive,
verified source notices and sanitized acceptance evidence; dependency-source URLs
retain their immutable earlier archives and resolve publicly. Model weights,
credentials, private proof logs and personal settings were excluded.

Website commit `cce3376e86e2f7c594259eef7da4bd29a746ba6d` is deployed through
[successful GitHub Pages run](https://github.com/ManoloRemiddi/augmentoragent.com/actions/runs/36921396021).
All 15 website tests pass. The public homepage, Linux guide, documentation and Mac
guide match the committed HTML byte for byte. Both download buttons and both
checksum destinations return HTTP 200. The live installation textarea contains
the exact 0.2.13 archive and checksum URLs. The in-app Browser copy button reports
successful copying; its session clipboard readback is empty, so clipboard contents
were not independently qualified. The source handler copies the textarea value,
and the existing source test verifies that binding. Existing preview labels and
manual setup limits remain visible at [downloads](https://augmentoragent.com/#installation).
