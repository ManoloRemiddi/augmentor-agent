<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Repository consolidation checks — September 23, 2026

## Identity and history

- Canonical public `ManoloRemiddi/augmentor-agent`: GitHub repository ID `1383187310`.
  This is the renamed clean source repository, not the old private repository.
- Private `ManoloRemiddi/augmentor-agent-history`: repository ID `1359071351`.
- Public root commit remains `2e62cec0accb8151e42e0d12c1295c9500a3ff43`.
- Public `SOURCE-PUBLICATION.json` is unchanged. Private branch histories were not imported.
- All discovered local clones of the private repository were moved to the explicit
  private-history remote before reusing its old GitHub name. Existing worktrees
  and their uncommitted application files were retained.

## Focused checks before deployment

- Website `node --test tests/*.test.mjs`: 13 passing tests, including canonical
  links, the copy-button target and prompt URLs, and every local page link,
  fragment and static asset reference.
- Browser install-proof clone location now accounts for `apps/browser` in the
  canonical monorepo; its referenced plugin, extension and host files exist.
  JavaScript and changed Python syntax checks passed. This is not a fresh
  installed-browser acceptance run.
- Plugin repository metadata names the canonical repository and its correct
  `apps/browser/plugin` subdirectory. Fedora package homepage points there too.

## Live verification

Live link, download and repository-state checks are recorded after deployment.
The historical full source CI run was blocked by GitHub artifact storage quota;
repository cleanup does not establish new runtime or installed-app qualification.
