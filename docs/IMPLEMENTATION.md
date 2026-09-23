<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->
# Composable Augmentor implementation

**Historical 0.2.0 implementation record.** Current ownership and behavior are in
[Architecture](ARCHITECTURE.md), [agent handoff](AGENT-HANDOFF.md), and
[dual memory](DUAL-MEMORY.md). The checklist below describes 6 September, not current deployment.

Accepted 2026-09-06; implemented as the working 0.2.0 migration below. The checkout path remains unchanged to preserve installed references.

- [x] Browser source imported with its Git history; shared design, template fixtures, adapter contract and feature ledger.
- [x] Independent transactional prompt service, Python/Node clients, stable IDs, revision conflicts, notifications and idempotent migration.
- [x] Linux and browser prompt editors use the shared service and clipboard semantics. DSH's settings page forwards to this service; the old independently writable namespace is inactive.
- [x] One native UI with Pi and DSH adapters; capability-gated branch/edit; selected model preserved in real local-model checks.
- [x] One browser UI with Pi and DSH adapters; actual Chromium page execution and mouse interaction tests.
- [x] Optional memory interface and scope/provenance boundary recorded. The user has now selected Hindsight as the first provider.
- [x] Connect Hindsight and verify that facts retained through either surface/harness are available to the other combinations in the same scope, including restart, provider failure and removal. At that historical checkpoint, no user memory was being read or written through this integration; automatic memory was activated on 19 September as recorded in the current handoff.
- [ ] Implement and test general Linux computer use for desktop applications. Existing command/file tools and desktop observation do not yet provide this capability.
- [x] Native app and independent service installed, DSH prompt adapter activated, native browser host registered, browser files deployed with backups.
- [ ] Reload of the existing user's Chromium extension and confirmation of its new version in that profile. Isolated Chromium acceptance has passed for both adapters.

## Evidence, 2026-09-06

- Node contract/SDK suite: 36 passing, including standalone native-host prompt access with both engines absent and preservation of the harness choice for legacy browser profiles.
- Native suite: 56 passing, including real Qt clicks at middle/bottom scroll positions, clipboard/tick behavior, prompt conflicts, shared-service concurrency and persistence, controller Stop/recovery regressions.
- Browser prompt DOM suite: 3 passing.
- `scripts/native-harness-proof.py`: the same Qt window/controller completed real conversations through both Pi and DSH using Qwen3.8-27B-UD-Q6_K_XL; model selection retained. This is local-model evidence, separate from unit tests.
- `AUGMENTOR_PROOF_HEADED=1 AUGMENTOR_PROOF_DSH=1 xvfb-run -a python3 scripts/browser-composable-proof.py`: real Chromium/native messaging/Pi SDK with a deterministic local model; actual mouse Copy checked with an external `xclip` process and stable scroll after feedback expiry; Branch/Edit checked against model tool context and unchanged parent history; competing prompt writes preserved the browser draft. The same extension then performed real browser actions through DSH with the local Qwen model. A real Pi worker restart also preserved the session without replaying a model request.
- Fresh release archive installed into an isolated prefix and launched the native app successfully.
- Installed native UI reload preserved the selected session, empty draft and visibility; Ctrl+Fn+Space's emitted `Ctrl+Hangul` binding retained.
- Live DSH route reads exactly the same three prompt records as the Python client. Old `prompt-library` settings namespace absence verified after an idle service restart.

The imported legacy browser end-to-end battery has fixtures tied to the old single-harness native host. It is not claimed as passing unchanged; the composable Chromium proof and current bridge/DOM tests are the acceptance path for this release.

See [feature ownership and limitations](FEATURE-MATRIX.md) and [deployment/rollback](MIGRATION-0.2.md).

Automatic transcript-based identity and work continuity is implemented separately; see [Dual memory](DUAL-MEMORY.md) for architecture and evidence.

Current desktop development, Hindsight migration and voice integration are recorded in the [September ledger](DESKTOP-UPDATE-2026-09-19.md). Earlier evidence remains tied to its original versions.
