<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Start here: agent handoff

## Application SDK alignment source — October 3

[SDK alignment](SDK-ALIGNMENT.md) owns the paired preview 4 candidate, feature
states, shared-settings boundaries, Codex role/tools/session/memory isolation,
platform bootstrap/private files and per-OS startup adapters. Source and fixture
qualification do not deploy the live YouTube/Sponsor apps or certify a fresh
Mac/Windows SDK install. Hosted platform/paired-package checks and installed
acceptance remain distinct. Preserve the owner's dirty canonical checkout and
independent third-app test.




## Windows 0.2.13 public preview — release record, October 2

Windows support is merged in [PR 20](https://github.com/ManoloRemiddi/augmentor-agent/pull/20),
main merge `9baf711440c104d645494b07758c7c1e8ef125a2`.
[The public preview](https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.13-windows-preview.1)
contains native x64/ARM64 installers, SHA256SUMS, a simple guide and per-architecture
package/health reports. Both architectures pass the [public build](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37064707283)
at exact source `f8afb844e8073e2f36674e8684094d95155a14e2` (the reviewed PR head).
Each complete payload is verified before and after actual public-launcher rendering
with native Windows Qt, readable fonts and 424×484 UI output. Installer packages
use ordinary per-user folders and no compiled development qualification switches.
The public x64 Setup is not installed on the hosted Server build runner, whose
OS is below the advertised Windows 11 25H2 minimum. Earlier development-candidate
installation/recovery evidence remains separately scoped below.


Installer digests verified locally and against GitHub's stored-asset digest:

- x64: 363,568,540 bytes, SHA256 `fef5902c5fd7222fe4f59c2777e5b8ae7bb0cab80d2e5edf736bf75e83d3e7cd`.
- ARM64: 331,549,976 bytes, SHA256 `b5b2c8a79987c44bc4da10b1893bc9459af5797d96deef18fa0e2f7d20867e5d`.

The owner explicitly chooses first physical installation through this public
download and subsequent feedback. No physical Windows, RTX Spark or every-provider
acceptance is claimed. This is unsigned preview delivery, not signed/stable
qualification. Automatic updates, cross-version upgrades, full local voice/memory,
desktop automation and Windows Pi/Codex remain pending; Handy is not bundled.
[The preview guide](WINDOWS-PREVIEW.md) is the current installation/update/removal
contract. Linux/Mac installed applications and their existing release assets have
not been replaced by this Windows publication.


## Windows public preview — October 2, current direction

The owner explicitly authorizes merging and publishing the Windows preview now,
then installing the public download on a physical PC to provide feedback. They do
not have a remotely accessible Windows test machine and waive that prerequisite.
This supersedes the September 28 draft-only/publication restriction below.
[Public installation guide and limits](WINDOWS-PREVIEW.md) own the current delivery
scope. Windows 11 25H2+, native x64/ARM64, unsigned preview, DSH setup/chat and manual
Chromium extension installation. Automatic updates, cross-version manual upgrades,
local voice/memory engines, desktop automation and Windows Pi/Codex are unqualified.
No physical Windows or RTX Spark acceptance is claimed.

Latest completed development evidence at `14f7e57`, merge checkout
`cede6c752b2aed964bf93136e655ea78adee266c`:
[full Windows application](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36438724509)
and [native installer](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36438724443)
pass both native CPUs; shared Mac Qt also passes. Downloaded full reports confirm
independent source restoration/completion and actual native UI reopening, with no
inventory differences (x64 65,946 files; ARM64 65,930). These reports concern 0.2.12
development candidates, deterministic provider chat and same-build updates, not
this new public distribution profile, real-provider acceptance or N-to-N+1 updates.
The public build integrates current 0.2.13 main including the Handy shared controls;
the Windows preview does not bundle Handy and avoids starting its unavailable companion.
Delivery uses the reviewed merged source and records fresh native
rendering, sealed inventory and installer digests separately.

### Historical September 28 implementation record


## Windows implementation — active, September 28

The owner authorizes autonomous implementation through the complete Windows app;
physical testing follows when a Windows machine is connected. Work on
`feat/windows` in [draft PR 20](https://github.com/ManoloRemiddi/augmentor-agent/pull/20).
Do not merge, publish customer downloads or deploy personal installations.
Keep one shared product, approved UI and existing model/voice settings. Native
Windows x64 and ARM64 are targets, including NVIDIA RTX Spark N1X; no RTX hardware
qualification is claimed. The app is not complete or ready for customers.

### Current evidence

- [Full e98a142 qualification](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36432080543)
  passes both CPUs and shared Mac Qt at merge checkout
  `521151e33204421421981be0f1f35742bb1c688b`. Downloaded installed reports confirm
  actual full-payload displacement before authenticated replacement, independent
  installer health rendering the real Windows UI with the pending record preserved,
  installation/browser/login identity, busy-draft refusal, damaged-runtime repair,
  coordinated same-build apply, verified reopening and removal with data retained.
  Inventories have zero differences: x64 65,943 files / 1,266,306,830 bytes; ARM64
  65,927 files / 1,245,008,845 bytes. DSH chat/history uses a deterministic provider.
  This predates source restoration/completion and is not N-to-N+1 or physical acceptance.
- [Fast Windows at 5277087](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36434815432)
  passes both CPUs, including native UI health, compiled guards and all 62 update
  cases with thirteen distinct-restoration cases. Current active-record pinning
  during completion and the independent observer below postdate this evidence.
- [Inno at 04f3317](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36433486621)
  passes both CPUs at merge checkout `abf36a2cf01fb7c71b2604ae3e72a53c1d64f617`.
  Downloaded reports confirm standalone exact-source application without installed
  launcher/Python/metadata, source lookup despite changed selection, busy/wrong-source
  refusals, old payload preservation, restored repair metadata and synthetic health
  with the original update unchanged. These exact-template tests use real private
  Python/native bootstrap and inert other components; they do not render Qt.
  [Inno at 5277087](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36434815332)
  also passes both CPUs. New extracted observer execution remains pending.

- Full `5277087` x64 source restoration/completion now passes in
  [36434815454](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36434815454),
  merge checkout `c57a5c7492cf0f338e8e59df7f11a07b9e0fdb9e`. Downloaded evidence confirms
  actual standalone source installation, exact original archival, distinct outcome,
  real Windows UI health and reopening. ARM64 is still running. This revision uses
  fixture orchestration and predates the extracted product observer at `9005784`.
- [Fast Windows at 9005784](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36437964535)
  passes both CPUs, including health-time active-record pinning. Its native installer
  observer and full application workflows are running/pending; no observer pass is claimed.

### Implemented contracts and current work

The retained original installer and its durable private selection identify the
exact source bytes. Registered repair needs no installed executable/runtime and
refuses unresolved updates or a foreign source. These raw receipts are not
publisher trust or proof of health. Separate signed-bundle verification supports
an exact recorded recovery artifact after delivery expiry; no customer key/feed
or updater UI is enabled.

Ordinary native desktop/browser startup blocks an unresolved journal before Python
loads. A fixed health action renders the shared UI in a temporary private profile
without conversations or companion startup; an independent observer checks its
release identity and owned process exit. Full payload verification and health are
required before journal completion. Confirmed live reversible preparation can
archive cancellation before any shutdown; uncertain cleanup/write/APPLY retains
its unresolved record. See [lifecycle](LIFECYCLE.md#confirmed-cancellation-before-shutdown).

Windows staging seals every packaged file/directory into an inventory bound by
release metadata. Intake refuses changed stages rather than resealing. The shared
inspector accepts independently supplied metadata, allowing missing/corrupt installed
metadata to be detected. Windows uses full no-follow stat and explicit birth time
across path/handle APIs; handle-to-handle change time remains checked. See
[payload inspection](WINDOWS-UPDATE-DELIVERY.md#exact-installed-payload-inspection).

The [independent installer inspector](WINDOWS-INSTALLER-DECISION.md#independent-installer-inspection-before-recovery)
extracts its own Python/shared inspector into fresh protected scratch, checks its
compiled release digest and runs a bounded read-only worker under native exclusive
maintenance admission. It reports counts without clearing a journal, applying,
selecting or repairing a build. Recovery files are packed first in extraction
order. The full app proof additionally checks inspection refusal while a real
window holds an unsent draft; that assertion passes both CPUs at `4412deb`.

New source adds [independent recorded-source assessment](WINDOWS-INSTALLER-DECISION.md#independent-recorded-source-assessment).
The native helper holds a live journal-writer lock and pins the private active
record; its extracted worker matches actual installer bytes and embedded metadata
to the exact recorded source. It reports identity/remaining observation only,
never apply authority. Both native CPUs now pass source assessment and absent-root
inspection/repair at `3b3f89f`; the preceding corruption-fixture failure is corrected.

Exact recorded-source cache lookup now passes both native CPUs at `68062de`,
including a replaced selection naming a synthetic future target. It pins only the
journal's previous installer and still requires independent embedded-metadata
comparison; lookup is neither publisher trust nor recovery apply.

New source adds `/augmentorinspect=health`: the standalone installer retains the
journal writer and active-record pin while exchanging exclusive admission for
read admission. Its independent worker requires a complete source inventory,
launches only the fixed isolated health action, validates exact metadata/native
UI evidence and observes the entire owned Job. Normal startup remains blocked
and no journal is cleared. Five portable health-report cases, 49 update cases
(one local Windows skip), six source-assessment cases, four package cases and
Inno script compilation pass. Native template tests now require damaged-source
refusal, preserved state after failed synthetic health, held kernel admission
and ordinary-startup refusal. Both native templates now pass these cases at
`b6b2313`. Full independent UI health now passes both CPUs at `c530fda`;
synthetic template health remains separate from that actual rendering evidence.

Current work adds [clean authenticated payload placement](WINDOWS-INSTALLER-DECISION.md#clean-payload-placement-before-authenticated-apply).
After actual coordinator exit and final installation admission, Setup pins the
original journal, saves its exact bytes and a fresh placement intent, then moves
any old `current` tree into an owned recovery attempt before copying new files.
A locked tree refuses without deleting files or terminating processes. Unknown
old files remain in the displaced tree rather than the new executable search
path. Missing `current` is permitted only for the registered owned installation.
A prepared receipt follows the move; the original journal remains unresolved.
Manual exact-build repair is unchanged. Local package/update checks and Inno
script compilation pass. Both native templates now pass at `e98a142` in
[36432080462](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36432080462),
merge checkout `521151e33204421421981be0f1f35742bb1c688b`; downloaded reports
confirm locked-tree preservation, clean replacement and missing-payload cases.
Full placement now passes both CPUs in `36432080543`, with each real displaced
payload preserved and complete inventory/independent UI health verified.

New source adds [independent previous-source application](WINDOWS-INSTALLER-DECISION.md#independent-previous-source-application).
The standalone installer explicitly verifies its exact recorded source under fresh
exclusive maintenance, keeps the same writer/record pins, and performs clean
source installation while preserving the unresolved original journal. It restores
its installer/repair metadata and source selection as well as the app payload.
Ordinary launch remains blocked. Native template/full tests now exercise missing
installed launcher/runtime, changed selection, refusal and independent health;
both native templates pass at `04f3317` in
[36433486621](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36433486621),
merge checkout `abf36a2cf01fb7c71b2604ae3e72a53c1d64f617`. Downloaded evidence from both CPUs
confirms the source-application stage, followed by independent synthetic health.
Full source application and actual cross-version qualification remain pending.

New source adds the [distinct durable restoration outcome](WINDOWS-INSTALLER-DECISION.md#distinct-durable-restoration-outcome).
A separate live attempt records fresh apply intent and observed installer exit,
then requires source registration/selection, full inventory and local health under
read admission before writing `source-restored` and archiving the original bytes
unchanged. Thirteen new portable fault/storage tests and all 62 update cases pass
locally (one Windows-only skip). The full proof now composes this shared journal
with actual source installation and native health, then reopens; native execution
is pending. Its proposed target is synthetic, not a second packaged version.
The new [independent recovery observer](WINDOWS-INSTALLER-DECISION.md#independent-recovery-observer)
now composes source restoration and completion through the retained installer's
private runtime, including when installed Python is missing. It creates a fresh
attempt, launches a separately owned source installer, observes its actual exit,
then verifies source registrations, selection, helper hash, full inventory and UI
health before unchanged archival. The active record stays pinned during health.
The exact-template and full-app proofs now invoke this product action directly;
template health is synthetic, while the full proof requires actual rendering and
reopening. Local update/package checks and Inno script compilation pass. Fast Windows at
`9005784` passes both CPUs with health-time record pinning. Native observer and
crash-resume qualification remain pending. Additional Inno fault cases now require
real Setup to escape an explicit observer Job and survive its normal exit/crash,
while an ordinary observer child terminates. These cases use production breakaway
without the hosted fallback; Python compilation passes and native execution is pending.

Next: qualify independent observer/source completion, then finish crash-resume
outcome inspection, bounded disk/retention policy, actual N-to-N+1
and customer notification/update wiring. Preserving a displaced tree alone is not
power-loss recovery. Cache artifacts and displaced payloads still survive ordinary
removal. Never infer a healthy rollback source from the selection pointer or clear
a pending journal manually to bypass recovery.

Continue the [feature ledger](FEATURE-MATRIX.md#windows-development-target--september-28):
Windows desktop control, speech/memory provisioning, Home/Pi parity, real selected
Chromium/extension compatibility, ordinary-user Windows and physical input/audio/
graphics/live-provider acceptance remain required. Shared Resonant Voice is 0.1.19
from qualified source `7d0fd6d`, in separate [draft PR 2](https://github.com/ManoloRemiddi/resonant-voice/pull/2).
Personal models, voice placement and installations remain untouched.

Read [implementation status](WINDOWS-IMPLEMENTATION-STATUS.md),
[installer decision](WINDOWS-INSTALLER-DECISION.md), [delivery](WINDOWS-UPDATE-DELIVERY.md)
and [the plan](WINDOWS-IMPLEMENTATION-PLAN.md). Superseded evidence and failure
checkpoints remain in the [historical archive](WINDOWS-IMPLEMENTATION-CHECKPOINTS-2026-09-28.md).

## September 27 Windows implementation plan — historical planning checkpoint

The owner requested a detailed plan before coding. Read the
[Windows implementation plan](WINDOWS-IMPLEMENTATION-PLAN.md) and its
[corrected research](WINDOWS-RTX-SPARK-RESEARCH.md). The targets are Windows x64
and native ARM64, explicitly including **NVIDIA RTX Spark N1X on Windows**.
Retain one shared Augmentor product across Linux, macOS and Windows. The plan
specifies work packages W0–W10, installer/runtime proof, platform adapters,
browser setup, safe coordinated updates and evidence gates. No product code,
Windows build, CI configuration, installation or release changed in this planning
work. Implementation awaits the next instruction to build; start with W0 and W1,
then follow their exit criteria. The existing Mac activation checkpoint below
remains separate and unchanged.
## October 2 embedded Handy candidate

The owner has now accepted the installed Linux dictation through real use and
authorized PR #30's merge after successful checks. The merge review fixes an
existing Codex cancellation fixture to wait for actual provider request receipt
within a bounded deadline, preserving all cancellation/fencing/no-replay
assertions. Await that follow-up's hosted checks before merging; no new installed
cutover is needed. See [the owning guide](HANDY-INTEGRATION.md).

Current implementation qualification: source `81a2bba` passes all hosted native
component jobs (Linux x64, Mac ARM64, Windows x64), shared SDK/application checks,
Debian build and clean installation/update/rollback/removal, actual packaged
Chromium acceptance, and both macOS 14/26 signed development product jobs.
[Validation](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37036303734)
and [Mac product qualification](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37036303739)
record the exact completed runs. The owner's Linux installation is enabled and
ready, with Desktop/Mobile online and the standalone tray/startup retired.
Full Windows installer convergence with PR #20, Developer ID/notarization and
physical OS/microphone/compositor acceptance remain customer-release gates.


`feat/handy-integration` starts from public main `d91c520` and implements the
owner-approved system-wide dictation and themed Handy overlay. Read
[the implementation guide](HANDY-INTEGRATION.md) for supplier pins, settings,
microphone ownership, OS adapters, packaging, reproducible proofs and explicit
qualification boundaries. The canonical dirty checkout and existing installed
settings work are preserved. Feature source `c8f67a3` now has an installed Linux
adoption: selected/running build `20261002-141437-663e6383`, artifact
`a47433db434bf446d8001c18182d85b8318c0e78f92fd72f14f8131f75cfd308`, compatible
installed 0.2.11 contracts retained. Standalone Handy startup/process ownership
was reversibly retired and embedded Ctrl+Space dictation enabled on CPU with the
owner's actual palette. [The adoption record](HANDY-INTEGRATION.md#owners-installed-adoption--2-october-2026)
separates that Linux evidence from open hosted lifecycle/platform package gates.
Follow-up source `f60148b` verifies patch application in a separate build Git root
and fences delayed microphone admission. Current selected/running adoption is
`20261002-160803-407ce464`, artifact
`ac681aadeea466f7ce280f5641e8c89ba01e216a299702de3f1de134886240b9`;
both idle windows adopted through acknowledged maintenance. The original cutover
above remains historical evidence. Source `85034ac` includes native admission
expiry and the short Unix socket path. All 615 native cases pass (3 expected skips),
both clean-source Debian packages build and their extracted component passes
actual lifecycle/theme/ownership/EOF proof. Hosted platform results are recorded
in the owning guide as they qualify.
Final feature source `c40e53b` passes 617 shared native cases (3 expected skips)
and a fresh-user clean Debian install/component/shortcut/uninstall proof.
CI follow-up `0e7a19a` prepares reviewed source before restoring compiler files;
Windows checksum-pinned notices retain exact bytes under automatic conversion.
The current installed Linux root above stays enabled and ready; Mac-only
permission/package refinements do not require another Linux cutover.
At `0e7a19a`, macOS 14/26 signed Desktop/Browser development product jobs
pass, including actual copied-helper proofs. The Windows notice-only follow-up
preserves the original missing clipboard dependency license and passes the full
target-filtered notice audit. Final hosted results are recorded in the guide.
Do not claim a qualified Windows installer or physical microphone acceptance
solely from a native build or successful component enable.

## October 1 merge blockers: current main and separate Codex prerequisite

The feature branch integrates canonical main `8c3be5a` at merge `338dbc5`.
Browser observations retain both current main's paging/explicit-read behavior
and Codex's document-epoch action ownership; both documentation/test histories
are preserved. Product versions follow main's 0.2.13.

[Codex packaging](CODEX-PACKAGING.md#separately-installed-runtime--october-1)
now excludes supplier Codex files from production staging on Linux and Mac.
The exact 0.159.2 dependency remains for source tests; products use an explicitly
installed, version-checked CLI in a separate location. Native unknown-file
rejection stays enabled. Bundled supplier redistribution review is incomplete,
not bypassed. Local type/build, 480 Node cases (478 pass, two opt-in memory proof
skips), 65 Browser cases and 598 native cases (596 pass, two Mac-only skips) pass.
The actual production stage collects 229 npm notices, contains no Codex package,
and records the external prerequisite. The real isolated external app-server
startup passes. Final GitHub package evidence follows after qualification.
Source `84beebca01d5f9ee997a2d1ab14f1e50d0dda9f6` also builds both Debian packages
locally from a clean tree and passes artifact hashes/private-state/native notices
review. Its extracted real runtime, using packaged Node, completes one synthetic
Responses request through the default external prerequisite location and reopens
the exact native thread/history without another request. The followup reusable
proof runs at the real Debian and Mac Desktop/Browser packaging boundaries in CI.
The first Linux CI for `84beebc` exposed a loaded-Chromium proof timing race:
the memory status/label changes while its button remains disabled until context
loading finishes. The proof now waits for the requested button to become enabled
before clicking once; it does not retry the configuration action or skip the
pause/resume assertions. This changes test synchronization, not memory behavior.
No installed app, source from private dependencies, original canonical working
files, user login cache or live model/speech configuration changed. Subscription
eligibility gates and full C0–C9 acceptance remain open.

## October 1 model-catalog platform qualification

Source `3ca4778b1a6b4e368dd1e82e106a10c29cdea504` passes Mac 14/26 CI,
including all six actual Keychain account lifecycle proofs through the build,
packaged Desktop and standalone Browser interpreters. Linux type/build and
462 root, 65 Browser and 590 native cases pass, with the four documented opt-in/
Mac-only skips; isolated actual Linux protected storage passes again. Linux CI
passes application/Home/credential/source/npm/extension checks and still fails
only at the known native Codex executable notice gate. See
[exact account-model source and CI](CODEX-ACCOUNTS.md#published-account-model-source-and-platform-checkpoint).

All 30 original canonical working files remain byte-identical to their private
backups. No installed app, global auth cache, private speech or approved model
placement changed. A short OpenAI eligibility request is prepared in the account
guide for owner review; it was not submitted. The owner was asked whether OpenAI
has already approved Augmentor's subscription use. Keep production gates false
without confirmed eligibility, and retain the separate pending Qwen activation
question. Native managed auth, live acceptance, notices and the complete C0–C9
plan remain open; do not mark the full integration complete. These followups are
documentation only.

## October 1 current account model catalog

[Current account models](CODEX-ACCOUNTS.md#current-account-model-choices--october-1)
now load through the same host and both existing setup forms. The fixed OpenAI
GET uses only the selected account's protected bearer; no bundled catalog,
inference, redirects, retries or fallback. Visible names/IDs preserve server
order. Bounded parsing, logout/revision/cancellation fencing and both surface
contracts pass with synthetic responses. A choice edits a draft and needs a
completed connection check. Production SIWC eligibility stays false.

The actual pinned native auth schema was also inspected: external
`chatgptAuthTokens` is internal-only and is not used. Native managed auth still
needs its separate eligible, keyring-only, serialized account authority and
thread-state design; it cannot bypass commercial restrictions. Continue the
complete C0–C9 plan. Local Qwen activation awaits owner direction, native package
notices remain a gate, and no installed app/private speech/model placement changed.

The preceding renewal source `57ba17d` passes Mac 14/26 CI and all six actual
Keychain account proofs; Linux application/Home/source/credential/extension
checks pass with only the known Debian native executable notice failure. This
platform evidence is for that exact source; model-catalog source is newer.

## October 1 account-bound profiles and credential renewal

[Bound account/model connections](CODEX-ACCOUNTS.md#bound-connections-and-worker-renewal--october-1)
now separate profile configuration revisions from protected-account token
revisions. Desktop and Browser save the chosen consented account without API-key
fields; changing the default account cannot redirect existing connections.
Every queued root turn checks its saved binding and authoritative native idleness
before durable dispatch. Token changes retire the owned process and initialize/
resume the same native thread. Stop, unknown outcomes and failed resume preserve
unsent work without replay or billing fallback. The transport observer stays
attached and ignores retired child output.

Full local source/UI suites pass; scripted subscription protocol tests and the
actual pinned Codex/loopback synthetic API provider renewal proof pass. The latter
proves new-bearer transport and exact native history, not real SIWC inference.
Final publishing/CI source identity follows in the account guide. Production
SIWC remains source-disabled; the native managed account route, eligibility,
models/limits, live subscription/provider qualification, native executable notice
review and full C0–C9 acceptance remain open. Installed apps, original canonical
work and approved speech/GPU/model placement remain unchanged. Qwen formatter
activation still awaits owner direction. Continue the complete plan.

## October 1 shared ChatGPT host and setup controls

[The account guide](CODEX-ACCOUNTS.md) now covers one lazy host-owned login
controller, provisional issued-client recovery, shared status/cancellation,
explicit plan consent and logout. Existing Desktop/Browser forms use the same
host RPC. Closing cancels only the form's owned attempt, including late start
replies. Cancelled native-store writes cannot activate new credentials; completed
durable activation cannot be falsely reported cancelled. Account changes freeze
admission and release only verified-idle workers; active/unknown work refuses them.
Logout receipts replace stale successful-login text across surfaces.

Build/type, 71 focused account cases, the full 428-case Node suite (426 pass,
two opt-in Docker memory proofs skipped), 61 Browser tests and 586 native tests
(584 pass, two Mac-only skips) pass on Linux with the existing isolated Qt
environment. Actual native-adapter/Browser-bridge IPC tests pass with synthetic
grants; real isolated Secret Service save/rotation/restart/logout/cleanup passes
again. The private-source boundary passes. Published implementation source is
`95229aaf0dfc979b895fb0ef06ed131aaf84c550`.
[Mac CI](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36866967195)
passes on Mac 14/26, including the new account/controller/native setup tests and
all six actual Keychain proofs through build, packaged Desktop and standalone
Browser interpreters. These use synthetic grants/renewal, not live OpenAI consent.
[Linux CI](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36866967360)
passes source boundary, Home, application/UI/credential checks, production
dependency notices and extension packaging. Debian packaging still fails only at
the known unreviewed native Codex executable gate; installed-package jobs skip.
All 30 original dirty canonical files again match their private backup bytes.
The following evidence/next-contract documentation update changes no code.

Historical host-controls checkpoint, superseded for account/model binding and
worker renewal by the section above. Production login stays disabled pending
eligibility, with no RPC/environment bypass. The Codex-managed subscription
route, live consent/inference and full C0–C9 acceptance remain open.
Installed apps, the canonical checkout's unrelated work, private speech and
approved model/GPU placement remain untouched. Qwen activation/restart still
awaits the owner's answer. Continue the full plan.

## October 1 protected ChatGPT account primitives

[Account implementation and remaining integration](CODEX-ACCOUNTS.md) now covers
actual cryptographic/loopback OAuth transactions, issued-client reuse, identity
and scope validation, protected account mappings, serialized rotating-token
persistence, interrupted-refresh fencing and bounded revocation/local logout.
Identity-only consent does not enable inference; network-uncertain rotations
quarantine old tokens without replay. The actual isolated Linux native-store proof
passes account save/rotate/reopen/logout/cleanup, with synthetic OAuth/renewal.
Build/type, 55 focused cases, six license-inventory tests and the complete 412-case
Node suite pass (410 pass, two opt-in Docker memory proofs skipped). The default
system Python lacked QtTest; the passing suite used the existing isolated Qt
test environment. No installed dependencies or apps were altered.
`jose` 6.2.12 is locked, and its real MIT notice passes the inventory collector.

Historical primitive checkpoint, superseded for host/UI wiring by the section
above. These classes remained internal and production login defaulted off: no host/profile,
Desktop/Browser or worker-renewal wiring, real account consent/inference,
distribution eligibility or C4/full C0–C9 completion is claimed. Existing Mac CI
passes the expanded account-store proof on Mac 14/26 for source `91db7aa` through
the build, packaged Desktop and standalone Browser interpreters; see
[Mac CI](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36861022280).
[Debian CI](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36861022467)
passes application/Browser/credential/npm-notice/Home checks and still stops at
the unreviewed native Codex executable gate. All 30 original dirty canonical
working files remain byte-identical to their private backups. Continue wiring and the
remaining full plan. The separate Qwen activation/restart decision is pending;
do not change its approved formatting/model deployment without owner direction.

## October 1 owner-authorized private-source cleanup

The owner explicitly approved preserving all work privately and removing the
speech-source archive from public GitHub history. See
[cleanup and current evidence](CODEX-SOURCE-CLEANUP.md). A verified private Git
bundle and working-file backups preserve the integration and unrelated native
changes. The approved rewrite is now public at `8e418a0`; current branch/PR
archive requests return 404, but the old cached introduction commit still serves
it. The owner-approved private Support request has been submitted; cached-copy
removal awaits GitHub's review. At `1281935`, source-boundary/Home and both Mac
jobs pass; Debian still stops at the existing native Codex notice gate.
Public voice tests now use an independently authored scripted peer;
real-service source qualification is historical and must not be claimed for the
replacement. No installed app, production speech, owner settings or GPU/model
placement changed. Continue Codex C0–C9 after cleanup; do not reintroduce private
source from old refs, local backups, sibling repositories or npm caches.

## October 1 native V8 sources and original notice collection

[Native source collection](CODEX-PACKAGING.md#october-1-native-source-collection-and-v8-inputs)
now verifies 28 public archives and retains 3,817 original notices plus 25 pinned
source/build files. Eleven additional sources trace the embedded V8 dependencies;
the module lock selects Abseil 20250814.1, and its registry metadata/hash are
verified before fetching the archive. Two full native reports are byte-identical.
Contained aliases have their original targets retained; no filesystem links are
created and no downloaded source code is executed. Three focused native-source tests pass.
The compact committed inventory is reproducible from the collector. Native linked
coverage, unresolved crate/generated-source notices and actual packaging remain
release gates. `2641227` passed both Mac jobs and Debian application/credential/Home
checks, with the same Debian native Codex notice failure. Installed apps, private
speech, credentials and GPU/model settings remain unchanged; Qwen activation still
awaits the owner's answer. Continue full C0–C9, not a narrowed chat-only milestone.

## October 1 native store platform results and packaging source identity

`0726234` passed both Mac 14/26 jobs, including actual Keychain roundtrip/update/
isolation/removal/cleanup through build, packaged Desktop and standalone Browser
companion interpreters. Package inventory/signature checks pass. Debian credential,
application and Home checks pass; its Codex native notice gate still blocks
packaging. See [credential evidence](CODEX-CREDENTIALS.md).

[Packaging source identity](CODEX-PACKAGING.md#october-1-version-and-source-identity-evidence)
now verifies supplementary notices against actual archive bytes and compares
version/commit/path plus all published Rust files. All 128 identity records match
version/VCS metadata; 109 match Rust source completely and 19 retain explicit
source gaps. Two added candidates reduce missing candidate attribution to 20 of
138 archives. Eight focused tests and actual full collection pass; no release
clearance or installer-gate bypass. Installed apps, owner settings and private
speech are untouched. Qwen activation still awaits the owner's answer; continue
remaining C0–C9 work without silently changing its formatter/service.

## October 1 native credential dependencies and actual Linux proof

[Secure credential correction](CODEX-CREDENTIALS.md) supplies the missing native
Python store dependencies for future Debian/Mac packages. Five hashed Mac wheels
have verified notices and complete target dependency edges. A real isolated
Secret Service proof passes through actual Node/helper processes on the pinned
Debian image, covering update/isolation/removal and cleanup. Unit and Mac package
inventory checks pass. Mac build/bundle Keychain proofs are required in CI but
remain pending, including the separate Browser companion without Qt. Owner
credentials/settings and installed apps are untouched.
The Qwen formatter/restart question is pending; do not apply the candidate without
the owner's answer. Continue independent C0–C9 work while waiting.

## October 1 real local-provider diagnosis and unactivated candidate

[Current local Qwen blocker](CODEX-LOCAL-QWEN.md) is now traced to multiple system
messages after llama.cpp maps Codex developer instructions. A fresh real pinned
Codex tool check fails once with HTTP 400, without model replay or owner data.
The separate candidate helper preserves later system/developer text instead of
dropping it. Actual offline tools reproduce original rejection, render both
leading/later developer messages with the candidate, keep single-system output
byte-identical and retain system-image rejection. Guard checks pass. No service
was changed or restarted; owner direction is required to change approved model
formatting. After authorization, qualify real tools/stream/Stop/resume and DSH/Pi
regressions, restoring the original formatter on failure. Continue full C0–C9.
`70935e8` passed both Mac jobs and Debian application/Home checks; Debian packaging
retains the unreviewed Codex native executable notice gate.

## October 1 complete Codex-controlled memory pipeline

[Complete scoped stage proof](CODEX-INTEGRATION.md#complete-scoped-memory-stages-through-actual-codex-activity)
now executes all six actual pinned Hindsight retain/consolidate/page stages during
a Codex Browser I/O window. Both banks cache observations and generated pages;
a page-only marker reaches the next native request. Startup/idle/restart cause
no extra inference, and the complete job receipt/remaining budget survive restart.
All seven focused real-host/companion cases and all 357 root Node tests pass
with both Docker proofs enabled. Replies are synthetic; live classification/page
quality and full C0–C9 remain open. The implementation checkpoint is `7dad3f2`.
`f4f8d87` passed both Mac jobs and Debian application/Home checks; Debian
packaging still stops at the unreviewed Codex executable notice gate. No installed
app/settings, private speech source or model placement changed.

## October 1 Unicode capture integrity and platform checkpoint

[Unicode source integrity](CODEX-INTEGRATION.md#original-memory-text-across-unicode-storage-boundaries)
now preserves emoji across shared memory chunk boundaries. An actual pinned
Codex/real companion proof reproduced SQLite rejection of split surrogate pairs
and verifies exact source reconstruction plus restart dedupe after the fix.
Build/type and all 356 root Node tests pass with real-engine opt-in, including
actual DSH/Pi regression contracts. `4ac6a54` passed both Mac jobs, Debian
application/native/Chromium checks and Home. Debian packaging still stops at the
unreviewed Codex native executable notice gate. Continue full C0–C9; complete
memory stages/quality, live providers, eligible subscription login and release
qualification remain open. No installed app or private speech source changed.

## October 1 Codex memory source activation and both interfaces

[Launcher and UI qualification](CODEX-INTEGRATION.md#codex-memory-launcher-and-existing-interface-controls)
now enables the shared memory client in the development launcher. Actual Qt
Enter/Send and Memory dialog tests use that launcher, pinned Codex and isolated
real companions. Loaded Chromium verifies continuity, exact branch/edit capture
and existing Memory settings pause/resume. Browser's missing memory RPC route is
connected; both adapters report host-owned capability. Old chats retain their
recorded contract; new chats receive memory tools. Build/type, all 355 root Node
tests (real engine opt-in enabled), 56 Browser tests and 570 native tests (568 pass,
two Mac-only skips) pass on Linux. Window lifecycle assertions also pass after
replacing the Mac CI fixed animation sleep with a bounded completion wait.
`cec1fe4` CI exposed an asynchronous recovery-export race and that Mac 26 timing
failure; both are corrected in source. Await fresh Mac/Debian CI before claiming
platform parity. Full C0–C9, memory quality/complete stage qualification and
distribution gates remain. No installed app, private speech source or inference
configuration changed.

## October 1 Codex controlled-engine cancellation

[Actual controlled-engine proof](CODEX-INTEGRATION.md#actual-codex-controlled-memory-window-and-cancellation)
joins pinned Codex, the real Python companion/gateway and a disposable pinned
Hindsight 0.10.0 container with synthetic inference. Browser tool activity admits
one generation; Stop closes its upstream socket, stops the job and grants no idle
or restart replay. The proof corrected `browser_tabs` to the actual registered
`browser_tabs_list` in memory's spare-compute allowlist. Build/type and all 354
root Node tests pass on Linux with the opt-in Docker proof enabled. Default CI
skips that one Docker case; no model-quality or completed memory-stage claim.
Continue loaded native/Browser memory proofs and launcher activation, then full
C0–C9 requirements. Installed apps, settings and private speech remain untouched.

## October 1 actual Codex host and memory-companion qualification

[Pinned host/companion evidence](CODEX-INTEGRATION.md#actual-pinned-host-and-memory-companion-qualification)
now covers scoped source reads, voice/text provenance, historical child capture,
capture pause across restart, pre-turn Stop and outage/backfill without replay.
It found and fixed native rejection of mixed dynamic-tool registration formats;
memory tools now use the same canonical function format as Browser/Home.
Build/type, 353 root Node, 56 Browser and eight memory-budget tests pass on Linux.
The actual Codex and Python companions use isolated state and synthetic inference;
this does not certify real controlled-engine generation or memory quality.
Continue controlled inference/gateway, loaded native/Browser proofs and activation;
the standalone launcher still leaves memory disabled. No installed app/settings or
private speech source changed. `c987f40` passed both Mac jobs and Debian
application/Home checks; binary notices remain the packaging gate.

## September 30 Codex shared-host memory wiring

[Host memory integration](CODEX-INTEGRATION.md#shared-host-memory-wiring-and-pre-turn-stop)
now connects an explicitly injected shared client to scoped source/recall tools,
pre-turn context, durable capture, historical-child cutoffs and activity owners.
Stop cancels lookup before dispatch; stale native events cannot acknowledge
queued work. Native idle inventory and subsequent child/hook/voice activity
govern Browser processing windows. Shutdown awaits removed-worker cleanup.
Build/type, 350 root Node and 56 Browser tests pass on Linux. New host wiring is
synthetic-boundary qualified; pinned context and actual isolated memory-companion
proofs also pass. Main launcher still leaves memory disabled pending actual
pinned-host/companion, controlled inference, failure and both-surface tests, then
activation. Continue those C6 proofs, not another replacement-context spike.
`12f6608` passed Mac and Debian application/Home checks; binary notices remain
the packaging gate. No installed configuration or private speech source changed.

## September 30 bounded versioned continuity qualification

[Continuity transport](CODEX-INTEGRATION.md#versioned-continuity-transport-and-native-compaction)
now separates a current-request manifest from bounded untrusted data fragments,
preserves Unicode without truncation, retains voice/text source provenance and
omits fresh historical-child recall. Seven new contracts include actual pinned
Codex fragment dedupe, exact reply/edit inheritance, supported native compaction
and restart. Build/type and 343 root Node tests pass on Linux. Host memory is
still disabled; continue scoped source/recall tools, pre-turn cancellation,
capture/activity/branch cutoff wiring and full C6 qualification. No private
native store or installed configuration changed. Preceding `1f62a80` passed both
Mac jobs and Debian application/Home checks; binary notices still block packaging.

## September 30 Codex chat/tool connection qualification

The existing Desktop/Browser setup check now runs a
[pinned Codex tool round trip](CODEX-INTEGRATION.md#codex-model-and-tool-connection-check)
in temporary state, with a pure nonce/receipt tool and no environment access.
Host-owned evidence is tied to profile revision and runtime; shutdown cancels
checks, and setup/maintenance cannot race them. Build/type, 336 root Node,
56 Browser and three Qt setup tests pass on Linux, including actual pinned Codex
with synthetic inference. No live model/account or installed app was used.
Continue real provider/account qualification and remaining C0–C9 work. Preserve
the publication boundary and core-chat priority below; do not copy more private
speech source or change installed settings.

## September 30 publication review and core-chat priority

The owner accepted keeping the reviewed work without deleting repository history
and prioritizing Codex chat/tools before further speech work. No additional
private speech source is authorized for public copying. The test archive added
at `c9f9067` was audited byte-for-byte; six source files and the MIT license match
the previously public 0.1.16 package, and only the service bridge differs. No
credentials, recordings, installed configuration or private Git history were
found. Retain the work; preserve installed applications and private state.

`c603a46` passed both macOS jobs and Home's container check. Debian exposed a
loaded-Chromium test race: the source-history snapshot preceded native turn/end.
The test now waits for terminal operation status before asserting Branch leaves
source history unchanged. This is a fixture timing correction, not qualification
of the remaining release gates.

## September 30 spoken style and late audio rejection

[Request-scoped voice guidance](CODEX-INTEGRATION.md#spoken-input-style-and-interrupted-synthesis)
now covers starts, steering and queue promotion, with an explicit typed-input
reset. Pinned native/Browser synthetic proofs verify provider context and clean
display history. All 328 root tests pass; the added seventh focused voice test
also proves late cancelled synthesis cannot play into the next generation.
Home's CI build-input omission is corrected; the full local container build and
packaged prompt-service probe pass with no test archive in the final image.
Continue C7 structured expressive replies, hands-free/physical acceptance,
C6 production memory, subscription eligibility/login and all C0–C9 gates.

## September 30 shared Codex voice transport

[Codex speech integration](CODEX-INTEGRATION.md#codex-speech-through-the-shared-desktop-and-browser-engine)
now joins the shared host, confirmed operation IDs, public reply streaming,
scoped cancellation and both existing voice interfaces. Actual offscreen Qt
hold/release and Browser native-worker proofs pass with real pinned Codex and
synthetic device/model/ASR/TTS boundaries. Build/type, 327 root Node, 56 Browser
and 569 native tests (567 pass, two Mac-only skips) pass. Requires the proposed
Resonant Voice 0.1.17 scoped bridge at `cbf956d`; old companions fail explicitly.
The minimal MIT test archive is reviewed, hashed and development-only.
Continue C7 expressive/voice style, full hands-free and interrupted-generation
proofs, full dependency artifact and physical Linux/Mac audio qualification.
No installed service/app or Qwen/Breeze configuration changed. `b917153` passed
both Mac jobs; Debian still stops at native-binary packaging review. Full C0–C9,
including subscription login and production memory, remains unfinished.

## September 30 Mac guard cleanup correction

Mac `29cb4c9` CI exposed a redundant post-exit group KILL returning EPERM. The
[ownership correction](CODEX-INTEGRATION.md#guard-ownership-correction-from-macos-ci)
leaves cleanup with the live guard and avoids signaling a numeric group after
its owner exits. Build/type and 321 root tests pass locally, including both actual
native command crash cases. Await the new Mac run before claiming parity. Debian
at `29cb4c9` reached the existing unreviewed Codex binary packaging gate.
Continue the C7 trusted voice client and native/Browser wiring against Resonant
Voice PR #3 (`7267ad8`), while retaining the full remaining C0–C9 requirements.

## September 30 native crash proof and speech dependency

[Crash and speech checkpoint](CODEX-INTEGRATION.md#native-command-crash-qualification-and-speech-dependency)
adds actual pinned Codex PTY and background `exec_command` cleanup after owner
SIGKILL. The tool fixture finishes its root turn first and proves native idle
inspection still sees the background terminal. Both separate native groups stop;
321 root tests pass. Arbitrary escaped daemons remain outside this evidence.
C7 now has [Resonant Voice PR #3](https://github.com/ManoloRemiddi/resonant-voice/pull/3),
source `7267ad8`, development 0.1.17, with a scoped Codex bridge and host-expiry
cleanup. All 37 speech tests and the isolated real-DSH lifecycle fixture pass.
Continue the Augmentor host bridge, exact public-text/request association and
both voice surfaces, then dependency/artifact and physical audio qualification.
Voice stays disabled until this wiring works. No installed apps or model settings
changed. Full C0–C9 remains active, including subscription/account, memory and
packaging gates.

## September 30 Codex crash cleanup guard

[Process guard](CODEX-INTEGRATION.md#process-group-cleanup-after-an-owner-crash)
now keeps POSIX group ownership alive if the Augmentor RPC owner is killed.
A private liveness channel triggers scoped cleanup; wrapper exit also retires
helpers. Normal shutdown sends only one TERM to preserve native graceful cleanup.
Build/type and 318 root tests pass; 13 final transport cases include host SIGKILL,
an ignored-TERM helper, unrelated-process survival and single-TERM behavior.
The maintenance checkpoint `25f4ba6` has Mac run `36759092419` active; its Validate
run is `36759092307`. Prior `3c00243` Debian checks reached the known unreviewed
Codex binary gate; its Mac run was cancelled. No installed apps changed. Continue
native shell groups that escape the guard, unknown-native-identity recovery and
the full C0–C9 integration; simultaneous owner/guard death is not qualified.

## September 30 Codex maintenance native-idle verification

[Maintenance verification](CODEX-INTEGRATION.md#native-idle-verification-before-maintenance)
now freezes admission before reading every worker's native child, terminal, goal
and hook state. Host-wide revision checks reject activity during later-worker
inspection. Concurrent preparations share verification; cancellation is refused until
it settles, and failed checks preserve the previous admission policy. Build/type,
317 root Node and 55 Browser tests pass. Prior `3c00243` Mac and Validate runs
were still active when checked. No installed apps changed. Continue crash/orphan
ownership and unknown-native-identity recovery plus the remaining full C0–C9 plan.

## September 30 Codex bounded worker pool

[Worker reuse and admission](CODEX-INTEGRATION.md#bounded-worker-reuse-and-creation-admission)
now replaces the hard idle-capacity stop with serialized reservations and
least-recently-used verified-idle retirement. Request leases protect in-use
workers; active/unknown work and paused queues retain their outcome rules.
A durable pre-dispatch flag makes capacity/initialization refusals retryable
without guessing about a native creation. Older unknown records remain blocked.
Build/type, 314 root Node and 55 Browser tests pass. The pinned host/fork proof
uses two chat workers across branches, edits, restart and recovery without
replaying paused input. Prior `7f85c2a` passed both Mac jobs; its Debian application
checks passed and packaging still rejects the unreviewed Codex executable. No installed apps changed. Next extend native background-work verification to
host maintenance/shutdown, which still relies primarily on product-ledger state,
then continue orphan and unknown-native-identity recovery and full C0–C9.

## September 30 Codex worker-release prerequisite

[Native idle evidence and release fencing](CODEX-INTEGRATION.md#native-idle-evidence-and-worker-release-fencing)
checks every loaded thread, background terminals, unfinished goals, hook activity
and changing native notifications before release. Incoming worker requests wait
for release and resume the original thread; failed release preserves the worker.
Build/type and 307 root Node tests pass, with real pinned idle-inventory evidence
and release/queued-request race coverage. Automatic idle-worker reuse is **not
yet implemented**. Continue bounded pool admission with request reservations;
current capacity refusal can leave a pre-dispatch creation falsely unconfirmed
and must be distinguished from an actual lost native reply. Full C0–C9 remains
open; no installed apps changed. Prior `2ef08a8` Debian packaging still blocks the
unreviewed binary; Mac run `36755663211` was still active when checked.

## September 30 Codex interrupted fork recovery

[Known-ID fork recovery](CODEX-INTEGRATION.md#recovering-a-fork-with-a-saved-native-identity)
now verifies an interrupted child's saved native history and opens that same
thread on a repeated client request. It never repeats `thread/fork` or model
inference. Changed profiles, incomplete/mismatched history and failed durable
readiness keep the index unconfirmed. Build/type and 302 root Node tests pass;
final real pinned-runtime fixtures cover restart and each failure path. A lost
native reply before its ID was saved remains unknown and is never guessed.
No installed apps changed. Continue worker lifecycle/orphan recovery and the
remaining full C0–C9 plan. Previous `8d9d9e7` CI runs were still active when last
checked: Mac `36755147294`, Validate `36755147302`.

## September 30 Codex Branch/Edit client checkpoint

[Desktop/Browser Branch/Edit](CODEX-INTEGRATION.md#desktop-and-browser-exact-branchedit-controls)
now enables the existing transcript controls with persistent request identity,
child attachment and exact host boundaries. Pending intent survives client
restart; only authoritative absence clears rejected creation. Real offscreen
Qt and loaded Chromium proofs cover branching, first/latest input edits,
original-history preservation, tool-context inheritance, draft restoration and
reload without duplicate submission. Build/type, 302 root Node and 55 Browser
tests pass; the full native suite ran 569 tests, with 567 passing and two
macOS-only skips. A repeated Qt proof now waits for asynchronous Send readiness.
Prior `d5209a3` passed both Mac jobs; Debian checks passed before the known
binary-review packaging failure. Installed applications remain unchanged.
Continue unknown-creation reconciliation and the remaining C0–C9 requirements;
subscription login, full memory/voice, packaging and live/installed gates remain.

## September 30 Codex exact fork host checkpoint

[Exact fork host foundation](CODEX-INTEGRATION.md#exact-fork-host-foundation)
adds durable `session.branch`, exact display-to-native boundaries, native-store
ownership, verified history and a short-lived creator to release Codex's writer
lock. Source and child retain independent product ledgers/queues. Lost replies
and mismatched history cannot replay creation. Build/type and 301 root Node
tests pass, including actual pinned-runtime and shared-host synthetic-provider
proofs. Branch/Edit UI flags remain disabled pending client and real UI work;
unconfirmed creation reconciliation and full C0–C9 remain unfinished. Prior
Browser source passed Mac CI; Debian application checks passed and packaging
still fails the unreviewed binary gate. No installed application changed.

## September 30 Codex Browser queue checkpoint

[Browser queue controls](CODEX-INTEGRATION.md#browser-queue-controls-and-snapshot-ordering)
now share native admission/steering/removal and durable pause. Compact composer
rows retain unknown text; exact IDs prevent duplicate delivery and stale targets.
Persisted revisions suppress older poll snapshots. The loaded Chromium fixture
qualifies real Enter/Steer/Remove, panel reload, same-turn correction, removal
without model delivery and next-turn FIFO input with pinned Codex/synthetic
Responses. A race between Steer and immediate typing is fixed by serializing
queue actions and submissions. Build/type checks, 294 root Node and 53 Browser
DOM tests pass. No installed app/profile changed. Previous `3fd287b` passed both
Mac jobs; Debian application checks passed and packaging still blocks unreviewed
Codex binaries. Continue exact fork/edit and the remaining C0–C9 requirements.

## September 30 Codex native queue checkpoint

[Queue controls and pause](CODEX-INTEGRATION.md#native-queue-controls-and-durable-pause)
enables existing native Enter/Steer/Remove controls with subscription baselines,
atomic promotion and delivered-message correlation. Stop pause survives restart;
an explicit idle Send resumes FIFO waiting input. Unknown work is never removed
or replayed, and aggregate queue size is bounded before admission. The real
offscreen Qt/controller/IPC/pinned-Codex fixture verifies reconnect, removal,
same-turn steering and next-turn delivery with a synthetic provider. Build/type,
293 Node, 48 Browser, eight queue Qt and 16 Codex Python checks pass locally.
Browser running-turn queue controls, fork/edit and the remaining C0–C9 work are
still unfinished; no installed app changed. Preceding `0f96407` passed Mac CI;
Debian application checks passed but packaging still refuses unreviewed Codex
native binaries. Check the new commit's CI before claiming Mac source parity.

## September 30 Codex durable steering checkpoint

[Active-turn steering](CODEX-INTEGRATION.md#durable-active-turn-steering) now
uses exact target/client identities and durable admission through the shared
host. Real pinned Codex consumes the correction once in the existing turn and
preserves both user IDs after host restart. Lost acknowledgments remain unknown
until native client-ID reconciliation; no correction becomes a new prompt.
Build/type checks and 289 Node tests pass, plus the final shared-host fixture.
Existing native/Browser queue presentation, snapshots, queued-item promotion
and removal still need integration before enabling the UI. Exact fork/edit and
remaining C0–C9 gates remain open; installed applications are unchanged.

## September 30 Codex paginated recovery checkpoint

[Native-history recovery](CODEX-INTEGRATION.md#paginated-native-history-recovery)
uses turn/item pages, validates complete reads before ledger reconciliation and
shares the result with display restoration. Real pinned Codex with one-item pages
preserves client IDs and command output. Build/type checks and 285 root Node
tests pass. A failed later page keeps unknown work unresolved without replay.
The context probe also confirms that clearing collaboration-mode developer
instructions retains earlier snapshots; memory remains disabled pending the
replacement contract. Full C0–C9, packaging review and installed qualification
remain unfinished. This source checkpoint does not change installed apps.

## September 30 Codex memory foundation checkpoint

[Memory foundation and context evidence](CODEX-INTEGRATION.md#memory-capture-foundation-and-context-api-qualification)
adds a tested capture/lifecycle adapter, but does not activate memory in the
Codex host. Real companion tests preserve committed text, deduplicate replay,
respect skipped paused records and admit no idle inference. Pinned Codex proves
that `additionalContext` preserves earlier snapshots in model history even when
keys change/disappear and after restart. Do not use it as a supposedly replaceable
memory slot or count its fragments as new user messages. Continue C6 context,
host/lifecycle/profile wiring, scoped tools, compaction and fork exclusions.

Local build/type checks and 281 root tests pass; five final focused contracts
cover the adapter and real context transport. At `cf220f7`, macOS and Home CI
passed, as did Debian's application/Chromium checks. Debian remains blocked at
native executable review. Full C0–C9 completion is still outstanding.

## September 30 Codex paired Home checkpoint

[Home integration evidence](CODEX-INTEGRATION.md#paired-home-tools) records the
shared NAS tool bridge for new Codex chats, persistent request ownership, no
unknown-action replay, and server-checked request-specific cancellation. The
actual pinned Codex/native/Browser path, including resumed Browser tools, passes
isolated provider/NAS fixtures. Local validation: build/type checks, 276 root
Node tests, 48 Browser tests and 30 Home tests. Existing NAS deployments and
household devices were not changed or qualified. Old NAS versions cannot perform
Codex's scoped cancellation and never receive a broad-cancel fallback.

At preceding `372dcfe`, macOS and Home CI passed. Debian exposed a Chromium
fixture navigation race; the corrected proof waits for the extension document
and messaging API and passes locally. Follow the next CI run for runner evidence.
Continue the full plan: generic MCP, account eligibility/login, memory, speech,
remaining conversation operations, platform/device and release qualification.

## September 30 Codex draft improvement checkpoint

[Draft improvement](CODEX-INTEGRATION.md#apilocal-draft-improvement) now connects
both existing composers to a shared, bounded, tool-free Responses transformation
using the selected API/local profile and saved improvement instructions. Actual
native/Browser bridge fixtures verify no chat history or Codex worker is created;
subscription support and live rewrite quality remain unqualified. The preceding
real Plasma proof passed all three cases on exact `ce77fa6`; its disposable VM is
stopped. Both macOS CI jobs passed that source. Debian still blocks unreviewed
native binaries; a separate Home deadline-test race has been made deterministic.
Local validation: build/type checks, 270 root Node, 48 Browser, four native
prompt-editor and 29 Home tests pass.
Continue C0–C9, especially account eligibility/login, Home/MCP, memory, speech,
remaining conversation operations and installed/device qualification.

## September 30 Codex consented desktop checkpoint

[Desktop evidence](CODEX-INTEGRATION.md#consented-desktop-tools-and-plasma-vm-evidence)
records the shared desktop tool bridge, durable consent/call admission, fresh
observation tokens, sharing cleanup and crash recovery. The actual native adapter
and pinned Codex pass a real isolated Plasma Wayland task: declined consent, screen
pixels, exact Kate saved-file contents and Stop during partial typing with no
replay. This uses staged source and a deterministic provider, not the owner's
installed app or a live-model vision test. Build/type checks, 265 Node tests and
16 focused Python cases pass. Continue the complete plan: Mac/device and actual
Qt UI qualification, OAuth, Home/MCP, prompt improvement, memory, speech, remaining
conversation operations and native binary distribution gates remain open.

## September 30 Codex image qualification checkpoint

The [image checkpoint](CODEX-INTEGRATION.md#image-qualification-and-actual-browser-screenshot-transport)
adds explicit synthetic-image checks in both setup forms and conditionally enables
browser screenshots in new Codex chats. The loaded Chromium proof found and fixed
the toolbar/activeTab permission mismatch and now verifies actual JPEG transport
through pinned Codex, alongside DOM actions and rendered replies. Type checking,
build, 256 root Node tests, 48 Browser DOM tests and three native setup cases pass.
The model remains synthetic; this does not qualify live vision, OAuth or installed
artifacts. Continue the full C0–C9 plan: desktop tools, prompt improvement, memory,
voice, account eligibility/login and packaging are not finished. Previous macOS
CI passed; Debian still blocks the unreviewed Codex native executable inventory.

## September 30 Codex runtime foundation

[Implementation evidence](CODEX-INTEGRATION.md) records the pinned 0.159.2
app-server transport, durable submission ledger, session driver, shared host and
private IPC. The real Linux binary passes streaming/tool/Stop/reopen and host
restart against a synthetic Responses endpoint; 21 focused tests pass. The real
local Qwen endpoint rejects the Responses instruction layout, and the pinned
runtime no longer supports Chat Completions. See the evidence guide for the CI
sandbox fixture and license corrections. This is partial C0/C1 work. Continue the full
[build plan](CODEX-INTEGRATION-PLAN.md): service supervision, profiles, both actual
surfaces, login, tools, memory, voice and release qualification remain. Codex is
not yet selectable and no installed application was changed.

The next source checkpoint adds API/local profile records, OS credential-store
plumbing, standalone host startup/crash recovery and a thin native adapter.
Focused coverage is now 27 tests, the root Node suite passes 220, and the isolated
native suite runs 551 with two skips. The real native adapter passes against the
shared host and synthetic model, but actual Qt setup/send qualification remains.
Secret Service is unavailable/locked on the development host, so its positive
store proof remains pending. At `3ff5c5d`, Mac 14/26 bundle workflows pass and
Debian packaging refuses the unreviewed Codex native executable; complete the
native dependency inventory rather than bypassing that release gate.

The following setup checkpoint makes Codex selectable in development source and
adds API/local profile forms to native and Browser settings. Both forms share the
same host and credential-store boundary, with explicit text-only provider checks.
The actual Chromium native-messaging bridge passes the pinned-runtime fixture
without a Desktop window. Root Node tests pass 225 and Browser DOM tests pass 45;
the native suite runs 554 with two skips, including three new Qt setup cases.
See the implementation evidence for the validation
limits. Continue C3 real UI/tool/approval qualification and C4–C9; source selectors
do not establish a finished integration or installed release.

The approval checkpoint adds a shared one-presenter broker for Codex command and
file-change approvals, with fresh reply capabilities on presenter transfer and no
persistent grants. Both real client bridges now deny a synthetic escalated command
through pinned Codex, which receives the denial and continues. Broker/socket tests
cover stale replies, disconnect and expiry. Structured questions, scoped dynamic
tools and actual approval-dialog qualification remain unfinished. Browser now adds
a per-document live-connection claim behind its shared host subscription; a second
panel cannot claim the same prompt. Browser DOM coverage passes 46 tests. See the updated
[implementation evidence](CODEX-INTEGRATION.md#one-presenter-approval-broker).

Structured questions now round-trip through both real client bridges and pinned
Codex with its default-mode question flag explicitly enabled. The shared broker
preserves IDs, rejects incomplete answers and returns no invented answer on cancel.
Browser uses a cancellable form; native reuses its existing dialog. Secret questions
remain unsupported. Root Node tests pass 234, focused Codex 41, Browser DOM 48 and
eight offscreen native interaction cases. Debian CI still stops at the unreviewed
Codex native executable inventory. Continue the full plan, including tool scoping,
OAuth, memory, voice and artifact qualification.

[Packaging inventory](CODEX-PACKAGING.md) now pins the complete observed Linux
Codex native payload and source inputs. The collector verifies 1,304 locked source
archives without rewriting Cargo resolution. The corrected nested-license scan
leaves 138 missing-notice sources. Another 53 exact-commit archives supply candidate
notices for 116 of those; 22 lack a retrieved candidate. Applicability and native
binary coverage remain explicit review work. The existing Debian gate is not bypassed. Continue its source
coverage work and the remaining runtime/product phases independently.

New Codex chats now bind the maintained shared persona through developer
instructions, preserving Codex's base instructions. The host snapshots and hashes
that guidance per conversation and reuses it on resume; existing chats without a
snapshot are not silently migrated. The real runtime fixture verifies exactly one
persona on initial and resumed inference. Scoped tools and prompt improvement are
still separate C5 work.

The maintenance checkpoint freezes Codex admission when shutdown readiness is
confirmed, including pending profile/thread work and saved unresolved operations.
It also suspends scheduled queue pumps; cancellation restores normal processing.
Five focused maintenance cases and the standalone socket proof cover these races.
The root Node suite passed 239 tests before the fifth focused case was added.
Installer orchestration and installed upgrade/rollback remain outstanding.

Subsequent CI exposed an upstream Git helper surviving its Codex parent and racing
fixture cleanup on Linux/macOS. Workers now own a POSIX process group and stop its
remaining members on close or wrapper failure. All 242 root Node tests pass locally,
including real Codex and two TERM-resistant descendant cases. Follow the next CI
run for macOS evidence; this does not resolve the native packaging inventory gate.

Linux maintenance now discovers and prepares Codex before closing surfaces, then
stops it through the private socket. A later refusal cancels preparation, and local
backups include Codex state without sockets. The actual isolated host exits through
this script; five Python cases and 244 root Node tests pass. See the implementation
guide for the remaining installed-upgrade and macOS coordination evidence gaps.

New Codex chats now expose scoped Browser tab/navigation/snapshot/click/type tools
through the pinned experimental dynamic-tool protocol. Calls are durable before
dispatch, executor replies are socket-owned, and writes require observed selectors
bound to the same tab/document. A real loaded Linux Chromium extension completes
an isolated snapshot/type/snapshot/click task and renders the reply through native
messaging and Codex with a synthetic model. All 252 root Node and 48 Browser DOM
tests pass. Screenshots/model image qualification, native GUI tools, memory, voice,
OAuth and installed release acceptance remain unfinished. See the current
[Browser evidence](CODEX-INTEGRATION.md#scoped-browser-tools-and-loaded-chromium-evidence).

## October 1 browser observation repair

[Browser observation repair](BROWSER-OBSERVATION-REPAIR.md) corrects early pruning
of unread browser results, adds direct original-result recovery and paged DOM
reads, and keeps explicit observations from replacing the action target. Shared
DSH/Pi and Chromium checks pass; installation evidence is recorded in that guide.
Compatible Linux release `20261001-161942-544b2e90` is selected, both shared
personal adapters are active, and the restricted real local model correctly reads
the saved Amazon product price. Chromium extension Reload and fresh live-site
acceptance remain pending; existing native windows retain their earlier build.
[PR #26](https://github.com/ManoloRemiddi/augmentor-agent/pull/26) includes the #21 dependency and current main.
[Matched 0.2.13 public previews](RELEASE-0.2.13.md) are published with verified
anonymous Linux/Mac downloads. The live website serves the matching downloads
and prompt; package checksums, Pages deployment and source tests are verified.
Preserve the selected compatible application/SDK build when staging this repair.

## September 28 task reliability correction

[Task reliability](TASK-RELIABILITY.md) owns binary tool-evidence protection,
changed-command error checkpoints, bounded recovery reassessment and restored
effective-reasoning visibility. Model/GPU settings are preserved. Read the guide
for fixture versus real-model evidence and installed adoption boundaries.
Implementation through `70c5c79` is selected and running in all three Linux windows
as `20260928-093018-2d4431f6`. Both shared DSH presets use the updated adapters;
model settings and saved conversation selections were preserved. At that September 28 checkpoint, PR #21 was draft and Mac/public downloads
were unchanged. PR #21 is now merged and included in the 0.2.13 previews above. After two unsuccessful full-preset checks,
the final read-only retest identified the correct control in 79 seconds / six calls.
Physical standby/wake remains untested; xhigh reasoning and task latency remain.
## September 30 application SDK foundation

[SDK foundation](APP-SDK.md) owns the DSH-only application contract, exact tool
grants, recoverable profile installation and experimental workspace voice toggle.
The SDK is a separate private repository; product changes belong here. Preserve
the owner’s independent third-app test. Source qualification is recorded there;
source success does not imply activation of any existing application.

See [embedded Browser and specialist workspaces](WORKSPACE-EMBEDDING.md) for product-owned embedding, scoped tools and memory.

## September 30 Codex integration build plan

The owner selected Codex-backed Desktop and Browser integration with subscription,
API-provider and local-model connection options. [The build plan](CODEX-INTEGRATION-PLAN.md)
records the shared host/adapter design, existing DSH coupling, authentication and
commercial eligibility gates, ten ordered work packages, acceptance matrix and
release/rollback requirements. Begin implementation at C0 against current main.
This is a documentation-only plan based on `b8e36a4`; no Codex runtime, login,
provider, memory, speech or installed-app behavior has been implemented or tested
by this planning change. Existing DSH/Pi defaults and installations remain intact.

## September 27 installed Chromium browser choice

[Browser choice qualification](MACOS-BROWSER-CHOICE.md) records the generic Mac
app chooser and Comet compatibility fix. The clean `3627dae` package passes actual
Comet/Chrome native-host chat, 130 Mac tests, Mac 14/26 and DMG launch/integrity
checks. Full Linux/Home/Browser/installed lifecycle and Mac 14/26 CI passed at
reviewed head `114a879`; PR #17 is merged as `9451682`. [Mac preview 3](MACOS-PREVIEW-3-RELEASE.md)
is published and the complete anonymous DMG download matches its checksum.
The website serves the new download and Comet/browser-choice guide. Owner
activation remains pending: the open dialog must close before safe maintenance,
and remote Accessibility control is denied. Preserve the working installed
`b8dac9d` app; do not confuse the published release with the running installation.

## September 27 Mac preview 2 publication — historical

The owner accepted the installed fix and requested public release. PR #16 is
merged at `482a63a`; the release carries the exact accepted `b8dac9d` app, not a
new runtime build. Read [Mac preview 2](MACOS-PREVIEW-2-RELEASE.md) for the DMG,
source provenance, release verification and fresh-install qualification. Keep
public preview limits visible. Linux downloads and the owner's installed Mac
are unchanged by publication. Historical checkpoints below retain earlier scope.

## September 27 live zoom correction

The owner accepts the flare fix. The earlier size slider only affected startup;
the shared replacement resizes the existing interface immediately and preserves
active work. Read [live zoom qualification](MACOS-LIVE-ZOOM-2026-09-27.md) for current
source, package and deployment evidence. The sealed `b8dac9d` artifact is now
installed on the 32 GB Mac, retaining the owner's 120% setting. Native pointer
drags and zoom during a real reply pass; model settings and conversations remain
intact. The older startup-only record below is
historical; do not reinstate its restart instruction.

## September 27 transparency and app size — historical checkpoint

The owner's remaining outline report is tracked in [the appearance correction](MACOS-APPEARANCE-2026-09-27.md).
The transparent effect window had an AppKit shadow; its shadow is now disabled.
The earlier performance fixture did not reliably trigger a flare and is corrected.
The shared Appearance slider adds uniform 75–150% sizing on the next window process
start, without interrupting active work. Read the record for qualification and
the actual installed build; do not treat source tests as an installed update.
The clean `7ff6712` artifact is now installed and live-chat tested on the 32 GB
Mac at 110%. One app/registration/Dock tile remains. Mac 14/26 validation passed;
a Linux maintenance exit race caught by package CI is corrected separately.
At `fa77135`, both complete workflows passed, including installed Linux lifecycle
checks and Mac 14/26. The installed Mac artifact remains the sealed `7ff6712` build.

## September 26 continued Mac recovery

The [recovery record](MACOS-RECOVERY-2026-09-26.md) supersedes the source gap status
below: guided setup/resize and shared rendering are integrated, the Mac second
shortcut is implemented, and Metal/OpenGL fixtures pass. Installed state:
the clean `c3a7fab` artifact is now installed and live-tested on the 32 GB Mac.
One canonical application/registration and one Dock tile remain; legacy previews
and helpers are retired. The record owns exact hashes, real/native versus fixture
evidence, the browser CI race correction and remaining publication boundaries.
Preserve the approved UI and private data; do not resume the old overlay workflow.

## September 26 shared flare rendering correction

[Flare fidelity](FLARE-FIDELITY.md) records the coarse-texture root cause and the
shared detailed-emission/bounded-fluid correction. Both platforms use the same
renderer; no UI layout changed. The 32 GB Mac now runs the verified replacement;
Linux has it selected while earlier open windows retain their builds. Read the
guide for exact identities, captures, CI and activation evidence. The earlier one-product audit
remains an analysis of the still-pending shortcut and release convergence gaps.

## September 26 one-product architecture direction and parity audit

The owner requires one Augmentor product across OSs, with common features and UI
behavior and platform adapters underneath. The [audit](PLATFORM-PARITY-AUDIT.md)
identifies the Mac second-shortcut gap in UI, storage, service protocol and
activation; the three shared instance tests pass on Linux and installed Mac
modules. It also records release drift between open embedding PR #12 and Mac
correction PR #13, and Mac CI's omission of several shared suites. Engineering
rules and the PR review template now require both-platform impact assessment.
The document includes the correction sequence and acceptance criteria. This is
an analysis/documentation change: no shortcut implementation, branch integration,
CI expansion, active-app restart or deployment was performed. Mac installed
application source remains `252215b` from PR #13; older entries below are dated
checkpoints. Begin implementation with the shared instance/shortcut contract.

## September 26 owner-requested Mac menu placement and resizing

Preserve the owner's approved UI: additional visible changes require permission.
Current source removes the recent DSH main-window row; Agent setup/Open DSH stay
in the three-dot menu. Cocoa rejected the native resize request, which the old
code ignored. The existing eight handles now have a logical-coordinate fallback
while supported Linux compositor resizing is retained. Five resize regressions,
117 Mac tests, 27 window tests, and eight synthetic pointer drags on the real
32 GB Mac's Cocoa window passed. See [resize behavior and installed scope](WINDOW-RESIZING.md).
The owner explicitly requested installation after the draft-preservation warning.
The sealed `252215b` candidate is now installed on the 32 GB Mac and reopened
normally, online/model-ready without connection or restoration errors. The owned
shortcut had relaunched the old window during the first attempt; pausing it via
its registrar and durable resume intent allowed safe activation. DSH settings,
connection and session metadata matched before/after. Both login services are
restored, installed integrity and overlay hashes passed, and the previous bundle
is retained as a backup. Mac 14/26 and full validation passed at documentation ref
`166e1ae`; see the resize guide for exact artifact and test scope. Public downloads,
Linux, the NAS and the other Mac were not updated.

## September 26 runtime-first Mac setup — earlier installed checkpoint

The owner reported the earlier installed form remained unusable. Fresh diagnosis
confirmed DSH was bundled but still unprovisioned, and the browser menu omitted
DSH authentication. Current source separates engine installation from model setup,
adds persistent Agent setup/Open DSH buttons, and uses DSH's native provider UI.
The owner requested activation: application code `60413de` is now installed,
DSH is provisioned and online, both login services are loaded, and the default
browser accepted the authenticated DSH opening. Integrity and installed file
hashes passed. No model is configured yet; live owner-model chat remains
unqualified. Both clean-build workflows passed at documentation ref `33b58ff`.
Read [qualification, the drained idle runtime, and installed scope](MACOS-GUIDED-DSH-SETUP.md).
The public preview DMG is unchanged.

## September 26 guided Mac DSH installation

The 32 GB Mac's public preview contains DSH but had no saved connection. The
native first run now offers **Install DSH** before connection recovery, streams
the managed installer's five stages, and retains failed settings for retry.
An incomplete bundle is diagnosed before offering an existing-DSH form.
See [the scoped evidence and deployment record](MACOS-GUIDED-DSH-SETUP.md).
The qualified candidate is now installed and reopened on the 32 GB Mac after
the owner closed its earlier window. Integrity, the native process and shortcut
service were checked; model setup remains unfinished. Both full validation and
the Mac 14/26 workflow passed at `6bead5a`. The published preview DMG is unchanged.
## September 27 tool context correction

[Tool context budget](CONTEXT-BUDGET.md) separates per-result trimming from the
model-relative compaction trigger. Both personal presets compose the existing
DSH pruner at step boundaries, retain original evidence with bounded excerpts,
and expose `/trim-tools` for idle conversations without inference. Repeated
identical outputs produce one reassessment checkpoint. Consult its qualification
and installed evidence before assuming a running host has adopted this change.

## September 26 public Apple-independent macOS preview

The owner approved publishing a clearly labelled macOS preview without Developer
ID or notarization after Apple enrollment failed; do not ask again for that
choice. [Release v0.2.12-macos-preview.1](https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.12-macos-preview.1)
is public for Apple silicon, macOS 14+. [The preview record](MACOS-PREVIEW-RELEASE.md)
owns exact binary provenance, checksums, source archives, test scope and limits.
PR #10 is merged; the binary was built from `ea128d6`, before documentation-only
publication records. Final-source Mac 14/26 and full Linux/Home/Browser/lifecycle
CI passed. Real native Send/reopen, Chrome native-host chat, managed DSH/plugin
setup and DMG copy/launch/seal checks passed on the 16 GB Mac with a deterministic
model. The earlier Qt library-replacement proof is identified separately.

[augmentoragent.com](https://augmentoragent.com/#installation) and its
[Mac guide](https://augmentoragent.com/macos.html) are deployed and verified.
The complete anonymous DMG download matched its published SHA-256; live platform
links, guide navigation and the Linux copy-button success state were checked.
The working personal Mac application and private models remain unchanged; temporary
proof apps and their registrations were removed. The normal user Open Anyway
dialog, manual browser folder chooser, physical speech and full privacy-permission
flows remain unqualified. Automatic updates and complete removal are not available
in this preview. The following dated checkpoints retain earlier evidence and are
superseded by this publication record where their status differs.

## September 26 public Mac download audit and signing preparation — historical

The owner requested a macOS download on augmentoragent.com. The fresh audit
found that the working personal install remains an ad-hoc development build;
Gatekeeper rejects it and clean-user DSH provisioning is not implemented. The
authenticated Apple account shows enrollment rather than certificate access.
See [the release operator guide](MACOS-RELEASE.md) for the candidate-signing
tool, actual tests, Apple prerequisite and remaining product/release gates.
The corrected recovery proof (`a4317cd`) passes the complete GitHub workflows.
No Mac binary was published, no website download changed and the working Mac
installation was not modified by this audit. Never package the owner's private
model profile as a public-install shortcut.

Follow-up source work adds [managed Mac runtime/model setup](MACOS-MANAGED-SETUP.md).
It passed real isolated launchd/DSH chat, service restart and conversation
restoration with a fixture provider, plus private-state and Qt form tests.
This supersedes the basic provisioning implementation gap above; full plugin,
signed installed, licensing, browser and update gates remain. The source feature
has not replaced the owner's working app, and no public Mac download is live.

At `4fdd8a4`, full validation and the managed first-run Mac 14/26 matrix passed.
The preceding Mac 26 run had an unexplained startup timeout; a passing rerun
does not establish its cause. The follow-up source corrects the service's
launchd scheduling class for interactive chat, adds private startup timings,
and retains failing fixture reports. See the managed-setup evidence before
calling this intermittent issue resolved. Apple enrollment remains pending.

The scheduling/timing correction at `81f3726` passed its own Mac 14/26 build,
managed chat/restart/history and post-use signature checks. The 16 GB working
installation remains unmodified and online/model-ready, with strict signature
verification passing. Five completed synthetic proof profiles were removed after
verifying their exact login jobs and shared socket peers were stopped; reports
remain in the non-indexed staging cache. The release guide now identifies the
published, checksummed extra-plugin artifacts and their missing dependency graph;
do not assume their exact package versions are available from npm.
Full Linux, installed-package lifecycle, Browser and Home validation also passed
at `81f3726`. Later documentation-only commits do not change those tested bytes.

## September 26 clean Mac installation and default shortcut

The duplicate development apps were removed and their application registrations
cleared. The canonical installation is now `/Applications/Augmentor Agent Desktop.app`
with one repaired Dock tile and a native icon. Its DSH runtime and owned integration
references follow that location; private model settings and conversations are retained.
Fn+Space is the default persistent shortcut, and clicking the icon opens rather
than toggles the window. See [clean installation evidence and remaining boundaries](MACOS-DISTRIBUTION.md#september-26-clean-installation-and-default-shortcut).
The old suspended qualification process no longer exists. Do not resurrect the
historical paused-process workaround described below. Public distribution still
requires the release gates, including signing/notarization.

## September 26 corrected Mac primary app activated — historical location

Autonomous activation is complete for desktop chat. The installed user
Applications copy passed Send-button and Enter requests in the **actual native
primary process**, including same-conversation restoration after reopening. It
was then reopened normally with test control disabled and left online/model-ready.
The desktop shortcut points to this copy. See
[installed native evidence and recovery details](MACOS-DISTRIBUTION.md#september-26-follow-up-corrected-primary-mac-app-activated).
The obsolete qualification window is hidden and paused to retain any draft in
memory; its private checkpoint records the displaced socket/lock. Do not resume
it alongside the replacement. That volatile preservation is not a durable draft
backup. Configuration and DSH data have separate private backups.
The earlier activation-pending report below is superseded. Public distribution,
voice and browser-extension qualification remain incomplete.

## September 26 desktop readiness correction — historical activation-pending checkpoint

The owner reported that the Mac still could not chat. The failure was reproduced:
an already-open pre-setup controller retained the missing legacy preset while
reporting online. The desktop adapter now verifies its preset before readiness.
The corrected packaged Qt window passed actual composer/Send and Enter tests
against DeepSeek, including same-conversation restoration after reopening;
445 native tests (one skip) and the full packaged DSH/Qt fixture passed.
See [the correction and activation boundary](MACOS-DISTRIBUTION.md#september-26-correction-verify-chat-readiness-and-the-actual-composer).
The corrected candidate is staged. The owner's old window still has a dialog
open; preserve its draft and finish activation after it closes. Do not repeat
the earlier claim that an online status alone proves desktop chat works.

## September 26 personal Mac model access

The owner requested their MX model access on the test Mac. The existing
`c03c32e` development bundle now has a private per-user DSH profile, matching
Augmentor integration, Model Picker 1.1.2 and launchd-managed runtime/model tunnel.
Exact catalog comparison passed (365 models, seven providers), a real DeepSeek
Flash reply succeeded, and the open desktop reported online/model-ready. The
secondary GPU endpoint is offline on the workstation too; no GPU settings changed.
See [Mac connection evidence](MACOS-DISTRIBUTION.md#september-26-personal-mac-model-connection)
for deployment boundaries. Keep personal credentials/configuration out of GitHub.
This does not complete the public installer, signing, voice or browser rollout.

## September 25 macOS distribution implementation

The owner authorized implementation and isolated network-Mac testing. See
[macOS distribution](MACOS-DISTRIBUTION.md) for the native launcher, complete
prepared DSH payload, hashed Python wheels, build/test workflow and exact evidence.
Native launcher and real packaged DSH/Qt proofs pass on ARM64 macOS 26.5.1.
This is development qualification; managed first-run, required plugin provisioning,
store migration, coordinated updating, production signing and permission acceptance
remain open. The build Mac has no valid Developer ID signing identity.
Linux installed selections, live model/speech settings and Mac registrations were
not changed. Do not present this source branch as a published Mac release.

## September 25 source integration

The user requested merging the composer correction and other ready changes.
The integration combines Home/tray PR #6, shared Desktop/Browser/voice PR #7,
and composer PR #9, preserving their original commits. The host idle-baseline
reservation and Browser prompt-improvement send guard both survive conflict
resolution. The full sidebar entrypoint now verifies immediate transfer, duplicate
Enter suppression and preservation of a newer draft.

Combined source checks pass: TypeScript check/build, 194 Node, 44 Browser,
29 Home and 427 native tests (one native environment skip). GitHub package checks
remain the final merge gate. Installed selections and running windows are unchanged
by source integration; public download bytes require a separate release. Home's
remaining qualification work stays documented in [Home](HOME.md).

## September 25 composer submission correction

[Immediate composer feedback](COMPOSER-SEND-FEEDBACK.md) records the Desktop
idle-baseline race and Browser acknowledgment delay. Send failures now own draft
restoration; status notifications do not. Consult that guide for tests and installed
adoption rather than assuming a source update has reloaded open windows.

## September 24 Home tray launcher

The owner confirmed the installed launcher works and requested click-to-open,
click-again-to-close. The KDE adapter now resolves the actual Chromium dashboard
window on each click; explicit Open raises it. Release `20260924-205229-78c3c113`
is selected and its tray is running. Actual tray activation passed open/close/open
with one Home window and unrelated window IDs preserved. See the launcher guide
for platform limits and evidence. This supersedes the initial selection below.

[Home launcher](HOME-LAUNCHER.md) implements a lightweight Qt tray process for
opening an existing NAS dashboard through the installed browser. It remembers
only the dashboard address, requires no copied API key and starts no model/agent.
A stable entrypoint follows desktop.json; install after managed artifact promotion.
Native tests and a two-process singleton check pass. Managed release
`20260924-202032-d5e07a94` is selected; its Home tray is installed and running,
with live KDE registration and dashboard app-window evidence. Main/mobile and
secondary retain their earlier running builds; their drafts/work were preserved.
See [installation evidence](HOME-LAUNCHER.md#installed-linux-evidence--24-september-2026).

## September 24 sidebar animation and product name

The Browser prompt-improvement preview now rolls letters and settles before
committing, with cancellation and late-response guards. Chromium display metadata
uses **Augmentor Agent**. See the [latest shared-surface entry](SHARED-SURFACES-2026-09-24.md#restore-sidebar-improvement-animation-and-product-name)
for validation and installed adoption; the prepared extension requires Reload.

## September 24 sidebar presentation refinement

The user confirmed the corrected sidebar is working and requested a simpler
Browser presentation: always follow tabs, remove Follow and circular activity
controls/functionality, remove the outer border and brand label, and keep the
empty composer one line tall. Conversation title and shared control order remain.
See [shared surfaces qualification](SHARED-SURFACES-2026-09-24.md#sidebar-refinement-after-user-acceptance)
for source checks and local adoption. Chromium needs Reload after updating the
prepared extension folder; do not remove/reinstall it or interrupt native drafts.

## September 24 shared personal agent and voice

The user requests one personal agent in the floating window and browser sidebar.
[Shared surfaces](SHARED-SURFACES-2026-09-24.md) owns the new shared preset, host
voice engine, approval bridge and stopped-task status correction. Earlier
browser-only tool-policy statements are superseded for DSH personal sessions.
Read its deployment evidence before assuming a running extension has reloaded.
Combined Home/shared source `d24e2ff` runs in the secondary
window. Primary/mobile adoption and Chromium reload remain pending; preserve the
primary draft. This is a compatible development artifact, not a public release.

## September 24 Home runtime preview

[Home](HOME.md) now has a headless DSH host in `apps/home` and a constrained
Assist MCP policy in `adapters/dsh-home`. Canonical application code stays here;
private household deployment and operational records belong in the Home companion.
The user clarified that Home must be a lightweight NAS-owned capability available
inside existing Augmentor clients, with independent household hardware/models/API
configuration. A shared client adapter, pairing/settings and lightweight NAS page are implemented.
NAS runtime source e5e5764 is promoted with direct On/Off device cards and an
owner-only discovery snapshot, building on selected-device policy, model settings,
cancellation propagation and clean shutdown. The KP303 uses HA’s existing TP-Link
integration; its three lighting outlets and the Elgato light have controls enabled.
Four unlinked Tapo devices remain listed with setup status. See Home for evidence.
Earlier Desktop deployment was coordinated with the shared-surfaces task: combined
source d24e2ff / release 20260924-125950-12694ac7 was selected and secondary adopted it.
At that checkpoint main/mobile retained the preceding Home-enabled release to
preserve a draft. The later flare selection below supersedes that selected identity;
consult current installed status before any changes. Preserve drafts and active work.
The prepared Browser extension combines Home and Voice; reload/adoption is separate.
Home PR #6 remains unmerged. Source synchronization with public main does not
redeploy Desktop or alter the separately coordinated shared-surfaces PR #7.
Full resource/release qualification is pending. A finite NAS availability pilot is
running; it is not a completed seven-day workload/physical-device qualification.
New configuration defaults to owner-selected registered entities; the earlier
Assist MCP mode remains an explicit compatibility preview. Read the guide for
exact fixture/live evidence and limits before expanding device access.

exact fixture/live evidence and limits before expanding device
access. This preview does not change the installed Desktop or Browser release.

## September 24 desktop flare ownership

The [0.2.12 release record](RELEASE-0.2.12.md) tracks the managed transient
activity canvas correction, workspace/stacking proof and public download status.
PR #8 is merged and 0.2.12 is published. Website downloads select the new bundle.
Home/shared-surface previews remain separate; this release is based on public main.
The compatible local flare patch is selected in `20260924-140435-fa4c42f4`;
open windows still need reopening. Preserve unsent drafts and active work.

## September 24 WebSocket security release

See [the ws security correction](WS-SECURITY-2026-09-24.md) for the `ws 8.21.3`
pins, Pi shrinkwrap/bundled-CLI exclusions, regression evidence and publication
boundary. The build/test/start preparation step is required after installing
with lifecycle scripts disabled. The [0.2.11 release record](RELEASE-0.2.11.md) tracks final qualification,
publication and installed selection separately from the original source candidate.
PR #5 is merged; 0.2.11 is live on GitHub and npm. Desktop and mobile are running
the recorded user-local artifact, online with voice available. Chromium extension
loading remains a separate user action; see the release record before claiming
Browser activation.

## September 23 canonical repository and license

Current development is [ManoloRemiddi/augmentor-agent](https://github.com/ManoloRemiddi/augmentor-agent),
branch `main`, for both Desktop and Browser. The clean public repository was
renamed from `augmentor-agent-source`; its public history is retained.
The old private repository is now `augmentor-agent-history` and is an archive.
Read [repository roles and preserved work](REPOSITORIES.md) before resuming old tasks.

Augmentor-authored code carries [MIT with Augmentor Resale Restriction](../LICENSE).
Personal/business use and modification remain free; resale needs Manolo Remiddi's
written permission. See [publication scope](PUBLIC-SOURCE.md).
Earlier binary releases retain their shipped licenses. Source or documentation
publication does not redeploy the installed application.

## September 22 native opening-notice visibility

Source `ee5d8f1` hides only the exact successful minimal-to-xhigh request-policy
notice from native live/history transcripts. Other DSH messages and underlying
events remain intact. See [visibility contract](BOUNDED-EXECUTION-RECOVERY.md#settings-and-progress)
and [selected versus running deployment](DESKTOP-DEPLOYMENTS.md#september-22-hide-the-routine-opening-reasoning-notice).
The tested compatible artifact is selected; existing windows still need reopening.

## 0.2.10 action-aware recovery and complete distribution

Recovery now consumes structured tool outcomes and blocks exact duplicate changes,
tracks existing jobs, permits inspection and respects concluding handoffs even after
truncation. See [contract and limits](BOUNDED-EXECUTION-RECOVERY.md#action-aware-recovery--0210-preview)
and [complete installation](COMPLETE-INSTALL.md). This is generic lifecycle policy;
it does not certify answer correctness or add a cross-session transaction ledger.
The complete bundle includes the adapter and all required plugins. Public download
and candidate-specific acceptance are recorded in the [qualification ledger](RELEASE-QUALIFICATION-0.2.10.md). Product artifact source is `ad4bc7d`; subsequent test-driver/documentation changes do not alter that immutable artifact.

## September 21 general response validity

The execution adapter now handles reasoning-only/blank terminal responses using
the same bounded budget as truncation. It emits a durable incomplete outcome on
exhaustion, preserves valid answers/tool handoffs and does not certify task success.
Read [the contract, qualification and remaining scope](BOUNDED-EXECUTION-RECOVERY.md#general-response-validity-correction--september-21).
No task-specific rules, memory replacement or generic artifact verifier were added.

## September 21 bounded execution recovery

Read [bounded recovery](BOUNDED-EXECUTION-RECOVERY.md) for same-turn truncation
recovery, limits, effective-setting visibility and real-DSH regression coverage.
It is DSH-only and does not automatically certify task completion. Consult its
deployment and retest evidence before assuming installed behavior.


## September 21 controlled memory correction

The previous unattended-memory lifecycle is superseded. Read
[controlled memory](CONTROLLED-MEMORY.md), [dual memory](DUAL-MEMORY.md) and
[operations](MEMORY-OPERATIONS.md) before touching its worker or queue. Capture,
context selection and inference admission are separate. The original model and
speech placement/settings remain unchanged. Source qualification includes real
DSH/Pi fixtures, native regression, real-model memory completion, streaming
cancellation and failed-page preservation. Source `edf7d76` is installed in compatible release
`20260921-011742-0b89b31a`; all three native windows have loaded it.
Installed selection is tracked in
[desktop deployments](DESKTOP-DEPLOYMENTS.md); source tests alone do not establish
which running window has adopted an update.

## September 20 voice latency update

The native voice path now uses a bounded startup/recovery playback reserve and
exposes stage timings without logging audio or text. Resonant Voice 0.1.16 adds
incremental CPU ASR during capture; complete-install component pins are updated.
See [native voice behavior and evidence](VOICE-SINGLE-BUTTON.md#incremental-recognition-and-buffered-playback--20-september-2026)
and [deployment selection](DESKTOP-DEPLOYMENTS.md). Full native regression: 395
passing tests. Recognition and playback fixes do not remove model prompt-processing
or reasoning time; no GPU/context/reasoning policy was reduced. The 0.2.8-compatible
native artifact is now running in the desktop, secondary and mobile windows
after the user-requested graceful restart. All three are online, with their
previous conversation/model preserved and `updatePending: false`. The 0.1.16
speech companion remains running.

## Complete installation and public distribution

See the [September 20 distribution audit](DISTRIBUTION-AUDIT-2026-09-20.md) and
[complete installer](COMPLETE-INSTALL.md) for current source/installed differences,
public-bundle contents, fresh-user setup and the next macOS phase.

## September 20 consistent desktop updates

The user subsequently performed a physical reboot and reported that everything
worked. Future desktop changes must use [desktop deployments](DESKTOP-DEPLOYMENTS.md).
Login, menu, shortcuts, recovery and mobile share `desktop.json`; `augmentor-update`
stages separate artifacts, validates promotion, records identity and retains the
previous selection. Do not revive the old preview-folder deployment workflow.

## September 20 startup correction

Startup/recovery implementation: `2dca65f`; Adaptive Reasoning correction:
`15d9981` / package 0.2.2. Read [restart reliability](RESTART-RELIABILITY-2026-09-20.md) before changing
launchers or investigating another offline desktop. It records two independent
root causes, the corrected adaptive plugin, the installed service/deployment
contract, preserved histories and actual cold-start/crash/recovery evidence.
Do not restore the old hard-coded login launcher or move diagnostic events back
into conversation logs. The September 19 qualification below remains historical.

## Source of truth and retrieval

GitHub is the durable source of truth for source, decisions, run instructions,
contracts and evidence summaries. Local conversations, ignored `outputs/` and
an individual machine's installed state are not a substitute for this record.
Never publish private transcripts, credentials, tokens, model weights or user
configuration to satisfy documentation completeness.

### Historical September 19 qualification (superseded repository location)

The following records the old private development state, not today’s checkout instructions:

- Historical private repository: [augmentor-agent-history](https://github.com/ManoloRemiddi/augmentor-agent-history).
- Historical development: branch `productization/shared-memory-and-desktop`,
  [draft PR #3](https://github.com/ManoloRemiddi/augmentor-agent-history/pull/3).
  Its source was exported into the clean public repository; use public `main` now.
- Last fully qualified implementation: commit
  [`29231fdf367fdade2aee74530785d29af2bee95e`](https://github.com/ManoloRemiddi/augmentor-agent-history/commit/29231fdf367fdade2aee74530785d29af2bee95e).
  Subsequent documentation commits do not expand its runtime evidence.
- Subsequent native voice correction: [buffered activation, echo guard and drag feedback](HANDS-FREE-IMPLEMENTATION.md#buffered-activation-and-playback-echo-protection--19-september-2026),
  based on `cc8845c`. Its own validation/deployment scope is recorded separately
  from the fully qualified product snapshot above.
- Speech repository: [resonant-voice](https://github.com/ManoloRemiddi/resonant-voice),
  `main`, package 0.1.14. Both repositories require the appropriate GitHub access.
- Product manifest: [`release/product.json`](../release/product.json), 0.2.9 preview.
  A version alone is insufficient to identify a development artifact: record its
  commit and artifact hash too.

Read in order: repository [AGENTS.md](../AGENTS.md), [current architecture](ARCHITECTURE.md),
[feature matrix](FEATURE-MATRIX.md), the [documentation index](README.md), then the
subsystem guide for your task. Dated evidence applies only to its stated build.
Historical plans do not override current source/contracts and maintained guides.
If these disagree, inspect the code, report the discrepancy and update the guide
alongside the fix instead of silently treating a plan as implemented behavior.

For a fresh clone:

```sh
git clone https://github.com/ManoloRemiddi/augmentor-agent.git
cd augmentor-agent
git status --short
git log -1 --oneline
```

For an existing working copy, inspect its origin, branch and changes first. Old
private-history checkouts stay pointed at the private archive. Preserve local
changes and port only selected, reviewed changes to a fresh canonical branch;
never merge private history or repoint an old checkout at the public origin.

## Reproduce development checks

Use tested Node 24.19.0. Install Python/Qt dependencies from
[`requirements-dev.txt`](../requirements-dev.txt), using a dedicated environment
or the matching system Qt packages. [`validate.yml`](../.github/workflows/validate.yml)
is the exact clean Debian dependency and test recipe; QtTest is needed for UI tests.

```sh
npm ci --ignore-scripts
python3 scripts/sync-version.py --check
npm run check
npm run build
npm test
npm run test:native
node --test apps/browser/test/*.test.mjs
```

Use the configured Python environment for `npm run test:native`. For locked DSH
qualification, follow `release/dsh/README.md` and the workflow's DSH environment
variables; a missing DSH installation is not a passing integration test.
[Tests](../tests/README.md) maps focused checks to subsystems. Physical desktop,
provider, audio and installed-package checks have separate prerequisites and
must not be confused with fixtures.

## Verified state

[CI run 35441917540](https://github.com/ManoloRemiddi/augmentor-agent-history/actions/runs/35441917540)
passed all three jobs for `29231fd`: Debian/source/native checks; installed
packages; packaged browser. It covered first run, actual pointer/clipboard,
DSH approvals/questions/exact forks, memory lifecycle fixtures, installation,
active-task refusal, interrupted configuration, upgrade, rollback and removal.

A separate real Hindsight 0.10.0 + local Qwen proof generated four synthetic
knowledge pages, recalled relationship preferences and project state after a
bridge restart, and checked person/project isolation. It used voice-labelled
text, not a physical microphone trial. The reproducible entrypoint is
`scripts/hindsight-proof.py`; results and limits are summarized in
[the September ledger](DESKTOP-UPDATE-2026-09-19.md).

Resonant Voice 0.1.14 passed 33 Node and 3 Python ASR tests plus real DSH lifecycle
and tarball install/remove checks with fixture LLM/TTS. Speech licensing and
human listening acceptance remain separate from code/test success.

## Historical September 19 installed preview

The worker/automatic migration described here is superseded by the September 21
controlled implementation above. Do not recreate its unattended queue processing.

The recorded local preview has Hindsight on loopback 8889, a persistent Docker
volume, CPU embeddings/reranking and one background worker. Memory inference uses
the existing local Qwen endpoint without changing the chat model or GPU settings.
The automatic memory adapter was activated from published source after DSH and
voice became idle. Journal migration continues asynchronously.

This is a dated observation, not a guarantee about a future machine. Read
`~/.local/share/augmentor-memory/active.json` locally to locate its actual release
and rollback backup. Use [memory operations](MEMORY-OPERATIONS.md) for checks and
[voice deployment](https://github.com/ManoloRemiddi/resonant-voice/blob/main/docs/DEPLOYMENT.md)
for speech state. Do not copy private local configuration into documentation.
Do not restart active DSH tasks or voice connections to load a change.

## Remaining work and evidence gaps

- Human two-session voice continuity and relationship quality; microphone,
  speaker echo/double-talk, interruption and latency acceptance.
- Longer memory quality/contradiction evaluation. Automatic memory currently has
  no supported per-person/project erase UI or multi-speaker identity recognition.
- Browser source controls require deployment/reload in the target profile;
  source/isolated acceptance is not proof of that profile's installed version.
- Fedora real desktop/browser acceptance, current macOS parity, public release
  and other [distribution gates](CROSS-PLATFORM-RELEASE-STATUS.md).

## Keep GitHub sufficient for the next agent

Every meaningful change should update its owning guide and any affected
architecture, feature matrix, data disclosure, setup, migration or test recipe.
Record what is implemented, what is installed, the exact tested ref, fixture vs
real-service evidence, and remaining work. Link new guides from the index.
Preserve dated evidence rather than relabelling old tests as new qualification.
Publish a reviewed commit and update the PR with scope and validation. A local-only
note or an unpublished branch is not a completed handoff. Merge/release status
must remain explicit; documentation publication does not itself merge a draft PR.
