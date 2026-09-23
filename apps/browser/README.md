<!-- Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
     Copyright © 2026 Manolo Remiddi
     SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
     License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root. -->

# Augmentor Agent Browser

The maintained Chromium MV3 surface supports DSH and Pi through a shared native
messaging entrypoint. It shares prompt records and memory services with the
native desktop, while keeping browser sessions and tool authority separate.
[Feature matrix](../../docs/FEATURE-MATRIX.md) records actual harness support;
[distribution](../../docs/BROWSER-DISTRIBUTION.md) is the current install guide.

| Component | Responsibility |
| --- | --- |
| `extension/` | Side panel, settings, service worker, page executor, overlays, microphone/playback bindings |
| `native-host.mjs` | Product handshake, harness selection and shared-service access |
| `pi-bridge.mjs` | Pi host bridge and browser lifecycle |
| `pipe.mjs`, `plugin/`, `wire.mjs` | DSH browser transport/plugin and wire primitives |
| `test/` | Current DOM and bridge regressions; imported old suites may require their original fixtures |

Browser audio controls are source-integrated with [Resonant Voice](https://github.com/ManoloRemiddi/resonant-voice).
Native hands-free support does not imply browser hands-free support. Installing
a speech tarball or activating the shared memory adapter does not update an
already loaded extension; build/install/reload the matching reviewed artifact.

Read [browser settings](../../docs/BROWSER-SETTINGS.md),
[recovery](../../docs/BROWSER-RECOVERY-REVIEW.md),
[automatic memory](../../docs/DUAL-MEMORY.md) and
[voice controls](../../docs/VOICE-SINGLE-BUTTON.md).
Tests and installed acceptance are mapped in [tests](../../tests/README.md).

The imported [DSH-only README](HISTORICAL-DSH-README.md),
[proposal](PROPOSAL-plugin-architecture.md), [release plan](RELEASE-PLAN.md) and
[changelog](CHANGELOG.md) preserve browser history. They do not override current
root product versions, setup instructions or qualification.
