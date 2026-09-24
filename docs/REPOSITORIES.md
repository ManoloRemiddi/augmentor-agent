<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# One active Augmentor repository

As of September 23, 2026, [ManoloRemiddi/augmentor-agent](https://github.com/ManoloRemiddi/augmentor-agent)
is the only active repository for Augmentor Desktop and Browser: source, issues,
pull requests and future releases. Default branch: **main**. “Save/push to the repo”
means this repository. Feature work uses branches within this repository.

## Repository map

| Repository | Role |
| --- | --- |
| [augmentor-agent](https://github.com/ManoloRemiddi/augmentor-agent) | Active Desktop + Browser project |
| [augmentoragent.com](https://github.com/ManoloRemiddi/augmentoragent.com) | Active website only |
| `augmentor-agent-history` | Private archive of original development history and unfinished branches |
| `augmentor-agent-linux` | Private archive of the old standalone desktop baseline |
| [augmentor-dsh-extension-plugin](https://github.com/ManoloRemiddi/augmentor-dsh-extension-plugin) | Archived standalone browser history and old releases |
| [augmentor-agent-app](https://github.com/ManoloRemiddi/augmentor-agent-app) | Archived historical downloads and documentation |

The former `augmentor-agent-source` URL redirects to this repository. Do not reuse
that old name: doing so would break its redirect. The public repository keeps its
original clean root commit `2e62cec0accb8151e42e0d12c1295c9500a3ff43`.
No private development history was merged or made public.

The old private repository occupied the name `augmentor-agent` before consolidation.
Links to its commits, PRs and Actions must explicitly use `augmentor-agent-history`;
reusing the short name prevents those old links from redirecting to private history.
Those provenance references still require owner access. They are not public setup links.

## Existing downloads

The current [0.2.11 security release](https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.11-complete-preview.1)
is published in this canonical repository. The website and copied installation
prompt point here. See [release evidence and upgrade guidance](RELEASE-0.2.11.md).

The archived 0.2.10 complete preview, older Fedora packages and Browser 0.1.32
remain at their original URLs with unchanged bytes, checksums and licenses. They
do not receive the new WebSocket fix automatically. Do not install the historical
0.1.32 package or mix its companion with the current product. New artifacts have
their own exact source revision and checksums; current source is not retroactively
the source of an older download.

## Preserved contributions and reports

Original issues were transferred with their discussions and remain open:

- [Native host orphan-process report](https://github.com/ManoloRemiddi/augmentor-agent/issues/1)
  (formerly standalone Browser issue #1).
- [Legacy Browser privacy/security report](https://github.com/ManoloRemiddi/augmentor-agent/issues/2)
  (formerly #5). Assess each item against the maintained product; moving the report
  does not establish resolution or reproduce it on the current version.
- [Bounded boot retry report](https://github.com/ManoloRemiddi/augmentor-agent/issues/3)
  (formerly #6). Proposed patch remains in
  [legacy PR #7](https://github.com/ManoloRemiddi/augmentor-dsh-extension-plugin/pull/7)
  by katkurigopi05 and archive branch `preserved/pr-7`. Current source still has the
  16-second backoff cap; this cleanup does not apply or certify the proposed fix.
- [Compatibility contribution follow-up](https://github.com/ManoloRemiddi/augmentor-agent/issues/4)
  tracks [legacy PR #4](https://github.com/ManoloRemiddi/augmentor-dsh-extension-plugin/pull/4)
  by maximilian-moore: initial auth redirect cookies, old/new persona schemas and
  macOS native messaging. Its patch remains in archive branch `preserved/pr-4`.

The two legacy PRs are closed because their target is archived, **not merged**.
Port selected changes onto the current source with attribution and focused checks.
Do not merge legacy Git history or silently relicense external contributions.

## Preserved private work

The private archive retains the `experiment/semif-tool` branch (six commits of
experimental evaluation outside the published snapshot) and
`planning/resonant-harness` (five planning commits outside it), plus the former
productization branches and PR #3. These are preserved work, not current releases.
The old standalone Linux head matches the recorded source baseline `473fece`.

Existing worktrees and their uncommitted files are retained. Before continuing an
old task, inspect its dirty state, preserve it, and select only the changes needed
for the intended product work. Review those changes for private data and port them
to a new branch based on this repository's `main`. Private plans and raw experiment
results are not automatically public. Do not repoint an old private checkout at
the public origin, use a mirror push, or merge unrelated histories.

Standalone dependencies and separate OS projects retain their own repositories;
they are not alternative Augmentor Desktop/Browser development repositories.

## Verification record

See [consolidation checks](REPOSITORY-CHECKS.md) for repository identities, live
website checks, redirects, copied installation prompt and preserved downloads.
