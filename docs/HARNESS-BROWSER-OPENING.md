<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Open Harness normally on MX Linux

## Login startup and recovery — October 20

The October 19 browser change preserved the address and login, but did **not**
arrange server startup after reboot. The owner reproduced the gap after a real
reboot: no listener at the saved address, no Harness login entry/service. The
existing verified launcher restored the registered pilot successfully without
changing its build or browser identity. A browser bookmark cannot start a local
server by itself.

Use **Augmentor Harness** in Applications, or run `augmentor-harness`. It opens
this explicitly configured registration in the default browser, starting it when
necessary. The existing bookmark remains **http://127.0.0.1:41789/**. After login,
`augmentor-harness.service` starts the server quietly, with an XDG Autostart entry
as a second activation route. Login startup does not open browser tabs. Repeated
login/menu requests and concurrent opens converge on one existing owner.

The separate startup controller is content-addressed and its stable launcher
verifies its checksum. It follows the existing private review registration;
updates do not pin the launcher to a source checkout or a particular app release.
It uses the original sealed opener for profile, full artifact, IPC peer, startup
lock and maintenance checks. It never chooses another registration or creates an
empty replacement when configuration is missing. The controller has its own
small installation/selection manifest and control-file backups; it does not
modify an immutable app or copy the whole application/profile.

The user service is enabled for `graphical-session.target`. XDG login activation
imports only current graphical session variables before starting it, supporting
MX session activation order. The normal launcher still uses the verified opener
if the user service manager is temporarily unavailable. Startup is for the
current MX Linux systemd session; SysV-only MX, other Linux distributions and
later OS startup adapters are not qualified here.

Every five seconds the controller checks the known same-user owner and its
fixed browser listener. It uses the IPC peer's actual listening socket inode
and an anonymous access-boundary probe; health checks never send a bearer to a
foreign listener. Full release verification occurs on startup, recovery and
registration changes, rather than scanning the full app on every healthy poll.
The address stays bound to loopback. Login links never appear in service output,
menus or status files.

| Case | Behavior |
| --- | --- |
| Reboot removes `/run/user` sockets/directories | Original launcher recreates the registered runtime directories and starts the same profile. |
| Browser closes | Backend stays available; reopening the bookmark works in an authenticated browser profile. |
| Runtime exits/crashes | Controller reopens the registered profile; saved unknown-outcome work is not replayed. |
| Controller exits | User service restarts it; it adopts the existing owner without restarting that owner. |
| Login and menu open together | Startup/registry locks and the controller lock prevent duplicate owners. The menu waits through a busy startup registration. |
| Fixed port occupied | Startup remains waiting; it does not change the bookmark or displace another listener. It retries when the port is free. |
| Maintenance lock/fence | Startup waits and preserves the current owner/work until the reviewed maintenance/recovery completes. |
| Live owner has missing/unresponsive IPC | No second owner and no forced kill. Status reports waiting; inspect the private runtime log. |
| Missing/edited registration, build or controller | Fail visibly and preserve existing data; no fallback to an older/empty profile. |
| New browser/profile or cleared storage | Launch Augmentor Harness once to authenticate that browser, then use its normal bookmark. |
| Model endpoint unavailable | Server startup does not issue a generation or wait for a model response. Model availability remains a separate app concern. |

Status and recovery controls:

```sh
augmentor-harness --status
systemctl --user status augmentor-harness.service
journalctl --user -u augmentor-harness.service
```

A manual `systemctl --user restart augmentor-harness.service` restarts the
controller and preserves the running owner. `KillMode=process` deliberately
prevents service-manager recovery from killing that owner's work. A slow or
unconfirmed owner is reported instead of being forcibly replaced. Profile
shutdown/update continues through the existing guarded maintenance procedure.

To install the controller against an existing, explicit registration:

```sh
python3 -B scripts/harness-startup.py --install --registry "$HOME/.config/augmentor-harness/reviews" --review pilot
systemctl --user daemon-reload
systemctl --user enable --now augmentor-harness.service
```

Source checks pass **32 Python cases** covering startup/review guards, protected
installation, rollback, tampered files, diagnostics, lock races and private output.
The existing exact sealed app passes **six Node cases** for real SDK startup,
missing reboot runtime directories, concurrent opens, crash recovery, controller
restart, maintenance and fixed-port collision/recovery. Native history and browser
identity stay exact; only the authored fixture's two initial model requests occur,
with **zero additional generation requests during startup/recovery**. The tests
use authored profiles and the current sealed app in place; no new full app copy
or replacement app seal is required. Actual installation is complete against the same registered **6fa33389…5d265e0**
app. Controller source **c48d647c**, code checksum
**97e77042…6b7d86c**, is installed through its private selection/owned-file manifest.
The user service is **enabled and active**. The exact installed login action
passes twice. Crashing only its verified supervisor causes an automatic service
restart while the same owner PID stays online. Registry **24**, the persistent
credential, current configuration, **111 conversations** and Metafolder revision
**29** are unchanged. The ordinary default-browser launcher succeeds, and a new
IAB tab at the bare address shows the real app with an editable composer and saved
groups, without a new private link. No owner generation or app restart occurs
during controller installation/testing. Small control-file recovery is retained;
no profile or full application copy and no new app seal were made.

A second physical reboot is not performed by the assistant; that full graphical
login check remains distinct from the observed post-reboot restoration, installed
activation action and isolated cold-start/recovery tests.
[Portable evidence](../release/harness-startup-20261020.json).

## Installed pilot — October 19

Bookmark **http://127.0.0.1:41789/** in the browser profile used for the pilot.
The pilot now runs the corrected immutable package; this is an installed update,
not a source-only claim. An authenticated opening has also been sent to the
normal default Chromium browser. After an authorized initial login, plain-address
new tabs use the remembered operator credential. Fresh/private browser profiles
and cleared website storage still require their own authorized first login;
anonymous API access remains refused.

The prior combined-migration prerequisite delayed this independent review fix
unnecessarily. Targeted adoption changes only the pilot's registered application,
retaining its configuration/state/workspace/shared pair, existing credential and
port. The original GUI and settings remain. Main still uses the older application;
Native/DSH/shared-store/loaded-extension consolidation remains separate. A Chromium
exit was not required for this isolated pilot update.

The idle, draft-free old owner acknowledged shutdown and its exact pidfd confirmed
exit. A persistent private backup verifies **363 profile files**, consistent shared
SQLite snapshots and the original registration. The owned registrar advanced
**22→23**. Three saved conversations and their paused/empty queues remain; all
**21 original protected prefixes** survive, with only typed MCP connection metadata
appended. Shared prompt/memory rows, engine configuration and both production
selectors are exact. No owner model request, new project import or new full app
build occurred; the existing qualified seal was reused.

Actual CUA inspection first reproduced the reported plain-address error. After
updating, an authorized login was followed by a **new tab at the plain address**:
Connected, no authentication error and an available composer. The pilot was then
gracefully stopped and reopened once more; its credential, port and private link
remained exact, authenticated HTTP returned 200 and anonymous access 401. A reload
and another fresh plain-address tab again showed Connected and an available
composer. These GUI checks used IAB against the actual installed pilot, not a
synthetic Host. The normal default Chromium launcher succeeded too; its UI is
not exposed to this session, so direct regular-browser UI acceptance is not claimed.

The existing package also has its earlier isolated whole-browser restart proof.
Full Linux SDK now succeeds at **ed603cec**
([Linux SDK job](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/39108195214/job/117618496431));
Mac's shared-memory fixture failed and Windows was cancelled, so this is no
whole-matrix or later-platform acceptance. Recompute any future combined cold
plan from registry 23 and the distinct main/pilot builds; registry 22 plans below
are historical. [Installed evidence](../release/harness-pilot-browser-opening-installed-20261019.json).

## Opening other profiles and historical qualification

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
