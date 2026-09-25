<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Development conventions

## Canonical repository

- The only active Augmentor Desktop + Browser repository is
  [ManoloRemiddi/augmentor-agent](https://github.com/ManoloRemiddi/augmentor-agent), default branch `main`.
- “Save/push to the repo” means this repository. Work on branches here as needed.
  Confirm `git remote -v`, branch and changes before committing or pushing.
- Home application code belongs in `apps/home` and `adapters/dsh-home`; read [Home](docs/HOME.md). The private `local-ai-smart-home` companion owns deployment, not another agent core.
- The website is maintained separately in `ManoloRemiddi/augmentoragent.com`.
- Old product repositories are historical archives. Never merge their Git history
  into this public repository or point an old private checkout at this remote.
  Port only explicitly selected, privacy-reviewed changes onto a current branch.
- Read [repository consolidation](docs/REPOSITORIES.md) for preserved work and
  historical downloads. Current `main` supersedes the former private development branch.


- GitHub is the durable source of truth. Start with [agent handoff](docs/AGENT-HANDOFF.md), [current architecture](docs/ARCHITECTURE.md) and the [documentation index](docs/README.md). Use the canonical repository and current branch; dated private branch references are historical evidence.
- Update the owning documentation with every behavior, setup, data, contract or lifecycle change. Record tested ref, deployment scope, fixture/live evidence and remaining work. Link new guides from the index and publish the documentation with the implementation; private local logs are not a handoff.
- Preserve dated historical evidence, but label it historical and link its current replacement. Keep credentials, private conversations and machine-specific state out of GitHub.
- Installed Linux desktop updates must follow [desktop deployments](docs/DESKTOP-DEPLOYMENTS.md): stage a separate tested artifact, activate it through `augmentor-update`, and report selected versus running build. Never patch a selected release in place or write a launcher to a version-specific preview/source folder. A source commit alone is not an installed update. Preserve matching DSH integration and speech dependencies; a product-version mismatch blocks promotion.

- Follow current `docs/ARCHITECTURE.md`: shared prompts, one native UI, one browser UI, replaceable harness adapters, separate relationship/work memory and a versioned speech package. The user-approved `docs/COMPOSABLE-AUGMENTOR-PROPOSAL.md` and dated `docs/IMPLEMENTATION.md` retain the design rationale and earlier evidence.
- This product originated as a Pi successor and now shares native/browser surfaces across DSH and Pi. Port selected code from the recorded DSH baseline; preserve its copyright and license headers. Legacy installations remain available until tested replacements are ready. Intentional DSH integration and prompt-store migration are authorized by the accepted architecture; preserve source data and attribution.
- Use supported Pi SDK and extension APIs. Keep Pi-specific integration in `packages/runtime` and `packages/pi-linux`; keep presentation and OS helpers separate.
- Use the coding-agent SDK's agent/session lifecycle. Do not start a parallel standalone agent-core loop for the same conversation.
- Pin and lock the versions actually tested. Record package compatibility in `docs/SOURCES.md`; never present an inspected upstream version as a verified integration.
- Carry forward useful existing UI and desktop regression tests. Test new runtime contracts and failure paths; keep fake tests distinct from live model and desktop evidence.
- Development uses separate Pi state, desktop identity and configuration paths. Preserve explicit model selection, visible Stop, and no replay of unknown-outcome actions.
- Use Markdown links for supporting sources. Add copyright/SPDX headers to authored source and documentation where the format supports comments; JSON must remain valid JSON.

- Current user-directed voice placement (19 September 2026): Qwen and Breeze run
  on the RTX 5090. Preserve Qwen context/concurrency/precision and the current
  CPU ASR/VAD path. Never move speech to another GPU or change model settings
  silently; report any failure and let the user direct the next change.
