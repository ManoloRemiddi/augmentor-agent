<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor 0.2.10 complete Linux preview — qualification

Qualified on 21 September 2026 for Debian 13 amd64. This record concerns the
immutable complete bundle below, not the author's running private installation.

## Exact identity

- Product source: `ad4bc7d560c4c10e3dcf8d5aeac6208218b2f01e`.
- Resonant Voice 0.1.16 source: `936a721531bf69b9dd453c56f1c54f709f288419`.
- Adaptive Reasoning 0.2.3 source: `64a1ef82e3d69f57a69809d530c1b9ed0bc67480`.
- Archive: `augmentor-0.2.10-complete-preview.1.tar.gz`.
- Archive SHA-256: `8e670c140a526f32a9fc0b1ac81121bd539ff2645e3db6be6d7f8435e14a82c4`.
- DSH 0.1.5-rc.1; Model Picker 1.1.2; included plugin list in `bundle.json`.

## Completed checks

- TypeScript check/build, generated version consistency, 160 Node tests,
  410 native/Python tests and 21 Browser tests passed.
- The final Debian package's execution adapter passed 35 checks with real pinned
  DSH and deterministic model responses (one is an isolated historical-event
  hook fixture). The final packaged native modules passed all 9 reply-completion
  checks. Outcome-contract cases additionally cover canonical shell failures,
  background job IDs, invalid metadata and repeat identity.
- The exact complete archive installed as a fresh non-root user in pinned
  Debian 13. Real DSH, all three external plugins, both Augmentor presets,
  execution adapter/module availability, private key-file permissions, saved
  connection, Qt rendering, second-window/login/recovery entries, matching
  browser registration and repeat-install preservation passed. Services were
  deliberately disabled in the container; the configured model URL was a fixture.
- Debian 0.2.9 to 0.2.10 upgrade, rollback, interrupted configuration and removal
  passed. In-use replacement was refused, active work survived refusal and
  desktop-only removal, histories and prompts survived upgrade/rollback/reinstall,
  custom improvement instructions and unrelated user files were preserved,
  and no model request was replayed by migration. The existing test driver was
  corrected to use maintenance for modern baselines rather than the 0.2.0
  manual shutdown sequence; that correction changes no shipped runtime code.
- Bundle hashes, source identity, extension file inventory, native executable
  notices and private-state exclusions passed. Complete source snapshots omit
  repository histories, outputs, credentials, installed profiles and user data.
- Website preview verified the download/installation content, plugin inclusion,
  visible layout and installation-prompt copy feedback.

## Behavior and limits

The execution adapter is bundled, not a separate installation step. It bounds
same-turn empty/truncated-response recovery, respects Stop and concluding tool
handoffs, guards exact duplicate changes during recovery and distinguishes
uncertain shell effects from settled execution. It tracks existing background
jobs and allows inspection without repeating a change. Ordinary tasks outside
automatic recovery retain their normal tool behavior.

This is not proof of general model competence, semantic answer correctness,
cross-session memory quality or exactly-once external effects. Different commands
can express the same action. Tools without adequate canonical outcome contracts
can conceal partial effects. The action ledger is per turn, not a persistent
cross-session transaction journal. Unknown effects remain conservative during
recovery and may require a user-directed resumption.

The preview targets Debian 13 amd64, with historical desktop-control qualification
scoped to KDE Plasma Wayland. Container checks do not establish physical login,
microphone/speaker performance, GPU placement or every desktop-control workflow.
Optional voice/memory engines were not reprovisioned in the release container;
their existing qualification and licensing requirements remain separate. No
live model benchmark was submitted, no production service was restarted and no
private user conversation was read or published by these tests. macOS and Windows
are not qualified by this release. Existing customized installations require the
maintenance/integration migration path; the fresh wizard refuses replacement.
