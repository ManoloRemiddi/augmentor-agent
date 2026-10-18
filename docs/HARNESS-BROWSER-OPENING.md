<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Open Harness normally on MX Linux

Use **Augmentor Harness (MX)** in the Applications menu. Its stable launcher is
`augmentor-harness-review open main`; it asks the verified current owner for its
private connection and opens the regular default browser. You do not need an
assistant to create the link. The separate Migration Pilot entry opens the pilot.

The source correction addresses the reported bare-address/new-tab failure:

- After a successful operator login, the browser remembers that operator
  credential in origin-local storage. Another tab or browser restart can open
  the ordinary root address without copying the private fragment.
- The same owner profile keeps its private credential and local port across
  an idle runtime restart. `harness-browser-access.json` is a bounded, private,
  owned single-link record, separate from the temporary `harness.json` liveness
  descriptor. Explicit nonzero configured ports remain authoritative. A port
  conflict fails rather than silently moving a bookmark elsewhere.
- A new browser/profile or cleared website storage still needs the Applications
  launcher once. Disabled persistent storage retains direct private-link access.
  No tokenless API, query-token login or anonymous local auto-login was added.
- An explicit private link wins over stored authority. Inspector credentials
  remain tab-scoped and expiring; they are never remembered as operator login,
  and a failed inspector is not retried using a remembered operator credential.

The initial launch on an older installation may choose a new address because the
old release deleted its temporary owner descriptor during shutdown. After opening
through the launcher, bookmark the new ordinary address. To revoke remembered
access, clear this site's browser storage; for a complete profile-key rotation,
stop the owner and preserve/remove its private `harness-browser-access.json`
through the existing owner recovery procedure before reopening from the launcher.
Restarting the owner alone now retains its browser credential intentionally.
Never publish either private connection record or a fragment-bearing URL.

Project relocation archives the complete original source, including its private
connection record, but imports only the existing selected operational trees. The
destination's active browser credential stays its own; source credentials are
not activated in another profile. The original GUI/layout and request admission,
origin checks, inspector scope, model settings and shared-data policy are preserved.

Source checks pass **22 Node cases**, including a real Chromium profile opening
the original GUI from a bare address in a second tab, then after both browser and
Host restart, with zero provider requests. A real inspector keeps read-only
controls and leaves the remembered operator credential unchanged. Native-profile
relocation confirms destination authority is unchanged and the source credential
is kept only in its exact private archive. TypeScript and GUI build pass.
The first focused run found that temporary owner metadata is removed on normal
shutdown; using a separate persistent record fixes it while preserving the
existing liveness cleanup. The first run had 12 passes/one failure; the corrected
focused run passes 14, followed by the 22-case original-GUI/relocation run.
These are authored isolated fixtures; installed adoption is still pending here.
No physical macOS/Windows acceptance is claimed; the owner still requests MX first.

The owner has authorized closing the older preview despite its unsent draft and
proceeding with the swap. The former draft blocker is resolved by that explicit
instruction. Build/qualify **one** new immutable candidate for this runtime/GUI
change; reuse the existing controller and guarded cold-cut pipeline. Do not patch
the selected app or create repeated retained build mirrors. Fresh caller
quiescence, one complete backup, matching publication, ordinary reopening and
actual owner continuation remain required. Preserve DSH projects/history and the
legacy compatibility dependencies until replacement clients verify.
