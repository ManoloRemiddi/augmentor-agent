<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Private speech-source cleanup — October 1, 2026

The owner authorized removing the private speech-source test archive while
preserving the complete Augmentor and Codex work. A verified private Git bundle
preserves the original integration history. Separate working-file/patch backups
preserve the unfinished login work and unrelated canonical checkout edits.
Backups are owner-only, outside all publication targets, and must never be pushed.

The integration branch is rewritten to omit the source archive and its private
source-packaging helper. The public application no longer depends on that npm
test package or passes it into the Home Docker build. Public voice tests use
an independently authored [synthetic protocol peer](../tests/fixtures/codex/VOICE.md).
All other product implementation remains; installed apps, conversations,
credentials, production speech and model/GPU settings are unchanged.

The publication boundary in AGENTS.md now explicitly requires approval for the
exact private files before copying them into public source or CI. A CI gate with
complete branch history rejects the removed archive, including renamed copies,
and its reproduction helper. The archive path is also ignored. This gate is
specific to this incident; it does not replace reviewing any future publication.

## Validation and current limits

- Clean locked dependency installation, TypeScript check and build pass.
- All seven Codex voice tests pass with the scripted peer, including actual
  pinned Codex plus native Qt and Browser native-messaging paths.
- Root Node suite: 357 tests, 355 pass, two opt-in real-memory-engine proofs skip.
- Browser suite: all 56 tests pass after installing its separately locked test
  dependencies. The first isolated run lacked jsdom and failed before setup.
- Native suite: 578 tests, 576 pass, two Mac-only checks skip on Linux; the two
  additional source-boundary tests pass separately.
- 111 downloadable Codex-branch CI artifacts were downloaded and recursively
  inspected. None contains the removed archive or exact original source files.
  The three visible forks' current branch/tag histories do not descend from the
  introduction commit. These checks do not establish what private clones retain.

The replacement validates Augmentor's protocol plumbing. Earlier tests using
the private real-service code are historical evidence, not current public CI
coverage. The separately versioned real companion and physical audio need
independent qualification. Codex's remaining C0–C9 gates remain open, including
live providers, eligible subscription login and native executable licensing.

Rewriting a branch does not guarantee removal of cached commit views or GitHub's
internal pull-request references. GitHub-controlled remnants need a Support
request; copies already downloaded elsewhere cannot be recalled. See
[GitHub's removal procedure](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).
Support decides whether this source disclosure qualifies for purging.
