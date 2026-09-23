<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# DSH qualification environment

Install this environment in an isolated directory with `npm ci --ignore-scripts`.
Use its `node_modules/.bin/dsh` on PATH and set `DSH_TEST_MODULES` to its absolute
`node_modules` path when running `scripts/dsh-setup-proof.py` from the repository.
Do not replace a user's existing DSH installation with this test environment.

The CLI and 230 internal DSH packages are locked to 0.1.5-rc.1. Installing the
CLI version alone permits its caret dependencies to select rc.2; that mixed suite
was rejected by Augmentor's version check on the Mac Mini. The overrides record
the internal suite present in the existing Linux integration. The lockfile also
pins registry tarballs and integrity hashes for the remaining dependencies.

This is a qualification fixture, not a claim that the full DSH release acceptance
matrix has passed. Update the suite deliberately and rerun both platform tests
before changing supported versions. macOS GUI control and public packaging have
separate release gates.

## Desktop capability composition

`desktop-capabilities.json` carries forward eleven entries from the user's
working `augmentor-linux` preset, originally generated from the DSH 0.1.5-rc.1
standard preset. Upstream copyright © 2026 DeepSeek, MIT license; see
`desktop-capabilities.LICENSE`. Local modifications copyright © 2026 Manolo
Remiddi, under [MIT with Augmentor Resale Restriction](../../LICENSE). The JSON format cannot contain license comments.

The entries preserve planning, compaction and workflow isolation realms, jobs,
filesystem search, skills, goals, to-dos, and web search. They supplement the
product persona, filesystem/shell/question tools, memory and desktop adapter.
Optional Codex/Claude delegation tool rows remain disabled, as in the reference
preset. This does not install host plugins or claim all external integrations
are qualified. Browser-only presets do not receive these desktop capabilities.
