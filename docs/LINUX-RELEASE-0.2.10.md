<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor 0.2.10 — complete Linux preview

This release includes action-aware recovery in the normal Desktop and Browser
installation. The same generic policy applies to research, writing, coding and
computer work; there are no benchmark-specific rules or expected answers.

## Download and install

Use the **complete Linux preview** download at [augmentoragent.com](https://augmentoragent.com/#installation).
Extract the archive and run `./install.sh` as your normal user. The installer
verifies the supplied checksums and guides model configuration. It asks separately
about optional voice and memory engines. Model credentials, histories and model
weights are never included. Internet and administrator access for Debian packages
are needed. See [complete installation](COMPLETE-INSTALL.md) for exact steps.

The supported preview is Debian 13 x86-64; desktop-control qualification is scoped
to KDE Plasma Wayland. Chromium requires the explicit **Load unpacked** extension
step printed by the installer. macOS, Windows and other Linux desktops are not
newly qualified by this release.

## Included components

- Matching Desktop, Browser, companion, shared prompts and dual-memory adapters 0.2.10.
- Pinned DSH 0.1.5-rc.1 and the bundled Augmentor execution adapter, enabled once
  in each Augmentor preset. Do not install a second copy from an older collection.
- Model Picker Augmented 1.1.2, Adaptive Reasoning 0.2.3 and Resonant Voice 0.1.16.
- Exact source snapshots, component manifest, licenses and SHA-256 checksums.

Adaptive Reasoning starts with neutral routes. Users choose their own model;
no developer-specific GPU, provider or reasoning settings are distributed.
Voice and local Hindsight provisioning remain optional, with their own dependencies
and terms. Memory extraction starts paused and is controlled by the user.

## Recovery behavior and limits

Empty or truncated terminal responses get bounded continuation in the same task.
Stop wins. Questions and voice handoffs are respected. During recovery, exact
repeated non-read actions are denied; uncertain effects and running jobs block new
changes while inspection remains available. DSH's shell exit/signal/timeout and
background job outcomes are used instead of treating every returned result as
success. Existing jobs can be collected by identity without launching duplicates.

This is not a guarantee of model correctness or exactly-once external execution.
Unknown tool contracts, differently expressed equivalent actions and cross-session
transaction reconciliation remain limitations. Read the [full contract](BOUNDED-EXECUTION-RECOVERY.md#action-aware-recovery--0210-preview).

## Existing installations

The guided archive is for a fresh setup and refuses to overwrite an existing
installation. Do not delete profiles to bypass this. Package-managed users should
follow [lifecycle and retained-data recovery](LIFECYCLE.md), then update the owned
DSH integration through Settings. Custom presets require a preserved, reviewed
merge. Close active tasks before updating/restarting their host. Matching product,
Browser and speech integration must be retained; a Debian package update alone
does not migrate an edited DSH preset.

Selected desktop builds and running windows can differ until reopening. See
[desktop deployments](DESKTOP-DEPLOYMENTS.md). Private development installations
are not silently changed by publishing this download.

## Qualification

The release includes real pinned DSH lifecycle tests driven by deterministic
provider responses, outcome-contract tests, native UI regressions and Browser
regressions. These are separate from real-model competence, physical microphone
quality and desktop hardware acceptance. Artifact-specific fresh-install and
lifecycle evidence, source commit and archive hash accompany the public release.
