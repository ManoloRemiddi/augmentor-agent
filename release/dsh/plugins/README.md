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
| `dsh-resonant-voice-0.1.19.tgz` | `793730ae6da8addd05fa70d82a2fe7341c1d469dc9ff415be2879d165022d36e` |

The parent npm lock records archive integrity and all runtime/peer dependencies,
including React and schemastery. Build with lifecycle scripts disabled. The Mac
ships the installed dependency graph; first run performs no npm installation.
The complete Linux bundle carries these archives beside its same lockfile.

Adaptive Reasoning source is `64a1ef82e3d69f57a69809d530c1b9ed0bc67480` in
[its own repository](https://github.com/ManoloRemiddi/dsh-adaptive-reasoning).
Voice 0.1.19 is an unmodified `npm pack --ignore-scripts` candidate from source
`7d0fd6d677ea4bbbca0183a6bb3a3d3f24a8147a` (branch `feat/windows-config`, PR #2) in
[its own repository](https://github.com/ManoloRemiddi/resonant-voice).
The complete release retains the distributed plugins' corresponding source
archives and labels their scope/digest; external service repositories are separate.
No CI job fetches private dependency repositories. Model Picker ships
its JavaScript and MIT notice. Continue maintaining these dependencies in their
own repositories; update the archives and shared lock deliberately together.

The voice candidate retains private maintenance admission and corrects Windows
ownership during automatic profile cloning and preference saves. All six private
configuration and five maintenance tests pass on native x64 and ARM64 at `7d0fd6d`
in [run 36389214161](https://github.com/ManoloRemiddi/resonant-voice/actions/runs/36389214161).
Linux passes 42 Node tests (three Windows skips), actual pinned DSH lifecycle
integration and disposable tarball install/compose/remove. The exact archive above
is shared by Linux/macOS/Windows. Full assembled Augmentor drain/restart is being
requalified; physical audio remains open. Existing installed voice runtimes, GPU
placement and public downloads remain unchanged.
