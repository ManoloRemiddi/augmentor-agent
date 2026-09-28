<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Historical Windows implementation checkpoints through 805664f

These dated working checkpoints preserve the earlier evidence and investigations.
Their pending/current statements are historical. Start with the
[current implementation status](WINDOWS-IMPLEMENTATION-STATUS.md).

## Former handoff checkpoints

Full `3c6d78b` x64 exposes two new qualification issues: the managed chat's
first read-only UI inspection times out after eight seconds, and the real Inno
package installs successfully but registers Inno's default versioned display name.
The installer now sets the stable AppVerName explicitly. Qualification records
read-only polling timeouts within its existing overall deadline and takes one
private Python stack sample in disposable UI-test launches; no Send/Enter/model
operation is retried. These corrections await native execution. Compiled two-window
preview and the native launcher lease checks passed in that same failed job.
The full installed repair/drain/removal test has not run past its initial name
assertion. Do not treat `3c6d78b` Windows qualification as passing.

All `3c6d78b` Linux source/installed-package/browser jobs, macOS feasibility,
fast native Windows and Inno handoff fixtures pass. The actual full Windows
application installer integration is still running and is not yet qualified.

Update journals now support independent completion after the caller has observed
installer exit, reverified the release pair/installed selection and passed a local
health callback. Completed records are durably archived; failed health, an
unmatched artifact pair or a pre-APPLY record cannot finish the attempt. Four
new local fault/preservation tests pass (16 combined coordinator/journal checks).
The installed Windows proof now checks every payload file and a real Qt launch
before archiving. Native execution of this completion path is pending. This does
not implement recovery from an unknown installer outcome or rollback.

The `3c6d78b` hosted Debian job now passes, including actual Chromium, the complete
Qt suite and first-run form/Pi checks with exit zero. This qualifies the earlier
Qt shutdown correction on the hosted runner; installed package jobs are finishing.

The [Windows feature ledger](FEATURE-MATRIX.md#windows-development-target--september-28)
now separates implemented/native-tested areas from the remaining parity gates.

Full native runtime at `f950a45` passes on **both x64 and ARM64** in
[36389905723](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36389905723),
plus the shared Mac Qt candidate. This qualifies the shared voice 0.1.19 pin with
actual managed DSH/voice startup, compiled desktop Send/Enter/history, observed
graph drain, exclusive access after drain, owner/service restart and compiled
browser commit. The provider is deterministic; physical audio/input and live
model quality are not claimed. The newer actual full-payload installer and
`WindowsApply` integration at `3c6d78b` are now running; those installed-package
checks have not yet passed.

The actual installed-app qualification now composes the shared coordinator with
`WindowsApply`: an independent Inno process, private authenticated handoff and
one-shot durable APPLY. The fixture starts an installed window and background
owner, drains their observed graph, retains the extracted Setup process across
coordinator exit, waits for its completion and relaunches installed binaries.
It repairs the identical retained artifact, so it does not establish N-to-N+1,
publisher trust, health-driven recovery or rollback. New native execution is
pending. Existing Inno handoff/final-access fixtures at `b006ebb` pass both CPUs
in [36390819194](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36390819194);
that result compiles the updated helper but does not execute the new app installer.

Current source builds an unsigned installer candidate from the actual staged
shared app with `scripts/package-windows.py`. It uses one app identity, stable
`current/Augmentor.exe`, bundled runtimes and a Start-menu shortcut. Native
startup/lifetime exclusion now supports fresh installation, identical-build
repair and removal. The remover copies its exact hash-bound helper to a temporary
location, retaining both gates while deleting installed binaries. Existing
redirected/hard-linked trees are refused; persistent data stays outside the
installer tree. Manual cross-build replacement is intentionally unavailable until
the coordinated update/recovery path is connected.

Three portable build-intake checks cover wrong CPU/public metadata, incomplete
payloads and source-link refusal. New full-payload installation, native Qt preview,
live-draft maintenance refusal, repair/relaunch, path refusal and uninstall/data
preservation assertions are scheduled on both native CPUs; execution is pending.
Qualification has compiled-in disposable paths and uses Server build 26100 only
for the hosted x64 runner; the normal candidate minimum remains Windows 11 25H2
build 26200. This is not signed/public delivery or ordinary-user/physical testing.
Login integration, browser-registration removal, product N-to-N+1, recovery and
rollback remain open alongside the feature ledger.

Current shared dependency is **Resonant Voice 0.1.19**, exact source
`7d0fd6d677ea4bbbca0183a6bb3a3d3f24a8147a`. Its native x64/ARM64 configuration and
maintenance checks pass in [36389214161](https://github.com/ManoloRemiddi/resonant-voice/actions/runs/36389214161),
and the packed archive passes disposable DSH install/compose/remove. This fixes
Windows ownership during automatic profile cloning/preferences. The shared lock
and complete package select this same archive on all OSs. Assembled native graph
drain/restart remains to be qualified with it; physical audio remains open.

At `9cc54b1`, [Inno final-access qualification](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36389318640)
and [fast Windows desktop](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36389318570)
pass both CPUs. Actual extracted Setup retains startup exclusion through
coordinator exit/crash, acquires final installation access and refuses an
additional lifetime holder. The fast run includes all 12 journal/coordinator
tests. These are controlled fixtures, not an installed customer update. Continue
product installer/backend wiring, independent recovery and the full feature ledger.
No Windows customer release or personal deployment is made.

The pending statuses below are historical checkpoints, superseded only by the
specific results recorded above.

Latest: shared update decision orchestration has five local fault-ordering tests
with real durable journals/admission (12 combined update tests pass). Backend/UI
wiring and independent recovery remain open. Full `2b1680d` x64 successfully
starts DSH and owned voice, then exposes an ownership failure after automatic
voice-profile cloning. The separate Resonant 0.1.19 candidate `7d0fd6d` corrects
that write path; 42 local tests and actual DSH fixture integration pass, while
native qualification is pending before repinning. `3394145` helper compilation
passes but Inno reports a Boolean type mismatch; current source corrects the
conversion. Earlier Inno journal qualification `1872e19` passes both CPUs. The
legacy rejected-Velopack fixture also hit a partial JSON read; read-only polling
now waits for completed fixture output. No customer installer has been released.

Current source adds [final installer access](WINDOWS-INSTALLER-DECISION.md#final-installation-access-after-coordinator-exit)
after observed coordinator exit, with an actual Inno additional-lifetime-holder
refusal case. Native compilation/execution is pending. Fast `1872e19` passes both
CPUs, including the seven durable-journal tests. Full `2b1680d` service/drain and
`1872e19` Inno journal qualification are still running. Continue full product
apply/recovery and feature parity; no customer package has been published.

Current addition: the shared [durable update record](LIFECYCLE.md#durable-update-record)
passes seven local crash/write/ordering/concurrency tests. Authenticated Inno
fixtures now record before and after APPLY; native execution is pending. Recovery,
archival, health/rollback and user-facing update integration remain open. The
voice startup correction at `2b1680d` passes the fast x64 job; ARM64 is finishing.
Its full service/drain qualification remains pending. Continue the complete app;
do not treat these mechanisms as a released installer.

The owner now authorizes autonomous implementation through the complete Windows
app; physical testing will follow when a Windows machine is connected. Work on
`feat/windows` in the canonical repository. Read the
[implementation evidence and remaining gates](WINDOWS-IMPLEMENTATION-STATUS.md).
W0/W1 have started with isolated baseline checks, hash-locked native x64/ARM64
runtime candidates and hosted qualification jobs. No Windows app or customer
release is complete. Preserve existing installations and unrelated open work.

Latest source: [observed dependency-order drain](LIFECYCLE.md#observed-dependency-order-drain)
now requires durable caller checkpoints, sends each commit once, retains exact
exit observations and checks complete Jobs before owner shutdown. Twelve local
reservation and three graph tests pass. New assembled window/DSH/voice/companion
drain and restart assertions await native execution; independent apply/recovery
and user-facing integration remain open. The Linux shutdown crash at `2bd7b67`
is reproduced and corrected by using the shell's creating Python thread for
dispatch; the complete local suite passes 645 assertions and exits zero. New
hosted execution is pending. Full `2bd7b67` x64 fails managed service startup;
the fixture now retains its previously discarded supervisor diagnostics and
adds a real free-loopback-port startup test. Do not treat that workflow as passing.
At `1bf1b78`, compiled browser commit passes x64; ARM64 stops earlier at a
desktop snapshot comparison. The fixture now compares the prepared snapshot
and records expected/actual state; corrected native qualification is pending.

The new free-port check at `c1070b2` fails on both native CPUs: Windows times out
on a closed loopback TCP connection before returning refusal. Current source
replaces that probe with exclusive binding without listening, covering occupied
loopback/wildcard and non-listening sockets. Six local checks pass; native service
startup and the complete graph drain still need the corrected source qualified.

Source `2bd7b67` adds the [owned Windows voice bridge](LIFECYCLE.md#windows-owned-voice-bridge)
to the background owner and observed maintenance graph. Five local private-profile/
ownership tests and existing preparation/supervisor/launcher checks pass. Actual
native service ticket/refusal/commit/restart assertions await x64/ARM64 execution;
speech engines and physical audio remain open. Full runtime at `e63312b` now
passes both CPUs, including corrected assembled graph and screenshot assertions.
Continue global commit/apply, recovery and the remaining shared feature ledger.

Latest browser source, September 28: browser idle commit now rechecks all documents,
delivers its reply through the private owner, and drains the native host naturally.
Actual isolated Chromium proves observed owner exit, same-page reconnection and
draft/conversation preservation; all 265 Node/Browser and seven private-transport
tests pass locally. New compiled x64/ARM64 commit assertions await execution.
At `e63312b`, both fast desktop and authenticated installer fixture jobs pass;
its full assembled graph qualification is still running. Continue global commit,
owned voice and remaining parity, installer recovery/rollback and release gates.
Existing personal installations and public downloads remain unchanged.

The following September 28 checkpoints are historical; later results supersede
their pending/disabled statuses within the specific tested scope.

Current source, September 28: coordinated reversible Windows preparation now
holds startup exclusion, reserves the existing owner/surfaces/DSH/companions,
renews independently and cancels safely on busy or lost replies. Portable checks
pass; new actual-companion and assembled desktop/DSH graph tests await native
execution. The Inno extracted-Setup handoff proof at `0ca8348` passes both CPUs,
as do its fast Windows, Linux and Mac checks. Full owned-DSH `f08c4f0` passes x64;
ARM64 is finishing. Continue from the [evidence ledger](WINDOWS-IMPLEMENTATION-STATUS.md)
with native graph qualification, browser/voice participation and authenticated
installer commit/apply/recovery. No customer release is complete.

Subsequently, full `f08c4f0` runtime passes both CPUs, and `2ce8d32` passes both
fast native jobs with actual companion graph renewal/cancellation. Current source
adds [independent installer process ownership](WINDOWS-INSTALLER-DECISION.md#independent-installer-process-ownership)
and integrates it into the actual Inno handoff fixture. New native execution and
assembled desktop/DSH graph qualification remain pending. Continue authenticated
handoff and global commit/apply while preserving all remaining feature gates.

Current installer source adds authenticated private-pipe transfer into an embedded
Inno helper and separates readiness from apply authorization, with actual fixture
checks for cancellation and coordinator loss before/after authorization. Native
execution is pending. Earlier independent-process runs failed a missing pywin32
constant (`3748282`), then CreateProcess access denied (`bacf148`); current source
corrects process/thread access mapping and explicitly scopes the enclosing CI Job.
Production never silently retries a refused independent launch. Qualify these
changes before continuing global commit/apply; read the installer decision ledger.

Latest native result: `261d3c4` passes the full authenticated Inno/WinSparkle
fixture on both CPUs, including refusal/cancel/crash boundaries. Full `3748282`
x64 graph qualification exposed a fixture assumption about lazy companions;
the fixture now explicitly starts and observes both owned services. Its separate
screenshot timeout now has capture-specific timing/PNG assertions. Portable
checks pass; corrected native execution is pending. Continue global commit,
browser/voice participation, installer recovery/rollback and remaining app parity.

Earlier checkpoint notes below are historical; later evidence supersedes their
pending statuses without expanding physical/customer-installation claims.

Latest checkpoint, September 28: full native runtime `6d245a7` passes both CPUs
in [run 36374006218](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36374006218),
including compiled window discovery and the pre-Python lifetime lease. The later
DSH/Pi bridge drain at `264227a` passes fast desktop, installer-candidate,
Linux and Mac checks; full x64 passes and ARM64 is finishing. Shared browser page
reservation now has local real Chromium/native-frame evidence: all open documents
are counted, drafts/Settings refuse, cancellation restores input and lost
reservations expire. [The contract](LIFECYCLE.md#browser-page-reservation) explicitly
refuses commit until native browser discovery, launch fencing and the shutdown
handoff are implemented. The draft remains unmerged and no product is deployed.

Subsequently, `f079931` passes all hosted workflows, including full x64/ARM64
[qualification](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36375929935)
and the first real Chromium reservation proof in Linux CI. Current source adds
the [native browser participant](LIFECYCLE.md#native-browser-participant): private
control, actual host admission, Windows Job-verified relay registration and
retained kernel process discovery. Local Chromium now uses the product owner
control instead of a framing proxy; 257 Node/Browser, four private-transport and
five launcher policy checks pass. Compiled Windows execution of this addition
is pending. Global startup fencing, commit/installer handoff and the other full
app gates remain open. Keep the draft unmerged and existing installations intact.

At `df52b47`, compiled native browser control/discovery passes x64; full ARM64
is still running. Both fast Windows jobs, installer feasibility and Linux/macOS
pass. Current source adds the [startup reader/writer fence](WINDOWS-SHELL.md#short-lived-startup-exclusion)
and readiness release in desktop, browser and supervisor, plus a native handle
inheritance proof across coordinator exit/crash. Local registration and policy
checks pass; new kernel/compiled execution is pending. Continue the complete
coordinator and independent installer handoff after qualifying this primitive.
Browser commit and public installer delivery remain disabled.

Latest: full `df52b47` qualification now passes both CPUs. Both fast Windows jobs
at `e4593b1` pass compiled startup exclusion/readiness and inherited-handle
preservation across coordinator exit/crash. Its Linux Chromium failure was
reproduced as a qualification-only shared-owner race during initial harness
switching. Current proof creates one actual private owner per native host and
adds explicit simultaneous-host/normal-exit coverage. Source also adds retained
background-owner discovery and exact component Job/executable checks after owner
reservation; new native execution is pending. Continue component transport
identity, global coordinator and independent installer apply. Keep the draft
unmerged and all public-release, feature-parity and physical test gates open.

Full `e4593b1` runtime now passes both CPUs, including assembled startup readiness.
The per-host Chromium proof and owner discovery are pushed at `3a379a2`; jobs are
running. Current source adds prompt/memory participant transport identity and
bounded idle acknowledgment checks. Native actual-companion prepare/renew/cancel
assertions are added but await execution. Next are owned DSH/voice transport
identity and the complete coordinator/apply transaction; no public installer or
browser commit is enabled.

Both fast Windows jobs at `3a379a2` pass owner discovery/Job checks. The prompt/
memory participant transport is pushed at `6531e2d` for native execution. Current
source adds [observed loopback HTTP](WINDOWS-SHELL.md#observed-local-http), binding
an established socket to its kernel peer before tokens and refusing replacement
processes. New native HTTP tests are pending; follow with DSH/voice adapters and
coordinator/apply integration. No customer installer or website change is made.

Both fast jobs at `6531e2d` now pass actual prompt/memory participant reservation.
Current source additionally integrates managed DSH profile/anchor/version/home
checks with the observed HTTP transport. Its assembled maintenance/restart proof
uses this client and retains the server process through normal exit. New native
HTTP and DSH execution is pending. Voice still needs an owned Windows service
and speech provisioning; do not assume it belongs to the DSH Job merely because
the plugin is installed. Continue global reservation, commit/apply and rollback.

At `f08c4f0`, both fast Windows jobs pass the real TCP ownership tests; full DSH
integration is running. Full `3a379a2` runtime and Linux/Mac `6531e2d` regressions
pass. Current source extends the Inno fixture to explicitly duplicate the startup
writer into the actual extracted Setup process and preserve it after coordinator
exit/crash. This is a pending native mechanism proof, with intentionally
fixture-only PID/handle arguments. Do not promote that unauthenticated interface
into production; installer identity, artifact binding and recovery still need
the real transaction protocol. Browser commit remains disabled.

Current Windows worktree: `feat/windows` in an isolated canonical-repository
checkout; draft [PR #20](https://github.com/ManoloRemiddi/augmentor-agent/pull/20).
At `523fe9a`, real hosted x64/ARM64 runtime and disposable two-version installer
lifecycle probes pass, as do candidate Mac Qt behavior checks. The full Windows
job still failed DSH metadata decoding; later source corrects UTF-8 handling.
W2 adds process leases, Windows private paths/token identity and an isolated
named-pipe adapter, with continuing native CI. Read the status ledger for exact
ref/evidence boundaries and outstanding service, setup, UI, browser, update and
public-release work. The owner will connect physical Windows hardware later;
keep building independently while that is pending. No installed personal app,
model endpoint, speech placement or website download has been changed.

Later W2/W3 source adopts shared prompt/memory transport, protected file records,
Windows Job containment and one initial DSH supervisor. Managed first-run setup
is shared with Mac while LaunchAgent ownership stays in the Mac entrypoint.
Actual Windows Qt fonts and Python/Node prompt persistence pass on both CPUs;
the prepared DSH terminal passes natural shutdown at `635d0a9` on x64, and Job
crash containment passes on both CPUs at `89e8a84`. New staged-application DSH
conversation/restart checks are being introduced. Keep the detailed ledger and
latest CI authoritative; no Windows customer installation or release is complete.

The current shared first-run UI also selects the Windows runtime owner. DSH
startup exposed a voice token Unix-permission check; a separately versioned
Resonant Voice 0.1.17 candidate has passed native ACL tests on both CPUs and is
now in the shared graph. Full DSH conversation/restart qualification remains
pending. Follow the evidence ledger rather than inferring completion from the
dependency tests.

At `79d9efc`, native x64/ARM64 source-preview window control passes. At
`e9467ff`, the assembled x64 DSH runtime passes setup, deterministic-model chat,
Stop, actual history-writer exclusion and crash/restart history preservation.
The detailed ledger distinguishes the GitHub merge checkout from branch heads.
The next candidate adds the embedded `Augmentor.exe` entrypoint and direct binary
window tests; it is not yet a complete installer or public Windows build.

The full `e9467ff` runtime run subsequently passed on ARM64 as well. At `6cac5e5`,
x64 assembly, real DSH and cross-user kernel ACL probes pass, but the compiled
desktop preview fails its zoom assertion after launching both windows. Diagnostic
capture now retains the actual zoom response. The next source integrates the
two native shortcuts into the same supervisor's Qt event loop; see
[Windows shell ownership](WINDOWS-SHELL.md). Native hotkey/owner tests are pending.

Later native evidence supersedes those pending entries: both CPUs pass native
shortcut persistence, and at `840127f` the fixed prompt/memory owner contains both
real services after a deliberate fault. At `0a1d086`, compiled x64 zoom and native
resources also pass; ARM64 full runtime remains in progress. Current source routes
Windows Python/Node companion startup through that owner. The compiled actual
DSH composer/reopen proof, client ownership, browser integration, graceful global
Quit and production updating still need their remaining qualification. Consult
the detailed ledger for exact runs; source progress is not an installed release.

At `13c6c0d`, full Windows runtime qualification passes **both** native CPUs:
compiled preview zoom/resources, actual desktop Send/Enter/restored DSH history,
compiled browser host protocol, and Python/Node companion ownership. Shared
Linux and Mac workflows also pass at that ref. Browser source now shares the Mac
chooser and adds Windows preparation behind an installer-owned stable anchor;
native preparation/real-browser acceptance remains pending.

W1 is reopened after identifying stock Velopack's forced busy-uninstall behavior.
Read the [installer decision and alternative proof](WINDOWS-INSTALLER-DECISION.md):
The bounded native proof passes both CPUs, and Inno Setup 7.1.0 with WinSparkle
0.9.4 is now selected for implementation. Full product integration, signing,
rollback and client-machine gates remain. At `4f2f763`, full Windows runtime
qualification passes both CPUs, including prompt/memory maintenance admission
and the corrected browser staging ACL. New source adds actual DSH admission,
natural shutdown and corrected Cordis cleanup; local SDK/HTTP/CLI proof passes,
native execution is pending. Global coordination, voice/browser/desktop drain,
production installer and public release remain incomplete. Keep the detailed
ledger authoritative; do not change the website or merge the draft PR.

At `795a72b`, Linux/macOS, fast Windows desktop and installer-candidate workflows
pass. The full native Windows run finds a DSH token owner/ACL defect on both CPUs;
source now creates the token with the current user's explicit private descriptor.
Shared desktop reservation and normal committed close are also implemented, with
local Qt/regression and two-process evidence. Both changes await native execution.
Voice/browser participation and global coordination remain the next lifecycle
work; source or a component pass is not a finished Windows app.

At `187bee6`, both fast desktop jobs, Linux/macOS and installer-candidate checks
pass. The full x64 run finds a second bootstrap token writer; it is now unified
with the private helper and covered by a failure/retry check. The shared graph
also advances to Resonant Voice 0.1.18 (`7a6645e`): its maintenance/normal-exit and
private-configuration tests pass on both Windows CPUs. Full product integration,
owned voice startup, browser drain and global coordination remain pending. The
actual complete installer compose/restart proof passes locally with this archive.

The Windows supervisor and shell now share reversible startup admission, including
accepted shortcut work whose caller timed out. Existing children must drain
before the owner accepts commit, and its acknowledgment precedes normal exit.
Portable tests pass; native owner execution is pending. Continue with global
component discovery/coordination and browser participation, preserving the
remaining installer, feature-parity and physical acceptance gates.

Normal Windows status must also retain an exited leader's Job until all its
descendants exit. Source now queries the kernel active-process count and exposes
a non-terminating graceful wait. The earlier status path closed the Job after
leader exit and could kill a straggler. Portable owner tests pass; new native
detached-child tests are pending. Keep this boundary separate from deliberate
fault containment and failed-setup cleanup.

Full runtime `e7228e5` now passes both native CPUs, qualifying both bootstrap
token paths, compiled desktop/DSH maintenance and the voice 0.1.18 bundle. Fast
desktop `303a619` passes both CPUs including owner reservation and full Job drain;
its full runtime run remains pending. New source adds held-instance discovery
with authenticated pipe peers, retained process handles and executable/build
checks. Its portable proof passes; native source/compiled assertions are pending.
Continue browser/companion coordination and early native startup exclusion before
claiming global Quit or safe production installation. Preserve the draft PR and
all remaining installer, feature-parity and physical acceptance gates.

Source-window discovery passes both native fast jobs at `dc41a56`. New source
closes the early native-entrypoint gap by acquiring a private lifetime lease
before Python loads. Actual compiled positive/negative probes are added to the
fast Windows workflow and full assembled window proof; execution is pending.
The historical installer fixture stays distinct, and complete coordinated
installation is still required. See the shell guide for the exact new boundary.

Current shared browser source drains accepted parent operations on disconnect,
sends EOF to its selected bridge and waits for actual child close. Voice retains
busy state through retiring workers and accepted operations; no ordinary
two-second worker kill remains. Thirteen focused Node/DOM checks pass, including
actual process natural-exit observations. DSH/Pi bridge admission, extension
panel/reconnect reservation and global coordination are still pending. No
installed browser or private audio configuration changed.

Full runtime `303a619` now passes both native CPUs. Compiled early-startup lease
qualification passes both fast desktop jobs at `bfde231`; its full assembled
integration is pending. Current browser source extends natural draining into
both DSH/Pi bridges, suppresses reconnect after EOF and makes the Windows wrapper
wait for every Job descendant. Four real-process portable checks observe natural
exit after accepted work; real compiled connected-browser integration remains
pending. Continue extension reservation/global coordination and installer work.

## Former implementation status checkpoints

Full `3c6d78b` x64 exposes two new qualification issues: the managed chat's
first read-only UI inspection times out after eight seconds, and the real Inno
package installs successfully but registers Inno's default versioned display name.
The installer now sets the stable AppVerName explicitly. Qualification records
read-only polling timeouts within its existing overall deadline and takes one
private Python stack sample in disposable UI-test launches; no Send/Enter/model
operation is retried. These corrections await native execution. Compiled two-window
preview and the native launcher lease checks passed in that same failed job.
The full installed repair/drain/removal test has not run past its initial name
assertion. Do not treat `3c6d78b` Windows qualification as passing.

All `3c6d78b` Linux source/installed-package/browser jobs, macOS feasibility,
fast native Windows and Inno handoff fixtures pass. The actual full Windows
application installer integration is still running and is not yet qualified.

Update journals now support independent completion after the caller has observed
installer exit, reverified the release pair/installed selection and passed a local
health callback. Completed records are durably archived; failed health, an
unmatched artifact pair or a pre-APPLY record cannot finish the attempt. Four
new local fault/preservation tests pass (16 combined coordinator/journal checks).
The installed Windows proof now checks every payload file and a real Qt launch
before archiving. Native execution of this completion path is pending. This does
not implement recovery from an unknown installer outcome or rollback.

Full native runtime at `f950a45` passes on **both x64 and ARM64** in
[36389905723](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36389905723),
plus the shared Mac Qt candidate. This qualifies the shared voice 0.1.19 pin with
actual managed DSH/voice startup, compiled desktop Send/Enter/history, observed
graph drain, exclusive access after drain, owner/service restart and compiled
browser commit. The provider is deterministic; physical audio/input and live
model quality are not claimed. The newer actual full-payload installer and
`WindowsApply` integration at `3c6d78b` are now running; those installed-package
checks have not yet passed.

The actual installed-app qualification now composes the shared coordinator with
`WindowsApply`: an independent Inno process, private authenticated handoff and
one-shot durable APPLY. The fixture starts an installed window and background
owner, drains their observed graph, retains the extracted Setup process across
coordinator exit, waits for its completion and relaunches installed binaries.
It repairs the identical retained artifact, so it does not establish N-to-N+1,
publisher trust, health-driven recovery or rollback. New native execution is
pending. Existing Inno handoff/final-access fixtures at `b006ebb` pass both CPUs
in [36390819194](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36390819194);
that result compiles the updated helper but does not execute the new app installer.

Current source builds an unsigned installer candidate from the actual staged
shared app with `scripts/package-windows.py`. It uses one app identity, stable
`current/Augmentor.exe`, bundled runtimes and a Start-menu shortcut. Native
startup/lifetime exclusion now supports fresh installation, identical-build
repair and removal. The remover copies its exact hash-bound helper to a temporary
location, retaining both gates while deleting installed binaries. Existing
redirected/hard-linked trees are refused; persistent data stays outside the
installer tree. Manual cross-build replacement is intentionally unavailable until
the coordinated update/recovery path is connected.

Three portable build-intake checks cover wrong CPU/public metadata, incomplete
payloads and source-link refusal. New full-payload installation, native Qt preview,
live-draft maintenance refusal, repair/relaunch, path refusal and uninstall/data
preservation assertions are scheduled on both native CPUs; execution is pending.
Qualification has compiled-in disposable paths and uses Server build 26100 only
for the hosted x64 runner; the normal candidate minimum remains Windows 11 25H2
build 26200. This is not signed/public delivery or ordinary-user/physical testing.
Login integration, browser-registration removal, product N-to-N+1, recovery and
rollback remain open alongside the feature ledger.

Current shared dependency is **Resonant Voice 0.1.19**, exact source
`7d0fd6d677ea4bbbca0183a6bb3a3d3f24a8147a`. Its native x64/ARM64 configuration and
maintenance checks pass in [36389214161](https://github.com/ManoloRemiddi/resonant-voice/actions/runs/36389214161),
and the packed archive passes disposable DSH install/compose/remove. This fixes
Windows ownership during automatic profile cloning/preferences. The shared lock
and complete package select this same archive on all OSs. Assembled native graph
drain/restart remains to be qualified with it; physical audio remains open.

At `9cc54b1`, [Inno final-access qualification](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36389318640)
and [fast Windows desktop](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36389318570)
pass both CPUs. Actual extracted Setup retains startup exclusion through
coordinator exit/crash, acquires final installation access and refuses an
additional lifetime holder. The fast run includes all 12 journal/coordinator
tests. These are controlled fixtures, not an installed customer update. Continue
product installer/backend wiring, independent recovery and the full feature ledger.
No Windows customer release or personal deployment is made.

The pending statuses below are historical checkpoints, superseded only by the
specific results recorded above.

Current source adds shared update decision orchestration: five local tests with
real journal writes/admission pass (12 combined journal/coordinator checks).
`2b1680d` full x64 confirms managed DSH and owned voice startup, then refuses a
voice config whose Windows owner changed during automatic profile cloning.
Resonant 0.1.19 candidate `7d0fd6d` corrects that separate package; native checks
must pass before Augmentor repins it. The `3394145` native helper compiles on both
CPUs; Inno's Boolean/BOOL type mismatch is corrected in source and awaits execution.
Earlier [Inno journal qualification](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36388207448)
passes both CPUs. Full graph drain, installed update and recovery remain open.

Fast native [`1872e19`](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36388207564)
passes both CPUs, including all seven private-journal crash/write tests. Current
source adds final Setup access after actual coordinator exit and refusal while an
additional lifetime holder remains. New helper compilation/Inno execution is
pending; full owned-voice/graph drain and the earlier Inno journal additions are
still being qualified. See [final access contract](WINDOWS-INSTALLER-DECISION.md#final-installation-access-after-coordinator-exit).

The shared [durable update record](LIFECYCLE.md#durable-update-record) now has seven
passing local tests, including actual process crash and exclusive writer claims.
New native fast tests and authenticated Inno before/after-APPLY journal assertions
await execution. This does not implement automatic recovery/rollback or installed
N-to-N+1 application. The port correction at `2b1680d` passes fast x64; ARM64 and
the actual owned-service/drain integration are still being qualified.

Current correction: both native CPUs reproduce the free-loopback-port timeout in
[`c1070b2` desktop qualification](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36387350489).
The voice startup probe now uses exclusive wildcard binding without listening;
it cannot mistake a short connect timeout for an unavailable port or contact an
external service. Six local tests pass, including occupied wildcard and
bound-but-not-listening sockets. Native corrected startup/drain remains pending.

September 27, 2026. The owner authorized autonomous implementation and will
connect a Windows machine for joint physical testing afterward. Follow the full
[implementation plan](WINDOWS-IMPLEMENTATION-PLAN.md); this ledger does not narrow
its outcome. No Windows customer release or installed-product claim exists yet.

Latest source, September 28: explicit graph drain requires durable caller
checkpoints and observed exits, renews remaining participants, and checks complete
Jobs before owner shutdown. Twelve local reservation and three graph tests pass.
The assembled window/DSH/voice/companion drain, exclusive-lease and restart proof
awaits native execution; installer application and recovery remain unfinished.
Linux [`2bd7b67`](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36385346967)
passes all 647 native assertions but exits 139 during Qt interpreter shutdown.
The actual Chromium commit/reconnect step passed before that failure. Local
isolation and GDB traced the shutdown failure to the shell's temporary Qt thread
wrappers. The corrected creating-thread dispatch passes all 645 local assertions
and exits zero; hosted qualification is pending. See [thread dispatch evidence](WINDOWS-SHELL.md#keyboard-ownership).
The failed workflow is not waived. The new free-loopback-port startup test also
passes locally (six voice ownership checks total).

Full `2bd7b67` x64 fails inside managed service startup, before voice integration
qualification. The fixture now writes its previously discarded supervisor output
to a private log and includes bounded diagnostics on failure. The earlier
`1bf1b78` compiled browser commit passes x64; ARM64 stops earlier at a native
transcript snapshot comparison. The updated fixture compares the snapshot taken
inside the prepared admission fence and includes expected/actual values on
failure. Both corrections require new native execution.

Source `2bd7b67`, September 28: managed DSH now starts its bundled Resonant loopback
bridge through the existing owner, with one retained Job, private profile and
occupied-port refusal. Kernel-bound voice maintenance joins graph preparation.
Five local profile/ownership refusal tests, two graph failure tests, six portable
owner tests and five launcher tests pass (two native owner tests skip on Linux).
Assembled real-service graph/ticket/commit/restart assertions are added; native
execution is pending. This does not qualify Windows ASR/TTS engines or audio.
Full runtime at [`e63312b`](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36383783733)
now passes both CPUs, including corrected graph and capture assertions.

Latest browser checkpoint, September 28: idle browser commit rechecks context inventory
and page state, replies through its private owner, then drains the native host
naturally. Actual local Chromium verifies retained-process exit, same-page
reconnection, a post-commit draft and selected conversation preservation. All
265 Node/Browser and seven private-transport tests pass. New compiled Windows
commit assertions await execution; this is not an installed-version upgrade.
At `e63312b`, [fast desktop](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36383783782)
and [authenticated installer fixture](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36383783743)
pass both CPUs. Its [full graph qualification](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36383783733)
also passes both CPUs. Global commit/apply, owned voice, remaining platform features,
recovery/rollback, physical hardware and customer release gates remain open.

The following checkpoints are chronological history, not the latest capability
status; subsequent evidence supersedes pending/disabled statements only within
its stated scope.

Earlier checkpoint: full runtime passes both CPUs at `f079931`, including the
corrected bootstrap token, actual compiled desktop/DSH maintenance, background
owner reservation, complete Windows Job drain, kernel-verified window discovery
and the pre-Python native lifetime lease.
The separate voice 0.1.18 candidate passes native configuration and maintenance
on both CPUs.
Browser source drains accepted parent and DSH/Pi bridge operations and reserves
all open extension documents. Linux/Mac and all hosted Windows workflows pass at
`f079931`. New source adds the actual private native browser owner, correlated
admission and kernel-based Windows discovery. Local real Chromium, transport and
regression checks pass; compiled native execution is pending. Commit remains
disabled. The lifetime lease is not the short-lived global startup fence.
Installer backend is **Inno Setup/WinSparkle**; earlier Velopack
candidate entries below are historical. Global coordination and full app release
are not complete.

The native browser-owner change at `df52b47` passes compiled x64 qualification,
both fast Windows desktop jobs, installer feasibility, Linux (including actual
Chromium through product private control), and macOS. Full ARM64 qualification
is still running in [36377424868](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36377424868).
Current source adds [short-lived startup exclusion](WINDOWS-SHELL.md#short-lived-startup-exclusion)
before Python loads, releases it only after discoverable controls are ready, and
adds real-Windows duplicated-handle transfer tests. Portable browser registration,
supervisor policy and launcher policy checks pass. These new kernel/compiled
assertions await native execution. No installer apply or browser commit is enabled.

Subsequently, all workflows pass at `df52b47`, including full x64/ARM64 in
[36377424868](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36377424868).
The new startup fence at `e4593b1` passes [both fast Windows jobs](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36378514808),
including actual compiled launchers and inherited-gate preservation across exit
and crash. Full runtime execution is still running. Its Linux Chromium proof
exposed a qualification-owner race: initial DSH and replacement Pi native hosts
shared one test endpoint. Current qualification uses a separate actual private
owner per native host, matching Windows, and adds simultaneous-host registration
and normal-exit evidence. The product's Windows owner was already per process.
Current source also adds retained background-owner discovery and read-only
component Job verification; its new native assertions await execution. Global
coordination, component transports and installer apply remain unfinished.

Full native runtime `e4593b1` subsequently passes both CPUs in
[36378514796](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36378514796),
including actual assembled desktop/browser startup readiness. `3a379a2` contains
the corrected per-host Chromium qualification and background-owner observation;
its hosted jobs are running. Current source additionally binds prompt/memory
maintenance to their retained pipe peers and owner Jobs, validates idle/expiry
acknowledgments, and extends native companion reservation tests. Portable policy
checks pass; new native companion execution remains pending.

Both fast Windows jobs at `3a379a2` pass retained background-owner discovery and
exact prompt/memory Job observations in
[36379432569](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36379432569).
The companion participant client is pushed at `6531e2d` and awaits native execution.
Current source adds established-connection TCP ownership checks before local
HTTP credentials, retained process identity and replacement-port refusal. Syntax
checks pass; new real-Windows HTTP assertions are pending. DSH/voice profile
adapters, the complete coordinator and installer application remain open.

The actual prompt/memory participant assertions at `6531e2d` now pass both fast
Windows jobs in [36379716570](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36379716570).
Current source connects the observed HTTP transport to the private managed DSH
profile, verifying the service anchor, product version and home identity. The
full DSH maintenance/restart proof now uses this client and checks its retained
process exits with the complete Job. These new HTTP/DSH assertions await native
execution; owned voice startup/provisioning and global coordination remain open.

At `f08c4f0`, both [fast Windows jobs](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36380441839)
pass the actual TCP-peer/credential-refusal/reused-port tests. Its full owned-DSH
integration is running. Full runtime `3a379a2` now passes both CPUs in
[36379432589](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36379432589).
Linux and Mac regressions pass at `6531e2d`, including the corrected Chromium
proof. Current installer qualification adds gate transfer into Inno's actual
extracted Setup process and checks retention across coordinator exit/crash.
Native execution of this new Inno case is pending; production handoff identity,
coordinated apply, health and rollback remain open.

At `0ca8348`, the actual extracted Inno Setup gate-transfer proof passes both
CPUs in [36380756992](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36380756992),
including normal coordinator exit/crash and invalid-transfer refusal before
version change. Both fast Windows jobs and Linux/Mac workflows also pass. At
`f08c4f0`, full x64 managed DSH integration passes; ARM64 is still running.

Current source adds [coordinated reversible preparation](LIFECYCLE.md#coordinated-reversible-preparation)
with independent renewals, conservative expiry, single cancellation after lost
acknowledgments, and startup exclusion retained through cleanup. Six reservation,
two graph failure and four admission checks pass locally; six portable owner
checks pass with two Windows-only cases skipped. Actual companion group and
assembled desktop/DSH graph assertions are added and await hosted execution.
This is preparation/cancellation only: no product commit, installer apply,
voice provisioning, rollback or release gate is waived.

At `f08c4f0`, [full native runtime](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36380441902)
now passes both CPUs, including managed DSH's observed HTTP participant and
normal shutdown/history restart. At `2ce8d32`, [both fast Windows jobs](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36381768755)
pass real prompt/memory group preparation, renewal, startup exclusion and
cancellation. The assembled desktop/DSH graph additions await the full run.

Current source adds a non-killing installer observation Job, suspended assignment
and read-only artifact binding to the verified digest. The real Inno handoff
fixture now launches through this adapter and verifies extracted-Setup ownership,
wrong digest/unrelated PID refusal and retained gate across normal exit/crash.
Syntax checks pass; native execution is pending. This is not yet authenticated
installer IPC or a complete update transaction.

## Historical checkpoint before atomic fixture publication

## Windows implementation — active, September 28

Current source adds byte-verified removal of owned browser registrations, retaining
persistent data and preserving edited/foreign manifests. Browser setup records its
manifest digest before publishing registry pointers. The native remover pins the
private file while hashing and comparing it, without loading application Python.
New native manifest-retention and full installed browser-removal tests are pending.

Actual native registry fixtures at `2f17cb0` [pass both CPUs](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36397149278):
typed exact-value creation/removal, wrong-type/content refusal, unrelated-value
preservation and rejection without the installation gate. Actual installer startup
and browser-anchor integration still needs its full-payload run.

Full x64 `ead355c` now observes correct installed preview exit, then fails same-build
repair at native tree validation. Its installation log contains 205 ordinary paths
longer than 260 characters (maximum 283); source validation lacked extended paths.
Current source uses explicit extended local paths and deletion-compatible read-only
attribute inspection. A new actual Inno fixture exercises a deeper-than-260 payload
and requires it to pass. This correction and later full repair/apply/removal stages
await native execution; no passing full installer/update claim is made.

The owner authorizes autonomous implementation through the complete Windows app;
physical testing follows when a Windows machine is connected. Work on
`feat/windows` in [draft PR 20](https://github.com/ManoloRemiddi/augmentor-agent/pull/20).
Do not merge, publish customer downloads or deploy personal installations.
Keep one shared product, approved UI and existing model/voice settings. Native
Windows x64 and ARM64 are targets, including NVIDIA RTX Spark N1X; no RTX hardware
qualification is claimed.

Latest implementation: the actual installed x64 candidate at `594b56d` now passes
payload/name/shortcut validation, native preview launch, and busy repair/removal
refusal with its live draft intact. It then exposes a shared preview close defect:
legacy maintenance acknowledges closing, but the controller-free Qt process stays
alive. Current source explicitly exits after replying and rechecking idle state.
An actual two-process portable proof fails before the correction and passes after;
all four desktop maintenance and 28 window tests pass. Fast native `ead355c`
[passes both CPUs](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36396146636),
including observed normal exit from the corrected idle preview. Full installed
execution is still required before
claiming installed repair, coordinated apply/health/archive or removal success.

[Signed WinSparkle delivery](WINDOWS-UPDATE-DELIVERY.md) at `594b56d` passes
[both native CPUs](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36394998456):
valid signed ZIP delivery and refusal of wrong-CPU metadata, invalid metadata
signatures and replaced installers despite a valid outer signature. Fast native
checks at [594b56d](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36394998226)
and [98891c1](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36395166214)
pass both CPUs, including all 27 crypto/private-file/journal/coordinator tests.
[98891c1 Inno/WinSparkle fixtures](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36395166226)
also pass both CPUs. These are ephemeral signing fixtures, not customer trust or
an installed N-to-N+1 update. Current staging bundles native WinSparkle 0.9.4 and
notices, removing the rejected Velopack dependency; full payload DLL/import
qualification remains pending. No customer key/feed or automatic updater is enabled.

Assembled DSH/voice, desktop Send/Enter/history, observed graph shutdown/restart and
compiled browser commit pass on both CPUs at `f950a45` and `805664f`.
[Full f950a45](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36389905723)
is the last fully passing workflow before the actual installer step was added.
[805664f](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36392632237)
stops at the since-corrected shortcut argument assertion on both CPUs.
[Full 594b56d](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36394998252)
is failing on the preview-close issue above; ARM64 is still running. Tests use
real bundled DSH and a deterministic provider, not physical audio/input or live
model quality. Shared Resonant Voice is 0.1.19 from qualified source `7d0fd6d`,
kept in separate [draft PR 2](https://github.com/ManoloRemiddi/resonant-voice/pull/2).
[Linux at 805664f](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36392632260)
and [macOS](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36392632178)
pass; later full platform checks continue in CI.

Next: finish full-payload install, live-work refusal, repair, coordinated apply,
independent health/archive and removal on both CPUs. Connect verified delivery to
customer notification/UI and the coordinator; qualify actual N-to-N+1 and independent
recovery/rollback. Complete the [feature ledger](FEATURE-MATRIX.md#windows-development-target--september-28),
including login/browser cleanup, desktop actions, speech/memory provisioning,
Home/Pi parity, ordinary-user Windows and physical hardware. The app is not complete
or ready for customer distribution.

Read [implementation status](WINDOWS-IMPLEMENTATION-STATUS.md),
[installer decision](WINDOWS-INSTALLER-DECISION.md), and
[the implementation plan](WINDOWS-IMPLEMENTATION-PLAN.md). Earlier checkpoints,
including superseded pending results, are preserved in the
[historical archive](WINDOWS-IMPLEMENTATION-CHECKPOINTS-2026-09-28.md).
