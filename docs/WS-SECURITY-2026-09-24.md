<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# WebSocket dependency security correction — 24 September 2026

## Repository and scope

The live public repository is [ManoloRemiddi/augmentor-agent](https://github.com/ManoloRemiddi/augmentor-agent),
default branch `main`, not archived `augmentor-dsh-extension-plugin` or private
`augmentor-agent-history`. GitHub and the clean local checkout both identified
`68f58135ead2093dcf5162c5c15ad46e16e3168d` before this correction. That revision
already includes the September 23 repository consolidation.

At inspection, npm's `dsh-augmentor` latest was `0.1.32`, pinning `ws 8.21.0`.
Current product source `0.2.10` also pinned that dependency in the root runtime,
Browser companion, Browser plugin and mobile remote. The separately locked DSH
qualification/installer tree already resolved `ws 8.21.3` and is unchanged.

[CVE-2026-62389 / GHSA-73jw-fp74-p77x](https://github.com/advisories/GHSA-73jw-fp74-p77x)
describes memory exhaustion through incomplete fragmented WebSocket messages.
The [upstream 8.21.1 fix](https://github.com/websockets/ws/releases/tag/8.21.1)
counts empty fragments and lowers the default buffering/fragment limits.
This correction pins **8.21.3**. A vulnerable receiver is not evidence of malware
or credential theft. Application authentication and loopback restrictions still
matter to reachability; the regression below is a controlled loopback receiver
test, not a demonstrated unauthenticated attack on an installed Augmentor.

The advisory was unreviewed with no package/version mapping when inspected.
`npm audit` returned zero even on the affected tree. Audit output alone cannot
qualify this correction.

## Implementation and dependency preparation

- Pin `ws 8.21.3` in all four direct manifests and regenerate their npm/pnpm locks.
- Reconcile the Browser pnpm lock's stale `fflate 0.8.2` with the existing
  manifest/npm lock's `0.8.3` (the separate ZIP64 issue,
  [CVE-2026-45820](https://github.com/advisories/GHSA-px8p-9vwx-vf98)).
- Generate the mobile third-party notice's ws version from its installed manifest.
- Prepare Pi with `scripts/prepare-ws.mjs`: the published Pi 0.85.1 shrinkwrap
  restores a nested `ws 8.21.0` during `npm ci`, even when an npm override or
  a changed outer lock entry requests a patched version. Retain the truthful
  upstream entry in the lock, then remove that obsolete installed copy so Pi's
  unbundled SDK resolves the locked root `ws 8.21.3`.
- Remove Pi's unused `dist/bundle` standalone CLI/RPC executables and their
  local CLI symlink; those generated bundles embed another frozen vulnerable
  receiver. Augmentor uses the unbundled SDK and its own host, not those binaries.
  The upstream standalone `pi` executable is therefore not supplied by this
  Augmentor dependency tree. The supported Pi agent/session lifecycle is retained.

Preparation validates the root ws and Pi versions, rejects an unexpected nested
ws version, and is repeatable. It runs during normal root npm installation,
before `npm run build`, `npm test`, and `npm start`, in production staging, and
before activating the separate source-install staging directory. Dependency
scripts remain disabled in the documented `npm ci --ignore-scripts` workflow;
the build hook explicitly runs only this repository-owned preparation step.

For direct SDK use immediately after an install with scripts disabled, first run:

```sh
node scripts/prepare-ws.mjs
```

Do not treat a bare `npm ci --ignore-scripts` tree as a prepared release. Production
license inventories are generated after preparation and the removed upstream
copies are recorded in `distribution-exclusions.json`. An upstream Pi upgrade
requires reviewing this temporary workaround and rerunning the tests.

## Validation

The correction is prepared on `fix/ws-memory-exhaustion` from the base above.
Node is 24.19.0, npm 11.17.0, and pnpm 11.23.0. Local checks:

- Locked installs for root, Browser, Browser tests, mobile, plugin and DSH;
  TypeScript check/build; generated-version check; plugin and mobile builds.
- 180 root Node tests passed with the locked real DSH fixture, zero skips.
  These include four preparation/failure-path cases and sixteen WebSocket
  cases across the independently installed component copies.
- 21 Browser DOM/bridge tests passed.
- 412 native Python/Qt tests passed. The host lacked `PySide6.QtTest`; Debian's
  matching `python3-pyside6.qttest 6.8.2.1-4` and QtTest library were extracted
  into a temporary test directory. No system package or installed app changed.
- The security test accepts normal fragmented messages, then sends at most
  about 115 KiB of incomplete frames. Patched clients and servers reject both
  empty and nonempty fragments with `WS_ERR_TOO_MANY_BUFFERED_PARTS`.
  All four cases fail against an isolated `ws 8.21.0` control as expected.
- Fresh production staging and its license inventory succeeded; the same four
  receiver tests passed against the staged dependency tree. Browser ZIP
  generation and inventory verification succeeded.

The CI workflow installs the separate component trees, runs these tests and
repeats the receiver regression against the production tree used for packaging.
The pull request records native test results and the exact CI-tested revision.
No real model, microphone, installed desktop or user conversation was exercised
by this security-specific validation.

## Release boundary and remaining work

This is a source fix and review candidate. Product/extension/plugin versions
remain in lockstep at `0.2.10`; this work does not relabel current code as the old
plugin's `0.1.33`. Do not overwrite historical release artifacts or publish a
version without a separate release decision and compatibility qualification.

No npm publication, release promotion, installed desktop activation or change
to npm ownership/2FA or organisation permissions is performed here. Existing
`dsh-augmentor 0.1.32` installations and historical downloadable packages retain
their original dependencies until explicitly upgraded. A future release must
choose the maintained-product upgrade or an explicitly scoped legacy backport,
test that exact artifact, and communicate the upgrade to existing users.
