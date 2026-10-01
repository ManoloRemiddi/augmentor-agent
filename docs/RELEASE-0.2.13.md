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
for recovery semantics and limits. Complete local merged-source checks pass:
TypeScript check/build, 207 Node tests and 44 Browser tests. Final package, clean
installation and Linux/macOS CI qualification are recorded below after completion.

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

## Publication evidence

Release URLs, clean source ref, final checksums and website verification are added
only after the corresponding candidate checks and public downloads succeed.
