<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Exact plugin distributions

Model Picker and Adaptive Reasoning retain the unmodified MIT-licensed archives from the published
[Augmentor 0.2.12 complete preview](https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.12-complete-preview.1).
Their own licenses, authorship and notices are retained inside each archive.
The application's root license does not replace those terms.

| Archive | SHA-256 |
| --- | --- |
| `dsh-model-picker-augmented-1.1.2.tgz` | `9a2c2e17c128da3565520b5f39cb85606823440ee0e1e4c2316f806fc58914fc` |
| `dsh-adaptive-reasoning-0.2.3.tgz` | `5c142213e4f7935cf7e8f0ba839e17d274451c689c04637001dd1d89b6da967e` |
| `dsh-resonant-voice-0.1.18.tgz` | `3f21a07535c4e8652d704ce1d1b3c9b4dc418d50754eaae7c634caa20cde50ad` |

The parent npm lock records archive integrity and all runtime/peer dependencies,
including React and schemastery. Build with lifecycle scripts disabled. The Mac
ships the installed dependency graph; first run performs no npm installation.
The complete Linux bundle carries these archives beside its same lockfile.

Adaptive Reasoning source is `64a1ef82e3d69f57a69809d530c1b9ed0bc67480` in
[its own repository](https://github.com/ManoloRemiddi/dsh-adaptive-reasoning).
Voice 0.1.18 is an unmodified `npm pack --ignore-scripts` candidate from source
`7a6645ea27f55bdd18acbc22c2893a09bed58004` (branch `feat/windows-config`, PR #2) in
[its own repository](https://github.com/ManoloRemiddi/resonant-voice).
The complete release retains corresponding source archives. Model Picker ships
its JavaScript and MIT notice. Continue maintaining these dependencies in their
own repositories; update the archives and shared lock deliberately together.

The voice candidate retains Windows ACL validation and adds reversible private
maintenance admission with natural idle exit. Native config and all five
maintenance tests pass on x64 and ARM64 at `7a6645e` in
[run 36371851225](https://github.com/ManoloRemiddi/resonant-voice/actions/runs/36371851225).
Linux passes 41 Node tests (two Windows skips), eight Python ASR fixture tests,
real DSH SDK disposal, and disposable tarball install/compose/remove. The shared
lock and complete Linux assembly select the same candidate. Full Augmentor
coordination and real audio remain pending. Existing installed voice runtimes,
GPU placement and public downloads remain unchanged.
