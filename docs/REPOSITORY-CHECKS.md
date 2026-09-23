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

## Live website and link verification

Website commit: `d02a127c9e8db1508a230138bb3a36c3427e714b`.
[GitHub Pages deployment](https://github.com/ManoloRemiddi/augmentoragent.com/actions/runs/35857699961)
and [all 13 website checks](https://github.com/ManoloRemiddi/augmentoragent.com/actions/runs/35857699817)
passed. The six live HTML pages matched the committed files byte for byte.
The normal homepage, index and manual URLs were also checked without a query string.

All **24 distinct GitHub destinations** extracted from visible links and installation
prompt text returned HTTP 200 after following redirects. The old public source
URL redirected to `ManoloRemiddi/augmentor-agent`. The JSON
[link and download results](REPOSITORY-LINK-CHECKS.json) records each URL and destination.
The resale-request link intentionally requires GitHub sign-in; its return URL
points to the canonical repository's new-issue form with the licensing request title.

Browser interaction checked these actual user paths:

| Click or action | Observed result |
| --- | --- |
| Website GitHub link and licensing page's Explore source | Canonical public `augmentor-agent` repository |
| Full installation guide | Canonical `docs/COMPLETE-INSTALL.md` rendered on GitHub |
| What changed and release limits | Canonical `docs/LINUX-RELEASE-0.2.10.md` rendered on GitHub |
| Copy guided installation prompt | Success status; selected textarea contains canonical project/guide and exact historical artifact/checksum URLs |
| Download complete preview | Clicked without leaving the page; artifact delivery separately verified by a complete anonymous HTTP download below |
| Source & license | Live licensing page with canonical source and permission-request destinations |
| Read full license | Link targets `augmentor-license.txt`; HTTP-delivered bytes verified against canonical `LICENSE` |
| Open licensing request | GitHub sign-in with return URL for `augmentor-agent/issues/new` |
| Fedora guide | Original guide rendered with GitHub's archive notice |
| Legacy Browser release | Browser 0.1.32 release page rendered with archive notice |
| Legacy manual | Both generic GitHub links point to the canonical project; old-version prompt explicitly identifies the active project and its current guide |

The complete 0.2.10 archive was downloaded anonymously after archival:
**67,481,947 bytes**, SHA-256
`8e670c140a526f32a9fc0b1ac81121bd539ff2645e3db6be6d7f8435e14a82c4`.
It matches the original published `SHA256SUMS`; no release asset was changed.
The live combined license has SHA-256
`957e710bdd438f5e9c825fc610b8efc4f10e173f05a2c8ae99aae46b78e22cfe`,
matching the canonical root `LICENSE` byte for byte.

## Archives, reports and privacy

GitHub reports `augmentor-agent` as public, active, default branch `main`;
`augmentoragent.com` stays active for the website. The four superseded application
repositories are archived. Both private archives return 404 without authentication.
The historical PR, commit and Actions provenance links resolve using owner access
at the explicit private-history repository name.

Transferred Browser issues #1, #5 and #6 redirect to canonical issues #1, #2 and #3.
Both unmerged Browser PR heads remain in named archive branches, and their follow-up
work is recorded in [the repository map](REPOSITORIES.md). No open PRs remain in
the four archives. Uncommitted work in the old planning checkout was retained;
no product files from that worktree were staged or published by this cleanup.

Gitleaks 8.30.1 reported zero findings in each new publication diff, including the
freshly cloned public history after the original reviewed root. GitHub secret
scanning and push protection remain enabled, with zero open secret alerts.
The original snapshot's previously reviewed public-key and numeric-example findings
are described by its unchanged publication record; they are not credentials.

## Public CI and baseline correction

The first consolidation run caught JSON Unicode formatting in package metadata;
regenerating with `scripts/sync-version.py` corrected it. The local version check
and TypeScript check passed after installing locked dependencies.

The next run passed source/native checks, packaging, installed fresh-package
acceptance and packaged-browser acceptance, but its upgrade job still attempted
to fetch private historical commit `295dbc0`. The public workflow now uses
[`scripts/stage-lifecycle-baseline.py`](../scripts/stage-lifecycle-baseline.py)
to stage the original public 0.2.9 packages with pinned archive and package hashes.
The verified archive is **67,317,532 bytes**, SHA-256
`8149ac66866d79422cdcd84f672b228c4b6ac7db162e07eef846454e20035da4`.
Both extracted Debian packages report version 0.2.9. Additional synthetic checks
covered the exact selected files/source identity and rejection of a changed archive,
a wrong version, symlink members and a nonempty output folder.

To reproduce staging, run `python3 scripts/stage-lifecycle-baseline.py` from the
canonical checkout. Run `bash scripts/lifecycle-proof.sh` with built candidate
Debian packages in `outputs/debian` and a supported container engine.
See [lifecycle qualification](LIFECYCLE.md#public-ci-baseline-after-repository-consolidation).
This test uses the 0.2.9 public baseline; older 0.2.0 qualification remains historical.

Final CI implementation ref: `64a20a358294ffb1fdcebb372595f2a106dda74f`.
[Full validation run](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/35858808139).
**All three jobs passed:** Debian/source/native validation and package creation;
installed-package acceptance including active-task refusal, upgrade, interrupted
configuration, rollback, removal and data preservation; and packaged-browser
acceptance. The public baseline removed the private-history dependency without
skipping the lifecycle proof. The earlier artifact-storage limit did not block
this completed run.

This final evidence-only commit does not change the implementation tested at the
ref above. Repository cleanup does not redeploy the installed application or
create a new binary release.
