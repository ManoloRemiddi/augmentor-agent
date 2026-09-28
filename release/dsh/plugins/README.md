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
| `dsh-resonant-voice-0.1.17.tgz` | `75a4e5cc4f6ac7c0738e578d62568389aed7df0cdd063d9d47fc355a45a03386` |

The parent npm lock records archive integrity and all runtime/peer dependencies,
including React and schemastery. Build with lifecycle scripts disabled. The Mac
ships the installed dependency graph; first run performs no npm installation.
The complete Linux bundle carries these archives beside its same lockfile.

Adaptive Reasoning source is `64a1ef82e3d69f57a69809d530c1b9ed0bc67480` in
[its own repository](https://github.com/ManoloRemiddi/dsh-adaptive-reasoning).
Voice 0.1.17 is an unmodified `npm pack --ignore-scripts` candidate from source
`aae6a51` (branch `feat/windows-config`, PR #2) in
[its own repository](https://github.com/ManoloRemiddi/resonant-voice).
The complete release retains corresponding source archives. Model Picker ships
its JavaScript and MIT notice. Continue maintaining these dependencies in their
own repositories; update the archives and shared lock deliberately together.

The voice candidate adds native Windows ACL validation. Its four private-config
checks pass on x64 and ARM64 at code ref `22fd869`; full application integration
is pending. Linux passes 36 Node tests (two Windows skips). The shared lock and
complete Linux assembly now select the same 0.1.17 candidate. Existing installed
voice runtimes and public downloads remain unchanged.
