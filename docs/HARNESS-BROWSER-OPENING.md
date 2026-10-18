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

The MX main and pilot registrations now explicitly retain their existing local
ports for the first upgrade. This preserves their browser origins and existing
browser-local preferences. Other older profiles may choose a new address because
their old release deleted its temporary owner descriptor during shutdown. Open
through the launcher once after upgrading, then bookmark the ordinary address.
To revoke remembered
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

The owner authorized closing the older preview despite its unsent draft and
proceeding with the swap. Its Qt window and exact idle Pi Host are now closed;
saved data remain intact. The former draft blocker is resolved. Preserve DSH
projects/history and legacy compatibility dependencies until replacement clients
verify; further project transfers still require pilot feedback.

The registered-review cold-opening check now expects the intentional stable
bookmark, while still requiring a different confirmed owner PID, exact state and
configuration, caller-key exclusion, unchanged history and no additional model
request. It additionally checks that the restarted HTTP endpoint rejects anonymous
access and accepts the retained private credential. The former URL-rotation
assertion described the previous behavior and is superseded by this contract.

## Exact replacement package and remaining switch — October 18

Application **576975c04cfb3e71657401ae9f33d50e1e0a88a9** is sealed as artifact
**2a3b1c41c87fbd70f88868a79b6239876ea77031085089df87908da5d01b4c89**,
with **24,816 inputs / 1,146 compiled files**. This one new runtime/GUI package
supersedes the earlier 4f83 supplier for the pending switch; that supplier remains
recovery. Its publication controller includes schema 4. Continue orchestrating
from reviewed source outside the archived release-store parent.

Both ordinary and sealed application trees pass **434 Python / 88 Node** each;
the declared installed Python separately passes **233 core checks**. The full
UI suite uses the existing test environment because installed Python lacks optional
`PySide6.QtTest`; the initial full run with installed Python failed for that
missing test module. No owner Python environment was changed. Two earlier
disposable assembly attempts refused stale GUI output/path assumptions before
sealing and were cleaned. One successful seal was reused throughout.

The exact package passes **six registered SDK warm/cold reopening cases** using
test contract **ed603cec**. Nine retained plugin roles, including Prompt Library
and Improve, execute in place against authored public fixtures: no private source
copy, three synthetic provider requests and zero owner inference. The initial
registered check expected URL rotation; the corrected test requires stable
credentials while still proving a new owner PID, preserved state/history and
authenticated HTTP access. No application rebuild was needed for that test change.

Actual configuration stages read-only: **48 bound inputs / ten edits**. The owned
registrar advanced **20→21→22**, retaining the two current owner PIDs and all
profile fields except explicit existing ports. Normal Applications menu entries
now belong to these registrations. No owner restart, inference or data migration
occurred. The new read-only plan covers **28 roots / three shared pairs**, one
partial source and **32 bootstrap images**, only registry content changing
prospectively **22→23**. It must be recomputed under the real cold guard.

**Installed selection and running app remain old.** Chromium is still running;
the owner has been asked to save browser work and fully exit it. This session has
no control surface for that regular browser. Keep other clients online until
that prerequisite is met. Then recheck accepted work, quiesce every actual caller,
capture one full backup, prepare data/Browser before configuration fences, apply
and finalize the coupled publication, reopen normally and verify the loaded
extension/host plus actual pilot continuation. No cold owner archive or swap has
occurred at this checkpoint. Voice expansion and later operating systems stay
deferred. [Portable evidence](../release/harness-browser-opening-qualification-20261018.json).
